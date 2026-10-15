import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from model_check import validate


class ModelCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.nodes = self.root / "nodes.csv"
        self.members = self.root / "members.csv"
        self.node_text = "node_id,x_m,y_m\n001,0,0\n002,3,0\n003,0,4\n"
        self.member_text = "member_id,start_node_id,end_node_id\nm1,001,002\nm2,002,003\n"

    def check(self, nodes=None, members=None):
        self.nodes.write_text(self.node_text if nodes is None else nodes, encoding="utf-8")
        self.members.write_text(self.member_text if members is None else members, encoding="utf-8")
        before = (self.nodes.read_bytes(), self.members.read_bytes())
        result = validate(self.nodes, self.members)
        self.assertEqual(before, (self.nodes.read_bytes(), self.members.read_bytes()))
        return result

    def codes(self, result):
        return {error["code"] for error in result["errors"]}

    def test_valid_model_preserves_leading_zero_ids(self):
        self.assertEqual(self.check(), {"ok": True, "valid_nodes": 3, "valid_members": 2, "errors": []})

    def test_bom_and_crlf(self):
        self.assertTrue(self.check("\ufeff" + self.node_text.replace("\n", "\r\n"))["ok"])

    def test_header_order_is_irrelevant(self):
        self.assertTrue(self.check("y_m,node_id,x_m\n0,001,0\n0,002,3\n4,003,0\n")["ok"])

    def test_duplicate_and_extra_headers_rejected(self):
        for header in ["node_id,x_m,x_m", "node_id,x_m,y_m,extra"]:
            with self.subTest(header=header):
                self.assertIn("HEADER", self.codes(self.check(header + "\n")))

    def test_nonfinite_and_nonnumeric_coordinates(self):
        for number in ["nan", "inf", "-inf", "1e999", "bad", ""]:
            with self.subTest(number=number):
                self.assertIn("COORDINATE", self.codes(self.check(self.node_text.replace("002,3,0", "002," + number + ",0"))))

    def test_duplicate_node_reports_line(self):
        result = self.check(self.node_text + "001,4,5\n")
        self.assertEqual(next(x["line"] for x in result["errors"] if x["code"] == "DUPLICATE_NODE"), 5)

    def test_missing_reference(self):
        self.assertIn("UNKNOWN_NODE", self.codes(self.check(members=self.member_text.replace("003", "999"))))

    def test_same_id_and_coincident_endpoints(self):
        for end, nodes in [("001", self.node_text), ("002", self.node_text.replace("002,3,0", "002,0,0"))]:
            with self.subTest(end=end):
                self.assertIn("ZERO_LENGTH", self.codes(self.check(nodes, "member_id,start_node_id,end_node_id\nm1,001," + end + "\n")))

    def test_duplicate_and_empty_member_ids(self):
        self.assertIn("DUPLICATE_MEMBER", self.codes(self.check(members=self.member_text + "m1,001,003\n")))
        self.assertIn("MEMBER_ID", self.codes(self.check(members=self.member_text + ",001,003\n")))

    def test_empty_node_id(self):
        self.assertIn("NODE_ID", self.codes(self.check(self.node_text + ",1,2\n")))

    def test_row_width_mismatch(self):
        for row in ["004,1\n", "004,1,2,3\n"]:
            with self.subTest(row=row):
                self.assertIn("ROW_WIDTH", self.codes(self.check(self.node_text + row)))

    def test_quoted_id_with_comma(self):
        nodes = 'node_id,x_m,y_m\n"node,1",0,0\nnode2,1,0\n'
        members = 'member_id,start_node_id,end_node_id\nm1,"node,1",node2\n'
        self.assertTrue(self.check(nodes, members)["ok"])

    def test_malformed_quoted_csv(self):
        self.assertIn("CSV", self.codes(self.check(self.node_text + '"unfinished,1,2\n')))

    def test_missing_and_invalid_utf8_files(self):
        self.assertIn("READ", self.codes(validate(self.nodes, self.members)))
        self.check()
        self.nodes.write_bytes(b"\xff")
        self.assertIn("READ", self.codes(validate(self.nodes, self.members)))

    def test_empty_files_rejected(self):
        result = self.check("", "")
        self.assertFalse(result["ok"])
        self.assertTrue({"HEADER", "NO_NODES", "NO_MEMBERS"} <= self.codes(result))

    def test_cli_json_and_exit_codes(self):
        script = str(Path(__file__).with_name("model_check.py"))
        for bad in [False, True]:
            with self.subTest(bad=bad):
                self.check(members=self.member_text.replace("003", "999") if bad else self.member_text)
                run = subprocess.run([sys.executable, script, str(self.nodes), str(self.members)], capture_output=True, text=True)
                self.assertEqual(run.returncode, 1 if bad else 0)
                self.assertEqual(json.loads(run.stdout)["ok"], not bad)


if __name__ == "__main__":
    unittest.main()
