---
name: linkedin-csm-scraper
description: Scrape LinkedIn for new Customer Success Manager job postings (US, remote, past 24 hours) and append them to a local CSV tracker. Use this skill when asked to run a job scrape, find new CSM jobs, check for new postings, or update the job tracker. Also use it when a scheduled task fires for the daily job search.
---

# LinkedIn CSM Job Scraper

> **FORMATTING RULE - NO EM DASHES:** Never use em dashes (--) anywhere in any output - not in reports, summaries, or any other text. Use a regular hyphen (-) instead. This applies to every piece of text this skill generates, without exception.

Scrapes LinkedIn for Customer Success Manager job postings and appends new entries to a local CSV, deduplicating by Job ID. Every step below reflects what was confirmed working in live testing - follow it exactly for repeatable results.

---

## ⚠️ The one-and-only data file rule (read first)

There is **exactly one** data file in this project: **`{project_root}/csm_jobs.csv`**. Never create a second CSV, never write to a differently-named file, never write to a template/example file. The `append_jobs.py` script enforces this — it refuses any path whose filename isn't `csm_jobs.csv` and it creates the master with the correct columns automatically if it doesn't exist yet. The column layout is defined once in `{project_root}/schema.py`; do not invent your own columns. This is what keeps the scraper, the enrichment skill, and the dashboard perfectly in sync.

---

## Configuration

- **Project root**: The current working directory when this skill runs (i.e. `os.getcwd()` / `$PWD`). All paths below are relative to this.
- **Master CSV path** (the only data file): `{project_root}/csm_jobs.csv`
- **Schema (column definitions)**: `{project_root}/schema.py`
- **Cache path**: `{project_root}/seen_job_ids.txt`
- **Script path**: `<this skill's directory>/scripts/append_jobs.py`
- **Pages to scrape**: Up to 3 pages (stop earlier if fewer results exist)
- **Title filter**: Only process jobs where the title contains "Customer Success Manager" (case-insensitive). Longer titles like "Senior Customer Success Manager, Enterprise" are fine — include them. Skip everything else.

---

## 🎯 CUSTOMIZE: targeting a different role

This skill ships tuned for **Customer Success Manager** roles. If the user asks to track a different role (e.g. "Product Manager", "Account Executive", "Data Analyst"), **don't guess** — walk them through these knobs and confirm each before editing this file:

1. **Search keywords** — the `keywords=` value in the Step 1 URLs (currently `Customer+Success+Manager`).
2. **Title filter** — the phrase in the Configuration block above and the `.includes('customer success manager')` check in the Step 2 JavaScript (currently `customer success manager`).
3. **Location / remote / seniority filters** — the URL params `location`, `f_WT` (2 = remote), and `f_E` (2,4 = entry/mid-senior). Ask the user their preference and adjust.
4. **Report wording & examples** — update the CSM-specific examples in Step 6 to match the new role so reports read naturally.

The CSV schema, the de-dup logic, and the single-master-file rule **do not change** when retargeting — only the search/filter terms above. Make the edits, then tell the user what you changed so they can confirm.

---

## Aggregator & recruiter blocklist

Skip any job where the posting company is a known aggregator or recruiter that hides the real employer. No row should be created for these — they're useless for outreach.

**Skip by company name** (case-insensitive):
Swooped, Ladders, Jobgether, Recruit.net, Jobot, Nexxt, Talentify, Employbl, Adzuna, Hirect, Sci-Rec

**Skip by description text** — if the job description contains any of these phrases, it's a hidden-employer listing regardless of company name:
- "currently partnered with"
- "we are not the employer"
- "on behalf of"
- "our client is"
- "confidential company"

Check both the company name AND description before processing a job.

---

## Step 0 — Load the seen-IDs cache

Before opening any LinkedIn pages, read the cache file at `{project_root}/seen_job_ids.txt`.

Load all IDs into memory as a set (one ID per line, ignore blank lines). This set is your **seen_ids** filter — any job ID in this set is skipped immediately in Step 2, before any browser navigation is done for that job. This prevents re-processing recruiter postings that stay live for weeks.

If the file doesn't exist yet, treat seen_ids as an empty set and continue.

---

## Step 1 — Navigate to each page

Navigate to the search URL for the current page. Pages use the `start` parameter:

