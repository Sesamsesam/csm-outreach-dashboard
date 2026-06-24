# CSM Outreach Dashboard — Guide for Claude

> **FORMATTING RULE - NO EM DASHES:** Never use em dashes (--) anywhere - not in DMs, cover letters, reports, summaries, or any other output. Always use a regular hyphen (-) instead. This rule applies across all skills and all generated text, without exception.

This is a LinkedIn job-outreach tracker with a local web dashboard, two Claude Code skills (scrape + enrich), and optional Hunter.io email lookup. It ships tuned for **Customer Success Manager** roles but is built to be retargeted to any job title.

## 🔒 The most important rule: ONE data file

There is **exactly one** data file in this project: **`csm_jobs.csv`** in the project root.

- **Never** create a second CSV. Never write job data to any other filename. Never write to a template, backup, or "example" file — there is no example file.
- The column layout is defined **once** in `schema.py`. Do not invent columns or reorder them. If a column genuinely needs to change, edit `schema.py` and nothing else.
- Both skills write through helper scripts (`append_jobs.py`, `update_contacts.py`) that **physically refuse** any `--csv` path whose filename isn't `csm_jobs.csv`, and that always preserve the existing header. Always point them at `{project_root}/csm_jobs.csv`.
- If `csm_jobs.csv` doesn't exist, create it with `python3 schema.py` (or let the scraper create it automatically). Don't hand-roll a CSV.

This single-file discipline is the whole point of the project structure — the scraper, the enrichment skill, and the dashboard all stay in sync because they all bind to this one schema-defined file.

## How this project is used: Claude Code + Cowork share ONE folder

This project is built to live in a single folder that **both Claude Code and Cowork can see**, so there's one project, one `csm_jobs.csv`, and one set of skills no matter which tool touches it.

- **Claude Code** does the one-time setup (cloning, installing Flask, creating the CSV) and the on-demand work ("run my daily job search", "open the dashboard"). It auto-loads the skills from `.claude/skills/` whenever the project folder is open.
- **Cowork** can run the recurring **scheduled scrape** locally (it drives the user's logged-in browser and writes to the same `csm_jobs.csv`). Cowork does not auto-load `.claude/skills/`, but it doesn't need a separate skill install either — a scheduled task simply **references the skill files by path**, e.g. *"follow the steps in `.claude/skills/linkedin-csm-scraper/SKILL.md` to add new jobs to `csm_jobs.csv`."* Because the folder is shared, Cowork reads the same authoritative `SKILL.md` Claude Code uses.

The `.claude/skills/<name>/` folders are the **single source of truth**. There are no `.skill` bundles to build and no Skill Creator plugin to install — ignore any older instructions that mention them.

## When a new user opens this project

Run these steps **in order** to get them going. The user may be non-technical — do not tell them to open a terminal or run commands themselves. Run everything yourself. Only tell the user something if you need them to take a physical action (like clicking a button in a dialog).

### 0. Confirm the install location (so Cowork and Claude Code share it)

For the shared-folder setup to work, this project should live inside the user's **Cowork files location**, under `Projects/`. That location is user-configurable, so **discover it — never hardcode it.**

Read the Cowork desktop config and parse the `coworkUserFilesPath` value:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```bash
# macOS example — extract the configured Cowork files path
python3 -c "import json,os; p=os.path.expanduser('~/Library/Application Support/Claude/claude_desktop_config.json'); print(json.load(open(p)).get('coworkUserFilesPath',''))" 2>/dev/null
```

Then:
- **Ideal location** = `<coworkUserFilesPath>/Projects/csm-outreach-dashboard`.
- **If this project folder is already at that path** → nothing to do, continue.
- **If it's somewhere else and `coworkUserFilesPath` exists** → tell the user you'd like to move it so Cowork can see it too, and (with their OK) relocate the folder there, then continue from the new location.
- **If the config or key doesn't exist** (Cowork not installed, or a Claude Code-only user) → the current location is fine; continue.

> If you're cloning fresh, clone directly into `<coworkUserFilesPath>/Projects/csm-outreach-dashboard` so this step is already satisfied.

### 1. Check prerequisites (run these checks silently — install what's missing)

First, detect the OS:
```bash
uname -s 2>/dev/null || echo "Windows"
```
- `Darwin` → macOS. Follow the **macOS** path below.
- `Windows` or if `uname` fails → Windows. Follow the **Windows** path below.
- `Linux` → Follow the macOS path (skip Xcode/Homebrew steps; use `apt`, `dnf`, or whatever package manager is available).

Work through the checklist for the detected OS. Run each check yourself. If something is missing, install it automatically. Only involve the user if a step requires their physical action (like clicking a button in a dialog or typing a password).

---

#### macOS prerequisites

**a) Xcode Command Line Tools**
```bash
xcode-select -p 2>/dev/null && echo "INSTALLED" || echo "MISSING"
```
If MISSING: run `xcode-select --install`. This opens a macOS dialog — tell the user: "A dialog just appeared asking to install Command Line Tools. Click Install and wait for it to finish." Then wait for the install to complete before continuing. Do not proceed until `xcode-select -p` returns a path.

