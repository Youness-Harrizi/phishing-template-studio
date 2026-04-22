# Phishing Template Studio

A web-based application for building, previewing, and exporting phishing email templates for **authorised red team operations and social engineering assessments**.

> ⚠ **Responsible Use Notice**: This tool is for authorised security engagements only. Engagement context metadata (client name, authorisation, scope) is mandatory on all exports. Never use against systems or individuals without explicit written permission.

---

## Quickstart

### 1. Install dependencies

```bash
cd phishing_template_studio
pip install -r requirements.txt
```

### 2. Run the application

```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

### 3. Workflow

```
Create Persona → Generate Pretext → Compose → Score → Export
```

1. **Personas** — Go to *Persona Manager*, create a target profile (role, industry, seniority, known tools).
2. **New Template** — Click *New Template*, pick a category and assign the persona.
3. **Generate Pretext** — In the editor's left panel, click *Generate Pretext*. Pick a subject variant and click *Apply to Template*.
4. **Compose** — Write the HTML and plain-text body in the editor. Use `{{tokens}}` for variable substitution. The live preview updates in real time.
5. **Score** — The Persuasion Score and Red Flag panels update automatically. Fix flagged issues.
6. **Export** — Click *Export…*, choose a format, fill in engagement metadata, and download.

---

## Features

| Feature | Description |
|---|---|
| Persona Builder | Job title, industry, seniority, locale, known platforms |
| Pretext Generator | 8 lure categories, 3 subject variants, urgency level |
| Template Editor | HTML + plain text, real-time sync, formatting toolbar |
| Token System | `{{first_name}}`, `{{link}}`, etc. with autocomplete |
| Live Preview | Desktop, mobile, plain-text, dark mode render |
| Persuasion Scorer | 7 dimensions scored 1–10 with sentence attribution |
| Readability Score | Flesch-Kincaid Reading Ease with grade + feedback |
| Red Flag Detector | 10 checks with severity ratings and fix suggestions |
| Template Library | Search, filter, sort, tag, favourite, duplicate |
| A/B Variant Builder | 3 auto-generated variants per base template |
| Version History | Full-body snapshots, restore any version |
| Export Engine | 7 formats + ZIP archive |
| Engagement Context | Audit trail embedded in every export |

---

## Token Reference

| Token | Description | GoPhish | King Phisher |
|---|---|---|---|
| `{{first_name}}` | Recipient first name | `{{.FirstName}}` | `{first_name}` |
| `{{last_name}}` | Recipient last name | `{{.LastName}}` | `{last_name}` |
| `{{email}}` | Recipient email | `{{.Email}}` | `{email}` |
| `{{company}}` | Recipient company | `{{.From}}` | `{company_name}` |
| `{{department}}` | Recipient department | `{{.Position}}` | `{title}` |
| `{{link}}` | Phishing link | `{{.URL}}` | `{url}` |
| `{{tracker}}` | Tracking pixel | `{{.Tracker}}` | *(manual)* |
| `{{sender_name}}` | Sender display name | *(manual)* | *(manual)* |
| `{{sender_title}}` | Sender job title | *(manual)* | *(manual)* |
| `{{deadline}}` | Action deadline | *(manual)* | *(manual)* |
| `{{ticket_number}}` | IT ticket number | *(manual)* | *(manual)* |
| `{{attachment}}` | Attachment filename | *(manual)* | *(manual)* |

Custom tokens can be added by typing `{{my_token}}` anywhere in the editor.

---

## Export Format Compatibility

| Format | Platform | Notes |
|---|---|---|
| `gophish` | GoPhish ≥ 0.11 | Matches `/api/templates` import schema |
| `king_phisher` | King Phisher ≥ 1.14 | JSON companion for campaign configuration |
| `evilginx` | Evilginx2 ≥ 3.0 | Companion email template with phishlet notes |
| `eml` | Thunderbird, Outlook, Apple Mail | RFC 2822 compliant, testable before sending |
| `raw_html` | Any mail client / ESP | Self-contained with inline CSS |
| `plain_text` | Plaintext-only delivery | Subject header prepended |
| `pdf` | PDF viewer | Engagement documentation (requires `reportlab`) |
| `zip` | All platforms | Full archive with all formats for handoff |

---

## Scoring Logic

### Persuasion Dimensions

Each dimension is scored 1–10 via weighted keyword matching:

| Dimension | Weight | Examples |
|---|---|---|
| Urgency | 1.5× | "immediately", "within 24 hours", "deadline" |
| Fear | 1.4× | "suspended", "locked", "compliance violation" |
| Authority | 1.3× | "CEO", "mandatory", "on behalf of" |
| Scarcity | 1.2× | "unique link", "one-time", "expires" |
| Familiarity | 1.2× | "Office 365", "Okta", "ServiceNow" |
| Social Proof | 1.1× | "all employees", "company-wide", "your team" |
| Reciprocity | 1.0× | "we have prepared", "for your protection" |

**Overall** = weighted average of all dimensions.

### Readability (Flesch-Kincaid)

| Score | Grade | Guidance |
|---|---|---|
| 80–100 | Too Simple | May read as unsophisticated |
| 60–70 | **Optimal** | Conversational, clear — ideal for phishing |
| 40–60 | Moderate | Slightly complex |
| 0–40 | Too Complex | Simplify for better effectiveness |

---

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

Tests cover:
- Persuasion scorer determinism and keyword detection
- Readability scorer with known FK reference values
- Red flag detector: generic greeting, ALL CAPS subject, raw IP link
- Token substitution in HTML and plain text
- EML RFC 2822 compliance (parseable by `email` stdlib)
- GoPhish JSON schema structure and token mapping
- King Phisher token mapping
- ZIP archive file contents
- Version history restore round-trip
- Pretext generation for all 8 categories

---

## Architecture

```
phishing_template_studio/
├── app.py              # Flask API + SPA entry point
├── scorer.py           # PersuasionScorer, ReadabilityScorer, RedFlagDetector
├── exporter.py         # All export format generators
├── pretext.py          # Rule-based pretext generator
├── requirements.txt
├── data/
│   └── phishing_studio.db   # SQLite database (auto-created)
├── static/
│   ├── css/style.css
│   └── js/app.js       # Single-page application
├── templates/
│   └── index.html      # SPA shell
└── tests/
    └── test_core.py
```

All data is stored locally in SQLite. No cloud sync, no external API calls. All scoring and analysis runs locally.

---

## Engagement Context

Every export embeds an audit comment block:

```html
<!-- ENGAGEMENT AUDIT TRAIL
  Engagement : Q1 2026 Red Team (Ref: RT-2026-001)
  Client     : Acme Corp
  Assessment : Red Team
  Authorised : Jane Smith on 2026-01-15
  Scope      : Finance department, 50 users
  Exported   : 2026-04-22T09:00:00+00:00
-->
```

This is **mandatory** and cannot be disabled. It provides traceability for engagement review and client reporting.
