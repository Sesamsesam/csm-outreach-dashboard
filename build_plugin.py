#!/usr/bin/env python3
"""
build_plugin.py - (re)build the Cowork plugin as THIN LAUNCHERS.

Design (read this before "fixing" the plugin):
------------------------------------------------
There is ONE source of truth for the skills: .claude/skills/<name>/SKILL.md in the
project. The Cowork plugin does NOT copy that content. Each plugin skill is a thin
launcher that (1) discovers the shared project folder on the user's machine and
(2) reads and follows the project's live SKILL.md.

Why thin and not full content:
- The live SKILL.md is always current, so the plugin never goes stale and NEVER needs
  rebuilding when skills or knobs change. Knob changes live in search_config.json,
  which the project's SKILL.md loads live at runtime.
- Bundling a full copy of the skill text would (a) re-introduce drift and (b) break
  path discovery (the project's scripts auto-locate the project root from their own
  location; a copy inside the plugin install dir would not find csm_jobs.csv).

You normally never need to run this. Only re-run it if you change the LAUNCHER
shape itself (Step 0/Step 1 wording, plugin.json, or the descriptions):

    python3 build_plugin.py
"""

import json
import os
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "dist", "csm-outreach-dashboard.plugin")

SKILLS = {
    "linkedin-csm-scraper": {
        "title": "LinkedIn CSM Job Scraper",
        "description": "Scrape LinkedIn for new job postings matching your search config (ships tuned for Customer Success Manager) and save them to the local tracker. Use when asked to run a job scrape, find new jobs (CSM or any configured role), check for new postings, update the job tracker, or when a scheduled scrape fires.",
        "script": "append_jobs.py",
        "script_step": "the CSV-save step",
    },
    "linkedin-csm-enrichment": {
        "title": "LinkedIn CSM Enrichment",
        "description": "Enrich scraped job rows with LinkedIn contacts (tiers set by your search config; ships tuned for Customer Success Manager), draft DMs, and write cover letters. Use when asked to enrich jobs, find contacts, draft outreach, or write cover letters.",
        "script": "update_contacts.py",
        "script_step": "the CSV-update step",
    },
}

PLUGIN_JSON = {
    "name": "csm-outreach-dashboard",
    "version": "0.2.0",
    "description": "Thin-launcher plugin: adds the LinkedIn scraper + enrichment skills to Cowork. Delegates to the project's live skills and search_config.json, so targeting changes need no reinstall or rebuild.",
    "author": {"name": "Sami Hermes"},
    "repository": "https://github.com/Sesamsesam/csm-outreach-dashboard",
    "keywords": ["linkedin", "jobs", "customer-success", "outreach", "crm"],
}

PLUGIN_README = """# CSM Outreach Dashboard - Cowork plugin (thin launchers)

This plugin adds the **scraper** and **enrichment** skills to the Cowork panel.

**It deliberately contains no copy of the skill logic.** Each skill here is a thin
launcher that finds your shared project folder (`Projects/csm-outreach-dashboard`)
and runs the project's live `SKILL.md`. That means:

- Targeting (role, location, filters, contacts, tone) is driven by
  `search_config.json` in the project, loaded live on every run. **Changing knobs
  never requires reinstalling or rebuilding this plugin.**
- Skill edits in the project are picked up automatically. **This plugin never goes
  stale and should not be rebuilt into a full-content copy** - doing so breaks the
  project-folder discovery these launchers rely on.
"""

DO_NOT_REBUILD = """> ⚠️ **THIS IS AN INTENTIONAL THIN LAUNCHER - DO NOT "UPDATE", "REBUILD", OR REPLACE IT WITH FULL SKILL CONTENT.**
> It is deliberately short. The real, full skill lives in the project at
> `.claude/skills/{name}/SKILL.md` and is read **live at runtime** in Step 1 below, so
> it is ALWAYS current - including every knob/config change and skill edit. It is **not**
> stale or incomplete. Copying the full skill text in here would BREAK project-folder
> discovery (the run would lose track of the shared `csm_jobs.csv` and
> `search_config.json`). Leave it thin."""


def launcher(name: str, meta: dict) -> str:
    return f"""---
name: {name}
description: {meta['description']}
---

# {meta['title']} (Cowork launcher)

{DO_NOT_REBUILD.format(name=name)}

> **FORMATTING RULE - NO EM DASHES:** Never use em dashes (--) anywhere in any output. Use a regular hyphen (-) instead.

This skill is a thin launcher. It discovers the project root on this machine, then reads and follows the authoritative skill instructions from the project itself. All targeting (role, filters, contacts, tone) lives in the project's `search_config.json` and is loaded live - **changing knobs never requires touching or rebuilding this plugin.**

---

## Step 0 - Discover the project root

Read the Cowork desktop config to find the shared files folder:

**macOS:**
```bash
python3 -c "import json,os; p=os.path.expanduser('~/Library/Application Support/Claude/claude_desktop_config.json'); print(json.load(open(p)).get('coworkUserFilesPath',''))"
```
**Windows** (use `python`): same, but read `os.path.join(os.environ['APPDATA'],'Claude','claude_desktop_config.json')`.

Set `PROJECT_ROOT = {{coworkUserFilesPath}}/Projects/csm-outreach-dashboard`. Verify it exists:
```bash
python3 -c "import os; print('FOUND' if os.path.exists(os.path.join(r'{{PROJECT_ROOT}}','schema.py')) else 'MISSING')"
```
If the config is missing or the project is MISSING, stop and tell the user to open/clone
the project into their Cowork Projects folder.

---

## Step 1 - Load and follow the authoritative skill

Read the full instructions from:
```
{{PROJECT_ROOT}}/.claude/skills/{name}/SKILL.md
```

Follow every step in that file exactly. Use `{{PROJECT_ROOT}}` wherever the instructions
reference `{{project_root}}`. The helper-script path for {meta['script_step']} is:
```
{{PROJECT_ROOT}}/.claude/skills/{name}/scripts/{meta['script']}
```
That file loads `{{PROJECT_ROOT}}/search_config.json` (your current knobs) at the start
of the run, so whatever the user last set is what gets used - no rebuild needed.
"""


def build():
    if os.path.exists(OUT):
        os.remove(OUT)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(".claude-plugin/plugin.json", json.dumps(PLUGIN_JSON, indent=2) + "\n")
        z.writestr("README.md", PLUGIN_README)
        for name, meta in SKILLS.items():
            z.writestr(f"skills/{name}/SKILL.md", launcher(name, meta))
    print(f"Built {OUT} (thin launchers, no skill-content copy, no scripts bundled)")


if __name__ == "__main__":
    build()
