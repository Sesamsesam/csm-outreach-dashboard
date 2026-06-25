# Retargeting the job search (change or add knobs on the fly)

> **FORMATTING RULE - NO EM DASHES:** Never use em dashes anywhere in any output. Use a regular hyphen (-) instead.

This guide is the **single entry point** for changing what the two skills look for. It works the same whether the user is in **Claude Code** or **Cowork** (the Cowork plugin launchers delegate to the same `.claude/skills/` files, which read the same config this guide edits).

Use this whenever the user wants to **change** the search (different role, location, remote setting, recency, seniority, tone) **or add** something new (a new filter, a brand-new knob, a new captured field, a new contact type). For a brand-new knob, jump to **"Adding a brand-new knob: the full sync checklist"** - it lists every file to touch so the config never drifts out of sync with what runs.

---

## The model: one config file is the source of truth

All the knobs live in **`search_config.json`** in the project root. **Both skills load it at the start of every run** - scheduled or on-demand - and use only its values for every scraping and enrichment decision. The role-specific strings written inline in the skills are just labeled *defaults*; the loaded config always wins.

This is what makes retargeting a **one-way street**: change the config once, and every future run (including scheduled scrapes) follows the new targeting. A scheduled task can never drift back to a previous role, because it reads the same config the user just edited. The dashboard reads the same file and shows a "Current search settings" panel, so the user always sees what the next run will do.

**Files:**
- `search_config.json` - the live, user-edited settings. **Gitignored** (personal targeting never ships).
- `search_config.example.json` - the shipped Customer Success Manager default. Committed. Used as the fallback when no live config exists, and as the template to copy from.

So retargeting = **edit `search_config.json`** (create it by copying `search_config.example.json` if it does not exist yet). That single edit is the whole change - there are no inline values to hunt down.

---

## 🔒 Two rules that never change when retargeting

1. **Forward-only. Never touch existing rows.** Changing the config only affects **future** runs. Jobs already in `csm_jobs.csv` stay exactly as they are - even if they no longer match the new role/location/filters. They remain visible in the dashboard. Do **not** delete, re-filter, or "clean up" old rows to match new targeting. The user has explicitly confirmed this is desired.
2. **Still exactly one data file.** `csm_jobs.csv` stays the only data file, and its filename never changes (it is the guardrail constant `MASTER_CSV_NAME` in `schema.py`, not a role label - a "Sales" search still writes to `csm_jobs.csv`). Do not rename it.

---

## Users speak casually - translate, don't ask them to learn the config

The people using this project are not technical and did not build it. They will never say "change the `location` key" or "retarget the scraper." They will say "search United Kingdom" or "look for jobs in London." **Your job is to translate their plain language into the correct config key, confirm your understanding, and make the edit.**

If the user has already told you what they want (e.g. "search UK instead"), do NOT ask them to "pick a knob" - just confirm: "I'll change the search location from United States to United Kingdom. That sound right?" Then do it.

**Which block does their request touch?**
- **Where / what / when to search** (location, role, seniority, remote, recency, filters) → `scraper` block
- **Who to contact / how to write outreach** (DM tone, cover letter emphasis, contact types) → `enrichment` block
- **Change the role entirely** (e.g. "search for Product Manager") → **both blocks** - update `role_label`, `search_keywords`, `title_match_phrase`, `role_function`, `manager_title_keywords`, `contact_tiers`, and `function_code` together. See the Config Reference below.

See `CLAUDE.md` → **"Recognizing a settings change"** for a full table of example phrases mapped to config keys.

---

## How to run a retargeting session

1. **Read the current `search_config.json`** (or `search_config.example.json` if no live file exists yet) so you know the starting point.
2. **Confirm your understanding of what they want.** If the user already told you (e.g. "search UK"), confirm in plain language ("I'll change the search location to United Kingdom - correct?"). If their request is vague, ask a short clarifying question. Do not present them with a list of config keys or technical options - keep it conversational.
3. **Confirm the new values** in plain language before editing (e.g. "So: role = Account Executive, location = United States, remote only, posted in the last 7 days - correct?").
4. **Decide if the CSV is affected** using the decision rule below. Almost everything is config-only.
5. **Edit `search_config.json`** (create it from the example first if needed). Update `last_updated` to today. For label fields (`work_type_label`, `seniority_label`, `recency_label`), set a human-readable string so the dashboard panel reads well.
6. **Report back** what changed, and confirm old jobs were left untouched and the next scheduled run will use the new settings.

