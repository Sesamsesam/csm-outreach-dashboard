#!/usr/bin/env python3
"""
schema.py — THE single source of truth for the job tracker CSV.

There is exactly ONE data file in this project: csm_jobs.csv in the project root.
Its columns are defined here, in one place, and NOWHERE else. The dashboard, the
scraper skill, and the enrichment skill all conform to this list. If you ever need
to add or rename a column, change it HERE and only here.

Why this file exists
--------------------
Agents kept creating second CSVs or writing rows with a different column layout than
the dashboard expected. That can't happen anymore: every script creates and validates
the master file against CANONICAL_COLUMNS below, so there is never a "which CSV?" or
"why are the columns misaligned?" ambiguity.

Run this file directly to (re)create an EMPTY master tracker with the correct headers:

    python3 schema.py                  # creates ./csm_jobs.csv if missing
    python3 schema.py --force          # overwrites it with an empty header-only file
    python3 schema.py --path /x/y.csv  # target a specific path (default: ./csm_jobs.csv)
"""

import argparse
import csv
import os

# The master tracker filename. Never anything else.
MASTER_CSV_NAME = "csm_jobs.csv"

# ---------------------------------------------------------------------------
# CANONICAL COLUMN ORDER — the one and only schema.
# Columns 1–20 are written by the SCRAPER skill.
# Columns 21–37 are written by the ENRICHMENT skill.
# discovered_execs (38) is written by the DASHBOARD (Hunter.io lookups).
# ---------------------------------------------------------------------------
CANONICAL_COLUMNS = [
    # --- scraper fields ---
    "job_id",
    "date_scraped",
    "job_title",
    "company",
    "company_tagline",
    "industry",
    "hq_location",
    "company_size",
    "job_location",
    "salary",
    "work_authorization",
    "applicant_count",
    "easy_apply",
    "linkedin_job_url",
    "company_linkedin_url",
    "company_website",
    "key_requirements",
    "hard_requirements",
    "years_experience",
    "outreach_status",
    # --- enrichment fields ---
    "contact1_name", "contact1_title", "contact1_linkedin", "contact1_dm",
    "contact2_name", "contact2_title", "contact2_linkedin", "contact2_dm",
    "contact3_name", "contact3_title", "contact3_linkedin", "contact3_dm",
    "contact4_name", "contact4_title", "contact4_linkedin", "contact4_dm",
    "cover_letter_path",
    # --- dashboard field ---
    "discovered_execs",
]

# Columns the scraper is responsible for populating.
SCRAPER_COLUMNS = CANONICAL_COLUMNS[:CANONICAL_COLUMNS.index("outreach_status") + 1]

# Columns the enrichment skill is responsible for populating.
ENRICHMENT_COLUMNS = [
    "contact1_name", "contact1_title", "contact1_linkedin", "contact1_dm",
    "contact2_name", "contact2_title", "contact2_linkedin", "contact2_dm",
    "contact3_name", "contact3_title", "contact3_linkedin", "contact3_dm",
    "contact4_name", "contact4_title", "contact4_linkedin", "contact4_dm",
    "cover_letter_path",
]

# Default values applied to brand-new rows.
DEFAULTS = {
    "outreach_status": "Not started",
}


def assert_master_path(csv_path: str) -> None:
    """Guardrail: refuse to operate on anything other than the master csm_jobs.csv.

    This is what makes the single-CSV rule foolproof — a script can never be
    pointed at a stray or mis-typed filename and silently create a second tracker.
    """
    base = os.path.basename(csv_path)
    if base != MASTER_CSV_NAME:
        raise SystemExit(
            f"REFUSING TO WRITE: '{base}' is not the master tracker.\n"
            f"There is exactly one data file in this project: {MASTER_CSV_NAME}.\n"
            f"Point --csv at <project_root>/{MASTER_CSV_NAME} and try again."
        )


def ensure_csv(csv_path: str) -> bool:
    """Create the master CSV with the canonical header if it does not exist.

    Returns True if a new file was created, False if it already existed.
    Never overwrites existing data.
    """
    assert_master_path(csv_path)
    if os.path.exists(csv_path):
        return False
    os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=CANONICAL_COLUMNS).writeheader()
    return True


def read_header(csv_path: str):
    """Return the existing header of the CSV, or None if the file doesn't exist."""
    if not os.path.exists(csv_path):
        return None
    with open(csv_path, newline="", encoding="utf-8") as f:
        return csv.DictReader(f).fieldnames


def main():
    parser = argparse.ArgumentParser(description="Create the empty master tracker CSV.")
    parser.add_argument("--path", default=os.path.join(os.getcwd(), MASTER_CSV_NAME),
                        help=f"Target path (default: ./{MASTER_CSV_NAME})")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite with an empty header-only file (DELETES existing rows).")
    args = parser.parse_args()

    assert_master_path(args.path)

    if args.force and os.path.exists(args.path):
        os.remove(args.path)

    created = ensure_csv(args.path)
    if created:
        print(f"Created empty master tracker: {os.path.abspath(args.path)} "
              f"({len(CANONICAL_COLUMNS)} columns)")
    else:
        print(f"Master tracker already exists (left untouched): {os.path.abspath(args.path)}")


if __name__ == "__main__":
    main()
