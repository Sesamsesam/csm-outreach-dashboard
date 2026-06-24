---
name: linkedin-csm-enrichment
description: Enrich scraped CSM job rows with up to 4 LinkedIn contacts (recruiter, hiring manager, peer CSM, senior business leader), draft personalized LinkedIn DMs for each, and generate a formal cover letter per job. Use this skill when asked to enrich jobs, find contacts, draft outreach, write cover letters, or personalize the job tracker.
---

# LinkedIn CSM Enrichment Skill

> **FORMATTING RULE - NO EM DASHES:** Never use em dashes (--) anywhere in any output - not in DMs, cover letters, reports, or any other text. Use a regular hyphen (-) instead. This applies to every piece of text this skill generates, without exception.

For each unprocessed row in the CSM jobs CSV, find up to 4 relevant LinkedIn contacts, draft personalized DMs for each, write a formal cover letter, save outputs, and update the CSV. Every strategy in this skill was confirmed working in live LinkedIn testing.

---

## ⚠️ The one-and-only data file rule (read first)

There is **exactly one** data file in this project: **`{project_root}/csm_jobs.csv`**. This skill only ever reads from and writes to that file — never create a second CSV, never write to a differently-named or example file. The `update_contacts.py` script enforces this (it refuses any path whose filename isn't `csm_jobs.csv`) and always preserves the file's existing column order, defined once in `{project_root}/schema.py`. Update rows **in place**; do not rewrite or reshape the file yourself.

---

## Configuration

- **Project root**: The folder this skill lives in, **auto-located by the helper script** — it walks up from its own location (`.claude/skills/.../scripts/`) to find the project root (the folder containing `schema.py`). You do **not** need to compute or pass the project path; it works no matter what the current working directory is (important for scheduled runs). All paths below resolve against that auto-located root.
- **Master CSV path** (the only data file): `{project_root}/csm_jobs.csv`
- **Schema (column definitions)**: `{project_root}/schema.py`
- **Cover letters dir**: `{project_root}/cover_letters/`
- **Script path**: `<this skill's directory>/scripts/update_contacts.py`
- **Process rows where**: ALL four contact slots (`contact1_name` through `contact4_name`) are blank — regardless of `outreach_status`. This is keyed on the data, not the date: a row scraped weeks ago that was never enriched is still picked up. **Always enrich anything not yet enriched.**

---

## 🎯 CUSTOMIZE: targeting a different role

This skill ships tuned for **Customer Success Manager** roles. If the user asks to enrich a different role, **don't guess** — walk them through these knobs and confirm before editing this file:

1. **Contact Priority Tiers** (table below) — for a different function, redefine who Contacts 2–4 should be (e.g. for "Account Executive": Sales Director, peer AE, VP Sales/CRO).
2. **Segment keyword logic** (Step 2) — the parsing rules that pull "Enterprise/Strategic/SMB" out of the title.
3. **People-tab search terms & function codes** (Steps 4–7) — the `keywords=` values and `facetCurrentFunction` codes (12 = recruiting, 26 = "Sales/Customer Success" cluster). Adjust for the new function.
4. **DM tone templates** (Step 8) and **cover-letter emphasis** (Step 9) — rewrite the role-specific phrasing.

The CSV schema, the "enrich anything not yet enriched" rule, the zero-contact deletion behavior, and the single-master-file rule **do not change** when retargeting. Make the edits, then tell the user what you changed.

---

## Contact Priority Tiers

Every job gets up to 4 contacts, in this order:

| # | Type | Who | Why |
|---|------|-----|-----|
| 1 | **Recruiter** | Person actively hiring for this role | Most actionable — they hold the role to fill |
| 2 | **Hiring Manager** | CS Director / Sr. Director overseeing the team | Decision maker |
| 3 | **Peer CSM** | CSM on the same segment team | Warm relationship, insider info |
| 4 | **Senior Business Leader** | GM, VP, CRO, CCO or similar | Unconventional, memorable — found via profile hopping |

If fewer than 4 contacts are found, record what you have and move on. Never fabricate contacts. Always fill slots sequentially starting at contact1 — never leave contact1 blank if any contacts were found.

**Zero-contact rule:** If after all search strategies you find **no usable contacts at all** (not even Contact 1), the company is low-signal — likely too small, stealth, or not a serious employer for outreach. **Delete that job from the tracker** using the script's `--delete` mode (see Step 10). Its `job_id` stays in `seen_job_ids.txt`, so the scraper will never re-add it. Do this only when truly zero contacts were found; one or more contacts means keep the row.

---

## Step 1 — Read unprocessed jobs

Read the CSV at the path above. Identify rows where ALL four contact slots are empty (contact1_name, contact2_name, contact3_name, contact4_name are all blank). Process every such row — do not filter by outreach_status. If all rows already have at least one contact, report that and stop.

For each row, extract:
- `company_linkedin_url` → strip to clean slug URL: `https://www.linkedin.com/company/{slug}/`
- `company_size` → for search strategy selection
- `job_title` → for segment keyword extraction
- `key_requirements` → context for cover letter
- `job_id`, `company`, `company_tagline`, `industry`, `salary` → for cover letter

---

## Step 2 — Extract segment keyword from job title

The segment keyword drives the peer CSM search. Parse the job title:

- "Senior Customer Success Manager, **Strategic**" → `Strategic`
- "**Enterprise** Customer Success Manager" → `Enterprise`
- "**Commercial** CSM" → `Commercial`
- "**SMB** Customer Success Manager" → `SMB`
- "Customer Success Manager" (no segment) → use `Senior Customer Success` as fallback keyword

Also scan the job description / key_requirements for internal team names (e.g., "CSM Team", "Enterprise Team"). If found, this beats the title-derived keyword for the peer search.

---

## Step 3 — Get company slug

From `company_linkedin_url`, extract the slug. Examples:
- `https://www.linkedin.com/company/attentivehq/` → `attentivehq`
- `https://www.linkedin.com/company/servicetitan/life` → `servicetitan`

Base People tab URL: `https://www.linkedin.com/company/{slug}/people/`

---

## Step 4 — Find Contact 1: Recruiter

Navigate to:
```
https://www.linkedin.com/company/{slug}/people/?keywords=recruiter+talent&facetCurrentFunction=12
```

Wait 2 seconds. Call `get_page_text`. Parse the "People you may know" / results section for names and headlines.

Then run JS to extract paths:
```javascript
const cards = document.querySelectorAll('.org-people-profile-card__profile-info');
const results = Array.from(cards).slice(0, 10).map(card => {
  const nameEl = card.querySelector('.artdeco-entity-lockup__title');
  const subtitleEl = card.querySelector('.artdeco-entity-lockup__subtitle');
  const link = card.querySelector('a[href*="/in/"]');
  const path = link ? new URL(link.href).pathname : null;
  return { name: nameEl?.textContent?.trim(), title: subtitleEl?.textContent?.trim(), path };
});
JSON.stringify(results.filter(r => r.name && r.path));
```

**Selection rule**: Pick the recruiter whose headline most specifically targets GTM, CS, or tech roles at this company (e.g., "Hiring GTM @ Attentive" over a general recruiter). If multiple recruiters are equally specific, pick the first result.

Save as Contact 1: `name`, `title` (their LinkedIn headline), `linkedin` (full URL: `https://www.linkedin.com{path}`)

---

## Step 5 — Find Contact 2: Hiring Manager (CS Director)

Choose search URL based on `company_size`:

- **1K-5K or 5K+** (large):
  ```
  https://www.linkedin.com/company/{slug}/people/?keywords=Director+Customer+Success&facetCurrentFunction=26
  ```
- **201-1K** (mid-market):
  ```
  https://www.linkedin.com/company/{slug}/people/?keywords=Director+Manager+Customer+Success&facetCurrentFunction=26
  ```
- **11-200** (small):
  ```
  https://www.linkedin.com/company/{slug}/people/?keywords=CEO+Head+VP+Director+Manager+Customer+Success
  ```
  (no function filter — small orgs often don't segment by function)

Wait 2 seconds. `get_page_text` to see results. Run the same JS as Step 4 to extract paths.

**Selection rule**: Pick the most senior CS person (rank: Sr. Director / VP > Director > Head of > Senior Manager). If multiple at same level, prefer someone whose title mentions the segment (e.g., "Director Customer Success, Strategic" for a Strategic role).

**Important**: Validate the person's title actually matches their CURRENT role at this company — headlines can reflect past jobs. Cross-check the company name in their subtitle if visible.

Save as Contact 2.

---

## Step 6 — Find Contact 3: Peer CSM

Navigate to:
```
https://www.linkedin.com/company/{slug}/people/?keywords={segment_keyword}&facetCurrentFunction=26
```

Where `{segment_keyword}` = what you extracted in Step 2.

Wait 2 seconds. `get_page_text` + JS path extraction.

**Selection rule**: Pick the first result whose headline contains the segment keyword AND "Customer Success" or "CSM". Skip anyone with Director/Manager/Head titles (those belong in Contact 2). Prefer results showing a 2nd-degree connection indicator (they appear with "2nd" in the text).

Save as Contact 3.

---

## Step 7 — Find Contact 4: Senior Business Leader (via profile hopping)

Navigate to Contact 2's LinkedIn profile (the CS Director found in Step 5).

Call `get_page_text`. Find the "More profiles for you" section near the bottom.

Parse for people with senior leadership titles: **GM, General Manager, VP, SVP, EVP, CRO, CCO, Chief, President, Head of Revenue, Head of GTM**. Exclude other CS Managers/Directors — those are already covered.

Run JS to find their profile path:
```javascript
// Look for 'More profiles for you' section links
const links = Array.from(document.querySelectorAll('a[href*="/in/"]'));
// Filter to unique /in/ paths that aren't the current profile
const paths = [...new Set(links.map(a => new URL(a.href).pathname))]
  .filter(p => p !== window.location.pathname);
JSON.stringify(paths.slice(0, 15));
```

Cross-reference the paths against names/titles seen in `get_page_text` output to match the right person.

**Selection rule**: Pick the most senior non-CS-manager person. Prefer: GM of the business unit the role sits in > CRO/CCO > VP of a relevant function > any SVP/EVP.

Save as Contact 4.

**Fallback**: If no suitable senior leader found on Contact 2's profile, navigate to the company page and try:
```
https://www.linkedin.com/company/{slug}/people/?keywords=VP+General+Manager+CRO
```

---

## Step 8 — Draft DMs

Write a short LinkedIn DM for each contact found. Use the person's name, their title, and the specific job role. Keep every DM under 300 characters (LinkedIn's DM character limit is 300 for connection requests; InMail can be longer, but keeping it short is better for response rates).

**Tone and length guidelines:**

### Recruiter DM (Contact 1)
- Lead with the exact role name
- State your most relevant credential in 1 sentence
- Simple ask: interested in being considered / would love to connect
- Example structure: "Hi [Name], I saw you're recruiting for [exact job title] at [Company]. I have [X years/specific experience]. Would love to be considered!"

### Hiring Manager DM (Contact 2)
- Reference their team or their department
- Lead with what you'd bring to their specific challenge (use key_requirements context)
- Ask if they'd have a few minutes
- Example structure: "Hi [Name], I noticed you lead CS at [Company] and your team is hiring a [role]. With my background in [relevant skill from key_requirements], I'd love to connect and learn more about the team."

### Peer CSM DM (Contact 3)
- Casual, no hard sell
- Say you're applying for a similar role and are curious about the team/culture
- Example structure: "Hi [Name], I noticed you're on the [segment] CS team at [Company] — I'm applying for a similar role and would love to hear a bit about your experience there if you're open to it!"

### Senior Business Leader DM (Contact 4)
- Bold, specific opener — name the role and show you know their business
- Reference something specific about what they oversee (from job description or company context)
- Simple ask: happy to connect
- Example structure: "Hi [Name], I'm applying for the [role] at [Company] — your work building [their business unit/function] is exactly the kind of environment I'm looking to contribute to. Would love to connect!"

Store the drafted DM as `contact{N}_dm`.

---

## Step 9 — Generate cover letter

Write one formal cover letter per job. Save to:
```
{project_root}/cover_letters/{job_id}_{company_slug}.txt
```
Where `{company_slug}` = company name lowercased with spaces replaced by underscores (e.g., `4380516954_servicetitan.txt`).

**Cover letter format** (~350 words, 4-5 paragraphs):

1. **Opening**: Reference the company's mission/tagline and the specific role. Show genuine interest — not generic.
2. **Relevant experience**: Map 2-3 of the user's strongest credentials to the key_requirements. Be specific.
3. **Why this company**: 2-3 sentences on why this company specifically — use the industry, product, and company_tagline context.
4. **What you bring**: Brief forward-looking paragraph on how you'd contribute.
5. **Closing**: Formal close, express enthusiasm for next steps.

To get `{project_root}` reliably (without depending on the current working directory), run once:
```bash
python "<this skill's dir>/scripts/update_contacts.py" --print-root
```
Use the path it prints as `{project_root}` for the cover-letter file and `user_profile.txt` below.

Before writing the first cover letter, check for `{project_root}/user_profile.txt`. If it exists, read the user's name and email from it (format: `Name: ...` / `Email: ...`). If the file doesn't exist, ask the user for their name and email now, then write the file so future sessions don't need to ask again. Use name and email in the closing signature.

**Tone**: Professional and warm, not robotic. Avoid buzzword soup. It should sound like a real person who did their research.

Create the `{project_root}/cover_letters/` directory if it doesn't exist.

---

## Step 10 — Save to CSV

After processing each job, run the update script:

```bash
python "<this skill's dir>/scripts/update_contacts.py" \
  --job_id "{job_id}" \
  --data '{
    "contact1_name": "...",
    "contact1_title": "...",
    "contact1_linkedin": "https://www.linkedin.com/in/...",
    "contact1_dm": "...",
    "contact2_name": "...",
    "contact2_title": "...",
    "contact2_linkedin": "https://www.linkedin.com/in/...",
    "contact2_dm": "...",
    "contact3_name": "...",
    "contact3_title": "...",
    "contact3_linkedin": "https://www.linkedin.com/in/...",
    "contact3_dm": "...",
    "contact4_name": "...",
    "contact4_title": "...",
    "contact4_linkedin": "https://www.linkedin.com/in/...",
    "contact4_dm": "...",
    "cover_letter_path": "{project_root}/cover_letters/{job_id}_{company_slug}.txt"
  }'
```

Use the actual absolute path to `scripts/update_contacts.py` inside this skill's directory. **You do not need to pass `--csv`** — the script auto-locates `csm_jobs.csv` in the project root from its own location, so it works regardless of the current working directory. For `cover_letter_path`, use the `{project_root}` you obtained via `--print-root` above. Leave blank any contact fields where no person was found (but at least Contact 1 should be filled — see the zero-contact rule).

**If zero contacts were found for a job**, do not run the update command above. Instead delete the row:

```bash
python "<this skill's dir>/scripts/update_contacts.py" \
  --job_id "{job_id}" \
  --delete
```

This removes the low-signal job from the tracker while leaving its `job_id` in `seen_job_ids.txt` so it's never re-scraped.

---

## Step 11 — Report back

After all rows are processed, report:
- How many jobs were enriched
- How many jobs were deleted for having zero contacts (and which companies)
- For each enriched job: company name, contacts found (N/4), their names and types
- Path to updated CSV
- List of cover letter files created

Example:
```
Enriched 2 jobs:

ServiceTitan (4 contacts):
  1. Recruiter — Jane Smith (/in/janesmith)
  2. Hiring Manager — Alona Markowitz, Sr. Director CS (/in/alonamarkowitz)
  3. Peer CSM — Nicole Moore, CSM (/in/nicoleanderson)
  4. Business Leader — Alex Kablanian, GM Commercial (/in/alexkablanian)
  Cover letter: cover_letters/4380516954_servicetitan.txt

Attentive (3 contacts):
  1. Recruiter — Andrea Rodriguez (/in/androdriguez)
  2. Hiring Manager — Karen DiClemente, Sr. Director CS (/in/karendiclemente)
  3. Peer CSM — Miriam W., Sr. CSM Strategic (/in/miriamw)
  4. Business Leader — not found
  Cover letter: cover_letters/4429905861_attentive.txt
```

---

## Edge Cases

- **0 results on People tab search**: Try removing the `facetCurrentFunction` parameter and retry. If still 0, skip that contact tier and move on.
- **Zero contacts for the whole job** (no Contact 1 after every strategy): Delete the row with `--delete` (Step 10). Don't keep empty rows around — they'd be re-attempted on every future run.
- **Acquired company / company page shows new brand**: Try the original slug anyway; if People tab is empty, search the new parent company's slug.
- **Contact 2 profile shows no "More profiles for you"**: Skip Contact 4 for this job.
- **DM > 300 characters**: Trim to under 300, keeping the core ask and name intact.
- **Cover letter dir missing**: Create it with `mkdir -p` before writing.
- **Login wall appears**: Stop immediately and ask the user to log into LinkedIn in Chrome first.
- **Premium (✦) profiles**: Name, title, and path are still extractable from People tab search results even if the full profile is paywalled.
- **Misleading headline (contact seems wrong level)**: The People tab shows LinkedIn headlines, not current job titles. A headline like "Manager overseeing teams with $50M ARR" may refer to a past role. If uncertain, navigate to the person's full profile to verify their current role before selecting them as Contact 2.
