#!/usr/bin/env python3
"""
CSM Outreach Dashboard
Run:  python3 dashboard/app.py   (from the project root)
Then open: http://localhost:5001
"""

import csv
import json
import os
import urllib.request
import urllib.parse
from flask import Flask, render_template_string, request, jsonify, abort

app = Flask(__name__)

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CSV_PATH    = os.path.join(BASE_DIR, "..", "csm_jobs.csv")
CL_DIR      = os.path.join(BASE_DIR, "..", "cover_letters")
KEY_PATH    = os.path.join(BASE_DIR, ".hunter_key")
CONFIG_PATH = os.path.join(BASE_DIR, "..", "search_config.json")
CONFIG_EXAMPLE_PATH = os.path.join(BASE_DIR, "..", "search_config.example.json")


def read_search_config():
    """Load the single source of truth for what the skills scrape/enrich.

    Prefers the live, user-edited search_config.json. Falls back to the shipped
    search_config.example.json (CSM defaults) so a fresh clone still shows settings.
    Returns (config_dict_or_None, source_label).
    """
    for path, label in ((CONFIG_PATH, "live"), (CONFIG_EXAMPLE_PATH, "default")):
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f), label
            except (ValueError, OSError):
                continue
    return None, "none"


# Display spec for the "Current search settings" panel.
# (config_key, display label, Bootstrap icon) — order is left-to-right, wrapping.
# Any OTHER knob that carries a "<key>_label" companion in the config is appended
# automatically in the same style (see _auto_label_rows), so a brand-new knob shows
# up in the panel without editing this file — just give it a "<key>_label".
_SCRAPER_KNOBS = [
    ("search_keywords",              "Role / keywords", "bi-briefcase"),
    ("title_match_phrase",           "Title filter",    "bi-funnel"),
    ("location",                     "Location",        "bi-geo-alt"),
    ("work_type",                    "Work type",       "bi-laptop"),
    ("seniority",                    "Seniority",       "bi-bar-chart-steps"),
    ("recency",                      "Posted within",   "bi-clock-history"),
    ("pages_to_scrape",              "Pages scraped",   "bi-layers"),
    ("exclude_work_permit_required", "Work permit",     "bi-passport"),
]
_ENRICHMENT_KNOBS = [
    ("num_contacts",  "Contacts per job", "bi-people"),
    ("contact_tiers", "Contact tiers",    "bi-person-lines-fill"),
    ("dm_tone",       "Outreach tone",    "bi-chat-quote"),
]
# Label-companion keys the curated knobs above already consume, so the
# auto-discovery pass doesn't render them a second time.
_CONSUMED_LABELS = {"work_type_label", "seniority_label", "recency_label", "work_permit_label"}


def _knob_row(block, key, label, icon):
    """Resolve one knob into a display-row dict, or None if it has no value.

    A "<key>_label" companion (the config's display convention) wins over the raw
    value so the panel shows human-readable text. contact_tiers renders as chips;
    num_contacts as "N per job"; the work-permit toggle as plain text.
    """
    if key == "contact_tiers":
        chips = [t.get("type", "") for t in block.get(key, []) if t.get("type")]
        if not chips:
            return None
        return {"icon": icon, "label": label, "value": "", "chips": chips}
    if key == "num_contacts":
        n = block.get(key, "")
        if n == "" or n is None:
            return None
        return {"icon": icon, "label": label, "value": f"{n} per job", "chips": None}
    if key == "exclude_work_permit_required":
        value = (block.get("work_permit_label")
                 or ("Skip jobs that won't sponsor" if block.get(key) else "Off"))
        return {"icon": icon, "label": label, "value": value, "chips": None}

    value = block.get(f"{key}_label") or block.get(key, "")
    if key in ("search_keywords", "location"):
        value = str(value).replace("+", " ")
    value = str(value).strip()
    if not value:
        return None
    return {"icon": icon, "label": label, "value": value, "chips": None}


def _auto_label_rows(block, curated_keys):
    """Surface any NEW knob that carries a "<key>_label" companion.

    This is what makes the panel self-updating: when a retarget adds a brand-new
    knob with a human-readable "<key>_label", it appears here automatically, in the
    same style, with no edit to this file. Plumbing keys (function codes, phrase
    lists, blocklists) have no _label, so they correctly stay hidden.
    """
    rows = []
    for k, v in block.items():
        if not k.endswith("_label") or k in _CONSUMED_LABELS:
            continue
        base = k[: -len("_label")]
        if base in curated_keys:
            continue
        text = str(v).strip()
        if not text:
            continue
        label = base.replace("_", " ").strip().capitalize()
        rows.append({"icon": "bi-sliders", "label": label, "value": text, "chips": None})
    return rows


def search_config_summary():
    """Flatten the search config into display rows for the dashboard panel.

    Returns (rows, meta). Each row is a dict {icon, label, value, chips}: chips is a
    list (rendered as pills) or None (then `value` is shown). meta carries the source
    ("live"/"default"/"none"), the role label, and the last-updated date.

    Rows = curated scraper knobs, then any auto-discovered new scraper knob, then the
    curated enrichment knobs, their auto-discovered extras, and finally any custom
    captured fields. A new labeled knob appears here with no code change.
    """
    cfg, source = read_search_config()
    if not cfg:
        return [], {"source": "none", "role": "Customer Success Manager (built-in default)", "updated": ""}

    s = cfg.get("scraper", {})
    e = cfg.get("enrichment", {})

    rows = []
    for key, label, icon in _SCRAPER_KNOBS:
        row = _knob_row(s, key, label, icon)
        if row:
            rows.append(row)
    rows += _auto_label_rows(s, {k for k, _, _ in _SCRAPER_KNOBS})

    for key, label, icon in _ENRICHMENT_KNOBS:
        row = _knob_row(e, key, label, icon)
        if row:
            rows.append(row)
    rows += _auto_label_rows(e, {k for k, _, _ in _ENRICHMENT_KNOBS})

    meta = {
        "source":  source,
        "role":    cfg.get("role_label", ""),
        "updated": cfg.get("last_updated", ""),
        # Names of extra columns recorded per job. NOT search knobs — shown as a
        # caption below the grid, not as a tunable setting.
        "captured_fields": list(cfg.get("custom_fields_added") or []),
    }
    return rows, meta


