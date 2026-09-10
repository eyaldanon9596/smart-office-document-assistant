# N8N_SETUP.md — finishing and activating the Part 1 workflows

There was no Part 1 specification in the repo, so these workflows were built to
satisfy **`CONTRACT.md` only**. All three are now **active and tested end to
end** against `https://psagot.app.n8n.cloud`. JSON snapshots are in `n8n/`.

## What was created

| Workflow | ID | Webhook | Verified |
|---|---|---|---|
| Smart Office — GET /documents | `XgwL6Q0TUJvZuMSj` | `GET  /webhook/documents` | 200 + `[]` on empty log; 403 without key |
| Smart Office — POST /process-document | `xSdzr7O5RCANQwRg` | `POST /webhook/process-document` | 200, nested `fields`, Drive link, row appended, `notification_sent: true` |
| Smart Office — POST /review | `W4uXz3R6dympePtC` | `POST /webhook/review` | 200 `{status: updated}`; 404 on unknown id |
| Smart Office — POST /analyze (add-on) | `VFkK3dDke7eJuCA0` | `POST /webhook/analyze` | 200 with an AI-Agent briefing; 404 on unknown id. Not part of `CONTRACT.md`. |

The FastAPI app was also run against the live instance (`USE_MOCK=false`):
dashboard, detail page and upload all work through real n8n.

## Step 1 — Header Auth credential — DONE

Credential **`Smart Office Shared Secret`** (`httpHeaderAuth`, id
`q7gpb9rI1PNWoNgh`) was created and attached to all three Webhook nodes.

- Header Name: `x-api-key`
- Header Value: the `N8N_SECRET` value in the app's local `.env` (git-ignored).
  The secret is **not** in any committed file, so `git grep` finds nothing
  (SPEC F8).

Nothing to do here unless you want to rotate the secret — if you do, change it
in the credential and in `.env` together.

## Step 2 — Placeholders — DONE (all three project resources live in `eyal9596@gmail.com`)

| Placeholder | Where | Value now set |
|---|---|---|
| `REPLACE_WITH_NOTIFY_EMAIL` | "Notify (urgent)" / "Notify (normal)" | `eyal9596@gmail.com` |
| `REPLACE_WITH_SHEET_ID` | 4 Google Sheets nodes across the 3 workflows | `1o-wteplPPTwDuC6dGl-bQXKukYNS1adUkfxVmNd8GbM` |
| `REPLACE_WITH_DRIVE_FOLDER_ID` | "Upload original to Drive" | `19L3PCxpKXYVg9EKXHKys2PGy4Q0rpUwN` |

Created in `eyal9596@gmail.com` Drive:

- **Spreadsheet `Document Processing Log`** —
  `https://docs.google.com/spreadsheets/d/1o-wteplPPTwDuC6dGl-bQXKukYNS1adUkfxVmNd8GbM/edit`
  Header row already holds the 15 columns from `CONTRACT.md` section 7.
- **Folder `Smart Office Intake`** —
  `https://drive.google.com/drive/folders/19L3PCxpKXYVg9EKXHKys2PGy4Q0rpUwN`

Two things still need you in the n8n UI:

1. **Confirm the n8n Google credentials are the `eyal9596@gmail.com` account.**
   The nodes reference the existing credentials by id (Sheets `pHFYlfi7ARohCIG1`,
   Drive `ca58XKLdnQURD47g`, Gmail `AYgjFyDnQF1fGC7w`). I can't see which Google
   login they were authorised with. Open each, and if it isn't
   `eyal9596@gmail.com`, reconnect it (or add new credentials for that account
   and select them on the nodes).
2. **Confirm the sheet tab name.** The nodes use `sheetName` = "Document
   Processing Log". If the tab inside the new spreadsheet is called "Sheet1"
   instead, open each Google Sheets node and pick the tab from the list (this
   also populates the column mapper).

## Step 3 — The sheet columns (already created, for reference)

`CONTRACT.md` section 7 — the header row of `Document Processing Log`:

```
Document ID | Received At | File Name | File Link | Document Type |
Sender / Company | Summary | Requested Action | Deadline | Urgency |
Department | Submitted By | Status | Reviewed By | Review Note
```

The Code nodes map to these strings verbatim. If you rename a header, change the
`COLS` map in the Code node to match — in both places, not one.

## Step 4 — Credentials wired

| Node | Credential | Id | Action needed |
|---|---|---|---|
| Google Sheets (all 4) | Google Sheets OAuth2 API | `pHFYlfi7ARohCIG1` | Confirm it is the `eyal9596@gmail.com` login; reconnect if not |
| Upload original to Drive | Google Drive account | `ca58XKLdnQURD47g` | Same |
| Notify (urgent) / (normal) | Gmail OAuth2 API | `AYgjFyDnQF1fGC7w` | Same |
| Information Extractor's model | Google Gemini(PaLM) Api account | `3Bj78Dc8WJWZwwEF` | Working. See gap below. |

## Step 5 — Already activated and tested

All three are active. Verified live (see `PROMPTS.md` section 5 for the run log):

- `GET /webhook/documents` → `403` without the key, `200` + `[]` with it on an
  empty log, `200` + a flat array once rows exist.
- `POST /webhook/process-document` with a TXT invoice → `200`, the CONTRACT
  §3.2 body (seven fields nested under `fields`), a real Drive link, a row in
  the sheet, `notification_sent: true`, and a notification email.
- `POST /webhook/review` → `200 {"status":"updated",...}` and the row's Status
  flips to `Reviewed`; an unknown id → `404` with the error body.

To point the app at it: `.env` already has `USE_MOCK=false` and the matching
`N8N_SECRET`.

### Test data left behind

- Sheet rows `exec-42` and `exec-50` are from test runs — delete them if you
  want a clean log.
- Two test files remain in `Smart Office Intake`
  (`1GNXeuBjBfBQS916YJ6Zz0lMo1m8i7vNz`, `1oZzVhdHA_vCN5IdZqTPzj36E75NxXjoB`) —
  the rest were cleaned up.

## Known gaps (need the Part 1 spec or a decision)

- **DOCX text extraction is not implemented.** n8n's *Extract from File* has no
  DOCX operation. `/process-document` handles **PDF** (Extract from File) and
  **TXT** (decoded in "Decode file"). A DOCX upload reaches the extractor with
  empty text and returns `EMPTY_DOCUMENT`. Options: a community DOCX node, or
  upload to Drive with conversion to a Google Doc and export as `text/plain`.
- **AI model = Gemini, not OpenAI.** Both `openAiApi` credentials on the
  instance return `401 Incorrect API key`. The Information Extractor was wired
  to a **Google Gemini** chat model (`models/gemini-3.6-flash`) instead, which
  works. Add a valid OpenAI key and swap the model node back if you prefer.
- **No Workflow A / sub-workflow / Workflow C split.** `CONTRACT.md` refers to
  that decomposition and a **Google Drive trigger** intake path. Everything is
  folded into the three webhook workflows. The "Needs Review" rule still lives
  in exactly one place — the "Finalize fields and status" Code node.
- **`Submitted By` from the Drive path.** With no Drive trigger, every row's
  `Submitted By` comes from the webhook body (or `Not found`).
- **`document_id`** is `exec-<n8n execution id>` (e.g. `exec-42`), matching
  CONTRACT's `exec-1043` style. Confirm that is the key you want.
- **Notifications.** Both IF branches send Gmail (per CONTRACT). Subjects differ
  by urgency; bodies are the summary + action + deadline + file link.
