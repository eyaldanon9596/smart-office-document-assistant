# SPEC.md

Specification for the Smart Office Document Assistant application layer (Part 2).
Claude Code reads this file before generating anything. `CONTRACT.md` defines the wire format;
this file defines the application.

---

## 1. What this application is

A thin interface in front of an existing n8n automation. An office employee sends a document,
watches it being processed, reads the extracted business fields, searches past results, and marks
a document as reviewed.

The automation already works. This application does not improve it, extend it, or duplicate it.

---

## 2. Rules that must never be broken

1. **No business logic in the application.** No AI calls, no prompts, no urgency rules, no Google
   API calls, no email sending. The application collects input, calls n8n, and displays what came
   back.
2. **No invented values.** Everything on screen came from an n8n response. `Not found` and
   `No action found` are displayed as written.
3. **No secret in the browser.** The shared secret and the webhook URLs live in `.env` on the
   server. Browser code calls same-origin `/api/*` routes only.
4. **No database.** The Google Sheet is the source of truth, reached through `GET /documents`.
5. **No translation of field values.** Interface text may be Hebrew or English; the values from
   `CONTRACT.md` section 2 stay exactly as returned.

Any generated code that violates one of these is rejected, not patched.

### 2.1 Where the line sits

Two things look like business logic and are not — they are display concerns and belong here:

- **Sorting newest first.** `GET /documents` returns spreadsheet rows in sheet order, oldest
  first. The dashboard sorts them for display.
- **Filtering and searching.** Done client-side over the array already received. Never by asking
  n8n for a filtered set.

Two things look like display and are not — they belong to n8n:

- **The `Needs Review` status.** Computed in the sub-workflow per `CONTRACT.md` section 2.1.
- **Whether a document is urgent.** The AI decides, the IF node acts on it. The application only
  paints the badge.

---

## 3. Stack

| Part | Choice |
|---|---|
| Server | Python 3.11+, FastAPI, Uvicorn |
| Templates | Jinja2 |
| HTTP client | `httpx` with an explicit 90 second timeout |
| Front end | Server-rendered HTML plus one vanilla JS file |
| Build tooling | None |

No React, no bundler, no npm. The only JavaScript is `static/app.js`, roughly 40 lines: upload via
`fetch`, the processing state, button locking, and client-side filtering of the dashboard table.

### Run

```
pip install -r requirements.txt
cp .env.example .env      # then fill in the secret
uvicorn main:app --reload
```

A fresh clone must run with exactly these three lines. Nothing else.

---

## 4. File layout

```
main.py              FastAPI app: page routes and /api/* proxy routes
n8n_client.py        Every outbound HTTP call to n8n. The only file that knows n8n exists.
mock.py              Returns the example responses from CONTRACT.md
config.py            Reads .env, fails loudly if a required variable is missing
templates/
  base.html
  upload.html
  dashboard.html
  detail.html
static/
  app.js
  style.css
.env                 git-ignored
.env.example         committed
requirements.txt
SPEC.md  CONTRACT.md  PROMPTS.md  README.md
```

`USE_MOCK=true` in `.env` makes `n8n_client.py` return data from `mock.py`. Switching to real
calls is a one-line change, per endpoint.

### Environment variables

```
N8N_BASE_URL=https://your-instance.app.n8n.cloud/webhook
N8N_PROCESS_PATH=/process-document
N8N_DOCUMENTS_PATH=/documents
N8N_REVIEW_PATH=/review
N8N_SECRET=replace-me
REQUEST_TIMEOUT_MS=90000
MAX_FILE_MB=10
USE_MOCK=true
```

---

## 5. Server routes

| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Upload screen |
| `/dashboard` | GET | Dashboard |
| `/documents/{document_id}` | GET | Detail view |
| `/api/process` | POST | Adds the secret header, forwards to n8n `/process-document` |
| `/api/documents` | GET | Adds the secret header, forwards to n8n `/documents` |
| `/api/review` | POST | Adds the secret header, forwards to n8n `/review` |

The `/api/*` routes are a pass-through. They add the header, forward the body unchanged, and
return the response unchanged. They do not reshape, filter, enrich, or cache.

Set the JSON body limit to 15 MB — a 10 MB file grows by roughly a third when base64 encoded, and
the default limit will reject it with an unhelpful 413.

---

## 6. Required features, in build order

**F4 — Dashboard.** Lists every document from `GET /documents`, newest first. Handles 20+ rows
without breaking. Manual Refresh control. A document processed through the Part 1 Drive folder
appears here too.

**F5 — Search and filters.** Free-text search over file name, sender, and summary. Filters for
urgency, document type, department, and status. Filters combine. A clear "no results" state.

**F1 — Upload screen.** Choose or drag one document. Shows file name and size. Only PDF, DOCX and
TXT accepted; oversized and unsupported files are rejected before any request is sent.

**F2 — Processing state.** An unmistakable in-progress state while n8n works. Send is disabled for
the whole request. A wait of up to a minute must not look frozen. Double-clicking Send produces
exactly one spreadsheet row.

**F3 — Result view.** All seven extracted fields plus the file link. Urgency shown as a coloured
badge **with a text label** — colour alone is not enough. `Not found` and `No action found` are
rendered as text.

**F6 — Detail view with human review.** Opens one document, shows every field, offers "Mark as
reviewed" with an optional note up to 200 characters. Sends `POST /review` and reflects the new
status in the list.

**F7 — Error and empty states.** Every failure becomes a sentence a non-technical employee can act
on. Covers timeouts, 4xx, 5xx, an unreachable n8n instance, and an empty log. Never a blank screen
or a raw status code.

**F8 — Configuration and secrets.** Webhook URLs and the secret come from environment variables.
`.env.example` is committed with placeholders; `.env` is git-ignored. Searching the repository for
the secret returns nothing.

---

## 7. Quality requirements

| Area | Requirement |
|---|---|
| Usability | An employee who has never seen the app can send a document and understand the result without instructions |
| Readability | Urgency is distinguishable without relying on colour alone |
| Layout | Usable on a normal laptop screen; no horizontal scrolling on the dashboard |
| Honesty | The interface never displays information the workflow did not return |
| Runnability | A fresh clone runs after copying `.env.example` to `.env` and one documented command |

---

## 8. Working method

Build against `mock.py` first. The entire interface must be testable with `USE_MOCK=true` and no
n8n instance running. Only then connect endpoints one at a time, in this order:

1. `GET /documents` — read-only, cannot damage anything
2. `POST /process-document`
3. `POST /review`

Confirm the result in Google Sheets after each switch before moving on.

Commit after each working feature. Record every prompt that mattered in `PROMPTS.md` as you go,
with what came back and what had to be corrected.

Every file in the repository must be explainable out loud. Code that cannot be explained is
deleted, not kept.
