"""docx_number_recheck.py 的行为测试: 冻结数字缺失即 exit 1、在则 exit 0、
缩写三级分流 (歧义→❌ / ≥3位→人工确认清单 / ≤2位→warn)、符号/中文边界/e 记法/
下溢等 token 口径回归。

检查 2 分级 (v3.1.1) 行为:
- 显式关联冲突 ❌ (claim 标签完整匹配 / claim_id 标记 / source locator 源值与冻结值
  打架) 计入 n_fail 并拦门禁 —— 即使正确值仍在别的段落出现, 末位小差 (57.5406 →
  57.5403) 也必须拦;
- 弱关联 (单位一致 / 对象词元命中 / 同段标签) 与仅近邻 (无关联) 只提示, 不拦门禁;
- 两侧单位都识别到且不同 (质量 1.0081 kg vs 温度 1.0990 °C) 判为不同量, 不冲突;
- 来源登记 (results 登记与证据账本) 覆盖改变分类; 登记不足如实标注, 未找到 ≠ 不存在;
- 容限可配置 (近邻窗口位数 / 科学记数法相对容差)。
"""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

try:
    import docx
    from docx_number_recheck import load_provenance, main, run_recheck
    HAS_PYTHON_DOCX = True
except ImportError:
    HAS_PYTHON_DOCX = False


def _claim(value, **extra):
    rec = {"value": value, "unit": "", "source_file": "x.json",
           "status": "frozen"}
    rec.update(extra)
    return rec


def _workspace(tmp: Path, files: dict) -> Path:
    """最小工作区: 按 {"results/q3.json": {...}} 落盘 (登记来源复用测试用)。"""
    ws = tmp / "ws"
    ws.mkdir(parents=True, exist_ok=True)
    for name, payload in files.items():
        path = ws / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if name.endswith(".jsonl"):
            text = "\n".join(json.dumps(x, ensure_ascii=False) for x in payload)
        else:
            text = json.dumps(payload, ensure_ascii=False)
        path.write_text(text, encoding="utf-8")
    return ws


