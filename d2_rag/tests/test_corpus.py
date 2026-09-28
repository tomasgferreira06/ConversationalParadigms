"""Tests for the shared corpus helpers (manifest validation, JSONL format, hashes)."""

import sys
import tempfile
import unittest
from pathlib import Path


D2_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(D2_ROOT / "scripts"))

import corpus  # noqa: E402


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "manifest.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, text):
        self.path.write_text(text, encoding="utf-8")

    def test_records_are_returned_in_file_order(self):
        self._write('{"document_id": "b"}\n\n{"document_id": "a"}\n')
        self.assertEqual([r["document_id"] for r in corpus.load_manifest(self.path)], ["b", "a"])

    def test_invalid_json_duplicate_and_missing_ids_name_the_line(self):
        for text, line in (('{"document_id": "a"}\n{bad\n', 2),
                           ('{"document_id": "a"}\n{"document_id": "a"}\n', 2),
                           ('{"title": "sem id"}\n', 1)):
            with self.subTest(text=text):
                self._write(text)
                with self.assertRaisesRegex(ValueError, f"line {line}"):
                    corpus.load_manifest(self.path)

    def test_missing_manifest_is_reported(self):
        with self.assertRaises(FileNotFoundError):
            corpus.load_manifest(self.path)

    def test_real_manifest_has_35_unique_documents(self):
        self.assertEqual(len(corpus.load_manifest()), 35)


class FormatTests(unittest.TestCase):
    def test_jsonl_keeps_unicode_literal_and_lf_line_endings(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rows.jsonl"
            rows = [{"title": "Sé Velha", "pages": [1, 2]}, {"title": None}]
            corpus.write_jsonl(path, rows)
            self.assertEqual(path.read_bytes(), '{"title": "Sé Velha", "pages": [1, 2]}\n{"title": null}\n'.encode("utf-8"))
            self.assertEqual(corpus.read_jsonl(path), rows)

    def test_file_and_bytes_hashes_agree_in_manifest_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "raw.bin"
            path.write_bytes(b"coimbra")
            self.assertEqual(corpus.sha256_file(path), corpus.sha256_bytes(b"coimbra"))
            self.assertRegex(corpus.sha256_file(path), r"^sha256:[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