- Page 1: `https://www.linkedin.com/jobs/search/?keywords=Customer+Success+Manager&location=United+States&f_TPR=r86400&f_WT=2&f_E=2%2C4`
- Page 2: same URL with `&start=25`
- Page 3: `&start=50`

Wait for the left panel job list to render before extracting. If LinkedIn shows a login page, stop and tell the user to log in first.

---

## Step 2 — Extract all job IDs from the current page

Run this JavaScript to extract job IDs and titles from all visible cards:

```javascript
const cards = document.querySelectorAll('.job-card-container, [data-job-id]');
const jobs = [];
cards.forEach(card => {
  const jobId = card.getAttribute('data-job-id') ||
    card.getAttribute('data-entity-urn')?.match(/\d+/)?.[0];
  const titleEl = card.querySelector('.job-card-list__title, .job-card-container__link');
  const title = titleEl?.textContent?.trim().split('\n')[0].trim();
  if (jobId && title) jobs.push({ jobId, title });
});
// Deduplicate by jobId
const seen = new Set();
const deduped = jobs.filter(j => {
  if (seen.has(j.jobId)) return false;
  seen.add(j.jobId);
  return true;
});
// Filter to CSM titles only
const csm = deduped.filter(j =>
  j.title.toLowerCase().includes('customer success manager')
);
JSON.stringify({ total: deduped.length, csm: csm.length, jobs: csm });
```

Keep only the jobs in the `csm` array. Capture all IDs upfront — you'll use them to load each job directly without navigating back to this page.

**Immediately filter out any job whose `jobId` is in `seen_ids` (loaded in Step 0).** Do not navigate to those jobs at all — they've already been processed in a previous run.

---

## Step 3 — Process each qualifying job

For each job ID from Step 2, follow this sequence exactly.

### 3a — Load the job detail

**Do not use** `/jobs/view/{job_id}/` — that URL renders an empty shell.

Load the job via the search URL with `currentJobId`:
```
https://www.linkedin.com/jobs/search/?currentJobId={job_id}&f_E=2%2C4&f_TPR=r86400&f_WT=2&keywords=Customer%20Success%20Manager&location=United%20States
```

After navigating, call `get_page_text`. A successful load returns the `<article>` element with the full job description starting with "About the job". If the article is missing or shows only the job list (no right panel content), the job has expired or shifted pages — skip it and move on.

### 3b — Check company name and blocklist

Run this JS immediately after loading:
```javascript
document.querySelector('.job-details-jobs-unified-top-card__company-name a')?.textContent?.trim()
```

If the result is `undefined` or `null`, the panel hasn't rendered — wait 3 seconds and retry once. If still undefined, skip the job.

Check the company name against the aggregator blocklist. Also scan the `get_page_text` output for recruiter phrases ("currently partnered with", "on behalf of", etc.). If either match, skip this job entirely — do not create a row.

### 3c — Extract job fields

Parse from the `get_page_text` article output:

| Field | How to extract |
|---|---|
| `job_id` | The `{job_id}` from the URL |
| `job_title` | The job title heading at the top of the article |
| `company` | Company name from the JS in step 3b |
| `job_location` | Look for "Remote", "United States", or a city name near the top |
| `salary` | Any dollar amount or range (e.g. "$100K–$150K", "$76,900 USD"); leave blank if absent |
| `applicant_count` | Text like "Over 100 people clicked apply" or "25 applicants"; leave blank if absent |
| `linkedin_job_url` | `https://www.linkedin.com/jobs/view/{job_id}/` |
| `date_scraped` | Today's date in YYYY-MM-DD format |
| `key_requirements` | 1–2 sentence summary of the "What you'll bring" or "Qualifications" section |

For `easy_apply`, run:
```javascript
document.querySelector('.jobs-apply-button--top-card')?.textContent?.trim()
```
If it contains "Easy Apply" → `"Yes"`. Otherwise → `"No"`.

### 3d — Navigate to the company LinkedIn page

Get the company URL:
```javascript
document.querySelector('.job-details-jobs-unified-top-card__company-name a')?.href
```

This returns something like `https://www.linkedin.com/company/servicetitan/life`. Strip any trailing path to get the clean slug URL: `https://www.linkedin.com/company/{slug}/`. Navigate there.

