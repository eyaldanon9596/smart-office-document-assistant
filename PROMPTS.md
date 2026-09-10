# PROMPTS.md

A record of the prompts that shaped this build, what came back, and what had to
be corrected. Kept per `SPEC.md` section 8.

---

## 1. "Learn the files"

Read `SPEC.md` and `CONTRACT.md`. Established the scope: a thin FastAPI + Jinja
interface over an existing n8n automation, mock-first, no business logic in the
app, no secret in the browser, no database.

## 2. Setup decisions (given by the user)

- No Part 1 flows exist yet.
- Interface language: **English**.
- Identity: capture an **email** for `submitted_by` on upload and `reviewed_by`
  on review. No login.
- n8n reachable via the `n8n-mcp` server against `https://psagot.app.n8n.cloud`.

## 3. "Build everything, then debug"

Built Part 2 in full against `mock.py`, then Part 1 workflow definitions on the
n8n instance.

### What was generated

| Area | Result |
|---|---|
| `config.py` | Loads `.env`, fails loudly. Base URL and secret only required when `USE_MOCK=false`. |
| `mock.py` | 22 seeded rows (varied type / urgency / department / status, several with `Not found`). Nested `fields` shape for process, flat shape for the log. Keeps an in-memory list so uploads and reviews show on the dashboard. Seeded oldest-first so the dashboard sort is actually exercised. |
| `n8n_client.py` | The only file that imports `httpx`. Three functions, each with one `if settings.use_mock:` line. Raises `N8nError(kind, user_message)`; CONTRACT error codes mapped to sentences. |
| `main.py` | Three page routes, three `/api/*` pass-through routes. 15 MB body-size guard. Sorting newest-first and the filter option lists live here (display concerns). Filter options are the fixed CONTRACT enums, not values scraped from the data. |
| Templates | `base`, `upload`, `dashboard`, `detail`, `error`. |
| `static/app.js` | Upload with client-side type/size checks, base64, a `sending` lock against double-submit, processing spinner; dashboard filtering; review submit with a 200-char note counter. |
| `static/style.css` | Urgency shown as a word inside the badge, never colour alone. Dashboard table in an `overflow-x` wrapper; no horizontal scroll on a laptop. |

### Corrections made during the build

- **Sort direction conflict.** `CONTRACT.md` section 5 says `GET /documents`
  returns newest first; `SPEC.md` F4 says n8n returns sheet order (oldest first)
  and the dashboard sorts. Resolved by having the app always sort newest-first
  for display, so it is correct whichever order n8n actually sends. The mock
  returns oldest-first to prove the sort works.
- **Body-size limit.** Starlette has no default request-size cap, so the "413 on
  a big upload" `SPEC.md` warns about would not actually fire — replaced with an
  explicit `Content-Length` check that returns the friendly sentence instead.
- **`/api/*` on transport failure.** The pass-through cannot "return the n8n
  response unchanged" when there is no response (timeout, DNS). Those cases
  return a small `{status:"error", message, retryable}` object so F7 still holds.

## 4. Part 1 — n8n workflows

No Part 1 spec document exists. Three webhook workflows were built to satisfy
`CONTRACT.md` only (not the Workflow A / sub-workflow / Workflow C + Drive-trigger
decomposition it mentions). JSON snapshots are in `n8n/`; details and gaps in
`N8N_SETUP.md`.

### Built via the n8n MCP

- **GET /documents** — Webhook (Header Auth) → Google Sheets read → Code (map
  sheet headers to CONTRACT flat keys) → Respond.
- **POST /process-document** — Webhook → Code (base64 → binary, TXT → text) →
  Drive upload → IF pdf → Extract from File / carry-through → Code "Assemble
  text" → IF has-text → Information Extractor (Gemini) → Code "Finalize" (fills
  `Not found` / `No action found`, applies the §2.1 Needs Review rule, builds the
  row + response) → Sheets append → IF urgency High → Gmail (both branches) →
  Respond. Empty text → `EMPTY_DOCUMENT` 400.
- **POST /review** — Webhook → Sheets read → Code "Find matching row" (match on
  `document_id` only) → IF found → Sheets update / Respond `updated`, else
  Respond `404`.

