"""外源文献检索层的行为覆盖：引擎解析、降级、分档、缓存、schema 与 token 预算。"""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import literature_scout as scout  # noqa: E402


def openalex_payload():
    """两条 OpenAlex works：一条正常，一条撤稿，验证撤稿剔除与字段映射。"""
    return {
        "meta": {"count": 2},
        "results": [
            {
                "id": "https://openalex.org/W123",
                "doi": "https://doi.org/10.1000/demo",
                "title": "Domain adaptation for fault diagnosis",
                "publication_year": 2024,
                "cited_by_count": 150,
                "is_retracted": False,
                "open_access": {"oa_status": "gold"},
                "authorships": [{"author": {"display_name": "Alice Chen"}},
                                {"author": {"display_name": "Bob Li"}}],
                "primary_location": {"source": {
                    "display_name": "IEEE Transactions on Industrial Informatics",
                    "host_organization_name": "IEEE"}},
                "abstract_inverted_index": {"fault": [1], "diagnosis": [0]},
            },
            {
                "id": "https://openalex.org/W456",
                "doi": "https://doi.org/10.1000/retracted",
                "title": "Retracted paper",
                "publication_year": 2020,
                "cited_by_count": 900,
                "is_retracted": True,
                "open_access": {"oa_status": "closed"},
                "authorships": [],
                "primary_location": {"source": {}},
                "abstract_inverted_index": None,
            },
        ],
    }


def crossref_payload():
    return {
        "status": "ok",
        "message": {
            "total-results": 1,
            "items": [{
                "DOI": "10.3390/s20010320",
                "title": ["Triplet loss guided adversarial domain adaptation"],
                "container-title": ["Sensors"],
                "issued": {"date-parts": [[2020]]},
                "author": [{"given": "Xiaodong", "family": "Wang"}],
                "is-referenced-by-count": 74,
            }],
        },
    }


ARXIV_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1806.01512v1</id>
    <title>Bearing fault  diagnosis based on
      domain adaptation</title>
    <published>2018-06-05T06:30:19Z</published>
    <author><name>Zhe Tong</name></author>
    <author><name>Wei Li</name></author>
    <summary>Bearing fault diagnosis under varying working conditions.</summary>
    <arxiv:doi xmlns:arxiv="http://arxiv.org/schemas/atom">10.1016/j.ymssp.2018.06.052</arxiv:doi>
  </entry>
