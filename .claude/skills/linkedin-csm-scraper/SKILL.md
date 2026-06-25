---
name: linkedin-csm-scraper
description: Scrape LinkedIn for new job postings matching your configured search (ships tuned for Customer Success Manager) and append them to a local CSV tracker. Use this skill when asked to run a job scrape, find new jobs (CSM or any configured role), check for new postings, or update the job tracker. Also use it when a scheduled task fires for the daily job search.
---

# LinkedIn CSM Job Scraper

> **FORMATTING RULE - NO EM DASHES:** Never use em dashes (--) anywhere in any output - not in reports, summaries, or any other text. Use a regular hyphen (-) instead. This applies to every piece of text this skill generates, without exception.

Scrapes LinkedIn for job postings matching the configured search (loaded in Step 0a) and appends new entries to a local CSV, deduplicating by Job ID. Ships tuned for Customer Success Manager, but the skill text names no role - all targeting lives in the search config. Every step below reflects what was confirmed working in live testing - follow it exactly for repeatable results.

---

## ⚠️ The one-and-only data file rule (read first)

There is **exactly one** data file in this project: **`{project_root}/csm_jobs.csv`**. Never create a second CSV, never write to a differently-named file, never write to a template/example file. The `append_jobs.py` script enforces this — it refuses any path whose filename isn't `csm_jobs.csv` and it creates the master with the correct columns automatically if it doesn't exist yet. The column layout is defined once in `{project_root}/schema.py`; do not invent your own columns. This is what keeps the scraper, the enrichment skill, and the dashboard perfectly in sync.

---

## Configuration

- **Project root**: The folder this skill lives in, **auto-located by the helper script** — it walks up from its own location (`.claude/skills/.../scripts/`) to find the project root (the folder containing `schema.py`). You do **not** need to compute or pass the project path; it works no matter what the current working directory is (important for scheduled runs). All paths below resolve against that auto-located root.
- **Master CSV path** (the only data file): `{project_root}/csm_jobs.csv`
- **Schema (column definitions)**: `{project_root}/schema.py`
- **Cache path**: `{project_root}/seen_job_ids.txt`
- **Script path**: `<this skill's directory>/scripts/append_jobs.py`
- **Pages to scrape**: `{pages_to_scrape}` from the config (stop earlier if fewer results exist).
- **Title filter**: Only process jobs whose title contains `{title_match_phrase}` from the config (case-insensitive). Longer titles that also contain the phrase are fine — include them. Skip everything else.

> Everything role-specific in this skill is a code-word in `{curly braces}`, resolved from the search config loaded in **Step 0a**. The skill text never names a role itself - the config is the only legend.

---

## 🎯 CUSTOMIZE: targeting a different role

> **STOP - is the user asking to change settings, or to run a scrape?** If the user said something like "search UK", "look for PM jobs", "only remote", "only senior roles", or anything about changing *what* gets searched - **do not run this skill.** That is a settings change. Follow `{project_root}/RETARGETING.md` (or see `CLAUDE.md` → "Recognizing a settings change") to update `search_config.json`, then confirm the change. Only run this skill when the user wants to execute a search with the current settings.

This skill's behavior is driven entirely by the search config (the code-word legend) - **the skill text itself names no role.** To change or add to what gets scraped, **don't guess** — the single entry point is **`{project_root}/RETARGETING.md`**, and the change is a single edit to **`search_config.json`** (the menu card). Walk the user through it and confirm each change.

The scraper code-words (all documented in `RETARGETING.md` with their LinkedIn meaning) are: `search_keywords`, `title_match_phrase`, `location`, `work_type`, `seniority`, `recency`, `pages_to_scrape`, `blocklist_companies`, `blocklist_phrases`, `exclude_work_permit_required`, `work_permit_block_phrases`, and `work_permit_positive_phrases`. Capturing a brand-new field (a new CSV column) is the one case that also touches `schema.py` - see `RETARGETING.md`.

**Forward-only:** retargeting never touches rows already in `csm_jobs.csv` — old jobs stay in the tracker even if they no longer match the new knobs. The CSV schema, the de-dup logic, and the single-master-file rule **do not change** when retargeting — only the config values. After editing `search_config.json`, tell the user what changed.

