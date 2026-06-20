#!/usr/bin/env python3
"""
update_contacts.py — Update or delete a row in the ONE master tracker (csm_jobs.csv).

There is exactly one data file: csm_jobs.csv in the project root. This script refuses
to operate on any other filename, and always preserves the existing header order — it
only fills in the enrichment columns for the matching row, never reshapes the file.

Two modes:

  UPDATE (default) — fill enrichment fields for a job:
      python update_contacts.py --csv /path/csm_jobs.csv --job_id 123 \
          --data '{"contact1_name": "...", "cover_letter_path": "...", ...}'

  DELETE — remove a job that yielded ZERO usable contacts (low-signal / likely not a
  serious company). The job_id stays in seen_job_ids.txt so the scraper never re-adds it:
      python update_contacts.py --csv /path/csm_jobs.csv --job_id 123 --delete

Prints a summary line on success.
"""

import argparse
import csv
import importlib.util
import json
import os
import sys

_FALLBACK_MASTER = "csm_jobs.csv"
_FALLBACK_ENRICHMENT = [
    "contact1_name", "contact1_title", "contact1_linkedin", "contact1_dm",
    "contact2_name", "contact2_title", "contact2_linkedin", "contact2_dm",
    "contact3_name", "contact3_title", "contact3_linkedin", "contact3_dm",
    "contact4_name", "contact4_title", "contact4_linkedin", "contact4_dm",
    "cover_letter_path",
]


def load_schema(csv_path: str):
    """Load schema.py next to the master CSV; fall back to embedded constants."""
    schema_path = os.path.join(os.path.dirname(os.path.abspath(csv_path)), "schema.py")
    if os.path.exists(schema_path):
        spec = importlib.util.spec_from_file_location("schema", schema_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    class _Shim:
        MASTER_CSV_NAME = _FALLBACK_MASTER
        ENRICHMENT_COLUMNS = list(_FALLBACK_ENRICHMENT)

        @staticmethod
        def assert_master_path(p):
            if os.path.basename(p) != _FALLBACK_MASTER:
                raise SystemExit(
                    f"REFUSING TO WRITE: '{os.path.basename(p)}' is not the master tracker "
                    f"({_FALLBACK_MASTER})."
                )
    return _Shim()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to the master csm_jobs.csv")
    parser.add_argument("--job_id", required=True, help="Job ID of the row to update/delete")
    parser.add_argument("--data", help="JSON object of enrichment fields to update")
    parser.add_argument("--delete", action="store_true",
                        help="Delete this row (use when zero contacts were found).")
    args = parser.parse_args()

    schema = load_schema(args.csv)
    schema.assert_master_path(args.csv)

    csv_path = args.csv
    job_id = str(args.job_id).strip()

    if not os.path.exists(csv_path):
        print(f"Error: master CSV not found at {csv_path}", file=sys.stderr)
        sys.exit(1)

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    # ---------- DELETE MODE ----------
    if args.delete:
        before = len(rows)
        rows = [r for r in rows if str(r.get("job_id", "")).strip() != job_id]
        if len(rows) == before:
            print(f"Error: job_id '{job_id}' not found in CSV", file=sys.stderr)
            sys.exit(1)
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        print(f"Done. Deleted job_id={job_id} (zero contacts — left in seen cache so it "
              f"won't be re-scraped) | CSV: {csv_path}")
        return

    # ---------- UPDATE MODE ----------
    if not args.data:
        print("Error: --data is required unless --delete is given", file=sys.stderr)
        sys.exit(1)
    try:
        updates = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"Error: --data is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # Ensure all enrichment columns exist (in case of an older/partial header).
    for col in schema.ENRICHMENT_COLUMNS:
        if col not in fieldnames:
            fieldnames.append(col)

    matched = False
    for row in rows:
        if str(row.get("job_id", "")).strip() == job_id:
            for key, val in updates.items():
                if key in fieldnames:
                    row[key] = val
            matched = True
            break

    if not matched:
        print(f"Error: job_id '{job_id}' not found in CSV", file=sys.stderr)
        sys.exit(1)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            for col in fieldnames:
                row.setdefault(col, "")
            writer.writerow(row)

    print(f"Done. Updated job_id={job_id} | Fields: {', '.join(updates.keys())} | CSV: {csv_path}")


if __name__ == "__main__":
    main()