</feed>
"""


def json_fetch(payload):
    return lambda url, headers=None: json.dumps(payload).encode("utf-8")


class OpenAlexTest(unittest.TestCase):
    def test_parse_and_retracted_drop(self):
        cards, total = scout.search_openalex("domain adaptation fault diagnosis", 5,
                                             fetch=json_fetch(openalex_payload()))
        self.assertEqual(1, len(cards))
        self.assertEqual(2, total)  # 命中总量取 meta.count（含被剔除的撤稿条目）
        card = cards[0]
        self.assertEqual("https://openalex.org/W123", card["paper_id"])
        # journal 取期刊名 display_name，优先于出版商 host_organization_name（IEEE）
        self.assertEqual("IEEE Transactions on Industrial Informatics", card["journal"])
        self.assertEqual(["Alice Chen", "Bob Li"], card["authors"])
        self.assertEqual(2024, card["year"])
        self.assertEqual(150, card["cited_by"])
        self.assertEqual("gold", card["oa_status"])
        self.assertEqual("Q2", card["tier"])
        # abstract_inverted_index 按位置还原为连续文本
        self.assertEqual("diagnosis fault", card["abstract_snippet"])

    def test_mailto_and_api_key_reach_the_request(self):
        seen = {}

        def fetch(url, headers=None):
            seen["url"] = url
            return json.dumps({"meta": {"count": 0}, "results": []}).encode("utf-8")

        scout.search_openalex("q", 5, api_key="KEY123", mailto="user@example.com", fetch=fetch)
        self.assertIn("mailto=user%40example.com", seen["url"])
        self.assertIn("api_key=KEY123", seen["url"])
        self.assertIn("api.openalex.org/works", seen["url"])

    def test_real_openalex_connectivity(self):
        """真连 OpenAlex 一次；无网络或限流（429）时跳过，不在 CI 卡死。"""
        try:
            cards, _ = scout.search_openalex("domain adaptation fault diagnosis", 1)
        except (scout.ScoutHTTPError, OSError) as exc:
            self.skipTest(f"OpenAlex 不可达: {exc}")
        for card in cards:
            self.assertEqual("openalex", card["source_engine"])


class CrossrefFallbackTest(unittest.TestCase):
    def test_rate_limit_falls_back_to_crossref(self):
        def fetch(url, headers=None):
            if "api.openalex.org" in url:
                raise scout.ScoutHTTPError(429, "HTTP 429")
            return json.dumps(crossref_payload()).encode("utf-8")

        cards, fallback, total = scout.run_scout("domain adaptation", 3, "openalex", fetch=fetch)
        self.assertTrue(fallback)
        self.assertEqual(1, total)  # 降级后命中总量取 Crossref total-results 口径
        self.assertEqual(1, len(cards))
        self.assertEqual("crossref", cards[0]["source_engine"])
        self.assertEqual("Sensors", cards[0]["journal"])
        self.assertEqual(2020, cards[0]["year"])
        self.assertEqual(74, cards[0]["cited_by"])
        self.assertEqual("Q3", cards[0]["tier"])

    def test_other_http_errors_do_not_fall_back(self):
        def fetch(url, headers=None):
            raise scout.ScoutHTTPError(403, "HTTP 403")

        with self.assertRaises(scout.ScoutHTTPError):
            scout.run_scout("q", 3, "openalex", fetch=fetch)


class ArxivTest(unittest.TestCase):
    def test_atom_parse(self):
        cards, total = scout.search_arxiv("domain adaptation", 5,
                                          fetch=lambda url, headers=None: ARXIV_ATOM.encode("utf-8"))
        self.assertEqual(1, len(cards))
        self.assertIsNone(total)  # arXiv API 无命中总量概念
        card = cards[0]
        self.assertEqual("http://arxiv.org/abs/1806.01512v1", card["paper_id"])
        # 标题中的换行与连续空格压成单空格
        self.assertEqual("Bearing fault diagnosis based on domain adaptation", card["title"])
        self.assertEqual(2018, card["year"])
        self.assertEqual(["Zhe Tong", "Wei Li"], card["authors"])
        self.assertEqual("10.1016/j.ymssp.2018.06.052", card["doi"])
        self.assertEqual("arXiv (preprint)", card["journal"])
        self.assertEqual("green", card["oa_status"])
        self.assertEqual("arxiv", card["source_engine"])


class TierTest(unittest.TestCase):
    def test_threshold_boundaries(self):
        cases = {501: "Q1", 500: "Q2", 100: "Q2", 99: "Q3", 10: "Q3",
                 9: "Q4", 0: "Q4", -5: "Q4", "n/a": "Q4", None: "Q4"}
        for cited, expected in cases.items():
            self.assertEqual(expected, scout.classify_tier(cited), msg=f"cited_by={cited!r}")


class CardSchemaTest(unittest.TestCase):
    def test_card_fields_are_exactly_the_contract(self):
        card = scout.build_card("W1", "Title", ["A"], "Journal", 2024, "10.1/x",
                                50, "gold", "openalex", "q", "2026-01-01T00:00:00+00:00",
                                "abstract")
        self.assertEqual(list(scout.CARD_FIELDS), list(card.keys()))

    def test_card_respects_token_budget(self):
        long_text = "word " * 4000  # 约 20000 字符 ≈ 5000 token，必超预算
        card = scout.build_card("W1", long_text, [long_text[:80]] * 5, long_text[:120],
                                2024, "10.1/" + "x" * 100, 50, "gold", "openalex",
                                long_text, "2026-01-01T00:00:00+00:00", long_text)
        self.assertLessEqual(scout.card_tokens(card), scout.CARD_TOKEN_LIMIT)

    def test_unresolvable_card_raises(self):
        # 绕过 build_card 构造裁无可裁的卡片（不可裁字段本身超预算）
        fat = {"paper_id": "W1", "title": "", "authors": ["x" * 2000] * 20,
               "journal": "", "year": None, "doi": "", "cited_by": 0, "oa_status": "",
               "tier": "Q4", "source_engine": "openalex", "query": "",
               "fetched_at": "", "abstract_snippet": ""}
        with self.assertRaises(ValueError):
            scout.enforce_token_budget(fat)

    def test_trimming_caps(self):
        # 截断时省略号计入总长
        self.assertEqual(600, len(scout.trim_text("x" * 900, 600)))
        self.assertEqual("fault...", scout.trim_text("fault diagnosis", 8))
        self.assertEqual("fault diagnosis", scout.trim_text("  fault \n diagnosis  ", 100))


class CacheTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "literature_cache.json"

    def tearDown(self):
        self.folder.cleanup()

    def test_roundtrip_hit_and_expiry(self):
        cache = scout.load_cache(self.path)
        cards = [{"paper_id": "W1", "tier": "Q2"}]
        scout.save_cache(self.path, cache, "openalex", 5, "query a", cards)
        reloaded = scout.load_cache(self.path)
        self.assertEqual(cards, scout.cache_lookup(reloaded, "openalex", 5, "query a", 86400))
        # 键隔离：query/n/engine 任一不同即未命中
        self.assertIsNone(scout.cache_lookup(reloaded, "crossref", 5, "query a", 86400))
        self.assertIsNone(scout.cache_lookup(reloaded, "openalex", 3, "query a", 86400))
        self.assertIsNone(scout.cache_lookup(reloaded, "openalex", 5, "query b", 86400))
        # TTL 过期与 ttl=0 直通
        now = datetime.now(timezone.utc) + timedelta(seconds=86401)
        self.assertIsNone(scout.cache_lookup(reloaded, "openalex", 5, "query a", 86400, now=now))
        self.assertIsNone(scout.cache_lookup(reloaded, "openalex", 5, "query a", 0))
        # 降级事实随缓存条目落盘，命中时回填 payload 不遮蔽 engine 真实来源
        scout.save_cache(self.path, cache, "openalex", 5, "query a", cards,
                         fallback_used=True, total_results=9)
        entry = scout.load_cache(self.path)["entries"]["openalex|5|query a"]
        self.assertTrue(entry["fallback_used"])
        self.assertEqual("crossref", entry["engine_effective"])
        self.assertEqual(9, entry["total_results"])

    def test_corrupt_cache_warns_and_misses(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("{ not json", encoding="utf-8")
        cache = scout.load_cache(self.path)
        self.assertEqual({}, cache["entries"])


class CliTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.state = Path(self.folder.name)
        self.calls = []
        self.patcher = mock.patch.object(scout, "http_get", self._fake_http)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.folder.cleanup()

    def _fake_http(self, url, headers=None, timeout=30):
        self.calls.append(url)
        return json.dumps(openalex_payload()).encode("utf-8")

    def run_cli(self, *argv):
        stdout = StringIO()
        with redirect_stdout(stdout):
            code = scout.main([*argv, "--state-dir", str(self.state)])
        return code, json.loads(stdout.getvalue())

    def test_fetch_then_cache_hit(self):
        code, first = self.run_cli("domain adaptation", "--n", "5")
        self.assertEqual(0, code)
        self.assertFalse(first["cache_hit"])
        self.assertEqual(1, len(first["cards"]))
        self.assertEqual(2, first["total_results"])  # OpenAlex meta.count 进 payload
        self.assertFalse(first["fallback_used"])
        self.assertEqual("openalex", first["engine_effective"])
        self.assertTrue(Path(first["card_file"]).exists())
        on_disk = json.loads(Path(first["card_file"]).read_text(encoding="utf-8"))
        self.assertEqual("literature-card-1.0", on_disk["schema_version"])
        self.assertEqual(first["cards"], on_disk["cards"])

        self.assertEqual(1, len(self.calls))
        code, second = self.run_cli("domain adaptation", "--n", "5")
        self.assertEqual(0, code)
        self.assertTrue(second["cache_hit"])
        self.assertIsNone(second["card_file"])
        self.assertEqual(first["cards"], second["cards"])
        # 命中回填降级事实与命中总量，与首次输出一致
        self.assertFalse(second["fallback_used"])
        self.assertEqual("openalex", second["engine_effective"])
        self.assertEqual(2, second["total_results"])
        # 命中缓存不再发请求
        self.assertEqual(1, len(self.calls))

        # cache-ttl 0 绕过缓存重新检索
        code, bypassed = self.run_cli("domain adaptation", "--n", "5", "--cache-ttl", "0")
        self.assertFalse(bypassed["cache_hit"])
        self.assertEqual(2, len(self.calls))

    def test_min_tier_filters_output_not_cache(self):
        code, payload = self.run_cli("domain adaptation", "--n", "5", "--min-tier", "Q1")
        self.assertEqual(0, code)
        # mock 唯一保留条目 cited=150 → Q2，被 Q1 门槛滤掉
        self.assertEqual([], payload["cards"])
        # 但缓存仍存全量：放宽门槛重跑命中缓存且能拿到 Q2 条目
        code, relaxed = self.run_cli("domain adaptation", "--n", "5", "--min-tier", "Q2")
        self.assertEqual(1, len(relaxed["cards"]))
        self.assertEqual("Q2", relaxed["cards"][0]["tier"])

    def test_invalid_n_is_rejected(self):
        with self.assertRaises(SystemExit):
            scout.main(["q", "--n", "0", "--state-dir", str(self.state)])


if __name__ == "__main__":
    unittest.main()
