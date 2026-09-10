"""Behavioral coverage for optional mechanism sidecars and knowledge packs."""

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from mechanism_reviews import load_mechanism_reviews, validate_payload
from build_stage_pack import build_stage_pack, render_markdown


class MechanismReviewsTest(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads((ROOT / "competitions/huaweibei/cases/mechanism_reviews.json").read_text(encoding="utf-8"))
        self.hit = {"competition": "huaweibei", "id": "huaweibei_2025_F"}

    def test_zero_gain_is_valid_and_preserved(self):
        records = validate_payload(self.payload, "huaweibei")
        self.assertEqual(records[0]["validation"], self.payload["records"][0]["validation"])

    def test_absent_sidecar_is_compatible(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual([], load_mechanism_reviews([self.hit], 5, folder))

    def test_corrupt_sidecar_is_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "competitions/huaweibei/cases/mechanism_reviews.json"
            path.parent.mkdir(parents=True)
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_mechanism_reviews([self.hit], 5, folder)

    def test_competition_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_payload(self.payload, "huashubei")

    def test_duplicate_id_is_rejected(self):
        self.payload["records"].append(copy.deepcopy(self.payload["records"][0]))
        with self.assertRaises(ValueError):
            validate_payload(self.payload, "huaweibei")

    def test_missing_boundary_is_rejected(self):
        self.payload["records"][0]["validation"]["not_established"] = ""
        with self.assertRaises(ValueError):
            validate_payload(self.payload, "huaweibei")

    def test_unsupported_promotion_is_rejected(self):
        self.payload["records"][0]["review_status"] = "universally_proven"
        with self.assertRaises(ValueError):
            validate_payload(self.payload, "huaweibei")

    def test_only_matching_case_is_loaded(self):
        self.assertEqual(2, len(load_mechanism_reviews([self.hit], 5)))
        self.assertEqual([], load_mechanism_reviews([{**self.hit, "id": "huaweibei_2025_A"}], 5))

    def test_stage_one_does_not_load_reviews(self):
        self.assertEqual([], load_mechanism_reviews([self.hit], 1))

    def test_traversal_competition_rejected(self):
        with self.assertRaises(ValueError):
            load_mechanism_reviews([{**self.hit, "competition": "../huaweibei"}], 5)

    def test_actual_pack_and_markdown_preserve_records(self):
        pack = build_stage_pack("江南古典园林 美学 景观 游线 幻境", "huaweibei", 5, 1)
        self.assertEqual("huaweibei_2025_F", pack["case_hits"][0]["id"])
        self.assertEqual(2, len(pack["mechanism_reviews"]))
        markdown = render_markdown(pack)
        for record in pack["mechanism_reviews"]:
            self.assertIn(json.dumps(record, ensure_ascii=False, indent=2), markdown)


if __name__ == "__main__":
    unittest.main()
