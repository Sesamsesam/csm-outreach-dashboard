# CSM Outreach Dashboard — Guide for Claude

## 📌 Read me first — house rules (Claude Code AND Cowork)

**Any agent working in this project - Claude Code or Cowork - must follow these five rules before doing anything else.** They exist because the two tools share one folder, and inconsistency between them (re-running setup, rebuilding the plugin, making a second data file) is the main thing that breaks this project.

1. **Setup is once.** If `setup_complete.json` exists in the project root, setup is already done - do **not** re-run it.
2. **The plugin is an intentional thin launcher.** The file in `dist/` is short *by design*; it reads the project's live skills at runtime, so it is never stale. **Never "rebuild" or replace it with full skill content** - that breaks project-folder discovery.
3. **One data file, ever.** There is exactly one: `csm_jobs.csv`. Never create a second CSV, never rename it.
4. **Targeting lives in `search_config.json`.** To change what's searched/enriched (role, location, filters, contacts, tone), edit `search_config.json` - never hard-code role values into the skills. See `RETARGETING.md`.
5. **Retargeting is forward-only.** Changing the search never deletes or re-filters existing rows in `csm_jobs.csv` - old jobs stay.

Everything below expands on these. When in doubt, these five win.

---

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
- **Cowork** runs the recurring **scheduled scrape** locally (it drives the user's logged-in browser and writes to the same `csm_jobs.csv`). Cowork uses the **CSM Outreach Dashboard plugin** (in `dist/csm-outreach-dashboard.plugin`) which adds the two skills to the Cowork panel. The plugin skills are thin launchers that discover the project root from the Cowork config and then delegate to the authoritative `SKILL.md` files in `.claude/skills/`. This means the project skills remain the single source of truth for both tools.

The `.claude/skills/<name>/` folders are the **single source of truth**. The plugin in `dist/` is a thin wrapper — it does not duplicate skill logic.

> **Do NOT "rebuild" the plugin into a full-content copy of the skills.** The plugin SKILL.md files are intentionally short launchers; their brevity is by design, not staleness. They read the project's live `SKILL.md` at runtime, so they are always current - including every knob/config change and skill edit - and **never need rebuilding**. Knob changes (retargeting) live in `search_config.json`, which the project's skills load live, so a knob change is reflected in the plugin with no rebuild and no reinstall. Bundling the full skill text would re-introduce drift and break the project-folder discovery the launchers rely on (the run would lose track of the shared `csm_jobs.csv`). The only time `build_plugin.py` is re-run is if the launcher *shape* itself (Step 0/Step 1 wording or `plugin.json`) changes.

## "Set this up" trigger

If the user says anything like "set this up", "get me started", "initialize this", or "install this" — run the setup steps below in order. This is the intended onboarding phrase for new users in Cowork.

## ⚡ FIRST: check if setup is already complete

**Before running ANY setup step, check for a `setup_complete.json` file in the project root.**

- **If it exists** → setup has already been completed on this machine (likely by Claude Code, or by a previous Cowork run). **Do NOT re-run the setup steps.** Read the file, then tell the user something like: "This project was already set up by `{set_up_by}` on `{timestamp}`, so I'll skip setup." **However, if you are running in Cowork, you MUST still present the plugin file for installation** — Claude Code doesn't install the Cowork plugin, so even though setup is "complete", the user may not have the plugin yet. Present `dist/csm-outreach-dashboard.plugin` using `present_files` so the user can click Install (see Step 3 below for details). Then go straight to next actions: offer to run a scrape, enrich, or open the dashboard (http://localhost:5001). This is the common case when Cowork opens a folder that Claude Code already initialized — both tools share this one folder, so the work is already done.
- **If it does NOT exist** → this is a fresh setup. Run the setup steps below in order. The file is gitignored, so a fresh clone from GitHub will never have it — which is correct: a new user's machine genuinely needs setup. Every individual step is idempotent (check-then-act), so even a re-run is safe.
- **Write the marker only at the very END of a fully successful setup.** Create `setup_complete.json` with: `set_up_by` (the tool doing setup, e.g. "Claude Code" or "Cowork"), `timestamp` (ISO 8601), `install_path`, and a `steps_completed` array. Writing it only on full success means "file exists = setup fully done"; a setup that dies partway leaves no marker, so the next run correctly resumes (safely, because steps are idempotent).

> Why this exists: Claude Code and Cowork share the same project folder. Whichever tool runs setup first writes the marker; the other tool sees it and skips straight to real work instead of re-walking prerequisite checks. The marker guards against redundant work and confusing "setting up..." UX — the single-data-file rule (schema.py refusing to overwrite, helper scripts refusing other filenames) already protects your actual data.

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

### 3. Skills

**Claude Code:** The two skills live in `.claude/skills/` and **auto-load** when the project is open in Claude Code. No install command needed. The user already has:
- `/linkedin-csm-scraper` — scrapes new LinkedIn postings into `csm_jobs.csv`
- `/linkedin-csm-enrichment` — enriches any row that hasn't been enriched yet

**Cowork:** Present the pre-built plugin file for one-click install:

```
dist/csm-outreach-dashboard.plugin
```

Use `mcp__cowork__present_files` (or the present_files tool) to show the file in chat — it renders with an "Install plugin" button. Tell the user: "Click Install to add the scraper and enrichment skills to your Cowork panel."

The plugin skills are thin launchers that discover the project root at runtime and delegate to the `.claude/skills/` files, so the project skills remain the single source of truth for both Claude Code and Cowork.

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

### 7. Write the setup-complete marker (do this LAST, only after every step above succeeded)
Create `setup_complete.json` in the project root so a second tool (e.g. Cowork) opening this same folder skips setup instead of re-running it. Only write it on full success — a partial setup should leave no marker. Example:
```json
{
  "setup_complete": true,
  "set_up_by": "Claude Code",
  "timestamp": "2026-06-24T00:00:00Z",
  "install_path": "/absolute/path/to/csm-outreach-dashboard",
  "steps_completed": ["install_location_confirmed", "prerequisites_verified", "csv_created", "profile_saved", "dashboard_tested"]
}
```
This file is gitignored, so it never ships in the repo — a fresh clone correctly has no marker and runs setup. See **⚡ FIRST: check if setup is already complete** above for how it's read on later runs.

## How the two skills work together

1. **Scraper** finds new job postings on LinkedIn and **appends** them as new rows to `csm_jobs.csv` (scraper columns filled, enrichment columns blank). It de-dups by `job_id` using `seen_job_ids.txt`.
2. **Enrichment** scans `csm_jobs.csv` for **any row where all four contact slots are blank** — regardless of `outreach_status` or how long ago it was scraped — and fills in contacts, DMs, and a cover letter. "Enrich anything not yet enriched" is keyed on the data, not the date.
3. If enrichment finds **zero** usable contacts for a job, it **deletes** that row (low-signal company) but keeps the `job_id` in `seen_job_ids.txt` so the scraper won't re-add it.
4. The **dashboard** reads `csm_jobs.csv` and renders everything visually.

## Scheduling (the daily automated scrape)

A scheduled scrape needs to drive a **logged-in LinkedIn browser** and write to the **local** `csm_jobs.csv`. That means it must run **on the user's machine**, not as a cloud agent. Two ways to set it up:

- **Cowork scheduled task (runs locally).** With the plugin installed, the user can ask Cowork to schedule a daily scrape and it will use the plugin skills automatically. Example task prompt: *"Use the LinkedIn CSM Scraper skill to find new jobs. When that finishes, use the LinkedIn CSM Enrichment skill to enrich every row not yet enriched. Give a short combined summary."* The plugin skills handle project path discovery at runtime — no paths needed in the task prompt.
- **On-demand in Claude Code.** The simplest reliable flow: the user opens the project and says *"run my daily job search"* — the agent runs scrape → enrich in one session.

**Ordering:** the scraper must finish before enrichment starts (enrichment acts on the rows the scraper produced). A single chained task guarantees this. Enrichment is idempotent and only touches un-enriched rows, so a missed straggler is just caught next run.

**Always required:** a scheduled run still needs a **logged-in LinkedIn session** in the browser Claude controls, the machine **awake**, and someone available if LinkedIn throws a login wall or CAPTCHA (the skills stop and ask in that case).

## Retargeting / changing the job search (trigger)

If the user wants to **change or add to** what the skills look for - a different role, a different location/remote/seniority/recency setting, a different outreach tone, a new filter, **a brand-new knob**, or capturing a brand-new field - **follow [`RETARGETING.md`](RETARGETING.md).** That file is the single entry point and works identically in Claude Code and Cowork (the Cowork plugin launchers delegate to the same `.claude/skills/` files it edits).

> **Adding or changing a knob is never a one-off edit you improvise.** A knob can be wired in up to four places (the example config, the skill's Step 0a load table + the step that uses it, this guide's knob reference, and the dashboard panel) - skip one and the config drifts out of sync with what actually runs. `RETARGETING.md` has the exact, ordered checklist (**"Adding a brand-new knob: the full sync checklist"**) plus the drift traps (the live config is gitignored and per-user; never inline values in skills; never rebuild the plugin for a knob). Use it - do not guess the file list from memory.

**How it works:** all the knobs live in one config file, **`search_config.json`** (project root). Both skills load it at the start of every run - scheduled or on-demand - and use only its values for every scraping/enrichment decision. The role-specific strings inline in the skills are just defaults; the config always wins. So retargeting = **edit that one file**, and every future run (including scheduled scrapes) follows the new targeting. This is the one-way street: a scheduled task can never drift back to the old role, because it reads the same config the user just changed. The dashboard shows a "Current search settings" panel reading the same file, so the user always sees what the next run will do.

`RETARGETING.md` contains: the full knob reference (by config key), a plain-English interview flow, a "does this touch the CSV?" decision rule, the **"add a brand-new knob" sync checklist** (every file to touch, in order, with a verify step), and the safe procedure for additive changes (new column / new contact type). **Engage with the user - don't guess.**

Files: `search_config.json` is the live, gitignored settings (personal targeting never ships); `search_config.example.json` is the committed Customer Success Manager default and the fallback a fresh clone uses.

Two things that never change when retargeting:
- **Forward-only.** Existing rows in `csm_jobs.csv` are never touched, re-filtered, or deleted to match new targeting - old jobs stay in the dashboard. The change affects future runs only.
- **Still one data file**, and `csm_jobs.csv` is never renamed (the filename is an internal guardrail constant, not a role label).

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
├── RETARGETING.md            ← how to change/add search knobs (the retargeting flow)
├── search_config.example.json ← shipped CSM default knobs (committed; the fallback)
├── search_config.json        ← live user knob settings (gitignored; skills load this)
├── seen_job_ids.txt          ← scraper de-dup cache (gitignored)
├── user_profile.txt          ← name/email for cover letters (gitignored)
├── setup_complete.json       ← per-machine setup marker (gitignored)
├── cover_letters/            ← generated cover letters (gitignored)
├── .claude/skills/           ← AUTHORITATIVE skills (auto-load in Claude Code)
│   ├── linkedin-csm-scraper/     (SKILL.md + scripts/append_jobs.py)
│   └── linkedin-csm-enrichment/  (SKILL.md + scripts/update_contacts.py)
├── dist/
│   └── csm-outreach-dashboard.plugin  ← Cowork plugin (present this for install in Step 3)
└── dashboard/
    ├── app.py                ← Flask dashboard (port 5001)
    └── run.sh / run.bat      ← launchers
```

## CSV columns (defined in schema.py)

| Group | Columns |
|---|---|
| Scraper | job_id, date_scraped, job_title, company, company_tagline, industry, hq_location, company_size, job_location, salary, work_authorization, applicant_count, easy_apply, linkedin_job_url, company_linkedin_url, company_website, key_requirements, outreach_status |
| Enrichment | contact1–4 (name/title/linkedin/dm), cover_letter_path |
| Dashboard | discovered_execs (JSON array of execs found via Hunter.io) |