def get_hunter_key():
    if os.path.exists(KEY_PATH):
        k = open(KEY_PATH).read().strip()
        if k:
            return k
    return os.environ.get("HUNTER_API_KEY", "test-api-key")


def hunter_key_is_set():
    return get_hunter_key() != "test-api-key"


STATUSES = ["Not started", "DMs sent", "Replied", "Applied", "Archived"]

CONTACT_LABELS = {
    "contact1": "Recruiter",
    "contact2": "Hiring Manager",
    "contact3": "Peer CSM",
    "contact4": "Senior Leader",
}

STATUS_COLORS = {
    "Not started": "#6c757d",
    "DMs sent":    "#0d6efd",
    "Replied":     "#198754",
    "Applied":     "#6610f2",
    "Archived":    "#adb5bd",
}


# ── helpers ────────────────────────────────────────────────────────────────

def read_jobs():
    if not os.path.exists(CSV_PATH):
        return []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_jobs(jobs):
    if not jobs:
        return
    # Union of all keys across rows so new columns (e.g. email fields) propagate correctly
    seen = {}
    for j in jobs:
        for k in j:
            seen[k] = True
    fieldnames = list(seen.keys())
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", restval="")
        writer.writeheader()
        writer.writerows(jobs)


def get_contacts(job):
    contacts = []
    for key, label in CONTACT_LABELS.items():
        name = job.get(f"{key}_name", "").strip()
        if not name:
            continue
        contacts.append({
            "key":        key,
            "label":      label,
            "name":       name,
            "title":      job.get(f"{key}_title", ""),
            "linkedin":   job.get(f"{key}_linkedin", ""),
            "dm":         job.get(f"{key}_dm", ""),
            "email":      job.get(f"{key}_email", ""),
        })
    return contacts


def extract_domain(job):
    website = (job.get("company_website") or "").strip()
    if not website:
        return ""
    if not website.startswith("http"):
        website = "https://" + website
    host = urllib.parse.urlparse(website).netloc or ""
    if host.startswith("www."):
        host = host[4:]
    return host.split("/")[0]


def hunter_call(endpoint, params):
    params["api_key"] = get_hunter_key()
    url = f"https://api.hunter.io/v2/{endpoint}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read()), None
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read())
            msg  = (body.get("errors") or [{}])[0].get("details", str(e))
        except Exception:
            msg = f"HTTP {e.code}: {e.reason}"
        return None, msg
    except Exception as e:
        return None, str(e)


def read_cover_letter(job):
    path = job.get("cover_letter_path", "").strip()
    if not path:
        return None
    # Stored paths are absolute. If the project folder has moved (e.g. the user
    # changed their Cowork files location), the absolute path won't resolve —
    # fall back to locating the same filename in this project's cover_letters/.
    if not os.path.exists(path):
        local = os.path.join(CL_DIR, os.path.basename(path))
        if os.path.exists(local):
            path = local
        else:
            return None
    with open(path, encoding="utf-8") as f:
        return f.read()


def job_matches(job, query):
    q = query.lower()
    fields = [
        job.get("company", ""),
        job.get("job_title", ""),
        job.get("contact1_name", ""),
        job.get("contact2_name", ""),
        job.get("contact3_name", ""),
        job.get("contact4_name", ""),
        job.get("hq_location", ""),
        job.get("industry", ""),
    ]
    return any(q in f.lower() for f in fields)


# ── templates ──────────────────────────────────────────────────────────────