---

## Aggregator & recruiter blocklist

Skip any job where the posting company is a known aggregator or recruiter that hides the real employer. No row should be created for these — they're useless for outreach.

- **Skip by company name** (case-insensitive): if the posting company matches any entry in `{blocklist_companies}` from the config.
- **Skip by description text**: if the job description contains any phrase in `{blocklist_phrases}` from the config, it's a hidden-employer listing regardless of company name.

The actual company names and phrases live only in the config (`search_config.example.json` ships the defaults). Check both the company name AND description before processing a job.

---

## ⚙️ Step 0a (DO THIS FIRST, before any browser navigation) — Load the search config

**The search config is the single source of truth for what this skill scrapes. Every search/filter decision below uses these values, not the example values written inline.** This applies identically to on-demand runs and scheduled runs - both load the config first, so a scheduled scrape can never drift back to a previous role.

Load it from the project root, preferring the live file and falling back to the shipped default:

```bash
python3 -c "
import json, os
root = os.environ.get('PROJECT_ROOT') or '{project_root}'
for name in ('search_config.json', 'search_config.example.json'):
    p = os.path.join(root, name)
    if os.path.exists(p):
        print(json.dumps(json.load(open(p))['scraper'])); break
"
```

(`{project_root}` is the auto-located root - the folder containing `schema.py`.) From the returned `scraper` object, bind these code-words; every step below uses them as placeholders, never literal role values:

| Code-word (config key) | Substituted into |
|---|---|
| `{search_keywords}` | the `keywords=` URL param (Step 1 + Step 3a) |
| `{title_match_phrase}` | the title filter (Configuration + Step 2 JS) |
| `{location}` | the `location=` URL param |
| `{work_type}` | the `f_WT=` URL param (LinkedIn: on-site 1, remote 2, hybrid 3) |
| `{seniority}` | the `f_E=` URL param (URL-encode any comma as `%2C`) |
| `{recency}` | the `f_TPR=` URL param |
| `{pages_to_scrape}` | how many pages to page through (Step 4) |
| `{blocklist_companies}` / `{blocklist_phrases}` | the aggregator/recruiter blocklist (Step 3b) |
| `{exclude_work_permit_required}` | if `true`, skip jobs that explicitly won't sponsor (Step 3g) |
| `{work_permit_block_phrases}` | "no sponsorship" phrases that trigger a skip (Step 3g) |
| `{work_permit_positive_phrases}` | phrases that mark a job as sponsorship-friendly (Step 3c / 3g) |

**Hard rule:** the steps below contain **only code-words in `{curly braces}`** for anything role-specific - never a literal role name, keyword, or filter value. Always substitute the value loaded from the config. Never scrape for a role the config does not specify. The config is the only place the actual values live (the live `search_config.json`, or the committed `search_config.example.json` default). If **neither** file exists, stop and tell the user the search config is missing - do not invent values.

---

## Step 0 — Load the seen-IDs cache

Before opening any LinkedIn pages, read the cache file at `{project_root}/seen_job_ids.txt`.

Load all IDs into memory as a set (one ID per line, ignore blank lines). This set is your **seen_ids** filter — any job ID in this set is skipped immediately in Step 2, before any browser navigation is done for that job. This prevents re-processing recruiter postings that stay live for weeks.

If the file doesn't exist yet, treat seen_ids as an empty set and continue.

---

## Step 1 — Navigate to each page

Navigate to the search URL for the current page, **built from the code-words loaded in Step 0a** (substitute each `{...}` with its config value; URL-encode as needed). Pages use the `start` parameter:

- Page 1 (template): `https://www.linkedin.com/jobs/search/?keywords={search_keywords}&location={location}&f_TPR={recency}&f_WT={work_type}&f_E={seniority}`
- Page 2: same URL with `&start=25`
- Page 3: `&start=50`

