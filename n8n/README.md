# n8n workflows (Part 1)

Snapshots of the three webhook workflows running on `https://psagot.app.n8n.cloud`.
They implement `CONTRACT.md`. These files are for version control and re-import;
the live workflows are the source of truth.

| File | Workflow | ID | Webhook |
|---|---|---|---|
| `get-documents.json` | Smart Office — GET /documents | `XgwL6Q0TUJvZuMSj` | `GET /webhook/documents` |
| `post-process-document.json` | Smart Office — POST /process-document | `xSdzr7O5RCANQwRg` | `POST /webhook/process-document` |
| `post-review.json` | Smart Office — POST /review | `W4uXz3R6dympePtC` | `POST /webhook/review` |

All three are **active** and tested end to end (see `../PROMPTS.md`).

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
