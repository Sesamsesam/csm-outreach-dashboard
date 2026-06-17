# CSM Outreach Dashboard — Setup Guide for Claude Code

This is a LinkedIn CSM job outreach tracker with a local web dashboard, two Claude Code skills for scraping and enriching job data, and optional Hunter.io integration for finding executive emails.

## When a new user opens this project

Run these steps to get them up and running:

### 1. Install dependencies

On Mac/Linux:
```bash
pip3 install flask
```
On Windows:
```bash
pip install flask
```

### 2. Create their CSV data file

On Mac/Linux:
```bash
cp csm_jobs.example.csv csm_jobs.csv
```
On Windows:
```bash
copy csm_jobs.example.csv csm_jobs.csv
```
This gives them an empty tracker with all the right columns. Their jobs will be added here as they use the skills.

### 3. Install the skills into Claude Code
Both `.skill` files in this repo are Claude Code skills. Install them with:
```bash
claude skills install linkedin-csm-scraper.skill
claude skills install linkedin-csm-enrichment.skill
```
After installing, the user will have two new slash commands available:
- `/linkedin-csm-scraper` — scrapes a LinkedIn job posting URL into `csm_jobs.csv`
- `/linkedin-csm-enrichment` — enriches an existing job row with contact info from LinkedIn

### 4. Start the dashboard

On Mac/Linux:
```bash
bash dashboard/run.sh
```
On Windows:
```
dashboard\run.bat
```
Or cross-platform (works everywhere):
```bash
python3 dashboard/app.py
```
Then open http://localhost:5000 in a browser.

### 5. (Optional) Set up Hunter.io for executive email lookup
- Sign up free at https://hunter.io — the free plan includes 25 domain searches/month
- In the dashboard, click any job → open the **Hunter.io** sidebar → paste the API key
- The key saves locally to `dashboard/.hunter_key` (never committed to git)

## File structure

```
.
├── csm_jobs.csv              ← your personal job data (gitignored, never shared)
├── csm_jobs.example.csv      ← blank template with headers
├── cover_letters/            ← generated cover letters (gitignored)
├── dashboard/
│   ├── app.py                ← Flask dashboard (single file, all inline)
│   └── run.sh                ← launcher script
├── linkedin-csm-scraper.skill
└── linkedin-csm-enrichment.skill
```

## CSV columns

| Column | Description |
|---|---|
| job_id | LinkedIn job ID (unique) |
| date_scraped | When it was added |
| job_title / company | Role and employer |
| company_website | Used by Hunter.io for exec search |
| outreach_status | applied / interviewing / rejected / offer / saved |
| contact1–4_name/title/linkedin/dm | Up to 4 contacts per job |
| discovered_execs | JSON array of execs found via Hunter.io |
| cover_letter_path | Path to the generated cover letter |

## Notes for Claude

- **If the user says "start the dashboard", "open localhost", or similar:** detect their OS, run the appropriate command (`bash dashboard/run.sh` on Mac/Linux, `python3 dashboard/app.py` on Windows), then tell them to open http://localhost:5000.
- **OS detection:** check `sys.platform` or `os.name` in Python, or look at shell environment. Mac/Linux → use `bash` and `pip3`. Windows → use `python` and `pip`.
- The dashboard runs on port 5000 by default. If that port is taken, Flask will error — the user can change `PORT = 5000` at the top of `dashboard/app.py`.
- All data stays local — no cloud sync, no database. Everything is in `csm_jobs.csv`.
- Hunter.io API key is stored in `dashboard/.hunter_key` after the user enters it in the dashboard UI. You do not need to set it via environment variables.
- The skills write to `csm_jobs.csv` in the project root (one level above `dashboard/`).