@unittest.skipUnless(HAS_PYTHON_DOCX, "需要 python-docx")
class RunRecheckTest(unittest.TestCase):
    def _segs(self, *texts):
        return [(t, False) for t in texts]

    def test_frozen_value_present_passes(self):
        segs = self._segs("中心温度 33.5770 °C。")
        report = run_recheck(segs, {"q1.T": _claim("33.5770")})
        self.assertEqual(0, report["n_fail"])
        self.assertEqual(1, report["n_pass"])

    def test_frozen_value_missing_fails(self):
        report = run_recheck(self._segs("正文没有那个数。"), {"q1.T": _claim("33.5770")})
        self.assertEqual(1, report["n_fail"])
        self.assertEqual("q1.T", report["missing"][0]["claim"])

    def test_missing_reports_nearest_small_drift(self):
        """末位小差必须在缺失报告里可见 (57.5406 → 正文只有 57.5403)。"""
        report = run_recheck(self._segs("总工期 57.5403 h。"),
                             {"q3.t": _claim("57.5406", unit="h")})
        self.assertEqual(1, report["n_fail"])
        nearest = report["missing"][0]["nearest"]
        self.assertEqual("57.5403", nearest[0]["token"])
        self.assertLess(nearest[0]["rel_diff"], 1e-5)
        self.assertGreater(nearest[0]["rel_diff"], 0.0)

    def test_trailing_zero_equality(self):
        # 2.5500 与 2.55 是同一值 (书写格式差异), 应命中
        report = run_recheck(self._segs("浓度为 2.55 kg/kg。"), {"q1.C": _claim("2.5500")})
        self.assertEqual(0, report["n_fail"])

    # ---- 符号口径 (P1-2) ----
    def test_signed_plain_value_matched(self):
        """P1-2 回归: 冻结 -4.8 须命中正文 "-4.8" (修复前符号没进 token 而 FAIL)。"""
        report = run_recheck(self._segs("偏差为 -4.8 小时, 可接受。"),
                             {"q4.diff": _claim("-4.8")})
        self.assertEqual(0, report["n_fail"])

    def test_sci_sign_mismatch_fails(self):
        """P1-2 回归: 冻结 2.30e-13 不得匹配正文 -2.30×10⁻¹³ (符号相反)。"""
        report = run_recheck(self._segs("残差为 -2.30×10⁻¹³。"), {"q1.res": _claim("2.30e-13")})
        self.assertEqual(1, report["n_fail"])

    # ---- 中文边界口径 (P1-2) ----
    def test_cjk_adjacent_digit_tokenized(self):
        """P1-2 回归: "温度33.5度" 的 33.5 可取 (修复前 \\w 边界把中文紧邻数字排除)。"""
        report = run_recheck(self._segs("实测温度33.5度, 符合预期。"),
                             {"q1.T": _claim("33.5")})
        self.assertEqual(0, report["n_fail"])

    def test_latin_identifier_adjacency_still_excluded(self):
        # 拉丁字母紧邻仍视为标识符: x33.5 不当作数字 33.5
        report = run_recheck(self._segs("变量 x33.5 与版本 v2.40 不参与核对。"),
                             {"q1.T": _claim("33.5")})
        self.assertEqual(1, report["n_fail"])

    # ---- 科学记数法形态 (P1-2/P1-3: ×10 与 e 记法分列) ----
    def test_sci_times_notation_unicode(self):
        # ×10⁻¹³ (上标) 与 ×10-13 (翻平) 两种形态
        report = run_recheck(self._segs("残差为 2.30×10⁻¹³。"), {"q1.res": _claim("2.30e-13")})
        self.assertEqual(0, report["n_fail"])
        report = run_recheck(self._segs("残差为 2.30×10-13。"), {"q1.res": _claim("2.30e-13")})
        self.assertEqual(0, report["n_fail"])

    def test_sci_e_notation_in_body(self):
        """P1-3 回归: 正文 e 记法 2.30e-13 须命中冻结 2.30e-13 (修复前不采集 e token)。"""
        report = run_recheck(self._segs("残差为 2.30e-13 量级。"), {"q1.res": _claim("2.30e-13")})
        self.assertEqual(0, report["n_fail"])

    def test_sci_omml_flattened_form(self):
        # pandoc OMML 把 \times 展平成 "imes": "2.30imes10-13"
        report = run_recheck(self._segs("残差为 2.30imes10-13 (OMML 展平形态)。"),
                             {"q1.res": _claim("2.30e-13")})
        self.assertEqual(0, report["n_fail"])

    def test_sci_different_value_is_hint_not_conflict(self):
        # 2.31×10⁻¹³ vs 冻结 2.30e-13: 缺失 1 (原值未见); 无显式关联 → 仅近邻提示,
        # 不再按"同前缀+相对差"判冲突 (v3.1.1)
        report = run_recheck(self._segs("残差为 2.31×10⁻¹³。"), {"q1.res": _claim("2.30e-13")})
        self.assertEqual(1, len(report["missing"]))
        self.assertEqual([], report["conflicts"])
        self.assertEqual(1, len(report["near_hints"]))
        self.assertIn("2.31", report["near_hints"][0]["token"])
        self.assertEqual(1, report["n_fail"])

    # ---- 极小值下溢/容差下限 (P1-4) ----
    def test_underflow_distinct_tiny_values_not_equal(self):
        """P1-4 回归: 2.30e-400 与 9.99×10⁻⁵⁰⁰ 都下糊成 0, 仍必须判不等。"""
        report = run_recheck(self._segs("另一处为 9.99×10⁻⁵⁰⁰。"),
                             {"q1.res": _claim("2.30e-400")})
        self.assertEqual(1, report["n_fail"])

    def test_underflow_same_tiny_value_equal_via_log_domain(self):
        # 正控: 同值下溢走 log10 域命中 (2.3×10⁻⁴⁰⁰ ↔ 2.30e-400)
        report = run_recheck(self._segs("该量为 2.3×10⁻⁴⁰⁰。"), {"q1.res": _claim("2.30e-400")})
        self.assertEqual(0, report["n_fail"])

    # ---- 缩写回退 (P1-5) + A5 三级分流 ----
    def test_abbrev_full_token_passes_as_confirm(self):
        # 规格示例: 冻结 -4.8822 (5 位有效数字), 摘要写 "短 4.88" → A5-b 人工确认清单
        report = run_recheck(self._segs("问题四比问题三短 4.88 小时。"),
                             {"q4.diff": _claim("-4.8822")})
        self.assertEqual(0, report["n_fail"])
        self.assertEqual(0, len(report["abbrev_only"]))
        self.assertEqual(1, len(report["abbrev_confirm"]))
        self.assertIn("4.88", report["abbrev_confirm"][0]["abbrev_seen"])
        self.assertEqual("q4.diff", report["abbrev_confirm"][0]["claim"])

    def test_abbrev_substring_does_not_bypass_gate(self):
        """P1-5 回归: 正文只有 104.88 时, 子串 "4.88" 不得给冻结 4.8822 放行。"""
        report = run_recheck(self._segs("总量为 104.88 万元, 别无他数。"),
                             {"q4.diff": _claim("4.8822")})
        self.assertEqual(1, report["n_fail"])
        self.assertEqual(0, len(report["abbrev_confirm"]))
        self.assertEqual(0, len(report["abbrev_only"]))

    def test_abbrev_rounding_mode_tolerance(self):
        # 0.7955 的三位显示既可能写 0.795 (half-even) 也可能 0.796 (half-up), 都算缩写
        for text in ("指数为 0.795 。", "指数为 0.796 。"):
            report = run_recheck(self._segs(text), {"q6.st": _claim("0.7955")})
            self.assertEqual(0, report["n_fail"], text)
            self.assertEqual(1, len(report["abbrev_confirm"]), text)
            self.assertEqual(0, len(report["abbrev_only"]), text)

    # ---- A5-a: 缩写歧义 (同前缀多冻结项) 强制全匹配 → ❌ ----
    def test_ambiguous_abbrev_forces_full_match(self):
        """A5 实战场景: 0.7403 只见 0.7, 而另一冻结 0.7253 同享 0.7 缩写空间——
        "0.7" 无法证明指向哪个键, 两键都要求全文原值, 否则 ❌。"""
        report = run_recheck(self._segs("最大显式步长取 0.7 s。"),
                             {"a.dt": _claim("0.7403"), "b.sobol": _claim("0.7253")})
        self.assertEqual(2, len(report["missing"]))
        self.assertEqual(0, len(report["abbrev_confirm"]))
        self.assertIn("歧义", report["missing"][0]["note"])
        self.assertIn("0.7253", report["missing"][0]["note"])

    def test_abbrev_matching_other_frozen_value_exactly_is_rival(self):
        # 冻结 0.7 存在时, "0.7" 对 0.7403 而言是歧义缩写 (可完整命中他键) → ❌
        report = run_recheck(self._segs("步长取 0.7 s, 系数 0.7。"),
                             {"a.dt": _claim("0.7403"), "b.k": _claim("0.7")})
        self.assertEqual(1, len(report["missing"]))
        self.assertEqual("a.dt", report["missing"][0]["claim"])
        self.assertIn("歧义", report["missing"][0]["note"])

    def test_co_prefix_without_shared_abbrev_goes_confirm_not_fail(self):
        """协调者清单场景: 0.7403 只见 0.7 且冻结表另有 0.3701——数值上 0.3701
        并不共享 0.7 前缀 (其前 2 位是 37, |0.7-0.3701| 远超缩写容差), 故两键均
        走人工确认清单而非 ❌; 真正触发 ❌ 的是同享缩写空间的 0.7xx 组 (上一测试)。"""
        report = run_recheck(self._segs("平面步长 0.7 s, 柱轴步长 0.370 s。"),
                             {"a.dt": _claim("0.7403"), "b.dt_cyl": _claim("0.3701")})
        self.assertEqual(0, report["n_fail"])
        self.assertEqual(2, len(report["abbrev_confirm"]))
        self.assertEqual(0, len(report["missing"]))

    def test_short_frozen_value_abbrev_stays_warn(self):
        # A5-c: 冻结值 0.74 仅 2 位有效数字 → 维持原 warn 语义, 不进确认清单
        report = run_recheck(self._segs("步长量级取 0.7 s。"),
                             {"q1.dt": _claim("0.74")})
        self.assertEqual(0, report["n_fail"])
        self.assertEqual(1, len(report["abbrev_only"]))
        self.assertEqual(0, len(report["abbrev_confirm"]))

    # ---- display 字段与 stale ----
    def test_display_field_used_when_present(self):
        report = run_recheck(self._segs("约为 57.5 小时。"),
                             {"q3.t": _claim("57.5406", display="57.5")})
        self.assertEqual(0, report["n_fail"])

    def test_thousands_separator_normalized(self):
        report = run_recheck(self._segs("总量 1,234.5 万元。"), {"q2.total": _claim("1234.5")})
        self.assertEqual(0, report["n_fail"])

    def test_stale_claims_skipped(self):
        report = run_recheck(self._segs("正文。"),
                             {"old": _claim("99.99", status="stale")})
        self.assertEqual(0, report["frozen_total"])
        self.assertEqual(0, report["n_fail"])

    # ---- 显式关联冲突 (v3.1.1 硬档): 只能由 claim 标签/claim_id 标记/locator 源值判定 ----
    def test_explicit_claim_label_conflict_even_when_correct_value_present(self):
        """协调者场景: 正确值 57.5406 仍在别的段落出现 (缺失门不响), 错误 57.5403
        仍必须拦 —— 依据是紧邻的 claim 标签, 不是数值距离。"""
        report = run_recheck(self._segs("q3.t = 57.5403 h, 另处写作 57.5406 h。"),
                             {"q3.t": _claim("57.5406", unit="h")})
        self.assertEqual(1, report["n_pass"])
        self.assertEqual([], report["missing"])
        self.assertEqual(1, len(report["conflicts"]))
        entry = report["conflicts"][0]
        self.assertEqual("57.5403", entry["token"])
        self.assertEqual("q3.t", entry["frozen_claim"])
        self.assertIn("claim_label:q3.t", entry["evidence"])
        self.assertLess(entry["rel_diff"], 1e-5)  # 末位小差也拦
        self.assertEqual(1, report["n_fail"])

    def test_claim_id_marker_evidence(self):
        report = run_recheck(self._segs("claim_id q2.unit_cost = 4368.3 元/吨, 另处 4368 元/吨。"),
                             {"q2.unit_cost": _claim("4368", unit="元/吨")})
        self.assertEqual(1, len(report["conflicts"]))
        evidence = report["conflicts"][0]["evidence"]
        self.assertIn("claim_label:q2.unit_cost", evidence)
        self.assertIn("claim_id_marker:q2.unit_cost", evidence)
        self.assertEqual(1, report["n_fail"])

    def test_locator_leaf_label_conflict(self):
        # source_locator 叶名 (t_total) 紧邻在数字前 → 显式绑定 → 冲突
        report = run_recheck(self._segs("t_total = 57.5403 h, 另处 57.5406 h。"),
                             {"q3.t": _claim("57.5406", unit="h",
                                             source_locator="data.t_total")})
        self.assertEqual(1, len(report["conflicts"]))
        self.assertIn("locator_form:t_total", report["conflicts"][0]["evidence"])

    def test_punctuation_separated_label_is_weak_not_conflict(self):
        """标点/句读把标签与数字隔开不算紧邻 (高置信只认紧邻形态) → 弱证据提示。"""
        report = run_recheck(self._segs("q3.t 见下表。总工期 57.5403 h, 冻结 57.5406 h。"),
                             {"q3.t": _claim("57.5406", unit="h")})
        self.assertEqual([], report["conflicts"])
        self.assertEqual(1, len(report["weak_associations"]))
        self.assertIn("claim_label_segment:q3.t",
                      report["weak_associations"][0]["evidence"])
        self.assertEqual(0, report["n_fail"])

    def test_explicit_label_conflict_beats_global_coverage(self):
        """复审 P1-1: A=57.5403 与冻结 A=57.5406 必须拦 —— 即使 57.5403 恰好等于
        另一键 B 的冻结值 (全局覆盖判定不得抢跑), 正确值 57.5406 也仍在文中。"""
        report = run_recheck(
            self._segs("A=57.5403; B=57.5403; reference 57.5406"),
            {"A": _claim("57.5406"), "B": _claim("57.5403")})
        self.assertEqual([], report["missing"])  # A/B 的值都在文中 (缺失门不响)
        self.assertEqual(1, len(report["conflicts"]))
        entry = report["conflicts"][0]
        self.assertEqual("57.5403", entry["token"])
        self.assertEqual("A", entry["frozen_claim"])
        self.assertIn("claim_label:A", entry["evidence"])
        self.assertEqual(1, report["n_fail"])

    def test_label_bound_low_sig_digits_still_conflicts(self):
        """复审 P1-1: 带标签的低有效位数字 (A=2.51 vs 冻结 2.52) 不得被位数筛查跳过。"""
        report = run_recheck(self._segs("A=2.51, 另处 2.52。"), {"A": _claim("2.52")})
        self.assertEqual([], report["missing"])
        self.assertEqual(1, len(report["conflicts"]))
        self.assertEqual("2.51", report["conflicts"][0]["token"])
        self.assertEqual(1, report["n_fail"])

    def test_source_value_equality_does_not_bind_text(self):
        """复审 P1-2: 正文数字与源 locator 值相同**不构成**正文关联 —— 只出源值漂移
        独立报告 (非阻断), 正文侧不判冲突。"""
        with tempfile.TemporaryDirectory() as td:
            ws = _workspace(Path(td), {"results/q3.json": {"data": {"t_total": 57.5403}}})
            prov = load_provenance(ws)
            report = run_recheck(
                self._segs("总工期 57.5403 h, 另处写作 57.5406 h。"),
                {"q3.t": _claim("57.5406", unit="h", source_file="results/q3.json",
                                source_locator="data.t_total")},
                provenance=prov)
        self.assertEqual([], report["conflicts"])
        self.assertEqual(1, len(report["source_drift"]))
        drift = report["source_drift"][0]
        self.assertEqual("q3.t", drift["claim"])
        self.assertEqual("results/q3.json@data.t_total", drift["source"])
        self.assertEqual(57.5403, drift["source_value"])
        self.assertEqual(0, report["n_fail"])

    def test_source_outside_workspace_is_not_read(self):
        """复审 P1-2: ../outside.json 这类工作区外源不读取, 也不产生冲突/漂移报告。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ws = _workspace(root, {"results/q3.json": {"t": 1.0}})
            (root / "outside.json").write_text(json.dumps({"t": 57.5403}),
                                               encoding="utf-8")
            prov = load_provenance(ws)
            report = run_recheck(
                self._segs("总工期 57.5403 h, 另处写作 57.5406 h。"),
                {"q3.t": _claim("57.5406", unit="h", source_file="../outside.json",
                                source_locator="t")},
                provenance=prov)
        self.assertEqual([], report["conflicts"])
        self.assertEqual([], report["source_drift"])
        self.assertTrue(any("工作区外" in n["note"] for n in report["source_notes"]))
        self.assertEqual(0, report["n_fail"])

    def test_generic_locator_does_not_bind(self):
        """复审 P2-3: 单层通用定位符 (value) 与单位名叶 (h) 不参与硬判 (只弱证据)。"""
        for locator in ("value", "h"):
            report = run_recheck(self._segs(f"{locator} = 57.5403 h, 另处 57.5406 h。"),
                                 {"q3.t": _claim("57.5406", unit="h",
                                                 source_locator=locator)})
            self.assertEqual([], report["conflicts"], locator)
            self.assertEqual(0, report["n_fail"], locator)

    def test_tiny_underflow_token_no_zero_division(self):
        """复审 P2-4: 2.345×10⁻⁴⁰⁰ 这类下溢 token 不得 ZeroDivisionError。"""
        prov = {"available": True, "entries": [(1.0, 0, "results/x.json", "y")]}
        report = run_recheck(self._segs("温度 33.5770 °C; 残差为 2.345×10⁻⁴⁰⁰。"),
                             {"q1.T": _claim("33.5770")}, provenance=prov)
        self.assertEqual(0, report["n_fail"])
        self.assertIn("2.345", report["uncovered"][0]["token"])
        prov2 = {"available": True, "entries": [(2.345, -400, "results/x.json", "y")]}
        report2 = run_recheck(self._segs("温度 33.5770 °C; 残差为 2.345×10⁻⁴⁰⁰。"),
                              {"q1.T": _claim("33.5770")}, provenance=prov2)
        self.assertEqual(1, report2["n_source_covered"])

    def test_source_coverage_requires_same_sign_underflow(self):
        """复审 P2: 下溢 log 域覆盖也必须同号 —— 源值 2.345e-400 不得覆盖
        -2.345×10⁻⁴⁰⁰ (修复前只比 log10|v|, 符号被丢掉)。"""
        prov = {"available": True, "value_evidence": True,
                "entries": [(2.345, -400, "results/x.json", "y")]}
        same = run_recheck(self._segs("温度 33.5770 °C; 残差为 2.345×10⁻⁴⁰⁰。"),
                           {"q1.T": _claim("33.5770")}, provenance=prov)
        opp = run_recheck(self._segs("温度 33.5770 °C; 残差为 -2.345×10⁻⁴⁰⁰。"),
                          {"q1.T": _claim("33.5770")}, provenance=prov)
        self.assertEqual(1, same["n_source_covered"])
        self.assertEqual(0, opp["n_source_covered"])
        self.assertIn("-2.345", "".join(e["token"] for e in opp["uncovered"]))

    def test_source_coverage_sign_pair_moderate_values(self):
        """同号/异号成对: 常规量级 (走缩放/舍入分支) 也不得跨号命中。"""
        prov = {"available": True, "value_evidence": True,
                "entries": [(2.3456, 0, "results/x.json", "y")]}
        same = run_recheck(self._segs("温度 33.5770; 残差为 2.3456。"),
                           {"q1.T": _claim("33.5770")}, provenance=prov)
        opp = run_recheck(self._segs("温度 33.5770; 残差为 -2.3456。"),
                          {"q1.T": _claim("33.5770")}, provenance=prov)
        self.assertEqual(1, same["n_source_covered"])
        self.assertEqual(0, opp["n_source_covered"])

    def test_path_only_registration_is_reported_not_usable(self):
        """复审 P2: 只有 run_manifest 路径登记时 available=True 但无值证据 ——
        报告须明示 (value_evidence=False / path_registration_only), 未覆盖口径按
        "登记来源不足"措辞, 不得当作已核出处。"""
        with tempfile.TemporaryDirectory() as td:
            ws = _workspace(Path(td), {
                "results/run_manifest.jsonl": [
                    {"script": "solve.py", "outputs": [{"path": "results/q1.json"}]}
                ]})
            prov = load_provenance(ws)
            report = run_recheck(self._segs("另一处结果 12.345 出现。"),
                                 {"q1.T": _claim("33.5770")}, provenance=prov)
        self.assertTrue(prov["available"])
        self.assertFalse(prov["value_evidence"])
        self.assertTrue(prov["path_registration_only"])
        self.assertIn("无值证据", prov["note"])
        entry = report["uncovered"][0]
        self.assertFalse(entry["value_evidence"])
        self.assertIn("登记来源不足", entry["note"])

    def test_descriptive_locator_does_not_bind_source_value(self):
        # 描述型定位符不做源值绑定 (无机器可解析语义): 正文只有 57.5403 时
        # 只报冻结值缺失, 不因"源值"判冲突
        with tempfile.TemporaryDirectory() as td:
            ws = _workspace(Path(td), {"results/q3.json": {"t": 57.5403}})
            prov = load_provenance(ws)
            report = run_recheck(
                self._segs("总工期 57.5403 h。"),
                {"q3.t": _claim("57.5406", unit="h", source_file="results/q3.json",
                                source_locator="第 1800 s 总工期 (h)")},
                provenance=prov)
        self.assertEqual([], report["conflicts"])
        self.assertEqual(1, report["n_fail"])  # 只有缺失门 (57.5406 未出现)

    # ---- 弱关联与仅近邻提示 (不拦门禁) ----
    def test_near_miss_without_association_is_hint_only(self):
        # 0.7450 与冻结 0.7403 无任何关联证据 → 仅近邻提示, 不计 n_fail
        report = run_recheck(self._segs("步长 0.7403, 另见 0.7450。"),
                             {"q1.dt": _claim("0.7403")})
        self.assertEqual([], report["conflicts"])
        self.assertEqual([], report["weak_associations"])
        self.assertEqual(1, len(report["near_hints"]))
        self.assertEqual("0.7450", report["near_hints"][0]["token"])
        self.assertAlmostEqual(0.00635, report["near_hints"][0]["rel_diff"], places=3)
        self.assertNotIn("0.7450", report["warn_numbers"])
        self.assertEqual(0, report["n_fail"])

    def test_unit_only_near_miss_is_weak_hint(self):
        # 同单位 (单位一致不证明同对象) → 弱关联必查清单, 但仍不拦门禁
        report = run_recheck(self._segs("入口温度 33.6000 °C, 冻结值 33.5770 °C。"),
                             {"q1.T": _claim("33.5770", unit="°C")})
        self.assertEqual([], report["conflicts"])
        self.assertEqual(1, len(report["weak_associations"]))
        entry = report["weak_associations"][0]
        self.assertEqual("33.6000", entry["token"])
        self.assertIn("unit:°C", entry["evidence"])
        self.assertIn("不证明同对象", entry["note"])
        self.assertEqual(0, report["n_fail"])

    def test_object_word_alone_is_weak_hint_not_conflict(self):
        """对象词元单命中不硬判 (v3.1.1 明确口径): 只进弱关联提示。"""
        report = run_recheck(self._segs("diff 处为 57.5403 h, 冻结 57.5406 h。"),
                             {"q3.diff": _claim("57.5406", unit="h")})
        self.assertEqual([], report["conflicts"])
        self.assertEqual(1, len(report["weak_associations"]))
        self.assertIn("object:diff", report["weak_associations"][0]["evidence"])
        self.assertEqual("57.5403", report["weak_associations"][0]["token"])

    def test_generic_words_are_not_object_evidence(self):
        # 通用词 (结果/数值/数据/result/data) 不作对象证据 → 只能落仅近邻
        report = run_recheck(self._segs("该结果 57.5403 与冻结 57.5406。"),
                             {"q1.result_diff": _claim("57.5406")})
        self.assertEqual([], report["conflicts"])
        self.assertEqual([], report["weak_associations"])
        self.assertEqual(1, len(report["near_hints"]))
        self.assertEqual("57.5403", report["near_hints"][0]["token"])

    def test_independent_quantities_with_different_units_do_not_conflict(self):
        """协调者场景: 质量 1.0081 kg 与温度 1.0990 °C 是独立量, 不互相冲突。"""
        report = run_recheck(self._segs("试样质量 1.0081 kg, 另一处温度 1.0990 °C。"),
                             {"q1.m": _claim("1.0081", unit="kg")})
        self.assertEqual([], report["conflicts"])
        self.assertEqual(1, len(report["unit_mismatch"]))
        entry = report["unit_mismatch"][0]
        self.assertEqual("1.0990", entry["token"])
        self.assertEqual("°C", entry["token_unit"])
        self.assertEqual("kg", entry["frozen_unit"])
        self.assertEqual(0, report["n_fail"])
        self.assertEqual(1, report["n_soft_covered"])  # 只有 1.0081 本身命中冻结值
        self.assertEqual(0, report["n_source_covered"])

    def test_unitless_near_neighbours_never_conflict(self):
        # 无单位无标签: 1.0990 与 1.0081 仅数值邻近 → 仅近邻 (不能按前缀百分比判冲突)
        report = run_recheck(self._segs("表面 1.0081, 温度 33.5770, 另一处写作 1.0990。"),
                             {"q1.C": _claim("1.0081"), "q1.T": _claim("33.5770")})
        self.assertEqual([], report["conflicts"])
        self.assertEqual([], report["missing"])
        self.assertEqual(1, len(report["near_hints"]))
        self.assertEqual("1.0990", report["near_hints"][0]["token"])
        self.assertEqual(0, report["n_fail"])

    def test_abbrev_form_is_covered_silently(self):
        # 0.740 是 0.7403 的合法缩写形态 (四舍五入) → C 级静默, 不进冲突/提示
        report = run_recheck(self._segs("步长 0.740 与原值 0.7403 均出现。"),
                             {"q1.dt": _claim("0.7403")})
        self.assertEqual([], report["conflicts"])
        self.assertEqual([], report["warn_numbers"])
        self.assertEqual(0, report["n_fail"])

    def test_sci_abbrev_form_is_covered_silently(self):
        # 2.09×10⁻³ 是 2.0932e-03 的合法缩写 (同指数尾数舍入) → C 级静默
        report = run_recheck(self._segs("温升跨约 2.09×10⁻³ °C, 原值 2.0932e-03。"),
                             {"q1.span": _claim("2.0932e-03")})
        self.assertEqual([], report["conflicts"])
        self.assertEqual([], report["warn_numbers"])
        self.assertEqual(0, report["n_fail"])

    def test_c_level_counts_covered_silently(self):
        # 与冻结值精确一致 → 计入 C 级覆盖计数, 不打扰
        report = run_recheck(self._segs("温度 33.5770 °C。"), {"q1.T": _claim("33.5770")})
        self.assertEqual(1, report["n_soft_covered"])
        self.assertEqual([], report["warn_numbers"])

    # ---- 来源登记复用 (C7): 覆盖可变分类 / 未找到 ≠ 不存在 ----
    def test_source_registry_coverage_is_silent(self):
        with tempfile.TemporaryDirectory() as td:
            ws = _workspace(Path(td), {"results/q9.json": {"y": 12.345}})
            prov = load_provenance(ws)
            report = run_recheck(self._segs("另一处结果 12.345 出现。"),
                                 {"q1.T": _claim("33.5770")}, provenance=prov)
        self.assertEqual([], report["warn_numbers"])
        self.assertEqual([], report["uncovered"])
        self.assertEqual(1, report["n_source_covered"])

    def test_registry_change_moves_classification(self):
        """修改登记来源能改变分类: 补一个含同值的结果文件 → 未覆盖变 C 级覆盖。"""
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            ws = _workspace(td_path, {"results/q1.json": {"other": 1.0}})
            before = run_recheck(self._segs("另一处结果 12.345 出现。"),
                                 {"q1.T": _claim("33.5770")},
                                 provenance=load_provenance(ws))
            self.assertIn("12.345", before["warn_numbers"])
            self.assertEqual(0, before["n_source_covered"])
            (ws / "results" / "q2.json").write_text(json.dumps({"y": 12.345}),
                                                    encoding="utf-8")
            after = run_recheck(self._segs("另一处结果 12.345 出现。"),
                                {"q1.T": _claim("33.5770")},
                                provenance=load_provenance(ws))
        self.assertNotIn("12.345", after["warn_numbers"])
        self.assertEqual(1, after["n_source_covered"])

    def test_ledger_result_field_is_provenance(self):
        # 证据账本 (trace_claims 输入) 的 result 字段数字同样算登记来源
        with tempfile.TemporaryDirectory() as td:
            ws = _workspace(Path(td), {
                "state/evidence_ledger.json": [
                    {"question": "Q3", "result": "峰值 12.345 万人"}
                ]})
            prov = load_provenance(ws)
            report = run_recheck(self._segs("另一处结果 12.345 出现。"),
                                 {"q1.T": _claim("33.5770")}, provenance=prov)
        self.assertEqual(1, prov["ledger_rows"])
        self.assertNotIn("12.345", report["warn_numbers"])
        self.assertEqual(1, report["n_source_covered"])

    def test_run_manifest_paths_are_registry_signal(self):
        # run_manifest.jsonl 存在即视为有登记来源 (available=True), 路径进 provenance
        with tempfile.TemporaryDirectory() as td:
            ws = _workspace(Path(td), {
                "results/run_manifest.jsonl": [
                    {"script": "solve.py", "outputs": [{"path": "results/q1.json"}]}
                ]})
            prov = load_provenance(ws)
        self.assertEqual(1, prov["manifest_records"])
        self.assertIn("results/q1.json", prov["manifest_files"])
        self.assertTrue(prov["available"])

    def test_missing_registry_marks_uncovered_honestly(self):
        """登记不足时不得推论数字为假: 未覆盖条目要写明"登记不足", 措辞"未找到 ≠ 不存在"。"""
        report = run_recheck(self._segs("另一处结果 12.345 出现。"),
                             {"q1.T": _claim("33.5770")},
                             provenance={"available": False, "entries": []})
        self.assertIn("12.345", report["warn_numbers"])
        entry = report["uncovered"][0]
        self.assertFalse(entry["provenance_available"])
        self.assertIn("未找到 ≠ 不存在", entry["note"])
        self.assertIn("登记来源不足", entry["note"])
        self.assertEqual([], report["conflicts"])

    # ---- 容限配置与证据档声明 ----
    def test_near_sig_digits_tolerance_configurable(self):
        # 默认 2 位前缀 → 0.7450 是邻近候选; 收紧到 3 位 → 不再邻近, 落未覆盖
        frozen = {"q1.dt": _claim("0.7403")}
        wide = run_recheck(self._segs("步长 0.7403 与 0.7450。"), frozen)
        tight = run_recheck(self._segs("步长 0.7403 与 0.7450。"), frozen, near_sig=3)
        self.assertEqual(1, len(wide["near_hints"]))
        self.assertEqual([], tight["near_hints"])
        self.assertIn("0.7450", tight["warn_numbers"])

    def test_sci_rel_tol_tolerance_configurable(self):
        # 默认 0.1% → 2.301×10⁻¹³ 与冻结 2.30e-13 判同值 (门禁过);
        # 收紧到 1e-6 → 不再等价, 冻结值判缺失 (容限真的在起作用)
        frozen = {"q1.res": _claim("2.30e-13")}
        loose = run_recheck(self._segs("残差为 2.301×10⁻¹³。"), frozen)
        tight = run_recheck(self._segs("残差为 2.301×10⁻¹³。"), frozen, sci_rel_tol=1e-6)
        self.assertEqual(0, loose["n_fail"])
        self.assertEqual(1, tight["n_fail"])

    def test_evidence_tiers_declared(self):
        report = run_recheck(self._segs("温度 33.5770 °C。"), {"q1.T": _claim("33.5770")})
        tiers = report["evidence_tiers"]
        self.assertIn("显式关联", tiers["hard"])
        self.assertIn("只提示", tiers["hint"])
        self.assertIn("不构成", tiers["scope_note"])


@unittest.skipUnless(HAS_PYTHON_DOCX, "需要 python-docx")
class MainCliTest(unittest.TestCase):
    def _build_docx(self, tmp: Path, text: str) -> Path:
        doc = docx.Document()
        doc.add_paragraph(text)
        path = tmp / "final.docx"
        doc.save(str(path))
        return path

    def _build_frozen(self, tmp: Path, claims: dict) -> Path:
        path = tmp / "frozen_numbers.json"
        path.write_text(json.dumps(claims, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        return path

    def _run(self, docx_path, frozen_path, extra=None):
        buf = io.StringIO()
        args = ["--docx", str(docx_path), "--frozen", str(frozen_path),
                "--workspace", str(Path(docx_path).parent)]
        args.extend(extra or [])
        with contextlib.redirect_stdout(buf):
            rc = main(args)
        return rc, buf.getvalue()

    def test_exit_1_when_frozen_number_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._build_docx(Path(tmp), "只有 11.11 一个数。")
            f = self._build_frozen(Path(tmp), {"q1": _claim("33.5770")})
            rc, out = self._run(d, f)
            self.assertEqual(1, rc)
            self.assertIn("[FAIL] q1 = 33.5770", out)

    def test_exit_0_when_frozen_number_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._build_docx(Path(tmp), "温度 33.5770 °C。")
            f = self._build_frozen(Path(tmp), {"q1": _claim("33.5770")})
            rc, out = self._run(d, f)
            self.assertEqual(0, rc)
            self.assertIn("[OK]", out)

    def test_missing_inputs_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, _ = self._run(Path(tmp) / "nope.docx",
                              self._build_frozen(Path(tmp), {}))
            self.assertEqual(2, rc)

    def test_bad_tolerance_args_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._build_docx(Path(tmp), "温度 33.5770 °C。")
            f = self._build_frozen(Path(tmp), {"q1": _claim("33.5770")})
            rc, out = self._run(d, f, ["--near-sig-digits", "0"])
            self.assertEqual(2, rc)
            self.assertIn("--near-sig-digits", out)
            rc, out = self._run(d, f, ["--sci-rel-tol", "2"])
            self.assertEqual(2, rc)
            self.assertIn("--sci-rel-tol", out)

    def test_json_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._build_docx(Path(tmp), "温度 33.5770 °C。")
            f = self._build_frozen(Path(tmp), {"q1": _claim("33.5770")})
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main(["--docx", str(d), "--frozen", str(f),
                           "--workspace", tmp, "--json"])
            self.assertEqual(0, rc)
            data = json.loads(buf.getvalue())
            self.assertEqual(0, data["n_fail"])
            self.assertEqual(1, data["n_pass"])

    def test_table_numbers_counted(self):
        # 表格单元格里的数字参与回检 (w:tbl 遍历)
        with tempfile.TemporaryDirectory() as tmp:
            doc = docx.Document()
            doc.add_paragraph("结果见下表。")
            table = doc.add_table(rows=2, cols=2)
            table.cell(0, 0).text = "时刻"
            table.cell(1, 0).text = "1800"
            table.cell(1, 1).text = "36.7864"
            d = Path(tmp) / "final.docx"
            doc.save(str(d))
            f = self._build_frozen(Path(tmp), {"q1.s": _claim("36.7864")})
            rc, _ = self._run(d, f)
            self.assertEqual(0, rc)

    # ---- A5/C7 CLI 输出结构 ----
    def test_confirm_list_section_and_action_last_line(self):
        # ≥3 位有效数字冻结值仅见缩写 → 确认清单一节 + 末行 ACTION, 门禁不拦
        with tempfile.TemporaryDirectory() as tmp:
            d = self._build_docx(Path(tmp), "最大显式步长约 0.74 s。")
            f = self._build_frozen(Path(tmp), {"q1.dt": _claim("0.7403")})
            rc, out = self._run(d, f)
            self.assertEqual(0, rc)
            self.assertIn("⚠️ 缩写形态需人工确认（1 条）", out)
            self.assertIn("q1.dt = 0.7403", out)
            self.assertIn("0.74", out)
            self.assertEqual("ACTION: stage9-必查 缩写确认 1 条",
                             out.strip().splitlines()[-1].strip())
            self.assertIn("[OK]", out)

    def test_no_action_line_without_confirm_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._build_docx(Path(tmp), "温度 33.5770 °C。")
            f = self._build_frozen(Path(tmp), {"q1": _claim("33.5770")})
            rc, out = self._run(d, f)
            self.assertEqual(0, rc)
            self.assertNotIn("ACTION:", out)
            self.assertNotIn("缩写形态需人工确认", out)

    def test_explicit_conflict_exit_1(self):
        # 显式 claim 标签 + 末位小差 → ❌ 拦门禁; 正确值仍在别处出现也不放过
        with tempfile.TemporaryDirectory() as tmp:
            d = self._build_docx(Path(tmp), "q3.t = 57.5403 h, 另处写作 57.5406 h。")
            f = self._build_frozen(Path(tmp), {"q3.t": _claim("57.5406", unit="h")})
            rc, out = self._run(d, f)
            self.assertEqual(1, rc)
            self.assertIn("[FAIL-A] 57.5403", out)
            self.assertIn("q3.t=57.5406", out)
            self.assertIn("claim_label:q3.t", out)

    def test_weak_and_near_hints_print_but_not_blocking(self):
        # 同单位弱关联 (33.6000 vs 33.5770) 只提示: 独立成节、不拦门禁
        with tempfile.TemporaryDirectory() as tmp:
            d = self._build_docx(Path(tmp), "入口温度 33.6000 °C, 冻结 33.5770 °C。")
            f = self._build_frozen(Path(tmp), {"q1.T": _claim("33.5770", unit="°C")})
            rc, out = self._run(d, f)
            self.assertEqual(0, rc)
            self.assertIn("弱关联", out)
            self.assertIn("33.6000", out)
            self.assertNotIn("[FAIL-A]", out)

    def test_unit_mismatch_section_printed(self):
        # 独立量对照 (1.0081 kg vs 1.0990 °C) 打印为不同量, 不判冲突
        with tempfile.TemporaryDirectory() as tmp:
            d = self._build_docx(Path(tmp), "试样质量 1.0081 kg, 温度 1.0990 °C。")
            f = self._build_frozen(Path(tmp), {"q1.m": _claim("1.0081", unit="kg")})
            rc, out = self._run(d, f)
            self.assertEqual(0, rc)
            self.assertIn("不同量对照", out)
            self.assertIn("1.0990", out)
            self.assertNotIn("[FAIL-A]", out)

    def test_evidence_tier_statement_printed(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._build_docx(Path(tmp), "温度 33.5770 °C。")
            f = self._build_frozen(Path(tmp), {"q1": _claim("33.5770")})
            rc, out = self._run(d, f)
            self.assertEqual(0, rc)
            self.assertIn("证据口径: 只声明两档", out)
            self.assertIn("不构成", out)

    def test_report_file_written_with_path_printed(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._build_docx(Path(tmp), "温度 33.5770 °C。")
            f = self._build_frozen(Path(tmp), {"q1": _claim("33.5770")})
            report_path = Path(tmp) / "state" / "recheck.json"
            rc, out = self._run(d, f, ["--report", str(report_path)])
            self.assertEqual(0, rc)
            self.assertIn("详细报告:", out)
            data = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(1, data["n_pass"])
            self.assertIn("evidence_tiers", data)

    def test_ambiguous_abbrev_exit_1(self):
        # 同前缀多冻结项 (0.7403/0.7253 同享 0.7 缩写) → 强制全匹配, exit 1
        with tempfile.TemporaryDirectory() as tmp:
            d = self._build_docx(Path(tmp), "最大显式步长取 0.7 s。")
            f = self._build_frozen(Path(tmp),
                                   {"a.dt": _claim("0.7403"), "b.sobol": _claim("0.7253")})
            rc, out = self._run(d, f)
            self.assertEqual(1, rc)
            self.assertIn("歧义", out)
            self.assertIn("[FAIL]", out)

    def test_json_output_has_tier_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._build_docx(Path(tmp), "步长约 0.74 s, 另见 0.7450。")
            f = self._build_frozen(Path(tmp), {"q1.dt": _claim("0.7403")})
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main(["--docx", str(d), "--frozen", str(f),
                           "--workspace", tmp, "--json"])
            self.assertEqual(0, rc)
            data = json.loads(buf.getvalue())
            for key in ("abbrev_confirm", "abbrev_only", "conflicts",
                        "a_candidates", "warn_numbers", "n_soft_covered",
                        "n_source_covered", "weak_associations", "near_hints",
                        "unit_mismatch", "uncovered", "provenance",
                        "source_drift", "source_notes",
                        "evidence_tiers", "n_fail"):
                self.assertIn(key, data)
            self.assertIn("value_evidence", data["provenance"])
            self.assertIn("path_registration_only", data["provenance"])
            self.assertEqual(1, len(data["abbrev_confirm"]))
            self.assertEqual([], data["conflicts"])
            self.assertEqual(1, len(data["a_candidates"]))
            self.assertEqual(0, data["n_fail"])


if __name__ == "__main__":
    unittest.main()
