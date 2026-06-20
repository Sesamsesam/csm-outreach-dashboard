# CSM Outreach Dashboard — Guide for Claude

This is a LinkedIn job-outreach tracker with a local web dashboard, two Claude Code skills (scrape + enrich), and optional Hunter.io email lookup. It ships tuned for **Customer Success Manager** roles but is built to be retargeted to any job title.

## 🔒 The most important rule: ONE data file

There is **exactly one** data file in this project: **`csm_jobs.csv`** in the project root.

- **Never** create a second CSV. Never write job data to any other filename. Never write to a template, backup, or "example" file — there is no example file.
- The column layout is defined **once** in `schema.py`. Do not invent columns or reorder them. If a column genuinely needs to change, edit `schema.py` and nothing else.
- Both skills write through helper scripts (`append_jobs.py`, `update_contacts.py`) that **physically refuse** any `--csv` path whose filename isn't `csm_jobs.csv`, and that always preserve the existing header. Always point them at `{project_root}/csm_jobs.csv`.
- If `csm_jobs.csv` doesn't exist, create it with `python3 schema.py` (or let the scraper create it automatically). Don't hand-roll a CSV.

This single-file discipline is the whole point of the project structure — the scraper, the enrichment skill, and the dashboard all stay in sync because they all bind to this one schema-defined file.

## When a new user opens this project

Run these steps to get them going:

### 1. Install dependencies
```bash
pip3 install flask     # macOS/Linux
pip install flask      # Windows
```

### 2. Create their one data file
```bash
python3 schema.py
```
This creates an empty `csm_jobs.csv` with the correct columns (from `schema.py`). It will not overwrite an existing file. There is no separate template/example CSV to copy.

### 3. Skills — nothing to install
The two skills live in `.claude/skills/` and **auto-load** when the project is open in Claude Code. There is no install command (do **not** tell the user to run `claude skills install` — that's not a real command). The user already has:
- `/linkedin-csm-scraper` — scrapes new LinkedIn postings into `csm_jobs.csv`
- `/linkedin-csm-enrichment` — enriches any row that hasn't been enriched yet

The `.claude/skills/<name>/` folders are the **single source of truth** (the Agent Skills open standard — portable across tools). The repo does **not** ship `.skill` zips; they're gitignored. `build_skills.sh` generates one on demand only if the user wants a Cowork/Desktop "Save skill" bundle. When editing a skill (e.g. retargeting the job title), edit the folder under `.claude/skills/` — that's the only copy.

**Prerequisite to flag:** the skills drive a browser to read LinkedIn, so the user must be **logged into LinkedIn** in the browser Claude controls before scraping or enriching. If a login wall appears, stop and ask them to log in.

### 4. Start the dashboard
```bash
bash dashboard/run.sh      # macOS/Linux
dashboard\run.bat          # Windows
# or cross-platform:
python3 dashboard/app.py
```
Then open **http://localhost:5001**.

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

## Scheduling (if the user wants it to run automatically)

The scraper must finish before enrichment starts (enrichment acts on the rows the scraper produced). Enrichment is idempotent and only touches un-enriched rows, so overlap can't corrupt anything — but for a same-day result, scrape first.

- **Preferred — one chained scheduled task.** Create a single daily task whose prompt runs the scraper to completion, then runs enrichment on all un-enriched rows, in the same session. One agent runs them in order, so enrichment can't start until the scrape is done regardless of duration. Example prompt: *"Run /linkedin-csm-scraper to add new jobs to csm_jobs.csv; when it finishes, run /linkedin-csm-enrichment on every row not yet enriched, then summarize."*
- **Alternative — two tasks ≥2h apart** (e.g. scrape 6am, enrich 8am) if the user prefers separate visible jobs. Works because enrichment is idempotent, but relies on the gap being long enough.

Scheduled runs still need a logged-in LinkedIn session in the browser Claude controls.

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
├── dashboard/
│   ├── app.py                ← Flask dashboard (port 5001)
│   └── run.sh / run.bat      ← launchers
└── build_skills.sh           ← optional: generate a .skill bundle for Cowork/Desktop (gitignored)
```

## CSV columns (defined in schema.py)

| Group | Columns |
|---|---|
| Scraper | job_id, date_scraped, job_title, company, company_tagline, industry, hq_location, company_size, job_location, salary, applicant_count, easy_apply, linkedin_job_url, company_linkedin_url, company_website, key_requirements, outreach_status |
| Enrichment | contact1–4 (name/title/linkedin/dm), cover_letter_path |
| Dashboard | discovered_execs (JSON array of execs found via Hunter.io) |