---

## Does this change the CSV? (decision rule)

| The user wants to... | CSV change? | What to do |
|---|---|---|
| Change role / keywords / title filter | **No** | Edit `search_config.json` only. |
| Change location / remote / seniority / recency / pages | **No** | Edit `search_config.json` only. |
| Change contact tiers / function codes / DM tone / cover-letter emphasis / zero-contact behavior | **No** | Edit `search_config.json` only. |
| Adjust an **existing** list/value (add an aggregator to skip, add a keyword, change a tone) | **No** | Edit the relevant key in `search_config.json`. One-file change. |
| Add a **brand-new knob** (a config key that does not exist yet, e.g. a new filter toggle) | **No** (usually) | Follow **Adding a brand-new knob: the full sync checklist** below. More than one file, but no CSV change. |
| **Capture a brand-new field** (e.g. "track visa sponsorship", add a 5th contact) | **Yes** | Follow **Additive change: new captured field** below. |

The only thing that ever changes the CSV is **adding a new captured field** (a new column). Everything else is config. And even a new column is **additive** - it appends a blank column and never deletes existing rows.

> **Adjusting an existing knob vs. adding a new one.** If the knob already exists in `search_config.example.json` (it has a row in the Config Reference below), changing it is a **one-file edit** to `search_config.json` - the skills already read it. If the knob is **new** (no key today), the config alone is not enough: the skill has to be taught to *load* and *use* it, or it will be silently ignored. That is the drift trap the checklist below exists to prevent.

---

## Config Reference (every knob, by config key)

### `scraper` block
| Config key | Controls | CSM default |
|---|---|---|
| `search_keywords` | LinkedIn `keywords=` (URL-encoded, `+` between words) | `Customer+Success+Manager` |
| `title_match_phrase` | which titles qualify (lowercased substring match) | `customer success manager` |
| `location` | LinkedIn `location=` | `United+States` |
| `work_type` / `work_type_label` | `f_WT=` - on-site `1`, remote `2`, hybrid `3` (omit for any) | `2` / "remote only" |
| `seniority` / `seniority_label` | `f_E=` - internship `1`, entry `2`, associate `3`, mid-senior `4`, director `5`, executive `6` (comma-separate) | `2,4` / "entry + mid-senior" |
| `recency` / `recency_label` | `f_TPR=` - past 24h `r86400`, week `r604800`, month `r2592000` | `r86400` / "past 24 hours" |
| `pages_to_scrape` | how many result pages to page through | `3` |
| `blocklist_companies` | aggregator/recruiter company names to skip | see config |
| `blocklist_phrases` | hidden-employer phrases to skip | see config |
| `exclude_work_permit_required` | if `true`, skip a job whose description has an explicit "no sponsorship" phrase; jobs silent on sponsorship are kept | `true` |
| `work_permit_block_phrases` | the explicit "won't sponsor" phrases that trigger the skip | see config |
| `work_permit_positive_phrases` | phrases that mark a kept job as "Sponsorship available" in the `work_authorization` column | see config |

> The work-permit filter records its finding in the `work_authorization` column (`Sponsorship available` / `No sponsorship` / `Not specified`). That column is shipped as a `custom_fields_added` entry, so it already exists in `schema.py` - turning the filter on/off is config-only and never touches the CSV schema.