### 3e — Extract company fields

First try `get_page_text`. A successful company page load returns a header block like:
```
ServiceTitan
The operating system for the trades
Software Development Glendale, California 111K followers 1K-5K employees
```

Parse from that:

| Field | How to extract |
|---|---|
| `company_tagline` | Line immediately after the company name |
| `industry` | First segment on the third line (before the city) |
| `hq_location` | City + state/country on the third line |
| `company_size` | The "X-Y employees" or "XK-YK employees" pattern on the third line |
| `company_linkedin_url` | The clean slug URL you navigated to |

**If `get_page_text` returns a post or article instead of the company header** (this happens when LinkedIn loads a pinned post into the `<article>` slot), fall back to this JS:
```javascript
const name = document.querySelector('h1')?.textContent?.trim();
const infoItems = Array.from(
  document.querySelectorAll('.org-top-card-summary-info-list__info-item')
).map(el => el.textContent.trim());
JSON.stringify({ name, infoItems });
```
`infoItems` returns an array like `["Software Development", "San Diego, CA", "79K followers", "1K-5K employees"]`. Use these to fill in industry, hq_location, and company_size.

For `company_tagline` when using the JS fallback:
```javascript
document.querySelector('.org-top-card-summary__tagline')?.textContent?.trim()
```

### 3f — Get the company website

Use the `find` tool with query: `"Visit website or Learn more external link"`

This returns the `href` directly without navigating. Both "Learn more" and "Visit website" button labels appear depending on the company — the `find` query handles both. Strip UTM parameters and subpaths — keep only the root domain (e.g. `https://www.servicetitan.com`, not `https://www.servicetitan.com/careers?utm_source=linkedin`).

If `find` returns no result, leave `company_website` blank and continue.

---

## Step 4 — Paginate

After processing all qualifying jobs from the current page, move to the next page using the `start` parameter (see Step 1). Repeat Steps 2–3 for up to 3 pages total. Stop early if a page returns 0 qualifying CSM jobs after the seen_ids filter.

---

## Step 5 — Save to CSV

After all pages are processed, build a JSON array of every job object collected. Run:

```bash
python "/path/to/skill/scripts/append_jobs.py" \
  --csv "{project_root}/csm_jobs.csv" \
  --jobs '<json_array>'
```

Replace `{project_root}` with the absolute path of the current working directory, and use the actual absolute path to `scripts/append_jobs.py` inside this skill's directory. The `--csv` argument must always point at `{project_root}/csm_jobs.csv` — the script **refuses** any other filename. The script:
- Refuses to run if `--csv` isn't the master `csm_jobs.csv` (single-file guardrail)
- Creates the master `csm_jobs.csv` with the full canonical header (from `schema.py`) if it doesn't exist yet
- Loads `{project_root}/seen_job_ids.txt` and pre-filters any IDs already there
- Deduplicates by `job_id` against existing rows
- Writes full-width rows that match the existing header exactly (enrichment columns left blank)
- Appends all newly processed IDs to `seen_job_ids.txt` so they're skipped on the next run
- Prints: `Done. Added: N | Skipped (duplicates): N | CSV: /path`

---

## Step 6 — Report back

Tell the user:
- How many pages were scraped
- How many total CSM jobs were found across all pages
- How many were skipped (aggregators/recruiters) and why
- How many were added vs skipped as duplicates
- Path to the updated CSV

Example: "Scraped 2 pages. Found 18 CSM titles. Skipped 4 (Swooped ×2, Ladders, Sci-Rec). Added 11 new rows, 3 already in your tracker."

---

## Edge cases

- **Login page**: Stop immediately and tell the user to log into LinkedIn in Chrome first.
- **Right panel never loads** (undefined company, blank article): Skip that job ID and continue to the next.
- **Job expired mid-run**: If the `currentJobId` URL loads the job list but shows no matching right panel, the job was removed — skip it.
- **Company page returns 404 or redirect**: Leave all company fields blank, continue.
- **No website button found**: Leave `company_website` blank, continue — do not navigate to guess the URL.
- **Salary absent**: Leave blank — never guess or pull from external sources.
- **CAPTCHA appears**: Stop, save whatever jobs have been collected so far by running the CSV script, then report to the user.
