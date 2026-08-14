import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from utils.asar_utils import (
    get_file_hash_in_asar,
    get_file_hashes_in_asar,
    is_valid_asar,
    parse_asar_header,
    validate_asar_with_reason,
)
from utils.asar_writer import _pickle_write_string, _pickle_write_uint32, asar_pack


class TestAsarUtils(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.src = self.root / "src"
        self.src.mkdir()

        self.package_content = b'{\n  "name": "asar-test"\n}\n'
        self.lang_content = b'console.log("patched");\n'

        (self.src / "package.json").write_bytes(self.package_content)
        tyrano_dir = self.src / "tyrano"
        tyrano_dir.mkdir()
        (tyrano_dir / "lang.js").write_bytes(self.lang_content)

        self.archive = self.root / "app.asar"
        asar_pack(self.src, self.archive)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_detects_generated_archive_as_modern_pickle(self):
        header = parse_asar_header(str(self.archive))

        self.assertIsNotNone(header)
        self.assertEqual(header.format_name, "modern_pickle")
        self.assertTrue(is_valid_asar(str(self.archive)))

    def test_hash_reader_matches_expected_sha256(self):
        package_hash = get_file_hash_in_asar(str(self.archive), "package.json")
        lang_hash = get_file_hash_in_asar(str(self.archive), "tyrano/lang.js")

        self.assertEqual(package_hash, hashlib.sha256(self.package_content).hexdigest())
        self.assertEqual(lang_hash, hashlib.sha256(self.lang_content).hexdigest())

    def test_batch_hash_reader_matches_single_file_reader(self):
        hashes = get_file_hashes_in_asar(
            str(self.archive),
            ["package.json", "tyrano/lang.js", "missing.txt"],
        )

        self.assertEqual(
            hashes["package.json"],
            get_file_hash_in_asar(str(self.archive), "package.json"),
        )
        self.assertEqual(
            hashes["tyrano/lang.js"],
            get_file_hash_in_asar(str(self.archive), "tyrano/lang.js"),
        )
        self.assertIsNone(hashes["missing.txt"])

    def test_invalid_when_archive_payload_is_truncated(self):
        truncated = self.root / "truncated.asar"
        archive_bytes = self.archive.read_bytes()
        truncated.write_bytes(archive_bytes[:-3])

        valid, reason = validate_asar_with_reason(str(truncated))
        self.assertFalse(valid)
        self.assertIn("outside archive", reason)
        self.assertFalse(is_valid_asar(str(truncated)))

    def test_hash_reader_reads_payload_instead_of_trusting_header_integrity(self):
        header = parse_asar_header(str(self.archive))
        self.assertIsNotNone(header)
        payload_offset = header.base_offset
        with self.archive.open("r+b") as archive:
            archive.seek(payload_offset)
            archive.write(b"X")

        self.assertNotEqual(
            get_file_hash_in_asar(str(self.archive), "package.json"),
            hashlib.sha256(self.package_content).hexdigest(),
        )

    def test_invalid_when_archive_contains_escaping_symlink(self):
        header = parse_asar_header(str(self.archive))
        self.assertIsNotNone(header)

        payload = self.archive.read_bytes()[header.base_offset :]
        malicious_header = json.loads(json.dumps(header.header_dict))
        malicious_header["files"]["evil-link"] = {"link": "../../outside.txt"}

        header_json = json.dumps(
            malicious_header, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        header_pickle = _pickle_write_string(header_json)
        size_pickle = _pickle_write_uint32(len(header_pickle))

        malicious = self.root / "malicious-link.asar"
        malicious.write_bytes(size_pickle + header_pickle + payload)

        valid, reason = validate_asar_with_reason(str(malicious))
        self.assertFalse(valid)
        self.assertIn("symlink escapes archive root", reason)
        self.assertFalse(is_valid_asar(str(malicious)))


if __name__ == "__main__":
    unittest.main()
