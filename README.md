# CSM Outreach Dashboard

A complete local job-outreach system for Customer Success Manager roles (retargetable to any title). Two AI skills scrape LinkedIn and enrich every job with contacts, personalized DMs, and a cover letter. A local web dashboard gives you a clean view of everything - search, filter, track outreach status, copy messages, and find executive emails - all from one page. Everything lives in **one CSV** on your machine; nothing is uploaded anywhere.

## 👩‍💻 Launch the dashboard

Once everything is installed, open Terminal (Mac) or Command Prompt (Windows), navigate to the project folder, and run:

**Mac / Linux:**
```bash
bash dashboard/run.sh
```

**Windows:**
```
dashboard\run.bat
```

Then open **http://localhost:5001** in your browser - that's your dashboard.

## What's included

- **Two Claude Code skills** - one scrapes LinkedIn job postings (17 fields per job, with blocklists and sponsorship detection), the other enriches them with up to 4 contacts, tier-specific DMs, and a formal cover letter.
- **Local web dashboard** - a Flask app with tab navigation, full-text search, a live settings panel, outreach status tracking, DM/cover-letter copy buttons, and Hunter.io executive email lookup.
- **23+ configurable settings** - change the role, location, seniority, tone, contact types, or any other knob by asking Claude in plain language. All settings live in one file and take effect on the next run.
- **One local data file** - `csm_jobs.csv`. No cloud, no database, no accounts.

## How the pieces fit together

```
        ┌─────────────────────┐        ┌──────────────────────────┐
        │  Skill 1: SCRAPER   │        │  Skill 2: ENRICHMENT      │
        │  LinkedIn -> new    │        │  fills contacts, DMs,     │
        │  rows (17 fields    │        │  cover letters for any    │
        │  per job)           │        │  row not yet enriched     │
        └──────────┬──────────┘        └────────────┬─────────────┘
                   │  appends new rows               │  updates rows in place
                   │                                 │
                   │  ── auto-triggers ──────────>   │
                   ▼                                 ▼
              ┌───────────────────────────────────────────┐
              │      csm_jobs.csv   (THE one data file)    │
              │   38 columns defined once in schema.py     │
              └───────────────────────┬───────────────────┘
                                      │  reads
                                      ▼
                          ┌──────────────────────┐
                          │  Dashboard (Flask)   │
                          │  localhost:5001      │
                          └──────────────────────┘
```

There is **exactly one data file: `csm_jobs.csv`.** The scraper appends new rows to it, the enrichment skill updates existing rows in it, and the dashboard reads from it. The column layout is defined in a single place - `schema.py` - so the two skills and the dashboard can never drift out of sync.

**Data safety:** the skills' helper scripts physically refuse to write to any file not named `csm_jobs.csv`, deduplicate by `job_id`, and preserve the existing header. An agent can't accidentally create a second tracker or reshape the schema.

## What the scraper actually does

The scraper doesn't just grab job titles. For each posting it extracts **17 fields**: job title, company, salary, location, applicant count, Easy Apply status, company tagline, industry, HQ location, company size, company website, LinkedIn URLs (job + company), key requirements, hard requirements, years of experience, and work authorization.

It also:
- **Filters out aggregators and recruiters** using a configurable blocklist (11 companies and 5 description phrases by default).
- **Detects sponsorship status** - scans job descriptions against 33 configurable phrases (25 negative, 8 positive) to flag jobs that explicitly won't sponsor. Jobs silent on sponsorship are kept.
- **Parses hard requirements** - distinguishes documentation-gated requirements (degree field, license, clearance) from soft items like years of experience.
- **Deduplicates** against a seen-job-IDs cache so re-runs never produce duplicate rows.
- **Auto-triggers enrichment** when it finishes - you don't have to run two separate commands.

## What the enrichment skill actually does

Enrichment runs a **4-tier contact search** for every un-enriched job, each tier using different LinkedIn People-tab parameters:

