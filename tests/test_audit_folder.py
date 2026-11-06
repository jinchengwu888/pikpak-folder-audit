"""Offline regressions: only a locally generated fake CLI is executed."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


HELPER = (Path(__file__).resolve().parents[1] / "skills" / "pikpak-folder-audit"
          / "scripts" / "audit_folder.py")
spec = importlib.util.spec_from_file_location("audit_folder", HELPER)
audit_folder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_folder)

FAKE_CLI = r'''
import json
import os
from pathlib import Path
import sys

fixture = Path(os.environ["AUDIT_TEST_FIXTURE"])
scenario = json.loads(fixture.read_text())
args = sys.argv[1:]
with fixture.with_suffix(".calls").open("a") as handle:
    handle.write(json.dumps(args) + "\n")
if args == ["--version"]:
    print(scenario.get("version", "pikpak version v0.6.0"))
    raise SystemExit(0)
if args[:6] != ["ls", "--raw", "-F", "json", "--limit", "100"]:
    raise SystemExit("unexpected command")
token = next((arg[8:] for arg in args if arg.startswith("--token=")), "")
page = scenario["pages"][token]
if "error" in page:
    print(page["error"], file=sys.stderr)
    raise SystemExit(7)
print(page["literal"] if "literal" in page else json.dumps(page))
'''


def file_row(ident, name="movie.mp4", size="100", mime="video/mp4", **extra):
    return {"id": ident, "parent_id": "folder_A", "name": name,
            "kind": "drive#file", "size": size, "mime_type": mime, **extra}


class FolderAuditTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="pikpak-audit-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.fixture = self.root / "fixture.json"
        self.cli = self.root / "fake-pikpak"
        self.cli.write_text("#!" + sys.executable + "\n" + FAKE_CLI)
        self.cli.chmod(0o700)

    def run_audit(self, pages, *, folder_id="folder_A", max_pages=3, version=None):
        scenario = {"pages": pages}
        if version is not None:
            scenario["version"] = version
        self.fixture.write_text(json.dumps(scenario))
        calls_path = self.fixture.with_suffix(".calls")
        calls_path.unlink(missing_ok=True)
        result = subprocess.run(
            [sys.executable, str(HELPER), "--folder-id=" + folder_id,
             "--cli=" + str(self.cli), "--max-pages=" + str(max_pages)],
            cwd=self.root,
            env={"AUDIT_TEST_FIXTURE": str(self.fixture),
                 "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True, text=True, timeout=10)
        self.assertEqual(result.stderr, "")
        report = json.loads(result.stdout)
        calls = [json.loads(line) for line in calls_path.read_text().splitlines()]
        self.assertEqual(calls[0], ["--version"])
        for call in calls[1:]:
            self.assertEqual(call[:6], ["ls", "--raw", "-F", "json", "--limit", "100"])
            self.assertTrue(all(arg.startswith(("--parent=", "--token=")) for arg in call[6:]))
            self.assertEqual([arg for arg in call if arg.startswith("--parent=")],
                             ["--parent=" + folder_id] if folder_id else [])
        return result.returncode, report, calls

    def test_two_pages_sizes_media_candidates_and_read_only_arguments(self):
        token = "next-$(touch INJECTION_SENTINEL)&x=y"
        first = [file_row("f1"), file_row("f2", "empty.mp4", "0"),
                 file_row("f3", "manual.pdf", None, "application/pdf"),
                 file_row("f4", "cover.png", "50", "image/png"),
                 file_row("b", "child", "99999", kind="drive#folder")]
        second = [file_row("f1"), file_row("f5"),
                  file_row("f6", "track.mp3", "25", "audio/mpeg"),
                  file_row("f7", "unknown.mov", "1.2 GB", ""),
                  file_row("f8", "Movie.mp4"),
                  file_row("f9", "$(touch INJECTION_SENTINEL)", "3", "text/plain")]
        code, report, calls = self.run_audit({
            "": {"files": first, "next_page_token": token},
            token: {"files": second, "next_page_token": ""}})
        self.assertEqual((code, report["status"], report["pages_read"]), (0, "complete", 2))
        self.assertFalse(report["more_pages_available"])
        self.assertEqual(report["counts"], {"files": 9, "folders": 1,
                         "unknown_size_files": 2, "zero_size_files": 1})
        self.assertEqual(report["known_logical_bytes"], 378)
        self.assertEqual(report["repeated_id_rows"], 1)
        self.assertEqual(report["media_by_reported_mime"],
                         {"audio": 1, "image": 1, "other": 2, "unknown": 1, "video": 4})
        self.assertEqual(report["name_size_candidate_group_count"], 1)
        self.assertEqual(report["name_size_candidate_examples"], [{
            "name": "movie.mp4", "size_bytes": 100, "member_count": 2,
            "file_ids": ["f1", "f5"], "content_equality_verified": False}])
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[2][-1], "--token=" + token)
        self.assertFalse((self.root / "INJECTION_SENTINEL").exists())

    def test_media_mime_types_are_case_insensitive(self):
        rows = [file_row("v", mime="VIDEO/MP4"), file_row("a", mime="Audio/MPEG"),
                file_row("i", mime="IMAGE/PNG")]
        code, report, _ = self.run_audit({"": {"files": rows}})
        self.assertEqual(code, 0)
        self.assertEqual(report["media_by_reported_mime"], {"audio": 1, "image": 1, "video": 1})

    def test_root_scope_and_empty_folder(self):
        code, report, calls = self.run_audit({"": {"files": []}}, folder_id="")
        self.assertEqual((code, report["status"], report["known_logical_bytes"]), (0, "complete", 0))
        self.assertEqual(report["scope"], {"folder_id": "", "depth": "direct_children",
                                          "atomic_snapshot": False})
        self.assertEqual(len(calls), 2)

    def test_page_cap_preserves_partial_totals_without_retry(self):
        code, report, calls = self.run_audit({
            "": {"files": [file_row("f")], "next_page_token": "next"}}, max_pages=1)
        self.assertEqual((code, report["status"]), (2, "partial"))
        self.assertIn("page_limit_reached", report["reasons"])
        self.assertTrue(report["more_pages_available"])
        self.assertEqual(report["known_logical_bytes"], 100)
        self.assertEqual(len(calls), 2)

    def test_cli_error_preserves_first_page_and_hides_stderr(self):
        code, report, calls = self.run_audit({
            "": {"files": [file_row("f")], "next_page_token": "next"},
            "next": {"error": "AUTH_ERROR credential=PRIVATE_SECRET"}})
        self.assertEqual((code, report["status"]), (2, "partial"))
        self.assertEqual(report["reasons"], ["cli_error"])
        self.assertEqual(report["known_logical_bytes"], 100)
        self.assertNotIn("PRIVATE_SECRET", json.dumps(report))
        self.assertEqual(len(calls), 3)

    def test_token_loop_stops_before_repeated_request(self):
        code, report, calls = self.run_audit({
            "": {"files": [file_row("f")], "next_page_token": "next"},
            "next": {"files": [file_row("g")], "next_page_token": "next"}})
        self.assertEqual(code, 2)
        self.assertIn("pagination_loop", report["reasons"])
        self.assertEqual(len(calls), 3)

    def test_conflicting_id_marks_partial_and_counts_id_once(self):
        code, report, _ = self.run_audit({
            "": {"files": [file_row("f")], "next_page_token": "next"},
            "next": {"files": [file_row("f", size="200")]}})
        self.assertEqual(code, 2)
        self.assertEqual(report["counts"]["files"], 1)
        self.assertEqual(report["known_logical_bytes"], 100)
        self.assertIn("metadata_changed_for_same_id", report["reasons"])

    def test_invalid_and_out_of_scope_rows_are_not_counted(self):
        rows = [None, {}, file_row("", name="empty id"), file_row("x", parent_id="other"),
                file_row("y", kind="unknown-kind"), file_row("good")]
        code, report, _ = self.run_audit({"": {"files": rows}})
        self.assertEqual(code, 2)
        self.assertEqual(report["invalid_or_out_of_scope_rows"], 5)
        self.assertEqual(report["counts"]["files"], 1)
        self.assertIn("invalid_or_out_of_scope_rows", report["reasons"])

    def test_invalid_json_and_listing_schema_fail_closed(self):
        for page, reason in [({"literal": "not JSON PRIVATE_SECRET"}, "invalid_cli_json"),
                             ({"files": {}}, "unexpected_listing_schema")]:
            with self.subTest(reason=reason):
                code, report, calls = self.run_audit({"": page})
                self.assertEqual((code, report["status"]), (1, "failed"))
                self.assertEqual(report["reasons"], [reason])
                self.assertNotIn("PRIVATE_SECRET", json.dumps(report))
                self.assertEqual(len(calls), 2)

    def test_invalid_page_token_makes_observed_page_partial(self):
        code, report, _ = self.run_audit({"": {"files": [file_row("f")], "next_page_token": 7}})
        self.assertEqual((code, report["status"]), (2, "partial"))
        self.assertIn("invalid_page_token", report["reasons"])
        self.assertIsNone(report["more_pages_available"])

    def test_raw_sensitive_fields_are_not_exported(self):
        row = file_row("f", params={"url": "https://example.invalid/SOURCE_SECRET"},
                       medias=[{"link": {"url": "https://example.invalid/PLAY_SECRET"}}],
                       thumbnail_link="THUMB_SECRET", user_id="ACCOUNT_SECRET")
        code, report, _ = self.run_audit({"": {"files": [row]}})
        self.assertEqual(code, 0)
        serialized = json.dumps(report)
        for marker in ("SOURCE_SECRET", "PLAY_SECRET", "THUMB_SECRET", "ACCOUNT_SECRET"):
            self.assertNotIn(marker, serialized)

    def test_invalid_sizes_remain_unknown_and_zero_pairs_are_not_candidates(self):
        rows = [file_row(str(i), size=value) for i, value in enumerate(
            [None, True, -1, "1.2 GB", "-1", "", "0", 0])]
        code, report, _ = self.run_audit({"": {"files": rows}})
        self.assertEqual(code, 0)
        self.assertEqual(report["counts"]["unknown_size_files"], 6)
        self.assertEqual(report["counts"]["zero_size_files"], 2)
        self.assertEqual(report["known_logical_bytes"], 0)
        self.assertEqual(report["name_size_candidate_group_count"], 0)

    def test_wrong_client_version_stops_before_listing(self):
        code, report, calls = self.run_audit({}, version="pikpaktui 1.0")
        self.assertEqual(code, 1)
        self.assertEqual(report["reasons"], ["unrecognized_cli_version"])
        self.assertEqual(calls, [["--version"]])

    def test_subprocess_timeout_and_os_error_are_sanitized(self):
        version = subprocess.CompletedProcess([], 0, "pikpak version v0.6.0\n")
        page = subprocess.CompletedProcess([], 0, json.dumps({
            "files": [file_row("f")], "next_page_token": "next"}))
        for error, reason in [(subprocess.TimeoutExpired("SECRET", 45), "cli_timeout"),
                              (OSError("PRIVATE_SECRET"), "cli_unavailable")]:
            with self.subTest(reason=reason), patch.object(
                    audit_folder.subprocess, "run", side_effect=[version, page, error]):
                report, code = audit_folder.audit(str(self.cli), "folder_A", 3)
                self.assertEqual((code, report["status"]), (2, "partial"))
                self.assertEqual(report["reasons"], [reason])
                self.assertEqual(report["known_logical_bytes"], 100)
                self.assertNotIn("SECRET", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
