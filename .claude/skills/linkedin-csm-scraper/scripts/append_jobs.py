#!/usr/bin/env python3
"""
append_jobs.py — Deduplicates and appends new job rows to the ONE master tracker.

There is exactly one data file: csm_jobs.csv in the project root. This script will
refuse to write to any other filename, always creates the master with the full
canonical header if it's missing, and always writes rows that match the existing
header exactly — so the column layout can never drift out of sync with the dashboard.

Usage:
    python append_jobs.py --csv /path/to/csm_jobs.csv --jobs '[{"job_id": "123", ...}, ...]'

The --jobs argument is a JSON array of job dicts (scraper fields only; enrichment
columns are left blank and filled later by the enrichment skill).

Exits 0 and prints a summary of how many jobs were added vs skipped.
"""

import argparse
import csv
import importlib.util
import json
import os
import sys
from datetime import date

# --- Embedded fallback schema (used only if schema.py can't be found) ----------
# The authoritative copy lives in <project_root>/schema.py. These constants are a
# safety net so the script still works if run outside the project for some reason.
_FALLBACK_MASTER = "csm_jobs.csv"
_FALLBACK_CANONICAL = [
    "job_id", "date_scraped", "job_title", "company", "company_tagline", "industry",
    "hq_location", "company_size", "job_location", "salary", "work_authorization",
    "applicant_count",
    "easy_apply", "linkedin_job_url", "company_linkedin_url", "company_website",
    "key_requirements", "outreach_status",
    "contact1_name", "contact1_title", "contact1_linkedin", "contact1_dm",
    "contact2_name", "contact2_title", "contact2_linkedin", "contact2_dm",
    "contact3_name", "contact3_title", "contact3_linkedin", "contact3_dm",
    "contact4_name", "contact4_title", "contact4_linkedin", "contact4_dm",
    "cover_letter_path", "discovered_execs",
]
_FALLBACK_DEFAULTS = {"outreach_status": "Not started"}


def find_project_root() -> str:
    """Locate the project root deterministically, independent of the CWD.

    This script lives at <root>/.claude/skills/<skill>/scripts/append_jobs.py,
    so the project root is four directories up. We confirm by checking for
    schema.py (the project marker). If that fails (e.g. the script was copied
    elsewhere), we walk upward looking for schema.py, and finally fall back to
    the CWD. This is what lets a scheduled task run the scrape correctly even
    when its working directory isn't the project folder.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.abspath(os.path.join(here, "..", "..", "..", ".."))
    if os.path.exists(os.path.join(candidate, "schema.py")):
        return candidate
    d = here
    for _ in range(6):
        if os.path.exists(os.path.join(d, "schema.py")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return os.getcwd()


def load_schema(csv_path: str):
    """Load schema.py sitting next to the master CSV; fall back to embedded constants."""
    schema_path = os.path.join(os.path.dirname(os.path.abspath(csv_path)), "schema.py")
    if os.path.exists(schema_path):
        spec = importlib.util.spec_from_file_location("schema", schema_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    # Fallback shim mimicking the schema module's surface.
    class _Shim:
        MASTER_CSV_NAME = _FALLBACK_MASTER
        CANONICAL_COLUMNS = list(_FALLBACK_CANONICAL)
        DEFAULTS = dict(_FALLBACK_DEFAULTS)

        @staticmethod
        def assert_master_path(p):
            if os.path.basename(p) != _FALLBACK_MASTER:
                raise SystemExit(
                    f"REFUSING TO WRITE: '{os.path.basename(p)}' is not the master tracker "
                    f"({_FALLBACK_MASTER})."
                )

        @staticmethod
        def ensure_csv(p):
            _Shim.assert_master_path(p)
            if os.path.exists(p):
                return False
            os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
            with open(p, "w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=_FALLBACK_CANONICAL).writeheader()
            return True

        @staticmethod
        def read_header(p):
            if not os.path.exists(p):
                return None
            with open(p, newline="", encoding="utf-8") as f:
                return csv.DictReader(f).fieldnames
    return _Shim()


def load_existing_ids(csv_path: str) -> set:
    if not os.path.exists(csv_path):
        return set()
    with open(csv_path, newline="", encoding="utf-8") as f:
        return {row["job_id"] for row in csv.DictReader(f) if row.get("job_id")}


def load_seen_ids(cache_path: str) -> set:
    if not os.path.exists(cache_path):
        return set()
    with open(cache_path, encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def update_seen_ids(cache_path: str, new_ids: list):
    with open(cache_path, "a", encoding="utf-8") as f:
        for job_id in new_ids:
            f.write(job_id + "\n")


def main():
    parser = argparse.ArgumentParser(description="Append new jobs to the master tracker CSV.")
    parser.add_argument("--csv", default=os.path.join(find_project_root(), "csm_jobs.csv"),
                        help="Path to the master csm_jobs.csv (default: auto-located project root)")
    parser.add_argument("--jobs", help="JSON array of job dicts")
    parser.add_argument("--print-root", action="store_true",
                        help="Print the auto-located project root and exit.")
    args = parser.parse_args()

    if args.print_root:
        print(find_project_root())
        return

    if not args.jobs:
        print("ERROR: --jobs is required (unless --print-root)", file=sys.stderr)
        sys.exit(1)

    schema = load_schema(args.csv)

    # Guardrail: only ever the master file.
    schema.assert_master_path(args.csv)

    try:
        jobs = json.loads(args.jobs)
    except json.JSONDecodeError as e:
        print(f"ERROR: Could not parse --jobs JSON: {e}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(jobs, list):
        print("ERROR: --jobs must be a JSON array", file=sys.stderr)
        sys.exit(1)

    # Create the master with the full canonical header if it doesn't exist yet.
    schema.ensure_csv(args.csv)

    # The existing header is the authoritative write order (always full-width).
    header = schema.read_header(args.csv) or list(schema.CANONICAL_COLUMNS)

    cache_path = os.path.join(os.path.dirname(args.csv), "seen_job_ids.txt")
    seen_ids = load_seen_ids(cache_path)
    existing_ids = load_existing_ids(args.csv)
    today = date.today().isoformat()

    added = 0
    skipped = 0
    ids_to_cache = []
    batch_seen = set()

    with open(args.csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        for job in jobs:
            job_id = str(job.get("job_id", "")).strip()
            if not job_id:
                print(f"  WARNING: skipping job with no job_id: {job.get('job_title', '?')}")
                skipped += 1
                continue
            if job_id in seen_ids or job_id in existing_ids or job_id in batch_seen:
                skipped += 1
                batch_seen.add(job_id)
                continue

            # Build a full-width row: blank for every column we don't have.
            row = {col: job.get(col, "") for col in header}
            if not row.get("date_scraped"):
                row["date_scraped"] = today
            for col, default in schema.DEFAULTS.items():
                if col in row and not row[col]:
                    row[col] = default

            writer.writerow(row)
            existing_ids.add(job_id)
            batch_seen.add(job_id)
            ids_to_cache.append(job_id)
            added += 1

    if ids_to_cache:
        update_seen_ids(cache_path, ids_to_cache)

    print(f"Done. Added: {added} | Skipped (duplicates): {skipped} | CSV: {args.csv}")


if __name__ == "__main__":
    main()
