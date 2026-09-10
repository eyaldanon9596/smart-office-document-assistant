# Smart Office Document Assistant — Part 2

A thin web interface in front of the Part 1 n8n automation. An employee sends a
document, watches it being processed, reads the extracted business fields,
searches past results, and marks a document as reviewed. All the intelligence
lives in n8n; this app only collects input, calls n8n, and shows what came back.

See `SPEC.md` for the rules and `CONTRACT.md` for the wire format.

## Run

```
pip install -r requirements.txt
cp .env.example .env      # then fill in the secret
uvicorn main:app --reload
```

Then open http://127.0.0.1:8000.

With `USE_MOCK=true` (the default) the app serves everything from `mock.py` and
needs no n8n instance and no secret. This is the intended way to develop and
review the interface.

## Going live against n8n

1. In `.env` set `N8N_BASE_URL` to your instance's `…/webhook` URL and
   `N8N_SECRET` to the shared secret configured on the n8n webhooks.
2. Flip `USE_MOCK=false`.
3. `n8n_client.py` is the only file that calls n8n. Each of the three functions
   at the bottom has a single `if settings.use_mock:` line — that is the switch.

Bring the endpoints up one at a time in this order, checking the Google Sheet
after each: `GET /documents`, then `POST /process-document`, then `POST /review`.

## Files

| File | Purpose |
|---|---|
| `main.py` | FastAPI app: three page routes, three `/api/*` pass-through routes |
| `n8n_client.py` | Every outbound call to n8n. The only file that knows n8n exists. |
| `mock.py` | In-memory stand-in for the workflows, used when `USE_MOCK=true` |
| `config.py` | Reads `.env`, fails loudly if a required value is missing |
| `templates/` | `base`, `upload`, `dashboard`, `detail`, `error` (Jinja2) |
| `static/app.js` | Upload, processing state, double-submit lock, dashboard filtering, review, AI-analysis button |
| `n8n/` | JSON snapshots of the four n8n workflows (the automation is the source of truth) |
| `static/style.css` | All styling; urgency is shown as a word, never colour alone |

## Features

- **F1 Upload** — one PDF / DOCX / TXT, drag or browse, name and size shown,
  oversized and unsupported files rejected before any request is sent.
- **F2 Processing state** — spinner, Send disabled for the whole request, a
  double-click produces exactly one row.
- **F3 Result view** — the detail page: all seven fields, the file link, an
  urgency badge with a text label. `Not found` / `No action found` shown as text.
- **F4 Dashboard** — every document from `GET /documents`, newest first, Refresh
  control, handles 20+ rows.
- **F5 Search & filters** — free text over file name, sender and summary; filters
  for urgency, type, department and status; they combine; a clear "no results"
  state.
- **F6 Detail with review** — every field, "Mark as reviewed" with an optional
  note up to 200 characters, `POST /review`, the new status shows in the list.
- **F7 Error & empty states** — timeouts, 4xx, 5xx, unreachable n8n and an empty
  log each become a sentence, never a blank screen or a raw status code.
- **F8 Config & secrets** — all URLs and the secret come from `.env`;
  `.env.example` is committed with placeholders; `.env` is git-ignored.

### Add-on: AI analysis

Not part of the data contract.

- **"Analyze this document"** (document detail page) → `POST /api/analyze` →
  `Smart Office — POST /analyze`: re-reads the original file from Drive and runs
  an **AI Agent** (Gemini) for a plain-language briefing — what the document is,
  a short profile of the sender company, and what each line item means. On
  demand only; the Sheet is not touched.
- **"Check email for invoices"** (dashboard) → `POST /api/scan-inbox` →
  `Smart Office — POST /scan-inbox`: finds PDF/DOCX/TXT attachments in the last
  12 hours of Gmail that aren't already tagged `SmartOffice/Processed`, feeds
  each through `/process-document`, and tags the email on success so nothing is
  imported twice. Capped at 4 per run (Gemini free-tier rate limit); run it
  again for the rest.

Mock mode returns canned results for both so the buttons work offline.
