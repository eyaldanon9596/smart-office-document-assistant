# n8n workflows (Part 1)

Snapshots of the three webhook workflows running on `https://psagot.app.n8n.cloud`.
They implement `CONTRACT.md`. These files are for version control and re-import;
the live workflows are the source of truth.

| File | Workflow | ID | Webhook |
|---|---|---|---|
| `get-documents.json` | Smart Office — GET /documents | `XgwL6Q0TUJvZuMSj` | `GET /webhook/documents` |
| `post-process-document.json` | Smart Office — POST /process-document | `xSdzr7O5RCANQwRg` | `POST /webhook/process-document` |
| `post-review.json` | Smart Office — POST /review | `W4uXz3R6dympePtC` | `POST /webhook/review` |
| `post-analyze.json` | Smart Office — POST /analyze (AI Agent add-on) | `VFkK3dDke7eJuCA0` | `POST /webhook/analyze` |
| `post-scan-inbox.json` | Smart Office — POST /scan-inbox (email intake) | `UHeONQn07UscXMGk` | `POST /webhook/scan-inbox` |

All five are **active**. The first three implement `CONTRACT.md`; the last two
are extras:

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
`POST /process-document` pipeline (decode → Drive upload → text extract → AI
extract → sheet append → Gmail → response), `POST /review` (200 + 404).

## Credentials the nodes reference (by id)

| Purpose | Credential | ID |
|---|---|---|
| Webhook auth | Smart Office Shared Secret (`httpHeaderAuth`) | `q7gpb9rI1PNWoNgh` |
| Sheets read/write | Google Sheets OAuth2 API | `pHFYlfi7ARohCIG1` |
| Drive upload | Google Drive account | `ca58XKLdnQURD47g` |
| Gmail notify | Gmail OAuth2 API | `AYgjFyDnQF1fGC7w` |
| AI extraction | Google Gemini(PaLM) Api account | `3Bj78Dc8WJWZwwEF` |

The two `openAiApi` credentials on the instance both have **dead API keys**
(`401 Incorrect API key`), so the Information Extractor runs on **Gemini**
(`models/gemini-3.6-flash`). Swap back to an OpenAI Chat Model node if you add a
working OpenAI key.

## Re-importing

n8n → Workflows → Import from File. After import, open every node with a
credential and re-select it (credential ids are instance-specific), then re-check
the Google Sheets `documentId` / `sheetName` pickers.

## Google resources (account: eyal9596@gmail.com)

- Spreadsheet `Document Processing Log` — `1o-wteplPPTwDuC6dGl-bQXKukYNS1adUkfxVmNd8GbM`, tab gid `870850851`
- Folder `Smart Office Intake` — `19L3PCxpKXYVg9EKXHKys2PGy4Q0rpUwN`