Page through `{pages_to_scrape}` pages total (see Step 4).

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
// Filter to matching titles only.
// Substitute {title_match_phrase} below with the config value (lowercased), e.g. '...'.includes('{title_match_phrase}')
const matched = deduped.filter(j =>
  j.title.toLowerCase().includes('{title_match_phrase}')
);
JSON.stringify({ total: deduped.length, matched: matched.length, jobs: matched });
```

Before running the JS, replace `{title_match_phrase}` with the lowercased config value. Keep only the jobs in the `matched` array. Capture all IDs upfront — you'll use them to load each job directly without navigating back to this page.

**Immediately filter out any job whose `jobId` is in `seen_ids` (loaded in Step 0).** Do not navigate to those jobs at all — they've already been processed in a previous run.

---

## Step 3 — Process each qualifying job

For each job ID from Step 2, follow this sequence exactly.

### 3a — Load the job detail

**Do not use** `/jobs/view/{job_id}/` — that URL renders an empty shell.

Load the job via the search URL with `currentJobId`, **using the same code-words as Step 1**:
```
https://www.linkedin.com/jobs/search/?currentJobId={job_id}&f_E={seniority}&f_TPR={recency}&f_WT={work_type}&keywords={search_keywords}&location={location}
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
| `salary` | Any dollar amount or range (e.g. "$100K–$150K", "$76,900 USD"); leave blank if absent. A blank salary never disqualifies a job. |
| `work_authorization` | Scan the description for sponsorship language. If it contains any `{work_permit_positive_phrases}` entry → `"Sponsorship available"`. If it contains any `{work_permit_block_phrases}` entry → `"No sponsorship"`. Otherwise → `"Not specified"`. This field also drives the `{exclude_work_permit_required}` filter in Step 3g. |
| `applicant_count` | Text like "Over 100 people clicked apply" or "25 applicants"; leave blank if absent |
| `linkedin_job_url` | `https://www.linkedin.com/jobs/view/{job_id}/` |
| `date_scraped` | Today's date in YYYY-MM-DD format |
| `key_requirements` | 1–2 sentence summary of the "What you'll bring" or "Qualifications" section |
| `hard_requirements` | The **documentation-gated must-haves only** - things an applicant cannot bend their background to satisfy because they would have to *produce proof*: a specific degree/field (e.g. "Bachelor's in Engineering"), a professional license or certification (e.g. "Active RN license", "CPA", "PMP"), a security clearance, bar admission, or legal credential. Write **at most 3** short bullets, separated by `; ` (semicolon-space). Exclude soft/bendable items - years of experience, "preferred", "nice to have", tool familiarity, soft skills. If the posting lists none, leave blank. **Degrees - the field is what matters:** only record a degree as a hard requirement when it names a **specific field** (e.g. "Bachelor's in Nursing"). A generic "Bachelor's degree required" with **no field** is satisfied by *any* degree, so do **not** list it as a hard requirement - flagging it would wrongly mark jobs the user actually qualifies for. See the education-filter note in `RETARGETING.md`. |
| `years_experience` | The required years of experience as a short phrase if stated (e.g. "4+ years", "5-7 years"); leave blank if not stated. This is captured separately because it is **not** a hard requirement - it is shown for context, not as a disqualifier. |

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

### 3g — Apply the work-permit filter

After the fields are extracted, decide whether this job earns a row. This filter is a config toggle loaded in Step 0a; apply it only when the toggle is on. A job that fails it is **dropped - do not create a row for it** (same as a blocklisted job). Do **not** add its ID to `seen_job_ids.txt`, so a later run can re-check it if the posting is updated (a sponsorship note may be added after first posting).

**Work-permit filter** - if `{exclude_work_permit_required}` is `true` and the description contains any phrase in `{work_permit_block_phrases}` (case-insensitive - these are explicit "no sponsorship" statements), **skip the job.** A posting that simply says nothing about sponsorship is **kept** (its `work_authorization` is `"Not specified"`); only an explicit refusal triggers the skip.

> Salary is **not** a filter - a job with no salary shown is always kept (a blank `salary` is fine). Only the work-permit check can drop a job here.

Jobs that pass keep their extracted `work_authorization` value and proceed to the CSV in Step 5. When you skip a job here, note it for the Step 6 report (e.g. "1 skipped: no sponsorship").

---

## Step 4 — Paginate