### `enrichment` block
| Config key | Controls | CSM default |
|---|---|---|
| `num_contacts` | contact slots to fill per job | `4` |
| `role_function` | the function phrase used in manager/peer searches and selection rules | `Customer Success` |
| `contact_tiers` | who Contacts 1..N are (`type` + `who`) | Recruiter / Hiring Manager / Peer / Senior Business Leader |
| `recruiter_function_code` | `facetCurrentFunction=` for the recruiter search | `12` |
| `function_code` | `facetCurrentFunction=` for the manager/peer searches | `26` |
| `manager_title_keywords` | People-tab `keywords=` for the hiring-manager search | `Director Manager Customer Success` |
| `segment_keywords` / `segment_fallback` | segment parsing for the peer search | Strategic/Enterprise/Commercial/SMB |
| `senior_leader_titles` | senior titles to target for Contact 4 | GM/VP/CRO/CCO/... |
| `dm_tone` | tone for all drafted DMs | warm, peer-to-peer |
| `cover_letter_emphasis` | what the cover letter emphasizes | CS outcomes |
| `zero_contact_behavior` | `delete` or `keep` a job with no contacts found | `delete` |

> When changing the role, set `role_function` (e.g. "Sales"), `manager_title_keywords` (e.g. "Director Manager Sales"), and `contact_tiers` together so the People-tab searches and selection rules line up.

### Top level
| Config key | Controls |
|---|---|
| `role_label` | friendly name shown in the dashboard panel |
| `last_updated` | date of the last retarget (set this on every edit) |
| `custom_fields_added` | list of any new CSV columns added (see below) |

### LinkedIn function codes (for `recruiter_function_code` / `function_code`)
`12` HR/Recruiting · `26` Sales/Customer Success cluster · `13` Engineering · `15` IT · `17` Marketing · `4` Business Development · `10` Finance. If unsure, omit the function filter and rely on `keywords` - the search still works, just less precisely.

---

## Adding a brand-new knob: the full sync checklist

Use this when the user asks for a **new** behavior knob that does not exist in the config yet (a new filter toggle, a new phrase list, a new search parameter). The work-permit filter (`exclude_work_permit_required` + its phrase lists) was added exactly this way - use it as the worked example.

A knob is only "wired" when **every** place that needs to know about it has been updated. Touch these in order; skipping any one is how drift happens.

| # | File | What to add | Why it is required |
|---|---|---|---|
| 1 | **`search_config.example.json`** | The new key, **plus a `"<key>_label"` companion** if you want it shown in the dashboard (the panel auto-displays any knob that has one). Put it under the right block (`scraper` or `enrichment`). Add a one-line note to `_filters_note` / `_README` if behavior is non-obvious. | This is the committed default **and** the fallback a fresh clone uses. The knob's real default lives here, and the `_label` is what the dashboard panel shows. |
| 2 | **`.claude/skills/<skill>/SKILL.md`** (scraper and/or enrichment) | (a) add the key to the **Step 0a "bind these code-words" table**; (b) reference it only as a `{code-word}` in the step that uses it - never inline a literal value; (c) state the **default-if-absent** behavior. | The skill only "sees" config keys it loads in Step 0a. A key the skill never binds is dead config. This is the step most often forgotten. |
| 3 | **`RETARGETING.md`** (this file) | A row in the Config Reference table for the new key. | So the next retarget knows the knob exists and what it controls - keeps this guide self-complete. |
| 4 | **`dashboard/app.py`** -> `search_config_summary()` *(usually automatic - no edit)* | If you gave the knob a `"<key>_label"` companion in step 1, the panel **auto-displays it** in the same style (label humanized from the key) - nothing to edit here. Only touch this file to give the knob a **custom icon**, a **fixed position** in the curated order, or **special formatting** (e.g. chips like `contact_tiers`): add it to `_SCRAPER_KNOBS` / `_ENRICHMENT_KNOBS`. | The "Current search settings" panel is how the user confirms what the next run will do. The auto-display reads the `_label`, so older configs without the key still render fine. |
| 5 | *(only if the knob captures new per-job data)* **`schema.py` + migration** | A new CSV column. | Follow **Additive change: new captured field** below. A pure filter/search knob does **not** need a column; a "record X about each job" knob does. |

### The drift traps (read these every time)

