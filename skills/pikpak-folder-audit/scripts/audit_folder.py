#!/usr/bin/env python3
"""Bounded metadata audit using only the official PikPak CLI's version and ls."""
import argparse
from collections import Counter, defaultdict
import json
import re
import shutil
import subprocess
import sys


def byte_size(value):
    if type(value) is int and value >= 0:
        return value
    if isinstance(value, str) and re.fullmatch(r"[0-9]{1,30}", value):
        return int(value)
    return None


def run(cli, args):
    result = subprocess.run([cli, *args], capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise RuntimeError("cli_error")
    return result.stdout


def audit(cli, folder_id, max_pages):
    reasons, records, seen_tokens = [], {}, set()
    pages, repeated_ids, invalid_rows, more = 0, 0, 0, None
    version = "unknown"
    token = ""
    try:
        version_line = run(cli, ["--version"]).strip()
        if not re.fullmatch(r"pikpak version v?[0-9][0-9A-Za-z.+-]*", version_line):
            raise RuntimeError("unrecognized_cli_version")
        version = version_line
        while pages < max_pages:
            if token in seen_tokens:
                reasons.append("pagination_loop")
                break
            seen_tokens.add(token)
            args = ["ls", "--raw", "-F", "json", "--limit", "100"]
            if folder_id:
                args.append("--parent=" + folder_id)
            if token:
                args.append("--token=" + token)
            page = json.loads(run(cli, args))
            if not isinstance(page, dict) or not isinstance(page.get("files"), list):
                raise RuntimeError("unexpected_listing_schema")
            pages += 1
            for item in page["files"]:
                if (not isinstance(item, dict) or not isinstance(item.get("id"), str)
                        or not item["id"] or not isinstance(item.get("name"), str)
                        or item.get("kind") not in ("drive#file", "drive#folder")
                        or item.get("parent_id", "") != folder_id):
                    invalid_rows += 1
                    continue
                row = {key: item[key] for key in ("id", "name", "kind")}
                row["size_bytes"] = byte_size(item.get("size"))
                row["mime_type"] = item.get("mime_type") if isinstance(item.get("mime_type"), str) else ""
                old = records.get(row["id"])
                if old is not None:
                    repeated_ids += 1
                    if old != row:
                        reasons.append("metadata_changed_for_same_id")
                else:
                    records[row["id"]] = row
            next_token = page.get("next_page_token", "")
            if not isinstance(next_token, str):
                more = None
                raise RuntimeError("invalid_page_token")
            more = bool(next_token)
            if not more:
                break
            token = next_token
        if more and pages == max_pages:
            reasons.append("page_limit_reached")
    except subprocess.TimeoutExpired:
        reasons.append("cli_timeout")
    except (json.JSONDecodeError, UnicodeError):
        reasons.append("invalid_cli_json")
    except (OSError, RuntimeError) as error:
        reasons.append(str(error) if isinstance(error, RuntimeError) else "cli_unavailable")
    if invalid_rows:
        reasons.append("invalid_or_out_of_scope_rows")
    files = sorted((row for row in records.values() if row["kind"] == "drive#file"), key=lambda x: x["id"])
    unknown = [row for row in files if row["size_bytes"] is None]
    zero = [row for row in files if row["size_bytes"] == 0]
    groups, media = defaultdict(list), Counter()
    for row in files:
        size = row["size_bytes"]
        if size is not None and size > 0:
            groups[(row["name"], size)].append(row["id"])
        kind = row["mime_type"].split("/", 1)[0].lower()
        media[kind if kind in ("video", "image", "audio") else ("other" if kind else "unknown")] += 1
    candidates = sorted((key, ids) for key, ids in groups.items() if len(ids) > 1)
    status = "failed" if not pages else ("partial" if reasons else "complete")
    report = {
        "status": status, "reasons": sorted(set(reasons)), "cli_version": version,
        "scope": {"folder_id": folder_id, "depth": "direct_children", "atomic_snapshot": False},
        "pages_read": pages, "more_pages_available": more, "repeated_id_rows": repeated_ids,
        "invalid_or_out_of_scope_rows": invalid_rows,
        "counts": {"files": len(files), "folders": len(records) - len(files),
                   "unknown_size_files": len(unknown), "zero_size_files": len(zero)},
        "known_logical_bytes": sum(row["size_bytes"] for row in files if row["size_bytes"] is not None),
        "media_by_reported_mime": dict(sorted(media.items())),
        "name_size_candidate_group_count": len(candidates),
        "name_size_candidate_examples": [{"name": key[0], "size_bytes": key[1],
                                           "member_count": len(ids), "file_ids": ids[:10],
                                           "content_equality_verified": False} for key, ids in candidates[:10]],
        "zero_size_examples": [{"id": r["id"], "name": r["name"]} for r in zero[:10]],
        "unknown_size_examples": [{"id": r["id"], "name": r["name"]} for r in unknown[:10]],
        "example_limit_per_section": 10,
    }
    return report, {"complete": 0, "partial": 2, "failed": 1}[status]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder-id", required=True, help="Actual folder ID; empty string means root")
    parser.add_argument("--max-pages", type=int, choices=range(1, 21), default=3, metavar="1..20")
    parser.add_argument("--cli", default="pikpak", help="Reviewed official PikPak CLI executable")
    args = parser.parse_args()
    cli = shutil.which(args.cli)
    if cli is None:
        print(json.dumps({"status": "failed", "reasons": ["cli_unavailable"]}))
        return 1
    report, code = audit(cli, args.folder_id, args.max_pages)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
