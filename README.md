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

## Prerequisites

- **Claude Code** installed (the skills run inside it). The two skills auto-load from this repo — see below.
- **Browser automation + a logged-in LinkedIn session.** The scraper and enrichment skills drive a web browser to read LinkedIn (job pages, company pages, the People tab). Before running them, open the browser Claude controls and **log into LinkedIn** — otherwise you'll hit a login wall and the skills will stop and tell you to log in.
- **Python 3** and **Flask** (one `pip` install, below) for the dashboard.

## The skills install themselves

There is **nothing to install for the skills.** They live in `.claude/skills/` inside this repo, which Claude Code discovers automatically the moment you open the project. After cloning, the commands `/linkedin-csm-scraper` and `/linkedin-csm-enrichment` are simply available.

> The `*.skill` files in the repo root are *packaged copies* of those same folders, for users on Claude Desktop / Cowork who install via the "Save skill" button. The folders under `.claude/skills/` are the source of truth; the zips are regenerated from them with `bash build_skills.sh`. You never need the zips when using Claude Code.

## Quick start (with Claude Code)

1. Clone this repo and open it in Claude Code.
2. Make sure you're logged into LinkedIn in the browser Claude controls (see Prerequisites).
3. Type: `set this up for me`.

Claude will install Flask, create your empty `csm_jobs.csv` from `schema.py`, save your name/email for cover letters, and start the dashboard. (The skills are already loaded — no install step.)

## Manual setup

```bash
# 1. Install Flask
pip3 install flask          # use 'pip' on Windows

# 2. Create your empty tracker (one data file, correct columns)
python3 schema.py           # creates ./csm_jobs.csv

# 3. (Skills need no install — they auto-load from .claude/skills/)

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

## Running it automatically (scheduling)

The two skills run in order: the **scraper** adds new rows, then the **enrichment** skill fills in any row that isn't enriched yet. So the daily automation has to run the scraper *first*, and only start enrichment *after the scraper has finished* — otherwise enrichment would run before the day's new jobs exist. (There's no risk of corruption if they ever overlap — enrichment only ever touches rows that have no contacts yet, so any stragglers are simply caught on the next run — but you still want the scrape complete first for a same-day result.)

**Recommended — one chained daily task (guaranteed order).** Schedule a single task whose prompt runs both skills back-to-back in the same session. Because one agent runs them sequentially, enrichment can't start until the scrape reports done, no matter how long the scrape takes. In Claude Code, ask:

> "Every day at 6am, run the linkedin-csm-scraper skill to find new jobs and add them to csm_jobs.csv. When it finishes, run the linkedin-csm-enrichment skill to enrich every row that isn't enriched yet. Then give me a short combined summary."

That single instruction is the whole schedule — scrape → wait for completion → enrich, all in one run.

**Alternative — two separate tasks, spaced apart.** If you prefer them as two visible jobs, schedule the scraper (e.g. 6:00am) and the enrichment (e.g. 8:00am) as separate daily tasks. Leave a generous gap (≥2 hours) so a long scrape finishes first. This works because enrichment is idempotent, but it relies on the gap being big enough; the chained approach above removes that guesswork.

Either way, remember the LinkedIn-login prerequisite: scheduled runs still need a logged-in LinkedIn session in the browser Claude controls.

## Customizing for a different role

This project ships tuned for **Customer Success Manager** roles, but the skills are built to be retargeted. To track a different title — say Product Manager, Account Executive, or Data Analyst — **just ask Claude**, e.g.:

> "Change these skills to track Account Executive jobs instead of CSM."

Claude will walk you through the handful of knobs that need to change and confirm each one before editing:

- **Scraper** — the search keywords, the job-title filter, and the LinkedIn location/remote/seniority filters.
- **Enrichment** — the contact tiers (who Contacts 2–4 should be for the new function), the People-tab search terms and function codes, and the DM/cover-letter tone.

The CSV schema, the de-duplication, the "enrich anything not yet enriched" behavior, and the single-data-file rule **stay the same** — only the search and outreach wording changes. Each skill has a clearly marked **🎯 CUSTOMIZE** section at the top documenting exactly what to edit, so the change is safe and contained.

Edits go in the authoritative copy under `.claude/skills/<skill-name>/SKILL.md`. If you also want to refresh the packaged `*.skill` bundles (only needed for Cowork/Desktop sharing), run `bash build_skills.sh` afterward.

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
├── .claude/
│   └── skills/               ← AUTHORITATIVE skills (auto-load in Claude Code)
│       ├── linkedin-csm-scraper/     (SKILL.md + scripts/)
│       └── linkedin-csm-enrichment/  (SKILL.md + scripts/)
├── dashboard/
│   ├── app.py                ← Flask dashboard (port 5001)
│   ├── run.sh / run.bat      ← launchers
│   └── .hunter_key           ← Hunter.io API key (gitignored)
├── build_skills.sh           ← regenerates the .skill bundles from .claude/skills/
├── linkedin-csm-scraper.skill      ← packaged copy (Cowork/Desktop only)
└── linkedin-csm-enrichment.skill   ← packaged copy (Cowork/Desktop only)
```