- **The live config is gitignored and per-user.** `search_config.json` already exists on the user's machine and will **not** automatically gain your new key. So: (a) the skill must read the key with a safe default (`(s.get("the_key", <default>))`) so existing live configs keep working, **and** (b) when the user actually asks to use the knob, write the key into their live `search_config.json` too (create it from `search_config.example.json` if absent). Updating only the example file means the new knob never takes effect for that user.
- **Never inline a value in a skill.** Anything role- or run-specific stays a `{code-word}` resolved from config. A literal in `SKILL.md` is drift waiting to happen.
- **Never rebuild the Cowork plugin for a knob.** The launchers in `dist/` read the live `.claude/skills/` files at runtime, so a knob added to the config + skills is picked up automatically - no rebuild, no reinstall. Rebuilding would re-introduce drift (see CLAUDE.md). The plugin only changes if the launcher *shape* changes, never for knob/skill content.
- **Forward-only + one data file still hold.** Adding a knob never edits existing `csm_jobs.csv` rows and never renames the file.

### Verify the wiring before reporting done

1. **Config loads:** run the Step 0a snippet (or `python3 -c "import json; print(json.load(open('search_config.example.json'))['scraper'])"`) and confirm the new key prints.
2. **Skill binds it:** grep the skill for the `{code-word}` - it must appear in both the Step 0a table and the step that uses it.
3. **Panel shows it:** load the dashboard (or call `search_config_summary()`) and confirm the new row renders with the expected value. A knob with a `"<key>_label"` appears automatically; if it does not show, check the `_label` is non-empty and sits in the same block (`scraper`/`enrichment`).
4. **(If a column was added)** confirm `python3 schema.py` reports the new count and a test append lands the value in the right column.

Then report back: which knob, its default, and that existing rows were untouched.

---

## Additive change: new captured field (the only CSV-touching case)

If the user wants to **start capturing a field that does not exist yet** (e.g. "also record whether the job mentions visa sponsorship", or add a 5th contact `contact5_*`):

1. **Add the column to `schema.py`** - insert the new field name into `CANONICAL_COLUMNS` (and into `SCRAPER_COLUMNS` or the enrichment list as appropriate). This is the only file where columns are defined.
2. **Migrate the existing `csm_jobs.csv` safely - never with `--force`.** `python3 schema.py --force` DELETES all rows. Instead, add the column in place so current data is preserved:
   ```bash
   python3 -c "
   import csv
   from schema import CANONICAL_COLUMNS
   path = 'csm_jobs.csv'
   with open(path, newline='', encoding='utf-8') as f:
       rows = list(csv.DictReader(f))
   with open(path, 'w', newline='', encoding='utf-8') as f:
       w = csv.DictWriter(f, fieldnames=CANONICAL_COLUMNS)
       w.writeheader()
       for r in rows:
           w.writerow({c: r.get(c, '') for c in CANONICAL_COLUMNS})
   print('Migrated. Existing rows preserved, new column added blank.')
   "
   ```
   Run from the project root so `schema.py` and `csm_jobs.csv` resolve. Existing rows get the new column blank; no row is lost.
3. **Teach the relevant skill to fill it** - add a field-extraction step to the scraper (Step 3c) or enrichment, and include it in the helper script's `--data` / job payload.
4. **Surface it in the dashboard** if the user wants to see it (the dashboard reads `csm_jobs.csv`).
5. **Record it in `search_config.json`** under `custom_fields_added`, so the dashboard panel shows it and future retargets know it exists.

> Renaming or removing a column is riskier (it can orphan dashboard logic). Only on explicit request, migrate the CSV the same in-place way - never `--force` a populated file.

---

## Adding a new contact type

- The CSV has fixed slots `contact1..4`. **A 5th contact is a new captured field** - follow the additive procedure above to add `contact5_name/title/linkedin/dm` columns, bump `num_contacts` to 5 and add the tier in `search_config.json`, then update the enrichment steps + the `--data` block.
- **Swapping who a tier is** (e.g. Contact 4 becomes "VP Product") is **config-only** - edit `contact_tiers` in `search_config.json`. No CSV change.