### Resources created (account `eyal9596@gmail.com`)

- Header Auth credential `Smart Office Shared Secret` (`q7gpb9rI1PNWoNgh`).
- Spreadsheet `Document Processing Log` with the 15 CONTRACT columns
  (`1o-wteplPPTwDuC6dGl-bQXKukYNS1adUkfxVmNd8GbM`, tab gid `870850851`).
- Folder `Smart Office Intake` (`19L3PCxpKXYVg9EKXHKys2PGy4Q0rpUwN`).

### Bugs found and fixed while testing live

1. **`GET /documents` returned an empty body, not `[]`, on an empty sheet.**
   Google Sheets read emits 0 items for a header-only sheet and n8n skips every
   downstream node. Fix: `alwaysOutputData` on the read node + the Code node
   filters the sentinel `{}` item and always returns `{ documents: [...] }`,
   which the Respond node stringifies.
2. **`/process-document` always hit `EMPTY_DOCUMENT` for TXT.** The Drive-upload
   node replaces `$json`, so `$json.text` from "Decode file" was gone by the
   next node. Fix: a "Assemble text" Code node after the pdf/non-pdf split that
   pulls text from `$('Decode file')` (TXT) or the Extract output (PDF).
3. **Both OpenAI credentials return `401 Incorrect API key`.** Swapped the
   OpenAI Chat Model for a Google Gemini chat model on the same Information
   Extractor. Then `gemini-1.5-flash` and `gemini-2.5-flash` 404'd (retired);
   `models/gemini-3.6-flash` works.
4. **Sheet tab name.** Workflows first used `sheetName` by name "Document
   Processing Log"; the actual tab was "Untitled" (later renamed). Switched all
   Sheets nodes to the stable gid `870850851`.

### Verified live

`403` without the key. `GET /documents` → `[]` then a flat array. TXT invoice
through `POST /process-document` → `200` with the seven fields nested under
`fields`, a real Drive link, a sheet row, `notification_sent: true`. `POST
/review` → `200 {"status":"updated"}` and the row flips to `Reviewed`; unknown id
→ `404`. The FastAPI app was also exercised end to end with `USE_MOCK=false`.

### Later fix — the PDF path

A real PDF upload returned 500 (`This operation expects the node's input data to
contain a binary file 'data'`). The Drive-upload node drops the item's binary,
so the downstream "Extract text from PDF" had nothing to read — the TXT tests
never hit that node. Fixed by extracting the text **before** the Drive upload:
`Decode → Is it a PDF? → extract/carry text → Assemble text (re-attaches the
Decode binary) → Upload to Drive → …`, with "Has readable text?" and the
Information Extractor reading via `$('Assemble text')` instead of `$json`.
Re-verified with a real PDF, through the app.

## 5. Add-on — the AI Agent analysis (`POST /analyze`)

Requested as an extra: an on-demand, deeper write-up of one document. It is not
in `CONTRACT.md` and does not change the three core flows or the sheet.

- **Workflow** `Smart Office — POST /analyze (AI Agent add-on)`
  (`VFkK3dDke7eJuCA0`): Webhook (Header Auth) → Sheets read → Code "Find the
  document" (row by `document_id`, pulls the Drive file id out of `File Link`) →
  IF found → Google Drive download → IF pdf → Extract PDF / Extract TXT → Code
  "Build the prompt" (stored fields + full file text) → **AI Agent** (Gemini
  `gemini-3.6-flash`, `promptType: define`, a system message that fixes the five
  headings) → Respond `{ document_id, analysis }`. No row match → `404`.
- **App**: `POST /api/analyze` pass-through (`main.py`), `analyze_document()` in
  `n8n_client.py` + `mock.py`, `N8N_ANALYZE_PATH` in `config.py`. The detail
  page gets an "Analyze this document" button and an output area;
  `static/app.js` renders the returned markdown-ish text (headings, bullets,
  `**bold**`).
- **Verified**: `POST /webhook/analyze` and `POST /api/analyze` both return the
  structured briefing (~12–30 s); unknown id → `404` becomes the app's friendly
  sentence. Analysis richness tracks the quality of the file's extracted text.
