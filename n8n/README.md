# n8n workflows (Part 1)

Snapshots of the six workflows running on `https://psagot.app.n8n.cloud`.
The first three implement `CONTRACT.md`; the fourth is the actual Part 1
no-code deliverable. These files are for version control and re-import; the
live workflows are the source of truth.

| File | Workflow | ID | Trigger |
|---|---|---|---|
| `get-documents.json` | Smart Office — GET /documents | `XgwL6Q0TUJvZuMSj` | `GET /webhook/documents` |
| `post-process-document.json` | Smart Office — POST /process-document | `xSdzr7O5RCANQwRg` | `POST /webhook/process-document` |
| `post-review.json` | Smart Office — POST /review | `W4uXz3R6dympePtC` | `POST /webhook/review` |
| `drive-trigger.json` | Smart Office — Drive Trigger (Part 1 automation) | `ybjMBekH8BWPNvid` | Google Drive Trigger on `Incoming Documents` |
| `post-analyze.json` | Smart Office — POST /analyze (AI Agent add-on) | `VFkK3dDke7eJuCA0` | `POST /webhook/analyze` |
| `post-scan-inbox.json` | Smart Office — POST /scan-inbox (email intake) | `UHeONQn07UscXMGk` | `POST /webhook/scan-inbox` |

All six are **active**. The last two are extras:

- **/analyze** — an AI Agent that re-reads the file from Drive and writes a
  briefing, shown on demand in the app; nothing written back to the Sheet.
- **/scan-inbox** — pulls PDF/DOCX/TXT attachments from the last 12 h of Gmail
  (that don't already carry the `SmartOffice/Processed` label) and feeds each
  through `/process-document`. On success the email is tagged
  `SmartOffice/Processed` so a re-run never processes it twice. Capped at 4
  attachments per run because Gemini's free tier allows 5 requests/minute —
  click again for the rest.

## Status

Working: header auth, `GET /documents` (incl. `[]` for an empty log), the full
`POST /process-document` pipeline (decode → route by file type → text extract
(PDF / DOCX / TXT) → **OCR fallback via Gemini for scanned PDFs** → Drive
upload → AI Agent extract → sheet append → Gmail → optional Calendar event →
response), `POST /review` (200 + 404), and the Drive Trigger pipeline
(same extraction, ending in a move to `Processed Documents`).

Both `post-process-document.json` and `drive-trigger.json` were rebuilt to run
extraction through an **AI Agent** node (`@n8n/n8n-nodes-langchain.agent`)
with a Structured Output Parser, instead of the Information Extractor node —
see the "Known limitations" entries in the top-level `README.md` for why, and
for the DOCX and Calendar additions that came with the rebuild. Because the
n8n API connection was down at the time, these two files were built and
tested locally (JS syntax-checked, and the new DOCX decoder verified against
6 real `.docx` files) rather than pushed live — see "Re-importing" below for
how to get them onto the live instance.

## Credentials the nodes reference (by id)

| Purpose | Credential | ID |
|---|---|---|
| Webhook auth | Smart Office Shared Secret (`httpHeaderAuth`) | `q7gpb9rI1PNWoNgh` |
| Sheets read/write | Google Sheets OAuth2 API | `pHFYlfi7ARohCIG1` |
| Drive upload/download/move | Google Drive account | `ca58XKLdnQURD47g` |
| Gmail notify | Gmail OAuth2 API | `AYgjFyDnQF1fGC7w` |
| AI extraction (Agent + Chat Model + OCR) | Google Gemini(PaLM) Api account | `3Bj78Dc8WJWZwwEF` |
| Calendar event (new — not yet created) | Google Calendar account | *(create this one — see below)* |

The two `openAiApi` credentials on the instance both have **dead API keys**
(`401 Incorrect API key`), so the AI Agent's Chat Model runs on **Gemini**
(`models/gemini-3.6-flash`). Swap back to an OpenAI Chat Model node if you add a
working OpenAI key.

## Re-importing `post-process-document.json` and `drive-trigger.json`

These two carry real credential ids from this instance, but they were
authored locally (not pushed via the n8n API), so importing them the normal
way would create **new** workflows with new ids and new webhook/trigger URLs
— breaking the app's existing `.env` config and the Drive Trigger's polling
target. Instead, replace each existing workflow's canvas in place:

1. Open the existing workflow in the n8n editor (e.g. **Smart Office — POST
   /process-document**, id `xSdzr7O5RCANQwRg`) — do **not** create a new one.
2. Click the **⋯** menu (top right) → **Import from File**, and pick the
   matching file from this folder. This replaces the canvas but keeps the
   workflow's id, so the webhook path / Drive Trigger folder watch is
   unaffected.
3. Every node's credential should already resolve (same instance, same ids)
   — except the new **Create Calendar event** node. Create a Google Calendar
   OAuth2 credential in n8n (Credentials → New → Google Calendar OAuth2 API,
   sign in as `eyal9596@gmail.com`), then open that node and select it.
4. Save, then **Execute workflow** once with a test document before trusting
   it — the rebuild changed several node names, which is enough to be worth
   one live check even though everything here was syntax- and logic-checked
   locally first.
5. Repeat for `drive-trigger.json` on the **Smart Office — Drive Trigger**
   workflow (id `ybjMBekH8BWPNvid`).

For every other file in this folder, plain **Import from File** as a new
workflow is fine — they're unchanged from what's already live.

## Google resources (account: eyal9596@gmail.com)

- Spreadsheet `Document Processing Log` — `1o-wteplPPTwDuC6dGl-bQXKukYNS1adUkfxVmNd8GbM`, tab gid `870850851`
- Folder `Smart Office Intake` — `19L3PCxpKXYVg9EKXHKys2PGy4Q0rpUwN`
