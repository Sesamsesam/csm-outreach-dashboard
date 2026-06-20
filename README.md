# CSM Outreach Dashboard

A local job-outreach tracker for Customer Success Manager roles. Scrape LinkedIn job postings, enrich them with contacts and DMs, generate cover letters, and find executive emails — all from a clean local web dashboard. Everything lives in **one CSV** on your machine; nothing is uploaded anywhere.

## What's included

- **Two Claude Code skills** — one scrapes LinkedIn job postings, the other enriches them with contacts, DMs, and cover letters.
- **Local web dashboard** — a Flask app to track outreach status, copy DMs, and manage contacts.
- **Hunter.io integration** — find executive emails by company domain (25 free searches/month).
- **One local data file** — `csm_jobs.csv`. No cloud, no database, no accounts.

## How the pieces fit together

```
        ┌─────────────────────┐        ┌──────────────────────────┐
        │  Skill 1: SCRAPER   │        │  Skill 2: ENRICHMENT      │
        │  LinkedIn → new rows│        │  fills contacts, DMs,     │
        │                     │        │  cover letters for any    │
        │                     │        │  row not yet enriched     │
        └──────────┬──────────┘        └────────────┬─────────────┘
                   │  appends new rows               │  updates rows in place
                   ▼                                 ▼
              ┌───────────────────────────────────────────┐
              │      csm_jobs.csv   (THE one data file)    │
              │   columns defined once in schema.py        │
              └───────────────────────┬───────────────────┘
                                      │  reads
                                      ▼
                          ┌──────────────────────┐
                          │  Dashboard (Flask)   │
                          │  localhost:5001      │
                          └──────────────────────┘
```

There is **exactly one data file: `csm_jobs.csv`.** The scraper appends new rows to it, the enrichment skill updates existing rows in it, and the dashboard reads from it. The column layout is defined in a single place — `schema.py` — so the two skills and the dashboard can never drift out of sync. The skills' helper scripts physically refuse to write to any other filename, so an agent can't accidentally create a second tracker.

## Quick start (with Claude Code)

1. Clone this repo and open it in Claude Code.
2. Type: `set this up for me`.

Claude will install Flask, create your empty `csm_jobs.csv` from `schema.py`, install both skills, save your name/email for cover letters, and start the dashboard.

## Manual setup

```bash
# 1. Install Flask
pip3 install flask          # use 'pip' on Windows

# 2. Create your empty tracker (one data file, correct columns)
python3 schema.py           # creates ./csm_jobs.csv

# 3. Install the skills into Claude Code
claude skills install linkedin-csm-scraper.skill
claude skills install linkedin-csm-enrichment.skill

# 4. Start the dashboard
bash dashboard/run.sh       # macOS/Linux
#   dashboard\run.bat        # Windows
```

Then open **http://localhost:5001**.

## Usage

1. Find CSM jobs on LinkedIn you want to track.
2. Run `/linkedin-csm-scraper` in Claude Code → it scrapes new postings into `csm_jobs.csv`.
3. Run `/linkedin-csm-enrichment` → it finds contacts, drafts DMs, and writes cover letters for **every row that hasn't been enriched yet** — no matter how long ago it was scraped.
4. Open the dashboard → track outreach status, copy DM templates, add notes.
5. Optional: paste a Hunter.io API key in the dashboard to find executive emails.

A job that the enrichment skill can't find **any** contacts for is treated as low-signal and removed from the tracker automatically (its ID is remembered so it won't be re-scraped).

## Customizing for a different role

This project ships tuned for **Customer Success Manager** roles, but the skills are built to be retargeted. To track a different title — say Product Manager, Account Executive, or Data Analyst — **just ask Claude**, e.g.:

> "Change these skills to track Account Executive jobs instead of CSM."

Claude will walk you through the handful of knobs that need to change and confirm each one before editing:

- **Scraper** — the search keywords, the job-title filter, and the LinkedIn location/remote/seniority filters.
- **Enrichment** — the contact tiers (who Contacts 2–4 should be for the new function), the People-tab search terms and function codes, and the DM/cover-letter tone.

The CSV schema, the de-duplication, the "enrich anything not yet enriched" behavior, and the single-data-file rule **stay the same** — only the search and outreach wording changes. Each skill has a clearly marked **🎯 CUSTOMIZE** section at the top documenting exactly what to edit, so the change is safe and contained.

## Hunter.io (optional)

Sign up free at [hunter.io](https://hunter.io) — 25 domain searches/month on the free plan. Enter your API key directly in the dashboard under any job's Hunter sidebar. The key is saved locally to `dashboard/.hunter_key` and is never committed.

## Privacy / what gets pushed

Your data never goes to GitHub. The `.gitignore` excludes `csm_jobs.csv`, `seen_job_ids.txt`, `user_profile.txt`, your cover letters, and your API keys. Only the **framework** is shared — code, skills, `schema.py`, and docs. When someone clones the repo they get an empty, ready-to-use project; when you push, your personal job data and contacts stay on your machine.

## File structure

```
.
├── schema.py                 ← single source of truth for the CSV columns
├── csm_jobs.csv              ← your ONE data file (gitignored, created from schema.py)
├── seen_job_ids.txt          ← scraper de-dup cache (gitignored)
├── user_profile.txt          ← your name/email for cover letters (gitignored)
├── cover_letters/            ← generated cover letters (gitignored)
├── dashboard/
│   ├── app.py                ← Flask dashboard (port 5001)
│   ├── run.sh / run.bat      ← launchers
│   └── .hunter_key           ← Hunter.io API key (gitignored)
├── linkedin-csm-scraper.skill
└── linkedin-csm-enrichment.skill
```
