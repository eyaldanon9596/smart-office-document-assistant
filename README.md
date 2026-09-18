# Smart Office Document Assistant — Part 2

A thin web interface in front of the Part 1 n8n automation. An employee sends a
document, watches it being processed, reads the extracted business fields,
searches past results, and marks a document as reviewed. All the intelligence
lives in n8n; this app only collects input, calls n8n, and shows what came back.

See `SPEC.md` for the rules and `CONTRACT.md` for the wire format. A fuller,
diagrammed walkthrough of the whole system (architecture, all flows, what's
verified, open points) is at:
https://claude.ai/code/artifact/f3a64f72-8398-4e8f-9f70-c6eb1d60b2c7

## Architecture

```
                    ┌──────────────────────────┐
  Browser  ───────▶ │   FastAPI app (Part 2)   │
  (upload,          │  adds x-api-key header   │
   dashboard,       │  /api/* pass-through     │
   review)          └────────────┬─────────────┘
                                  │ HTTPS + shared secret
                                  ▼
                    ┌──────────────────────────┐
                    │     n8n (Part 1 + 2)      │
                    │  webhooks:                │
                    │   POST /process-document  │
                    │   GET  /documents          │
                    │   POST /review             │
                    │  add-ons:                  │
                    │   POST /analyze (AI Agent) │
                    │   POST /scan-inbox (email) │
                    └───┬──────────┬─────────┬──┘
                        │          │         │
       Google Drive Trigger        │         │
       (Incoming Documents) ───────┘         │
                        │                    │
                        ▼                    ▼
              Google Sheet            Gmail (notify) +
           (Document Processing       Gemini (extract,
                 Log)                   OCR, briefings)
```

Two independent entry points reach the **same** extraction → Sheet → Gmail
logic: the webhook (app-driven) and the Google Drive Trigger watching
`Incoming Documents` (the original Part 1 no-code path). Both write to the
same Sheet, so a document dropped in Drive shows up in the dashboard exactly
like one sent from the app. See "Known limitations" below for how these two
paths are implemented (duplicated, not a shared sub-workflow).

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

## Known limitations

- **DOCX is not extracted.** n8n's *Extract from File* has no DOCX operation,
  and a DOCX has no page images for the OCR fallback either. A DOCX upload
  returns `EMPTY_DOCUMENT`. PDF and TXT both work, including scanned/
  image-only PDFs via a Gemini OCR fallback.
- **The Drive-trigger and webhook workflows duplicate their shared steps**
  (text extraction, AI extraction, the Needs-Review rule, the Sheet append,
  the Gmail notify) instead of calling one sub-workflow, which is what Part 2
  §4 recommends. This was a deliberate, documented trade-off — see
  `REFLECTION.md` for why and what it costs.
- **The extraction model is Gemini, not OpenAI.** Both `openAiApi`
  credentials on the n8n instance had dead API keys; the Information
  Extractor runs on `models/gemini-3.6-flash` instead. Its free tier allows
  5 requests/minute, which is the practical ceiling on how many documents can
  land at once — see `n8n/README.md`.
- **No content-level dedup on the Drive-folder path.** The email-intake
  add-on tags a processed message so it's never re-imported; a file dropped
  twice into `Incoming Documents` has no equivalent guard.
- **Browser calls n8n directly? No** — this build uses the recommended
  small-server pattern (Part 2 §8), so the CORS caveat in that section does
  not apply here.

## Other project documents

| File | What it is |
|---|---|
| `SPEC.md`, `CONTRACT.md` | The Part 2 specification and the app↔n8n data contract |
| `N8N_SETUP.md` | Every n8n workflow, its credentials, and how to activate them |
| `PROMPTS.md` | The graded prompt log, plus the full build history |
| `REFLECTION.md` | What the app adds, what still needs a human, what breaks at scale |
| `n8n/` | JSON exports of all workflows; `n8n/submission/` has credentials stripped |
