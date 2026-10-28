import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from onchain_reconstruction.cli import main
from tools.export import export

ROOT = Path(__file__).resolve().parents[1]


class ReleaseTests(unittest.TestCase):
    def test_offline_csv_and_markdown_commands(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(["import-csv", str(ROOT / "examples/movements.csv")]), 0)
        self.assertEqual(len(json.loads(out.getvalue())["events"]), 6)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(["reconcile", str(ROOT / "examples/ledger.json"), "--format", "markdown"]), 0)
        self.assertIn("Reconciled: True", out.getvalue())

    def test_discrepancy_cli_is_nonzero(self):
        document = json.loads((ROOT / "examples/ledger.json").read_text())
        document["observed"]["31337:native"] = "0"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            path.write_text(json.dumps(document))
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(main(["reconcile", str(path)]), 2)
            self.assertFalse(json.loads(out.getvalue())["reconciled"])

    def test_export_is_scoped_and_refuses_existing_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "release"
            count = export(destination)
            self.assertGreater(count, 10)
            self.assertTrue((destination / "README.md").is_file())
            self.assertFalse((destination / "data").exists())
            self.assertFalse((destination / "cache").exists())
            self.assertFalse((destination / "__pycache__").exists())
            self.assertFalse((destination / ".git").exists())
            with self.assertRaises(ValueError):
                export(destination)

    def test_export_refuses_nested_destination(self):
        with self.assertRaises(ValueError):
            export(ROOT / "nested-release-must-not-exist")

    def test_catalog_covers_every_original_once(self):
        document = json.loads((ROOT / "docs/source-catalog.json").read_text())
        rows = document["entries"]
        self.assertEqual(document["scripts"], 258)
        self.assertEqual(len({row["entry_id"] for row in rows}), 258)
        self.assertEqual(sum(row["lines"] for row in rows), document["lines"])
        self.assertTrue(all("file" not in row and "sha256" not in row for row in rows))


if __name__ == "__main__":
    unittest.main()