BASE_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CSM Outreach Dashboard</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
  <style>
    :root {
      --bg:        #f6f7f9;
      --surface:   #ffffff;
      --line:      #ebedf0;
      --ink:       #131720;
      --ink-soft:  #5b6472;
      --ink-faint: #9aa1ad;
      --brand:     #3b5bdb;
      --brand-bg:  #eef2ff;
    }
    body { background: var(--bg); font-size: .92rem; color: var(--ink);
           -webkit-font-smoothing: antialiased; }
    .navbar { background: var(--ink) !important; padding: .7rem 1.5rem; }
    .navbar-brand { color: #fff !important; font-weight: 700; font-size: 1rem; letter-spacing: -.01em; }

    /* Status dot + label (replaces the pill badge) */
    .status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%;
                  margin-right: 6px; vertical-align: middle; }
    .status-text { font-size: .76rem; font-weight: 500; color: var(--ink-soft); vertical-align: middle; }

    /* Contact rows — flat, only a colored accent bar, no box */
    .contact-row { padding: 14px 0 16px; border-top: 1px solid var(--line); }
    .contact-row:first-of-type { border-top: none; }
    .contact-label { font-size: .66rem; font-weight: 700; text-transform: uppercase;
                     letter-spacing: .5px; padding: .22em .55em; border-radius: 5px; }
    .contact-name  { font-weight: 600; font-size: .92rem; color: var(--ink); }
    .contact-title { color: var(--ink-soft); font-size: .82rem; }
    /* DM text — flat, no box/background, just an indented accent */
    .dm-text { font-size: .86rem; color: var(--ink); line-height: 1.55;
               padding-left: 12px; border-left: 2px solid var(--line); }
    .char-count { font-size: .72rem; color: var(--ink-faint); }

    /* Copy button — minimal text button */
    .copy-btn { font-size: .76rem; padding: .25em .6em; border-radius: 6px;
                color: var(--ink-soft); border: 1px solid transparent; background: transparent;
                cursor: pointer; transition: background .12s, color .12s; line-height: 1.4; }
    .copy-btn:hover { background: var(--bg); color: var(--ink); }
    .copy-btn.copied { color: #1f9d55; }

    /* Job cards — flat, one subtle border, soft hover lift, fully clickable */
    .job-card { display: flex; flex-direction: column; height: 100%;
                border: 1px solid var(--line); border-radius: 12px; background: var(--surface);
                padding: 18px 20px; text-decoration: none; color: inherit;
                transition: border-color .15s, box-shadow .15s, transform .15s; }
    .job-card:hover { border-color: #d7dbe0; box-shadow: 0 6px 20px rgba(19,23,32,.07);
                      transform: translateY(-2px); color: inherit; }
    .job-company { font-size: .95rem; font-weight: 700; color: var(--ink); letter-spacing: -.01em; }
    .job-role { font-size: .83rem; color: var(--ink-soft); }
    .job-meta { font-size: .78rem; color: var(--ink-faint); }
    .job-contacts { font-size: .78rem; color: var(--ink-soft); }
    .job-foot { font-size: .74rem; color: var(--ink-faint); }
    /* Hard-requirements line on a job card — always shown, so the absence of a
       gate (a degree/license you can't bend around) is itself a signal. */
    .job-hardreq { font-size: .76rem; line-height: 1.4; }
    .job-hardreq.has-req { color: #8a6400; display: -webkit-box; -webkit-line-clamp: 2;
                           -webkit-box-orient: vertical; overflow: hidden; }
    .job-hardreq.no-req { color: var(--ink-faint); }

    /* Cover letter — flat text, no surrounding box */
    .cover-letter { font-size: .88rem; white-space: pre-wrap; line-height: 1.7; color: var(--ink); }

    /* Hunter.io */
    .hunter-email { font-size: .82rem; color: var(--ink); font-family: ui-monospace, monospace; }
    .hunter-email-row { display: inline-flex; align-items: center; gap: 6px; }
    .confidence-badge { font-size: .67rem; font-weight: 700; padding: .2em .45em; border-radius: 4px; }
    .conf-high { background: #e6f9ee; color: #1a7a40; }
    .conf-mid  { background: #fff8e1; color: #8a6400; }
    .conf-low  { background: #fde8e8; color: #b91c1c; }
    .hunter-credits { font-size: .72rem; color: var(--ink-faint); }
    .exec-row { padding: 10px 0; border-top: 1px solid var(--line); }
    .exec-row:first-of-type { border-top: none; }

    /* Sidebar — single flat surface */
    .sidebar-card { border: 1px solid var(--line); border-radius: 12px; background: var(--surface); padding: 20px; }
    .sidebar-label { font-size: .72rem; text-transform: uppercase; letter-spacing: .5px;
                     color: var(--ink-faint); font-weight: 600; margin-bottom: 1px; }
    .sidebar-val { font-size: .9rem; color: var(--ink); }

    /* Unified nav — large clickable tab-cards (count + name) */
    .tabnav { display: flex; gap: 10px; }
    .tab-card { flex: 1; text-decoration: none; color: inherit; text-align: center;
                background: var(--surface); border: 1px solid var(--line); border-radius: 12px;
                padding: 16px 14px; transition: border-color .15s, box-shadow .15s, background .15s; }
    .tab-card:hover { border-color: #d7dbe0; box-shadow: 0 4px 14px rgba(19,23,32,.06); color: inherit; }
    .tab-card.active { border-color: var(--brand); background: var(--brand-bg); }
    .tab-num { font-size: 1.7rem; font-weight: 700; color: var(--ink); line-height: 1.05; letter-spacing: -.02em; }
    .tab-card.active .tab-num { color: var(--brand); }
    .tab-name { font-size: .72rem; text-transform: uppercase; letter-spacing: .5px;
                color: var(--ink-soft); font-weight: 600; margin-top: 5px; }
    .tab-card.active .tab-name { color: var(--brand); }

    /* Current search settings panel */
    .search-settings { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; }
    .search-settings > summary { list-style: none; cursor: pointer; padding: 13px 18px;
        font-size: .82rem; font-weight: 600; color: var(--ink); display: flex; align-items: center; gap: 8px; }
    .search-settings > summary::-webkit-details-marker { display: none; }
    .search-settings > summary::after { content: "\\F282"; font-family: "bootstrap-icons";
        margin-left: auto; color: var(--ink-faint); font-weight: 400; transition: transform .15s; }
    .search-settings[open] > summary::after { transform: rotate(180deg); }
    .ss-role { font-weight: 500; color: var(--ink-soft); }
    .ss-badge { font-size: .66rem; text-transform: uppercase; letter-spacing: .4px; font-weight: 700;
        padding: 2px 7px; border-radius: 20px; }
    .ss-default { background: #eef1f4; color: var(--ink-soft); }
    .ss-live { background: var(--brand-bg); color: var(--brand); }
    .ss-updated { font-size: .7rem; color: var(--ink-faint); font-weight: 500; }
    .ss-body { padding: 4px 18px 16px; }
    .ss-note { font-size: .76rem; color: var(--ink-soft); margin-bottom: 12px; }
    .ss-note code { background: #eef1f4; padding: 1px 5px; border-radius: 4px; font-size: .72rem; }
    /* Full-width auto-flowing grid: cells stretch to fill the row, then wrap to
       the next. Adding a knob to the config slots it in here in the same style. */
    .ss-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
        gap: 1px; background: var(--line); border: 1px solid var(--line);
        border-radius: 8px; overflow: hidden; }
    .ss-item { background: var(--surface); padding: 11px 14px;
        display: flex; gap: 10px; align-items: flex-start; }
    .ss-item > i { color: var(--ink-faint); font-size: .95rem; line-height: 1.3;
        margin-top: 1px; width: 16px; text-align: center; flex: none; }
    .ss-cell { min-width: 0; }
    .ss-key { display: block; font-size: .65rem; text-transform: uppercase; letter-spacing: .4px;
        color: var(--ink-faint); font-weight: 700; margin-bottom: 3px; }
    .ss-val { font-size: .84rem; color: var(--ink); line-height: 1.35; font-weight: 500;
        overflow-wrap: anywhere; }
    .ss-chips { display: flex; flex-wrap: wrap; gap: 5px; }
    .ss-chip { font-size: .72rem; font-weight: 600; background: var(--brand-bg); color: var(--brand);
        padding: 2px 9px; border-radius: 20px; }
    /* "Also captured per job" — informational, NOT a search knob, so it sits
       below the grid as a caption rather than inside it. */
    .ss-captured { display: flex; align-items: center; flex-wrap: wrap; gap: 6px;
        margin-top: 12px; font-size: .76rem; color: var(--ink-soft); }
    .ss-captured-label { color: var(--ink-faint); margin-right: 2px; }

    /* Search */
    .search-wrap input { font-size: .85rem; border-radius: 8px; padding: .4rem .9rem; border: none; }
    .search-wrap button { border-radius: 8px; font-size: .82rem; }
    .no-contacts { color: var(--ink-faint); font-style: italic; font-size: .87rem; }

    /* Section header */
    .section-title { font-size: .95rem; font-weight: 700; color: var(--ink);
                     margin-bottom: 14px; letter-spacing: -.01em; }

    /* Stat strip — flat, borderless, divider-separated */
    .stat-strip { background: var(--surface); border: 1px solid var(--line); border-radius: 12px;
                  display: flex; overflow: hidden; }
    .stat-cell { flex: 1; padding: 16px 18px; text-align: center; border-left: 1px solid var(--line); }
    .stat-cell:first-child { border-left: none; }
    .stat-cell.stat-highlight { background: var(--brand-bg); }
    .stat-value { font-size: 1.7rem; font-weight: 700; color: var(--ink); line-height: 1.05; letter-spacing: -.02em; }
    .stat-cell.stat-highlight .stat-value { color: var(--brand); }
    .stat-label { font-size: .7rem; text-transform: uppercase; letter-spacing: .6px;
                  color: var(--ink-soft); font-weight: 600; margin-top: 4px; }
    .stat-sub { font-size: .73rem; color: var(--ink-faint); margin-top: 2px; }
  </style>
</head>
<body>
<nav class="navbar navbar-dark mb-3">
  <div class="container-fluid">
    <a class="navbar-brand" href="/"><i class="bi bi-briefcase me-2"></i>CSM Outreach</a>
    <form class="d-flex search-wrap gap-2" method="get" action="/">
      <input class="form-control form-control-sm" type="search" name="q"
             placeholder="Search jobs, companies, contacts…"
             value="{{ request.args.get('q','') }}" style="width:260px">
      <button class="btn btn-outline-light btn-sm" type="submit">Search</button>
    </form>
  </div>
</nav>
<div class="container-fluid px-4">
  {% block content %}{% endblock %}
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script>
function flashCopied(btn) {
  btn.innerHTML = '<i class="bi bi-check2"></i> Copied';
  btn.classList.add('copied');
  setTimeout(() => {
    btn.innerHTML = '<i class="bi bi-clipboard"></i> Copy';
    btn.classList.remove('copied');
  }, 1800);
}
function legacyCopy(text, btn) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.focus(); ta.select();
  try { document.execCommand('copy'); } catch (e) {}
  document.body.removeChild(ta);
  flashCopied(btn);
}
function copyText(text, btn) {
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text)
      .then(() => flashCopied(btn))
      .catch(() => legacyCopy(text, btn));
  } else {
    legacyCopy(text, btn);
  }
}
</script>
</body>
</html>
"""

INDEX_HTML = BASE_HTML.replace("{% block content %}{% endblock %}", """
{% block content %}

<!-- Unified nav: count + name tab-cards -->
<div class="tabnav mb-4">
  {% for tab in tabs %}
  <a class="tab-card {% if active_status == tab.name %}active{% endif %}"
     href="/?status={{ tab.name|urlencode }}&q={{ q }}">
    <div class="tab-num">{{ tab.count }}</div>
    <div class="tab-name">{{ tab.name }}</div>
  </a>
  {% endfor %}
</div>

<!-- Current search settings: what the skills (incl. scheduled scrapes) will target -->
<details class="search-settings mb-4">
  <summary>
    <i class="bi bi-sliders me-1"></i>
    Current search settings
    <span class="ss-role">{{ cfg_meta.role }}</span>
    {% if cfg_meta.source == 'default' %}
      <span class="ss-badge ss-default">shipped default</span>
    {% elif cfg_meta.source == 'live' %}
      <span class="ss-badge ss-live">customized</span>
    {% endif %}
    {% if cfg_meta.updated %}<span class="ss-updated">updated {{ cfg_meta.updated }}</span>{% endif %}
  </summary>
  <div class="ss-body">
    <p class="ss-note">
      These are the knobs the scraper and enrichment skills load at the start of every run -
      including scheduled scrapes. To change them, ask Claude to retarget your search (it edits
      <code>search_config.json</code>). Existing jobs below are never removed when you change these.
    </p>
    <div class="ss-grid">
      {% for row in cfg_rows %}
      <div class="ss-item">
        <i class="bi {{ row.icon }}" aria-hidden="true"></i>
        <div class="ss-cell">
          <span class="ss-key">{{ row.label }}</span>
          {% if row.chips %}
          <span class="ss-chips">
            {% for chip in row.chips %}<span class="ss-chip">{{ chip }}</span>{% endfor %}
          </span>
          {% else %}
          <span class="ss-val">{{ row.value or '-' }}</span>
          {% endif %}
        </div>
      </div>
      {% endfor %}
    </div>
    {% if cfg_meta.captured_fields %}
    <div class="ss-captured">
      <span class="ss-captured-label">Also captured per job:</span>
      {% for f in cfg_meta.captured_fields %}<span class="ss-chip">{{ f.replace('_', ' ') }}</span>{% endfor %}
    </div>
    {% endif %}
  </div>
</details>

{% if not jobs %}
  <p class="text-muted mt-4 fst-italic">No jobs match your filters.</p>
{% endif %}

<div class="row g-3">
{% for job in jobs %}
<div class="col-md-6 col-xl-4">
  <a href="/job/{{ job.job_id }}" class="job-card">
    <div class="job-company mb-1">{{ job.company }}</div>
    <div class="job-role mb-1">{{ job.job_title }}</div>
    <div class="job-meta mb-3">
      {% if job.salary %}<span class="me-2">{{ job.salary }}</span>{% endif %}
      {{ job.job_location }}
    </div>
    {% set contacts = job._contacts %}
    <div class="mb-2">
    {% if contacts %}
      <div class="job-contacts">
        <i class="bi bi-people me-1"></i>{{ contacts|map(attribute='name')|join(', ') }}
      </div>
    {% else %}
      <div class="no-contacts" style="font-size:.78rem">No contacts yet</div>
    {% endif %}
    </div>
    <div class="mb-3">
    {% if job.hard_requirements %}
      <div class="job-hardreq has-req">
        <i class="bi bi-mortarboard-fill me-1"></i>{% for r in job.hard_requirements.split(';') if r.strip() %}{{ r.strip() }}{% if not loop.last %} · {% endif %}{% endfor %}
      </div>
    {% else %}
      <div class="job-hardreq no-req">
        <i class="bi bi-check2 me-1"></i>No hard requirements
      </div>
    {% endif %}
    </div>
    <div class="d-flex justify-content-between align-items-center mt-auto pt-2"
         style="border-top:1px solid var(--line)">
      <span class="job-foot">{{ job.date_scraped }}</span>
      <span>
        <span class="status-dot" style="background:{{ status_colors.get(job.outreach_status, '#9aa1ad') }}"></span>
        <span class="status-text">{{ job.outreach_status or 'Not started' }}</span>
      </span>
    </div>
  </a>
</div>
{% endfor %}
</div>
{% endblock %}
""")

CONTACT_CLASSES = {
    "Recruiter":       "recruiter",
    "Hiring Manager":  "hiring",
    "Peer CSM":        "peer",
    "Senior Leader":   "leader",
}

CONTACT_BADGE_COLORS = {
    "Recruiter":       "0d6efd",
    "Hiring Manager":  "6610f2",
    "Peer CSM":        "20c997",
    "Senior Leader":   "fd7e14",
}

JOB_HTML = BASE_HTML.replace("{% block content %}{% endblock %}", """
{% block content %}
<div class="mb-3">
  <a href="/" class="text-decoration-none text-muted" style="font-size:.85rem">
    <i class="bi bi-arrow-left me-1"></i>Back to all jobs
  </a>
</div>

<div class="row g-3">
  <!-- Left sidebar -->
  <div class="col-lg-3">
    <div class="sidebar-card mb-3">
      <h5 class="fw-bold mb-0" style="color:#1a1a2e">{{ job.company }}</h5>
      {% if job.company_tagline %}
      <p class="text-muted mb-3" style="font-size:.82rem">{{ job.company_tagline }}</p>
      {% endif %}

      <div class="mb-2">
        <div class="sidebar-label">Role</div>
        <div class="sidebar-val">{{ job.job_title }}</div>
      </div>
      <div class="mb-2">
        <div class="sidebar-label">Location</div>
        <div class="sidebar-val">{{ job.job_location }}</div>
      </div>
      {% if job.salary %}
      <div class="mb-2">
        <div class="sidebar-label">Salary</div>
        <div class="sidebar-val">{{ job.salary }}</div>
      </div>
      {% endif %}
      <div class="mb-2">
        <div class="sidebar-label">Company Size</div>
        <div class="sidebar-val">{{ job.company_size }}</div>
      </div>
      <div class="mb-2">
        <div class="sidebar-label">Industry</div>
        <div class="sidebar-val">{{ job.industry }}</div>
      </div>
      {% if job.applicant_count %}
      <div class="mb-2">
        <div class="sidebar-label">Applicants</div>
        <div class="sidebar-val">{{ job.applicant_count }}</div>
      </div>
      {% endif %}
      <div class="mb-3">
        <div class="sidebar-label">Easy Apply</div>
        <div class="sidebar-val">{{ job.easy_apply }}</div>
      </div>

      <div class="d-flex gap-2 flex-wrap">
        {% if job.linkedin_job_url %}
        <a href="{{ job.linkedin_job_url }}" target="_blank"
           class="btn btn-outline-primary btn-sm" style="font-size:.78rem">
          <i class="bi bi-linkedin me-1"></i>Job Post
        </a>
        {% endif %}
        {% if job.company_website %}
        <a href="{{ job.company_website }}" target="_blank"
           class="btn btn-outline-secondary btn-sm" style="font-size:.78rem">
          <i class="bi bi-globe me-1"></i>Website
        </a>
        {% endif %}
      </div>
    </div>

    <!-- Hard requirements (must-haves an applicant cannot bend, e.g. a specific degree, license, clearance).
         Always shown - the absence of a hard requirement is itself useful information. -->
    <div class="sidebar-card mb-3">
      <div class="sidebar-label mb-2">Hard Requirements</div>
      {% if job.years_experience %}
      <div class="mb-2" style="font-size:.82rem;color:#1a1a2e">
        <i class="bi bi-clock-history me-1" style="color:var(--ink-faint)"></i>{{ job.years_experience }} <span style="color:var(--ink-faint)">(experience, not a hard gate)</span>
      </div>
      {% endif %}
      {% if job.hard_requirements %}
      <ul style="margin:0;padding-left:1.05rem;font-size:.82rem;color:#1a1a2e;line-height:1.45">
        {% for r in job.hard_requirements.split(';') %}{% if r.strip() %}<li>{{ r.strip() }}</li>{% endif %}{% endfor %}
      </ul>
      {% else %}
      <div class="text-muted" style="font-size:.8rem;font-style:italic">No hard requirements (nothing documentation-gated like a specific degree, license, or clearance).</div>
      {% endif %}
    </div>

    <!-- Status -->
    <div class="sidebar-card">
      <div class="sidebar-label mb-2">Outreach Status</div>
      <select class="form-select form-select-sm" id="statusSelect" onchange="updateStatus(this.value)">
        {% for s in statuses %}
        <option value="{{ s }}" {% if s == job.outreach_status %}selected{% endif %}>{{ s }}</option>
        {% endfor %}
      </select>
      <div id="statusMsg" class="mt-2" style="display:none;font-size:.78rem;color:#198754">
        <i class="bi bi-check2-circle me-1"></i>Saved
      </div>
    </div>

    <!-- Hunter.io — exec emails -->
    <div class="sidebar-card mt-3">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <div class="sidebar-label">Hunter.io <span style="font-size:.68rem;color:var(--ink-faint);font-weight:400;text-transform:none;letter-spacing:0">exec emails</span></div>
        <span id="hunterCredits" class="hunter-credits"></span>
      </div>
      {% if not hunter_key_set %}
      <div id="hunterKeySetup">
        <input type="password" id="hunterKeyInput" class="form-control form-control-sm mb-2"
               placeholder="Paste Hunter API key…" autocomplete="off">
        <button class="btn btn-primary btn-sm w-100" onclick="saveHunterKey()">
          <i class="bi bi-key me-1"></i>Save key
        </button>
      </div>
      {% else %}
      <div id="hunterKeySetup" style="display:none"></div>
      {% endif %}
      <div id="hunterActions" {% if not hunter_key_set %}style="display:none"{% endif %}>
        <button class="btn btn-outline-primary btn-sm w-100" id="findExecsBtn"
                onclick="hunterFindExecs(this)"
                {% if discovered_execs is not none %}style="display:none"{% endif %}>
          <i class="bi bi-search me-1"></i>Find exec emails
        </button>
      </div>

      <div id="execResults" class="mt-2">
        {% if discovered_execs %}
          {% for e in discovered_execs %}
          <div class="exec-row">
            <div class="d-flex align-items-center gap-2 flex-wrap">
              <span class="contact-name" style="font-size:.85rem">{{ e.get('first_name','') }} {{ e.get('last_name','') }}</span>
              {% if e.get('position') %}<span class="contact-title">{{ e.position }}</span>{% endif %}
            </div>
            <div class="d-flex align-items-center gap-2 mt-1">
              <span class="hunter-email">{{ e.get('value','') }}</span>
              {% set conf = e.get('confidence', 0)|int %}
              <span class="confidence-badge conf-{{ 'high' if conf > 70 else ('mid' if conf > 40 else 'low') }}">{{ conf }}%</span>
              <button class="copy-btn" onclick='copyText({{ e.get("value","")|tojson }}, this)'><i class="bi bi-clipboard"></i></button>
            </div>
          </div>
          {% endfor %}
        {% elif discovered_execs is not none %}
          <p class="text-muted fst-italic mb-0" style="font-size:.82rem">No executive emails found.</p>
        {% endif %}
      </div>
    </div>
  </div>

  <!-- Main content -->
  <div class="col-lg-9">
    <div class="section-title">Contacts & DMs</div>

    {% if not contacts %}
      <p class="no-contacts">No contacts enriched yet — run the enrichment skill on this job first.</p>
    {% endif %}

    {% for c in contacts %}
    <div class="contact-row">
      <div class="d-flex align-items-center gap-2 flex-wrap">
        <span class="contact-label"
              style="background:#{{ badge_colors.get(c.label,'9aa1ad') }}1f;
                     color:#{{ badge_colors.get(c.label,'9aa1ad') }}">
          {{ c.label }}
        </span>
        <span class="contact-name">{{ c.name }}</span>
        {% if c.title %}
        <span class="contact-title">{{ c.title }}</span>
        {% endif %}
      </div>
      {% if c.dm %}
      <div class="dm-text mt-2">{{ c.dm }}</div>
      {% else %}
      <p class="text-muted mb-0 mt-1" style="font-size:.82rem">No DM drafted.</p>
      {% endif %}
      <div class="d-flex justify-content-between align-items-center mt-2">
        <div class="d-flex align-items-center gap-2 flex-wrap">
          {% if c.linkedin %}
          <a href="{{ c.linkedin }}" target="_blank"
             class="btn btn-outline-secondary btn-sm py-0 px-2" style="font-size:.76rem">
            <i class="bi bi-box-arrow-up-right me-1"></i>Profile
          </a>
          {% endif %}
        </div>
        {% if c.dm %}
        <div class="d-flex align-items-center gap-2">
          <span class="char-count">{{ c.dm|length }}ch</span>
          <button class="copy-btn" onclick='copyText({{ c.dm|tojson }}, this)'>
            <i class="bi bi-clipboard"></i> Copy
          </button>
        </div>
        {% endif %}
      </div>
    </div>
    {% endfor %}

    {% if cover_letter %}
    <div class="d-flex justify-content-between align-items-center mt-5 mb-3">
      <div class="section-title mb-0">Cover Letter</div>
      <button class="copy-btn" onclick='copyText({{ cover_letter|tojson }}, this)'>
        <i class="bi bi-clipboard"></i> Copy
      </button>
    </div>
    <div class="cover-letter">{{ cover_letter }}</div>
    {% endif %}
  </div>
</div>

<script>
function updateStatus(val) {
  fetch('/api/status', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({job_id: '{{ job.job_id }}', status: val})
  }).then(r => {
    if (r.ok) {
      const msg = document.getElementById('statusMsg');
      msg.style.display = 'block';
      setTimeout(() => msg.style.display = 'none', 2000);
    }
  });
}

function saveHunterKey() {
  const key = document.getElementById('hunterKeyInput').value.trim();
  if (!key) return;
  fetch('/api/save-hunter-key', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({key})
  }).then(r => r.json()).then(d => {
    if (d.ok) {
      document.getElementById('hunterKeySetup').style.display = 'none';
      document.getElementById('hunterActions').style.display = '';
      loadHunterCredits();
    }
  });
}

function loadHunterCredits() {
  fetch('/api/hunter-credits').then(r => r.json()).then(d => {
    const el = document.getElementById('hunterCredits');
    if (!el || d.error) return;
    el.textContent = d.remaining + ' left';
    el.style.color = d.remaining < 5 ? '#dc3545' : 'var(--ink-faint)';
  }).catch(() => {});
}

function hunterFindExecs(btn) {
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" style="width:.75rem;height:.75rem"></span>Searching…';
  fetch('/api/hunter-find-execs', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({job_id: '{{ job.job_id }}'})
  }).then(r => r.json()).then(d => {
    btn.style.display = 'none';
    const el = document.getElementById('execResults');
    if (d.error) {
      el.innerHTML = `<p class="text-danger mb-0" style="font-size:.82rem">${d.error}</p>`;
      btn.style.display = ''; btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-search me-1"></i>Find exec emails';
      return;
    }
    if (!d.execs || !d.execs.length) {
      el.innerHTML = '<p class="text-muted fst-italic mb-0" style="font-size:.82rem">No executive emails found.</p>';
      return;
    }
    el.innerHTML = d.execs.map(e => {
      const conf = parseInt(e.confidence) || 0;
      const cls  = conf > 70 ? 'high' : conf > 40 ? 'mid' : 'low';
      return `<div class="exec-row">
        <div class="d-flex align-items-center gap-2 flex-wrap">
          <span class="contact-name" style="font-size:.85rem">${e.first_name||''} ${e.last_name||''}</span>
          ${e.position ? `<span class="contact-title">${e.position}</span>` : ''}
        </div>
        <div class="d-flex align-items-center gap-2 mt-1">
          <span class="hunter-email">${e.value}</span>
          <span class="confidence-badge conf-${cls}">${e.confidence}%</span>
          <button class="copy-btn" onclick="copyText(${JSON.stringify(e.value)}, this)"><i class="bi bi-clipboard"></i></button>
        </div>
      </div>`;
    }).join('');
    if (!d.cached) loadHunterCredits();
  });
}

