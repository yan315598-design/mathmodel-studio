"""外源文献检索层（最小闭环）：OpenAlex 主检索 + Crossref 兜底 + arXiv 预印本补充。

定位：选型期"方法发现"，与写作期 reference_skill_bridge.md（引用核验）分层。
只用 stdlib（urllib/json/xml），不引入第三方依赖。脚本只接受英文 query，
中文题面到英文检索词的翻译由调用方（agent）负责。

限流口径：OpenAlex 匿名约 100 次/天（实测限流；带 mailto 进礼貌池），注册 key
可提额（api_key 1000 次/天）；OpenAlex 返回 429/503 时自动降级 Crossref（只取
DOI/标题/期刊/年份等核验要素）。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent

OPENALEX_URL = "https://api.openalex.org/works"
CROSSREF_URL = "https://api.crossref.org/works"
ARXIV_URL = "https://export.arxiv.org/api/query"

# http_get 只允许访问这三个主机（SSRF 白名单），新增引擎须先扩此表。
ALLOWED_HOSTS = {"api.openalex.org", "api.crossref.org", "export.arxiv.org"}

DEFAULT_MAILTO = "mathmodel-studio@example.com"
USER_AGENT = "mathmodel-studio/1.0 (mailto:{mailto})"

# 方法卡 schema（literature-card-1.0）：字段名与顺序即契约，测试逐一校验。
CARD_FIELDS = (
    "paper_id", "title", "authors", "journal", "year", "doi", "cited_by",
    "oa_status", "tier", "source_engine", "query", "fetched_at", "abstract_snippet",
)
CARD_TOKEN_LIMIT = 500        # 单篇方法卡 token 预算（4 字符≈1 token 估算）
ABSTRACT_SNIPPET_MAX_CHARS = 600
TITLE_MAX_CHARS = 300
QUERY_MAX_CHARS = 200
AUTHORS_MAX = 5

# 期刊分档启发式（按被引量）：Q1 >500 / Q2 100-500 / Q3 10-100 / Q4 <10。
TIER_ORDER = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}

# OpenAlex 触发 Crossref 降级的限流/故障码。
FALLBACK_CODES = (429, 503)

REQUEST_TIMEOUT = 30

ATOM_NS = "http://www.w3.org/2005/Atom"
ARXIV_NS = "http://arxiv.org/schemas/atom"


class ScoutHTTPError(RuntimeError):
    """携带 HTTP 状态码的请求失败，供降级判断使用。"""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


def resolve_state_dir(cli_arg: str | None = None) -> Path:
    """路径解析协议: CLI > MATHMODEL_STATE_DIR > CUMCM_STATE_DIR (兼容) > cwd/state。"""
    if cli_arg:
        return Path(cli_arg)
    env_dir = os.environ.get("MATHMODEL_STATE_DIR") or os.environ.get("CUMCM_STATE_DIR")
    if env_dir:
        return Path(env_dir)
    return Path.cwd() / "state"


def http_get(url: str, headers: dict | None = None, timeout: int = REQUEST_TIMEOUT) -> bytes:
    """GET 一个 URL 并返回原始字节；HTTPError 转成 ScoutHTTPError 保留状态码。"""
    parsed = urllib.parse.urlparse(url)
    # SSRF 防护：显式 raise（不用 assert，防 python -O 剥离）
    if parsed.scheme != "https":
        raise ValueError(f"协议不允许: {parsed.scheme}")
    if parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"非白名单主机，拒绝请求: {parsed.hostname}")
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise ScoutHTTPError(exc.code, f"HTTP {exc.code}: {url}") from exc


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def estimate_tokens(text: str) -> int:
    """轻量 token 估算：英文文本约 4 字符折 1 token，至少 1。"""
    return max(1, (len(text) + 3) // 4)


def card_tokens(card: dict) -> int:
    return estimate_tokens(json.dumps(card, ensure_ascii=False))


def classify_tier(cited_by: int) -> str:
    """期刊分档启发式：Q1 >500 / Q2 100-500 / Q3 10-100 / Q4 <10（含端点）。"""
    if not isinstance(cited_by, (int, float)) or cited_by < 0:
        return "Q4"
    if cited_by > 500:
        return "Q1"
    if cited_by >= 100:
        return "Q2"
    if cited_by >= 10:
        return "Q3"
    return "Q4"


def trim_text(text: str | None, max_chars: int) -> str:
    """压平空白并截断；截断时省略号计入 max_chars 总长。"""
    value = " ".join(str(text or "").split())
    if len(value) <= max_chars:
        return value
    return value[:max(max_chars - 3, 0)].rstrip() + "..."


def enforce_token_budget(card: dict, limit: int = CARD_TOKEN_LIMIT) -> dict:
    """把方法卡压进 token 预算：先对半裁摘要，再裁标题，其余字段不动。"""
    trimmed = dict(card)
    for field in ("abstract_snippet", "title"):
        while card_tokens(trimmed) > limit and trimmed.get(field):
            half = len(trimmed[field]) // 2
            trimmed[field] = trimmed[field][:max(0, half)].rstrip()
    if card_tokens(trimmed) > limit:
        raise ValueError(f"方法卡 {card.get('paper_id')} 超出 {limit} token 预算且无法再裁剪")
    return trimmed


def rebuild_abstract(inverted_index, max_chars: int = ABSTRACT_SNIPPET_MAX_CHARS) -> str:
    """把 OpenAlex 的 abstract_inverted_index 还原为连续文本并截断。"""
    if not isinstance(inverted_index, dict):
        return ""
    positions = {}
    for word, indexes in inverted_index.items():
        for index in indexes or []:
            if isinstance(index, int) and isinstance(word, str):
                positions[index] = word
    text = " ".join(positions[index] for index in sorted(positions))
    return trim_text(text, max_chars) if text else ""


def build_card(paper_id: str, title: str, authors: list, journal: str, year,
               doi: str, cited_by: int, oa_status: str, source_engine: str,
               query: str, fetched_at: str, abstract_snippet: str) -> dict:
    """构造 schema 固定的方法卡，落库前统一过 token 预算。"""
    card = {
        "paper_id": paper_id,
        "title": trim_text(title, TITLE_MAX_CHARS),
        "authors": [trim_text(name, 80) for name in authors[:AUTHORS_MAX]],
        "journal": trim_text(journal, 120),
        "year": year,
        "doi": doi or "",
        "cited_by": int(cited_by or 0),
        "oa_status": oa_status or "unknown",
        "tier": classify_tier(cited_by or 0),
        "source_engine": source_engine,
        "query": trim_text(query, QUERY_MAX_CHARS),
        "fetched_at": fetched_at,
        "abstract_snippet": trim_text(abstract_snippet, ABSTRACT_SNIPPET_MAX_CHARS),
    }
    return enforce_token_budget(card)


def search_openalex(query: str, n: int, api_key: str | None = None,
                    mailto: str = DEFAULT_MAILTO, fetch=None) -> tuple[list[dict], int | None]:
    """OpenAlex 主检索：免 key，mailto 进礼貌池；is_retracted=true 直接剔除。

    返回 (方法卡列表, 命中总量)；命中总量取 meta.count，供 stage 1 看量级用。
    """
    params = {
        "search": query,
        "per-page": str(max(1, min(n, 50))),
        "mailto": mailto,
        "select": ("id,doi,title,publication_year,cited_by_count,is_retracted,"
                   "open_access,authorships,primary_location,abstract_inverted_index"),
    }
    if api_key:
        params["api_key"] = api_key
    url = f"{OPENALEX_URL}?{urllib.parse.urlencode(params)}"
    fetcher = fetch or http_get
    payload = json.loads(fetcher(url, {"User-Agent": USER_AGENT.format(mailto=mailto)}).decode("utf-8"))
    fetched_at = utc_now_iso()
    cards = []
    for work in payload.get("results", []):
        if work.get("is_retracted"):
            continue
        source = (work.get("primary_location") or {}).get("source") or {}
        # journal 取期刊名 display_name（如 Nature Communications），
        # host_organization_name 是出版商（如 Springer Nature），仅作缺省回退。
        journal_name = source.get("display_name") or source.get("host_organization_name") or ""
        cards.append(build_card(
            paper_id=str(work.get("id") or ""),
            title=work.get("title") or work.get("display_name") or "",
            authors=[(a.get("author") or {}).get("display_name") or ""
                     for a in (work.get("authorships") or [])],
            journal=journal_name,
            year=work.get("publication_year"),
            doi=work.get("doi") or "",
            cited_by=work.get("cited_by_count") or 0,
            oa_status=(work.get("open_access") or {}).get("oa_status") or "unknown",
            source_engine="openalex",
            query=query,
            fetched_at=fetched_at,
            abstract_snippet=rebuild_abstract(work.get("abstract_inverted_index")),
        ))
    return cards, payload.get("meta", {}).get("count")


def search_crossref(query: str, n: int, mailto: str = DEFAULT_MAILTO,
                    fetch=None) -> tuple[list[dict], int | None]:
    """Crossref 兜底：只取期刊文章的 DOI/标题/期刊/年份等核验要素。

    返回 (方法卡列表, 命中总量)；命中总量取 message.total-results。
    """
    params = {
        "query.bibliographic": query,
        "rows": str(max(1, min(n, 50))),
        "filter": "type:journal-article",
        "select": "DOI,title,container-title,issued,author,is-referenced-by-count",
        "mailto": mailto,
    }
    url = f"{CROSSREF_URL}?{urllib.parse.urlencode(params)}"
    fetcher = fetch or http_get
    payload = json.loads(fetcher(url, {"User-Agent": USER_AGENT.format(mailto=mailto)}).decode("utf-8"))
    fetched_at = utc_now_iso()
    cards = []
    for item in payload.get("message", {}).get("items", []):
        date_parts = ((item.get("issued") or {}).get("date-parts") or [[None]])
        cards.append(build_card(
            paper_id=str(item.get("DOI") or ""),
            title=(item.get("title") or [""])[0],
            authors=[f"{a.get('given', '')} {a.get('family', '')}".strip()
                     for a in (item.get("author") or [])],
            journal=(item.get("container-title") or [""])[0],
            year=(date_parts[0] or [None])[0],
            doi=item.get("DOI") or "",
            cited_by=item.get("is-referenced-by-count") or 0,
            oa_status="unknown",
            source_engine="crossref",
            query=query,
            fetched_at=fetched_at,
            abstract_snippet="",
        ))
    message = payload.get("message", {})
    return cards, message.get("total-results")


def search_arxiv(query: str, n: int, fetch=None) -> tuple[list[dict], None]:
    """arXiv 补充：新方法/预印本，Atom XML 解析；预印本无期刊，tier 按被引启发式恒为弱档。

    返回 (方法卡列表, None)；arXiv API 无命中总量概念，total_results 恒为 None。
    """
    params = {
        "search_query": f"all:{query}",
        "start": "0",
        "max_results": str(max(1, min(n, 50))),
        "sortBy": "relevance",
    }
    url = f"{ARXIV_URL}?{urllib.parse.urlencode(params)}"
    fetcher = fetch or http_get
    raw = fetcher(url).decode("utf-8")
    # XML 实体扩展防护：拒绝 DOCTYPE/ENTITY（arXiv 可信源但防中间人篡改）
    if "<!DOCTYPE" in raw or "<!ENTITY" in raw:
        raise ScoutHTTPError(0, "arXiv 响应含 DTD/ENTITY，拒绝解析")
    if len(raw) > 1_000_000:  # 1MB 上限，防资源耗尽
        raise ScoutHTTPError(0, f"arXiv 响应过大 ({len(raw)} bytes)，拒绝解析")
    root = ET.fromstring(raw)
    fetched_at = utc_now_iso()
    atom = f"{{{ATOM_NS}}}"
    cards = []
    for entry in root.findall(f"{atom}entry"):
        entry_id = entry.findtext(f"{atom}id") or ""
        published = entry.findtext(f"{atom}published") or ""
        year = int(published[:4]) if published[:4].isdigit() else None
        summary = entry.findtext(f"{atom}summary") or ""
        cards.append(build_card(
            paper_id=entry_id,
            title=entry.findtext(f"{atom}title") or "",
            authors=[author.findtext(f"{atom}name") or ""
                     for author in entry.findall(f"{atom}author")],
            journal="arXiv (preprint)",
            year=year,
            doi=entry.findtext(f"{{{ARXIV_NS}}}doi") or "",
            cited_by=0,
            oa_status="green",
            source_engine="arxiv",
            query=query,
            fetched_at=fetched_at,
            abstract_snippet=summary,
        ))
    return cards, None


# ---- 结果缓存（state/literature_cache.json，同 query 24h 内直接读缓存） ----

def cache_key(engine: str, n: int, query: str) -> str:
    return f"{engine}|{n}|{query}"


def load_cache(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": "literature-cache-1.0", "entries": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # 缓存是一次性性能产物而非证据，损坏只告警不阻断，下次写入时覆盖。
        print(f"警告: 文献缓存 {path} 损坏，按未命中处理", file=sys.stderr)
        return {"schema_version": "literature-cache-1.0", "entries": {}}
    if not isinstance(payload, dict) or not isinstance(payload.get("entries"), dict):
        # JSON 合法但结构不对，与损坏同等处理：告警后按未命中，下次写入时覆盖。
        print(f"警告: 文献缓存 {path} 结构不符（应为含 entries 的对象），按未命中处理",
              file=sys.stderr)
        return {"schema_version": "literature-cache-1.0", "entries": {}}
    return payload


def cache_lookup(cache: dict, engine: str, n: int, query: str, ttl: int,
                 now: datetime | None = None) -> list[dict] | None:
    """命中且未过 TTL 返回缓存卡片，否则返回 None。ttl<=0 视为永远过期。"""
    entry = cache.get("entries", {}).get(cache_key(engine, n, query))
    if not isinstance(entry, dict):
        return None
    try:
        fetched_at = datetime.fromisoformat(entry["fetched_at"])
    except (KeyError, TypeError, ValueError):
        return None
    reference = now or datetime.now(timezone.utc)
    if reference.timestamp() - fetched_at.timestamp() > ttl:
        return None
    cards = entry.get("cards")
    return cards if isinstance(cards, list) else None


def save_cache(path: Path, cache: dict, engine: str, n: int, query: str,
               cards: list[dict], fallback_used: bool = False,
               total_results: int | None = None) -> None:
    """写入缓存条目；降级事实（fallback_used/engine_effective）随条目落盘，命中时回填。

    写盘失败（磁盘满/权限）只告警不阻断：缓存是性能产物，检索结果照常输出。
    """
    cache.setdefault("entries", {})[cache_key(engine, n, query)] = {
        "fetched_at": utc_now_iso(),
        "cards": cards,
        "fallback_used": fallback_used,
        "engine_effective": "crossref" if fallback_used else engine,
        "total_results": total_results,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        print(f"警告: 文献缓存写盘失败 {path}: {exc}", file=sys.stderr)


def write_card_file(state_dir: Path, query: str, engine: str, cards: list[dict]) -> Path:
    """方法卡落盘 state/literature/<timestamp>.json，同秒冲突时追加序号。"""
    folder = state_dir / "literature"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = folder / f"{stamp}.json"
    counter = 1
    while path.exists():
        path = folder / f"{stamp}_{counter}.json"
        counter += 1
    payload = {
        "schema_version": "literature-card-1.0",
        "query": query,
        "engine": engine,
        "fetched_at": utc_now_iso(),
        "cards": cards,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def run_scout(query: str, n: int, engine: str, api_key: str | None = None,
              mailto: str = DEFAULT_MAILTO,
              fetch=None) -> tuple[list[dict], bool, int | None]:
    """执行一次检索（含 OpenAlex→Crossref 降级）。

    返回 (cards, fallback_used, total_results)；降级时 total_results 取兜底引擎口径。
    """
    if engine == "openalex":
        try:
            cards, total = search_openalex(query, n, api_key=api_key, mailto=mailto, fetch=fetch)
            return cards, False, total
        except ScoutHTTPError as exc:
            if exc.code not in FALLBACK_CODES:
                raise
            print(f"OpenAlex HTTP {exc.code}，自动降级 Crossref 兜底", file=sys.stderr)
            cards, total = search_crossref(query, n, mailto=mailto, fetch=fetch)
            return cards, True, total
    if engine == "crossref":
        cards, total = search_crossref(query, n, mailto=mailto, fetch=fetch)
        return cards, False, total
    cards, total = search_arxiv(query, n, fetch=fetch)
    return cards, False, total


def main(argv: list[str] | None = None) -> int:
    """CLI 入口：检索 → 缓存 → 分档过滤 → 方法卡落盘 → JSON 输出。"""
    parser = argparse.ArgumentParser(
        description="外源文献检索（OpenAlex 主检索 / Crossref 兜底 / arXiv 预印本补充）")
    parser.add_argument("query", help="英文检索词；中文题面到英文的转换由调用方负责")
    parser.add_argument("--n", type=int, default=5, help="返回条数，默认 5")
    parser.add_argument("--engine", choices=("openalex", "crossref", "arxiv"), default="openalex")
    parser.add_argument("--cache-ttl", type=int, default=86400,
                        help="缓存秒数，默认 86400（24 小时）；0 表示跳过缓存")
    parser.add_argument("--api-key", default=None,
                        help="OpenAlex api_key（可选，注册后 1000 次/天）")
    parser.add_argument("--mailto", default=DEFAULT_MAILTO,
                        help="礼貌池邮箱参数，默认 %s" % DEFAULT_MAILTO)
    parser.add_argument("--min-tier", choices=("Q1", "Q2", "Q3", "Q4"), default="Q4",
                        help="期刊分档下限过滤，默认 Q4 即不过滤")
    parser.add_argument("--state-dir", type=Path, default=None,
                        help="state 目录；默认 MATHMODEL_STATE_DIR > cwd/state")
    args = parser.parse_args(argv)
    if args.n < 1:
        parser.error("--n 至少为 1")

    state_dir = resolve_state_dir(str(args.state_dir) if args.state_dir else None)
    cache_path = state_dir / "literature_cache.json"
    cache = load_cache(cache_path)

    payload = {
        "schema_version": "literature-card-1.0",
        "query": args.query,
        "engine": args.engine,
        "engine_effective": args.engine,
        "cache_hit": False,
        "fallback_used": False,
        "total_results": None,
        "fetched_at": utc_now_iso(),
    }
    cached_cards = cache_lookup(cache, args.engine, args.n, args.query, args.cache_ttl) \
        if args.cache_ttl > 0 else None
    if cached_cards is not None:
        entry = cache["entries"][cache_key(args.engine, args.n, args.query)]
        payload["cache_hit"] = True
        payload["fetched_at"] = entry["fetched_at"]
        # 降级事实随缓存条目回填；旧版条目缺这些字段时按"未降级、总量未知"处理。
        payload["fallback_used"] = bool(entry.get("fallback_used", False))
        payload["engine_effective"] = entry.get("engine_effective") or args.engine
        payload["total_results"] = entry.get("total_results")
        cards = cached_cards
        payload["card_file"] = None
    else:
        try:
            cards, fallback_used, total_results = run_scout(
                args.query, args.n, args.engine,
                api_key=args.api_key, mailto=args.mailto)
        except (ScoutHTTPError, urllib.error.URLError, ValueError, ET.ParseError) as exc:
            print(f"检索失败（engine={args.engine}）: {exc}", file=sys.stderr)
            return 1
        payload["fallback_used"] = fallback_used
        payload["total_results"] = total_results
        if fallback_used:
            payload["engine_effective"] = "crossref"
        if cards:
            payload["fetched_at"] = cards[0]["fetched_at"]
        # 缓存存全量（未过滤），分档过滤每次输出时按 --min-tier 现算。
        save_cache(cache_path, cache, args.engine, args.n, args.query, cards,
                   fallback_used=fallback_used, total_results=total_results)

    cards = [card for card in cards if TIER_ORDER[card["tier"]] <= TIER_ORDER[args.min_tier]]
    if cached_cards is None:
        card_file = write_card_file(state_dir, args.query, args.engine, cards)
        payload["card_file"] = str(card_file)

    payload["cards"] = cards
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