After processing all qualifying jobs from the current page, move to the next page using the `start` parameter (see Step 1). Repeat Steps 2–3 for up to `{pages_to_scrape}` pages total. Stop early if a page returns 0 qualifying jobs (matching `{title_match_phrase}`) after the seen_ids filter.

---

## Step 5 — Save to CSV

After all pages are processed, build a JSON array of every job object collected. Run:

```bash
python "<this skill's dir>/scripts/append_jobs.py" \
  --jobs '<json_array>'
```

Use the actual absolute path to `scripts/append_jobs.py` inside this skill's directory. **You do not need to pass `--csv`** — the script auto-locates `csm_jobs.csv` in the project root from its own location, so it works regardless of the current working directory (this is what makes scheduled runs reliable). Only pass `--csv` if you deliberately need to override the target, and even then the filename must be `csm_jobs.csv` — the script **refuses** any other filename. The script:
- Refuses to run if `--csv` isn't the master `csm_jobs.csv` (single-file guardrail)
- Creates the master `csm_jobs.csv` with the full canonical header (from `schema.py`) if it doesn't exist yet
- Loads `{project_root}/seen_job_ids.txt` and pre-filters any IDs already there
- Deduplicates by `job_id` against existing rows
- Writes full-width rows that match the existing header exactly (enrichment columns left blank)
- Appends all newly processed IDs to `seen_job_ids.txt` so they're skipped on the next run
- Prints: `Done. Added: N | Skipped (duplicates): N | CSV: /path`

---

## Step 6 — Report scrape results (this is NOT the end - enrichment follows immediately)

Give a brief summary of the scrape. **Do NOT end your turn here - Step 7 is mandatory and must happen in the same response.** This is a mid-flow status update, not a stopping point.

Tell the user:
- How many pages were scraped
- How many total matching jobs were found across all pages
- How many were skipped (aggregators/recruiters) and why
- How many were skipped by the work-permit filter (Step 3g) and why
- How many were added vs skipped as duplicates

Example: "Scraped 2 pages. Found 18 matching titles. Skipped 4 (2 aggregators, 2 recruiters), 1 that won't sponsor. Added 11 new rows, 2 already in your tracker. Now enriching these rows with contacts and outreach..."

**Then immediately continue to Step 7. Do not wait for user input.**

## Step 7 — Automatically run enrichment (MANDATORY - DO NOT STOP HERE)

**⚠️ CRITICAL: Do NOT stop, pause, wait for user input, or end your turn after reporting scrape results. You MUST immediately proceed to enrichment in the same response - no exceptions. This applies to on-demand runs, scheduled runs, and every other context. Stopping here breaks the scheduled workflow.**

**Do not ask the user whether to enrich. Do not say "just a moment" and then wait. Do not end your message after the scrape report. Immediately - in the same turn, with no interruption - begin the enrichment skill.**

After reporting the scrape results (Step 6), continue directly in the same response to run the enrichment skill (`/linkedin-csm-enrichment` in Claude Code, or follow `.claude/skills/linkedin-csm-enrichment/SKILL.md` in Cowork) to enrich every row that hasn't been enriched yet. The scraper and enrichment skills are designed to run as a single uninterrupted flow. Treat Steps 1-7 and the entire enrichment process as one atomic operation - there is no stopping point between scraping and enriching.

---

## Edge cases

- **Login page**: Stop immediately and tell the user to log into LinkedIn in Chrome first.
- **Right panel never loads** (undefined company, blank article): Skip that job ID and continue to the next.
- **Job expired mid-run**: If the `currentJobId` URL loads the job list but shows no matching right panel, the job was removed — skip it.
- **Company page returns 404 or redirect**: Leave all company fields blank, continue.
- **No website button found**: Leave `company_website` blank, continue — do not navigate to guess the URL.
- **Salary absent**: Leave blank — never guess or pull from external sources. A blank salary never disqualifies a job.
- **Sponsorship language ambiguous**: Only treat an *explicit* refusal (a `{work_permit_block_phrases}` match) as "won't sponsor". Generic "must be authorized to work" with no mention of sponsorship is **not** a refusal - set `work_authorization` to "Not specified" and keep the job.
- **CAPTCHA appears**: Stop, save whatever jobs have been collected so far by running the CSV script, then report to the user.