| Tier | Who | How it searches |
|------|-----|-----------------|
| **Contact 1** | Recruiter | People tab filtered by recruiter function code |
| **Contact 2** | Hiring Manager | CS Director/Sr. Director - adapts keywords based on company size (large/mid/small) |
| **Contact 3** | Peer | Same-function IC on the same segment team (Strategic, Enterprise, Commercial, SMB) |
| **Contact 4** | Senior Business Leader | Found via hiring manager's "More profiles for you" section, with fallback to company People tab |

For each contact it drafts a **personalized DM** (under 300 characters for LinkedIn/InMail limits) using tier-specific templates and a configurable tone.

Then it generates a **formal cover letter** (~350 words, 4-5 paragraphs) using your name and email from `user_profile.txt`, saved to `cover_letters/{job_id}_{company_slug}.txt`.

If enrichment finds **zero** usable contacts for a job, it treats that company as low-signal and removes the row (configurable - you can change this to keep all jobs). The job ID stays in the seen cache so the scraper won't re-add it.

## The dashboard

The dashboard is more than a table viewer. It gives you:

**Navigation and filtering:**
- **6 tab-cards** with live counts - Ready to Send, Pending Agent, DMs Sent, Replies, Applied, Archived
- **Full-text search** across company name, job title, all 4 contact names, location, and industry

**Job cards (grid view):**
- Company, title, salary, location, and contact names at a glance
- **Hard requirements** always displayed - the absence of a gate (like a required degree) is itself a useful signal
- Status dot and outreach label
- Click any card to open the detail page

**Job detail page:**
- Left sidebar with full company metadata - tagline, industry, size, HQ, applicant count, Easy Apply status, and links to the LinkedIn posting and company website
- **Outreach status dropdown** - change status (Not started, DMs sent, Replied, Applied, Archived) with real-time save
- All enriched contacts displayed with color-coded tier badges (Recruiter in blue, Hiring Manager in purple, Peer in green, Senior Leader in orange)
- Each contact's drafted DM with character count and a copy button
- Full cover letter with copy button

**Current search settings panel:**
- Expandable panel showing every active scraper and enrichment setting with human-readable labels
- Shows whether you're running shipped defaults or a customized config
- **Self-updating** - when you add a new setting with a `_label` companion, it appears in the panel automatically with no code change

**Hunter.io integration (built into the detail page):**
- Paste your API key once - it saves locally
- One-click executive email search by company domain
- Results show name, title, email, and a **confidence score** (color-coded: green for high, amber for mid, red for low)
- Copy button for each email
- Results are **cached** in the CSV so re-viewing a job doesn't spend another API credit
- Remaining credits displayed

## Prerequisites

- **Claude Code** installed (the skills run inside it). The two skills auto-load from this repo - see below.
- **Browser automation + a logged-in LinkedIn session.** The scraper and enrichment skills drive a web browser to read LinkedIn (job pages, company pages, the People tab). Before running them, open the browser Claude controls and **log into LinkedIn** - otherwise you'll hit a login wall and the skills will stop and tell you to log in.
- **Python 3** and **Flask** (one `pip` install, below) for the dashboard.

## The skills - how they load

The two skills live in `.claude/skills/` in this repo, and that folder is the single source of truth.

**Claude Code** discovers `.claude/skills/` automatically when you open the project folder - nothing to install. After setup, `/linkedin-csm-scraper` and `/linkedin-csm-enrichment` are immediately available.

**Cowork** uses the *same files* through a thin-launcher plugin (`dist/csm-outreach-dashboard.plugin`). The plugin discovers the project folder at runtime and delegates to the live `SKILL.md` files, so it's never stale - config changes take effect immediately with no rebuild or reinstall. This project is designed to be installed inside your Cowork files folder (under `Projects/`), so Claude Code and Cowork share one project, one `csm_jobs.csv`, and one set of skills.

