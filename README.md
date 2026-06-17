# CSM Outreach Dashboard

A local job outreach tracker for Customer Success Manager roles. Scrape LinkedIn job postings, track contacts and DMs, generate cover letters, and find executive emails — all from a clean local web dashboard.

## What's included

- **Two Claude Code skills** — scrape LinkedIn job URLs and enrich them with contact info
- **Local web dashboard** — Flask app to track outreach status, copy DMs, manage contacts
- **Hunter.io integration** — find executive emails by company domain (25 free searches/month)
- **CSV data store** — all your data stays local, no cloud, no accounts

## Quick start (with Claude Code)

1. Clone this repo and open it in Claude Code
2. Type: `set this up for me`

Claude will install Flask, set up your CSV, install both skills, and start the dashboard.

## Manual setup

```bash
# Install Flask
pip3 install flask

# Create your data file
cp csm_jobs.example.csv csm_jobs.csv

# Install the skills
claude skills install linkedin-csm-scraper.skill
claude skills install linkedin-csm-enrichment.skill

# Start the dashboard
bash dashboard/run.sh
```

Then open http://localhost:5000.

## Usage

1. Find a CSM job on LinkedIn you want to track
2. Run `/linkedin-csm-scraper` in Claude Code → paste the job URL
3. Open the dashboard → click the job → enrich with contacts via `/linkedin-csm-enrichment`
4. Track your outreach status, copy DM templates, add notes
5. Optional: paste a Hunter.io API key in the dashboard to find executive emails

## Hunter.io (optional)

Sign up free at [hunter.io](https://hunter.io) — 25 domain searches/month on the free plan. Enter your API key directly in the dashboard under any job's Hunter sidebar. The key saves locally and is never shared.

## Privacy

Your `csm_jobs.csv`, cover letters, and API key are all gitignored. Only the app code and skills are shared in this repo.