**b) Homebrew**
```bash
which brew && echo "INSTALLED" || echo "MISSING"
```
If MISSING: run the official installer:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
This may prompt for the user's password in the terminal — tell them: "Homebrew needs your Mac password to install. Type it in the terminal where you see the prompt (the characters won't show as you type, that's normal)." After install, ensure brew is on PATH (on Apple Silicon: `eval "$(/opt/homebrew/bin/brew shellenv)"`).

**c) Python 3**
```bash
python3 --version 2>/dev/null && echo "INSTALLED" || echo "MISSING"
```
If MISSING: install via Homebrew (`brew install python3`). Do not ask the user to download from python.org.

**d) pip3**
```bash
pip3 --version 2>/dev/null && echo "INSTALLED" || echo "MISSING"
```
If MISSING after Python 3 is installed: run `python3 -m ensurepip --upgrade`.

**e) Flask**
```bash
pip3 show flask 2>/dev/null && echo "INSTALLED" || echo "MISSING"
```
If MISSING: run `pip3 install flask`.

---

#### Windows prerequisites

**a) Git**
```powershell
git --version 2>$null && echo "INSTALLED" || echo "MISSING"
```
If MISSING: run `winget install Git.Git --accept-package-agreements --accept-source-agreements`. If `winget` itself is not available (older Windows 10), tell the user: "Git isn't installed and I can't install it automatically. Please download and install it from https://git-scm.com/download/win, then come back and say 'continue'." Do not tell them to open a terminal — that message is their only action.

**b) Python 3**
```powershell
python --version 2>$null && echo "INSTALLED" || echo "MISSING"
```
Note: on Windows, the command is `python` not `python3`. If MISSING: run `winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements`. After install, verify `python --version` works. If `winget` is unavailable, tell the user: "Python isn't installed and I can't install it automatically. Please download and install it from https://www.python.org/downloads/ — make sure to check 'Add Python to PATH' during install — then come back and say 'continue'."

**c) pip**
```powershell
pip --version 2>$null && echo "INSTALLED" || echo "MISSING"
```
If MISSING after Python is installed: run `python -m ensurepip --upgrade`.

**d) Flask**
```powershell
pip show flask 2>$null && echo "INSTALLED" || echo "MISSING"
```
If MISSING: run `pip install flask`.

---

Only after ALL prerequisites for the detected OS pass, continue to step 2.

### 2. Create their one data file
```bash
python3 schema.py
```
This creates an empty `csm_jobs.csv` with the correct columns (from `schema.py`). It will not overwrite an existing file. There is no separate template/example CSV to copy.

### 3. Skills — nothing to install
The two skills live in `.claude/skills/` and **auto-load** when the project is open in Claude Code. There is no install command (do **not** tell the user to run `claude skills install` — that's not a real command). The user already has:
- `/linkedin-csm-scraper` — scrapes new LinkedIn postings into `csm_jobs.csv`
- `/linkedin-csm-enrichment` — enriches any row that hasn't been enriched yet

The `.claude/skills/<name>/` folders are the **single source of truth**. When editing a skill (e.g. retargeting the job title), edit the folder under `.claude/skills/` — that's the only copy. (For Cowork's scheduled scrape, a task just references these same files by path; nothing extra to install.)

**Prerequisite to flag:** the skills drive a browser to read LinkedIn, so the user must be **logged into LinkedIn** in the browser Claude controls before scraping or enriching. If a login wall appears, stop and ask them to log in.

### 4. Start the dashboard
```bash
bash dashboard/run.sh      # macOS/Linux
dashboard\run.bat          # Windows
# or cross-platform:
python3 dashboard/app.py
```
Then tell the user to open **http://localhost:5001** in their browser.

### 5. Save their personal details for cover letters
Ask for the user's full name and email, then write `user_profile.txt` in the project root:
```
Name: [their full name]
Email: [their email]
```
This file is gitignored. The enrichment skill reads it for cover-letter signatures so it never has to ask mid-session. If skipped, the enrichment skill will ask the first time it writes a cover letter.

### 6. (Optional) Hunter.io for executive email lookup
- Sign up free at https://hunter.io (25 domain searches/month on the free plan).
- In the dashboard, open any job → the **Hunter.io** sidebar → paste the API key.
- The key saves to `dashboard/.hunter_key` (gitignored).

## How the two skills work together

