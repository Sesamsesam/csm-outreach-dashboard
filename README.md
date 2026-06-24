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

## The skills — how they load

The two skills live in `.claude/skills/` in this repo, and that folder is the single source of truth.

**Claude Code** discovers `.claude/skills/` automatically when you open the project folder — nothing to install. After setup, `/linkedin-csm-scraper` and `/linkedin-csm-enrichment` are immediately available.

**Cowork** uses the *same files*. This project is designed to be installed inside your Cowork files folder (under `Projects/`), so Claude Code and Cowork share one project, one `csm_jobs.csv`, and one set of skills. A Cowork scheduled task doesn't need a separate skill install — it just references the skill files by path (e.g. "follow `.claude/skills/linkedin-csm-scraper/SKILL.md`"). See [Running it automatically](#running-it-automatically-scheduling).

> This folder layout (`SKILL.md` + a `scripts/` folder) is the [Agent Skills](https://agentskills.io) open standard — plain, readable files that work across AI coding tools, not a Claude-only format.

## Quick start (with Claude Code)

1. Open Claude Code and tell it: **`set up https://github.com/Sesamsesam/csm-outreach-dashboard for me`**
2. Make sure you're logged into LinkedIn in the browser Claude controls (see Prerequisites).

Claude will install it into your Cowork files folder (so Cowork can see it too), check and install any prerequisites (Python, Flask), create your empty `csm_jobs.csv` from `schema.py`, save your name/email for cover letters, and start the dashboard. The skills auto-load — no install step.

> **Why the Cowork files folder?** Installing there lets Claude Code and Cowork share one project and one `csm_jobs.csv`. Claude Code handles setup and on-demand runs; Cowork can run the daily scheduled scrape against the same files. Claude figures out that location automatically — you don't need to.

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

A daily scrape has to drive your **logged-in LinkedIn browser** and write to your **local** `csm_jobs.csv` — so it runs **on your machine**, not in the cloud. Two ways to set it up:

**Cowork scheduled task (runs locally, daily).** Because the project lives in your shared Cowork files folder, a Cowork scheduled task can open it, scrape, and write the same `csm_jobs.csv`. Use a prompt like:

> "Open the project at `<your Cowork files>/Projects/csm-outreach-dashboard`. Follow `.claude/skills/linkedin-csm-scraper/SKILL.md` to add new jobs to csm_jobs.csv. When it finishes, follow `.claude/skills/linkedin-csm-enrichment/SKILL.md` to enrich every row not yet enriched. Then give me a short combined summary."

**On-demand in Claude Code (simplest).** Open the project and say **"run my daily job search"** — the agent scrapes, then enriches, in one session. Then **"open the dashboard"** to review.

**Why the order matters:** the scraper must finish before enrichment starts (enrichment fills the rows the scraper produced). A single chained task guarantees that. Enrichment is idempotent and only touches un-enriched rows, so a straggler is just caught on the next run.

**Requirements either way:** a logged-in LinkedIn session in the browser Claude controls, the machine **awake**, and someone available if LinkedIn shows a login wall or CAPTCHA (the skill stops and asks).

## Customizing for a different role

This project ships tuned for **Customer Success Manager** roles, but the skills are built to be retargeted. To track a different title — say Product Manager, Account Executive, or Data Analyst — **just ask Claude**, e.g.:

> "Change these skills to track Account Executive jobs instead of CSM."

Claude will walk you through the handful of knobs that need to change and confirm each one before editing:

- **Scraper** — the search keywords, the job-title filter, and the LinkedIn location/remote/seniority filters.
- **Enrichment** — the contact tiers (who Contacts 2–4 should be for the new function), the People-tab search terms and function codes, and the DM/cover-letter tone.

The CSV schema, the de-duplication, the "enrich anything not yet enriched" behavior, and the single-data-file rule **stay the same** — only the search and outreach wording changes. Each skill has a clearly marked **🎯 CUSTOMIZE** section at the top documenting exactly what to edit, so the change is safe and contained.

Edits go in `.claude/skills/<skill-name>/SKILL.md` — the one place each skill lives. Both Claude Code and Cowork read these same files, so an edit applies everywhere.

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
└── dashboard/
    ├── app.py                ← Flask dashboard (port 5001)
    ├── run.sh / run.bat      ← launchers
    └── .hunter_key           ← Hunter.io API key (gitignored)
```