> This folder layout (`SKILL.md` + a `scripts/` folder) is the [Agent Skills](https://agentskills.io) open standard - plain, readable files that work across AI coding tools, not a Claude-only format.

## Quick start (with Claude Code)

1. Open Claude Code and tell it: **`set up https://github.com/Sesamsesam/csm-outreach-dashboard for me`**
2. Make sure you're logged into LinkedIn in the browser Claude controls (see Prerequisites).

Claude will install it into your Cowork files folder (so Cowork can see it too), check and install any prerequisites (Python, Flask), create your empty `csm_jobs.csv` from `schema.py`, save your name/email for cover letters, and start the dashboard. The skills auto-load - no install step.

> **Why the Cowork files folder?** Installing there lets Claude Code and Cowork share one project and one `csm_jobs.csv`. Claude Code handles setup and on-demand runs; Cowork can run the daily scheduled scrape against the same files. Claude figures out that location automatically - you don't need to.

## Manual setup

```bash
# 1. Install Flask
pip3 install flask          # use 'pip' on Windows

# 2. Create your empty tracker (one data file, correct columns)
python3 schema.py           # creates ./csm_jobs.csv

# 3. (Skills need no install - they auto-load from .claude/skills/)

# 4. Start the dashboard
bash dashboard/run.sh       # macOS/Linux
#   dashboard\run.bat        # Windows
```

Then open **http://localhost:5001**.

## Usage

1. Say **"run my daily job search"** in Claude Code - the scraper finds new postings and enrichment runs automatically after.
2. Open the dashboard at **http://localhost:5001** to review what was found.
3. Use the **tab cards** to filter by outreach status (Ready to Send, Pending Agent, DMs Sent, Replies, Applied, Archived).
4. Click any job card to see the full detail page - contacts with DMs, cover letter, company info, and outreach status.
5. **Copy DMs** with one click, update the outreach status as you go.
6. Optional: paste a Hunter.io API key in the dashboard to find executive emails with confidence scores.

A job that the enrichment skill can't find **any** contacts for is treated as low-signal and removed from the tracker automatically (configurable via `zero_contact_behavior` in your settings). Its ID is remembered so it won't be re-scraped.

## Running it automatically (scheduling)

A daily scrape has to drive your **logged-in LinkedIn browser** and write to your **local** `csm_jobs.csv` - so it runs **on your machine**, not in the cloud. Two ways to set it up:

**Cowork scheduled task (runs locally, daily).** Because the project lives in your shared Cowork files folder, a Cowork scheduled task can open it, scrape, and write the same `csm_jobs.csv`. The scraper auto-triggers enrichment, so one task handles both.

**On-demand in Claude Code (simplest).** Open the project and say **"run my daily job search"** - the agent scrapes, then enriches, in one session. Then **"open the dashboard"** to review.

**Why the order matters:** the scraper must finish before enrichment starts (enrichment fills the rows the scraper produced). The scraper handles this automatically by triggering enrichment when it's done. Enrichment is idempotent and only touches un-enriched rows, so a straggler is just caught on the next run.

**Requirements either way:** a logged-in LinkedIn session in the browser Claude controls, the machine **awake**, and someone available if LinkedIn shows a login wall or CAPTCHA (the skill stops and asks).

## Customizing for a different role

This project ships tuned for **Customer Success Manager** roles, but the skills are built to be retargeted to any title. To track a different role - say Product Manager, Account Executive, or Data Analyst - **just ask Claude**, e.g.:

> "Change these skills to track Account Executive jobs instead of CSM."

You can also change individual settings in plain language:

> "Search United Kingdom instead of US"
> "Show me hybrid jobs too, not just remote"
> "Make the DMs more formal"
> "Only show me senior roles"
> "Don't delete jobs with no contacts"
> "Skip jobs from [company name]"
> "Focus the cover letter on sales leadership"

Claude will confirm what you mean, make the change in the config file, and tell you what it did. All changes live in one file (`search_config.json`) and take effect on the next run - no reinstall or rebuild needed. The dashboard's settings panel updates to reflect the change immediately.

**What can be changed (23+ settings):**
- **Scraper** - search keywords, job-title filter, location, remote/hybrid/onsite, seniority level, posting recency, pages to scrape, company blocklist, sponsorship filter.
- **Enrichment** - who the 4 contact tiers are (e.g. swap "Peer CSM" for "VP of Sales"), People-tab search terms, function codes, DM tone, cover letter emphasis, and whether to keep or delete zero-contact jobs.

**What stays the same:** the CSV schema, deduplication, the "enrich anything not yet enriched" behavior, the single-data-file rule, and the forward-only policy (old jobs are never deleted or re-filtered when you change settings).

For the full config reference and the procedure for adding brand-new settings, see [`RETARGETING.md`](RETARGETING.md).

## Cowork project prompt (recommended) 👈 🚨

If you're using this project in **Cowork**, paste the following into your **project prompt** (Project Settings -> Project Prompt). This ensures Claude always handles your requests correctly - even when you describe changes casually:

> The users of this project are not technical and did not build it. They will describe changes in casual, everyday language - "search UK", "look for PM jobs", "make the DMs shorter", "only senior roles." They do not know the config structure, skill names, or technical terms like "retarget" or "knob."
>
> When they ask to change anything about what jobs are searched, where they're searched, what filters apply, who gets contacted, or how outreach is written, that is a settings change - not a request to run a scrape or enrichment. Confirm what they mean in plain language, then read CLAUDE.md (specifically the "Recognizing a settings change" section) and follow the retargeting procedure in RETARGETING.md. All config changes go in search_config.json, never in skill files.
>
> When they ask to run a search, find new jobs, enrich, or do their daily job search - that is a run request. Use the skills as normal.
>
> If you're unsure whether they want a settings change or a run, ask a short clarifying question.

## Hunter.io (optional)

Sign up free at [hunter.io](https://hunter.io) - 25 domain searches/month on the free plan. Enter your API key directly in the dashboard under any job's Hunter sidebar. The key is saved locally to `dashboard/.hunter_key` and is never committed.

Once set up, you can search for executive emails from any job's detail page. Results include names, titles, email addresses, and confidence scores - and they're cached in the CSV so you only spend one credit per company, even if you revisit the page later.

## Privacy / what gets pushed

Your data never goes to GitHub. The `.gitignore` excludes `csm_jobs.csv`, `seen_job_ids.txt`, `user_profile.txt`, `search_config.json` (your personal search targeting), `setup_complete.json` (your local setup marker), your cover letters, and your API keys. Only the **framework** is shared - code, skills, `schema.py`, the default `search_config.example.json`, and docs. When someone clones the repo they get an empty, ready-to-use project; when you push, your personal job data and contacts stay on your machine.

## File structure

```
.
├── schema.py                 <- single source of truth for the 38 CSV columns
├── csm_jobs.csv              <- your ONE data file (gitignored, created from schema.py)
├── CLAUDE.md                 <- guidance for Claude agents (Claude Code + Cowork)
├── RETARGETING.md            <- how to change/add search settings (full config reference)
├── search_config.example.json <- shipped default settings (CSM)
├── search_config.json        <- your live settings (gitignored; skills load this)
├── seen_job_ids.txt          <- scraper de-dup cache (gitignored)
├── user_profile.txt          <- your name/email for cover letters (gitignored)
├── setup_complete.json       <- per-machine setup marker (gitignored)
├── build_plugin.py           <- builds the Cowork plugin from skill launchers
├── cover_letters/            <- generated cover letters (gitignored)
├── dist/
│   └── csm-outreach-dashboard.plugin  <- Cowork plugin (thin launcher, never stale)
├── .claude/
│   └── skills/               <- AUTHORITATIVE skills (auto-load in Claude Code)
│       ├── linkedin-csm-scraper/     (SKILL.md + scripts/append_jobs.py)
│       └── linkedin-csm-enrichment/  (SKILL.md + scripts/update_contacts.py)
└── dashboard/
    ├── app.py                <- Flask dashboard (port 5001)
    ├── run.sh / run.bat      <- launchers
    └── .hunter_key           <- Hunter.io API key (gitignored)
```