1. **Scraper** finds new job postings on LinkedIn and **appends** them as new rows to `csm_jobs.csv` (scraper columns filled, enrichment columns blank). It de-dups by `job_id` using `seen_job_ids.txt`.
2. **Enrichment** scans `csm_jobs.csv` for **any row where all four contact slots are blank** — regardless of `outreach_status` or how long ago it was scraped — and fills in contacts, DMs, and a cover letter. "Enrich anything not yet enriched" is keyed on the data, not the date.
3. If enrichment finds **zero** usable contacts for a job, it **deletes** that row (low-signal company) but keeps the `job_id` in `seen_job_ids.txt` so the scraper won't re-add it.
4. The **dashboard** reads `csm_jobs.csv` and renders everything visually.

## Scheduling (the daily automated scrape)

A scheduled scrape needs to drive a **logged-in LinkedIn browser** and write to the **local** `csm_jobs.csv`. That means it must run **on the user's machine**, not as a cloud agent. Two ways to set it up:

- **Cowork scheduled task (runs locally).** Because the project lives in the shared Cowork files folder, a Cowork scheduled task can open this project, scrape, and write the same `csm_jobs.csv`. The task prompt should reference the skill files by path, e.g.: *"Open the project at `<coworkUserFilesPath>/Projects/csm-outreach-dashboard`. Follow `.claude/skills/linkedin-csm-scraper/SKILL.md` to add new jobs to `csm_jobs.csv`. When that finishes, follow `.claude/skills/linkedin-csm-enrichment/SKILL.md` to enrich every row not yet enriched. Then give a short combined summary."*
- **On-demand in Claude Code.** The simplest reliable flow: the user opens the project and says *"run my daily job search"* — the agent runs scrape → enrich in one session.

**Ordering:** the scraper must finish before enrichment starts (enrichment acts on the rows the scraper produced). A single chained task guarantees this. Enrichment is idempotent and only touches un-enriched rows, so a missed straggler is just caught next run.

**Always required:** a scheduled run still needs a **logged-in LinkedIn session** in the browser Claude controls, the machine **awake**, and someone available if LinkedIn throws a login wall or CAPTCHA (the skills stop and ask in that case).

## Retargeting to a different job title

If the user asks to track a different role (not CSM), **engage with them — don't guess.** Each skill's `SKILL.md` has a clearly marked **🎯 CUSTOMIZE** section listing exactly what to change:

- **Scraper**: search keywords, the title filter, and LinkedIn location/remote/seniority URL params.
- **Enrichment**: the contact priority tiers, segment-keyword logic, People-tab search terms / function codes, and DM/cover-letter tone.

Walk the user through each knob, confirm their preferences, edit the `SKILL.md` files accordingly, then tell them what changed. The CSV schema, the single-file rule, and the enrich/delete behavior never change — only the search and outreach wording.

## Notes for Claude

- **"Start the dashboard" / "open localhost":** run `bash dashboard/run.sh` (macOS/Linux) or `python dashboard/app.py` (Windows), then tell the user to open http://localhost:5001.
- **OS detection:** check `sys.platform` / `os.name`. macOS/Linux → `bash` + `pip3`. Windows → `python` + `pip`.
- **Port:** the dashboard runs on **5001** (macOS reserves 5000 for AirPlay). To change it, set the `PORT` env var or edit the default in `dashboard/app.py`.
- All data stays local — no cloud, no database. Everything is in `csm_jobs.csv`.
- The Hunter.io key lives in `dashboard/.hunter_key` after the user enters it in the UI; no environment variable needed.
- The skills always write to `csm_jobs.csv` in the project root (one level above `dashboard/`).

## File structure

```
.
├── schema.py                 ← single source of truth for CSV columns
├── csm_jobs.csv              ← the ONE data file (gitignored; create via schema.py)
├── seen_job_ids.txt          ← scraper de-dup cache (gitignored)
├── user_profile.txt          ← name/email for cover letters (gitignored)
├── cover_letters/            ← generated cover letters (gitignored)
├── .claude/skills/           ← AUTHORITATIVE skills (auto-load in Claude Code)
│   ├── linkedin-csm-scraper/     (SKILL.md + scripts/append_jobs.py)
│   └── linkedin-csm-enrichment/  (SKILL.md + scripts/update_contacts.py)
└── dashboard/
    ├── app.py                ← Flask dashboard (port 5001)
    └── run.sh / run.bat      ← launchers
```

## CSV columns (defined in schema.py)

| Group | Columns |
|---|---|
| Scraper | job_id, date_scraped, job_title, company, company_tagline, industry, hq_location, company_size, job_location, salary, applicant_count, easy_apply, linkedin_job_url, company_linkedin_url, company_website, key_requirements, outreach_status |
| Enrichment | contact1–4 (name/title/linkedin/dm), cover_letter_path |
| Dashboard | discovered_execs (JSON array of execs found via Hunter.io) |