loadHunterCredits();
</script>
{% endblock %}
""")


# ── routes ─────────────────────────────────────────────────────────────────

# Unified nav tabs: display name → predicate over a job row. Order = left to right.
_TERMINAL_STATUSES = {"DMs sent", "Replied", "Applied", "Archived"}
TAB_FILTERS = {
    "Ready to Send": lambda j: any(j.get(f"contact{i}_name", "").strip() for i in range(1, 5))
                               and (j.get("outreach_status") or "") not in _TERMINAL_STATUSES,
    "Pending Agent": lambda j: not any(j.get(f"contact{i}_name", "").strip() for i in range(1, 5)),
    "DMs Sent":      lambda j: (j.get("outreach_status") or "") == "DMs sent",
    "Replies":       lambda j: (j.get("outreach_status") or "") == "Replied",
    "Applied":       lambda j: (j.get("outreach_status") or "") == "Applied",
    "Archived":      lambda j: (j.get("outreach_status") or "") == "Archived",
}


@app.route("/")
def index():
    all_jobs = read_jobs()
    q             = request.args.get("q", "").strip()
    # Default to "Ready to Send" if no status filter set
    active_status = request.args.get("status", "Ready to Send").strip()
    if active_status not in TAB_FILTERS:
        active_status = "Ready to Send"

    # Build tab cards with counts (computed over all jobs, before search filter)
    tabs = [{"name": name, "count": sum(1 for j in all_jobs if pred(j))}
            for name, pred in TAB_FILTERS.items()]

    # Apply active-tab filter, then search
    jobs = [j for j in all_jobs if TAB_FILTERS[active_status](j)]
    if q:
        jobs = [j for j in jobs if job_matches(j, q)]

    # Attach contacts list to each job for the template
    for j in jobs:
        j["_contacts"] = get_contacts(j)

    cfg_rows, cfg_meta = search_config_summary()

    return render_template_string(
        INDEX_HTML,
        jobs=jobs,
        total=len(jobs),
        q=q,
        active_status=active_status,
        tabs=tabs,
        status_colors=STATUS_COLORS,
        cfg_rows=cfg_rows,
        cfg_meta=cfg_meta,
        request=request,
    )


@app.route("/job/<job_id>")
def job_detail(job_id):
    jobs = read_jobs()
    job  = next((j for j in jobs if j.get("job_id") == job_id), None)
    if not job:
        abort(404)
    contacts     = get_contacts(job)
    cover_letter = read_cover_letter(job)
    raw_execs    = (job.get("discovered_execs") or "").strip()
    discovered_execs = json.loads(raw_execs) if raw_execs else None
    return render_template_string(
        JOB_HTML,
        job=job,
        contacts=contacts,
        cover_letter=cover_letter,
        statuses=STATUSES,
        contact_classes=CONTACT_CLASSES,
        badge_colors=CONTACT_BADGE_COLORS,
        discovered_execs=discovered_execs,
        hunter_key_set=hunter_key_is_set(),
        request=request,
    )


@app.route("/api/status", methods=["POST"])
def update_status():
    data   = request.get_json()
    job_id = data.get("job_id", "").strip()
    status = data.get("status", "").strip()
    if not job_id or status not in STATUSES:
        return jsonify({"error": "invalid"}), 400

    jobs = read_jobs()
    updated = False
    for j in jobs:
        if j.get("job_id") == job_id:
            j["outreach_status"] = status
            updated = True
            break

    if not updated:
        return jsonify({"error": "not found"}), 404

    write_jobs(jobs)
    return jsonify({"ok": True})


@app.route("/api/hunter-match-contacts", methods=["POST"])
def hunter_match_contacts():
    """Match contact names against already-fetched exec list — 0 credits."""
    data   = request.get_json()
    job_id = data.get("job_id", "").strip()
    if not job_id:
        return jsonify({"error": "missing job_id"}), 400

    jobs = read_jobs()
    job  = next((j for j in jobs if j.get("job_id") == job_id), None)
    if not job:
        return jsonify({"error": "not found"}), 404

    raw = (job.get("discovered_execs") or "").strip()
    if not raw:
        return jsonify({"matched": {}})

    execs = json.loads(raw)
    # Build lookup: last_name (lower) → exec record
    exec_by_last = {}
    for e in execs:
        ln = (e.get("last_name") or "").strip().lower()
        if ln:
            exec_by_last[ln] = e

    matched = {}
    changed = False
    for key in CONTACT_LABELS:
        name = (job.get(f"{key}_name") or "").strip()
        if not name or job.get(f"{key}_email", "").strip():
            continue  # skip if no name or already has email
        parts = name.split()
        last  = parts[-1].lower() if parts else ""
        if last in exec_by_last:
            e = exec_by_last[last]
            email = e.get("value", "")
            conf  = str(int(e.get("confidence", 0)))
            if email:
                job[f"{key}_email"]            = email
                job[f"{key}_email_confidence"] = conf
                matched[key] = {"email": email, "confidence": conf}
                changed = True

    if changed:
        write_jobs(jobs)
    return jsonify({"matched": matched})


@app.route("/api/save-hunter-key", methods=["POST"])
def save_hunter_key():
    key = (request.get_json().get("key") or "").strip()
    if not key:
        return jsonify({"error": "empty key"}), 400
    with open(KEY_PATH, "w") as f:
        f.write(key)
    return jsonify({"ok": True})


@app.route("/api/hunter-credits")
def hunter_credits_route():
    result, err = hunter_call("account", {})
    if err:
        return jsonify({"error": err}), 502
    credits = result.get("data", {}).get("requests", {}).get("credits", {})
    remaining = int(credits.get("remaining", 0))
    used      = int(credits.get("used", 0))
    available = int(credits.get("available", 0))
    return jsonify({"used": used, "available": available, "remaining": remaining})




@app.route("/api/hunter-find-execs", methods=["POST"])
def hunter_find_execs():
    data   = request.get_json()
    job_id = data.get("job_id", "").strip()
    if not job_id:
        return jsonify({"error": "missing job_id"}), 400

    jobs = read_jobs()
    job  = next((j for j in jobs if j.get("job_id") == job_id), None)
    if not job:
        return jsonify({"error": "not found"}), 404

    # Return cached — no credit spent
    cached = (job.get("discovered_execs") or "").strip()
    if cached:
        return jsonify({"execs": json.loads(cached), "cached": True})

    domain = extract_domain(job)
    if not domain:
        return jsonify({"error": "no company domain found"}), 400

    result, err = hunter_call("domain-search", {"domain": domain, "seniority": "executive"})
    if err:
        return jsonify({"error": err}), 502

    execs = result.get("data", {}).get("emails", [])
    job["discovered_execs"] = json.dumps(execs)
    write_jobs(jobs)
    return jsonify({"execs": execs, "cached": False})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"\n✅  Dashboard running at http://localhost:{port}")
    print(f"    CSV: {os.path.abspath(CSV_PATH)}\n")
    app.run(debug=False, port=port)
