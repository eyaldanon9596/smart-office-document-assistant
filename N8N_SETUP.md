# N8N_SETUP.md — finishing and activating the Part 1 workflows

There was no Part 1 specification in the repo, so these workflows were built to
satisfy **`CONTRACT.md` only**. They are created **inactive**. The Header Auth
credential, the `Document Processing Log` sheet, the Drive intake folder, the
notify address and all node ids are filled in. What remains is confirming the
n8n Google credentials use the `eyal9596@gmail.com` account, then activating.
**Review before activating.**

## What was created

| Workflow | ID | Webhook |
|---|---|---|
| Smart Office — GET /documents | `XgwL6Q0TUJvZuMSj` | `GET  /webhook/documents` |
| Smart Office — POST /process-document | `xSdzr7O5RCANQwRg` | `POST /webhook/process-document` |
| Smart Office — POST /review | `W4uXz3R6dympePtC` | `POST /webhook/review` |

All three validate clean (`n8n_validate_workflow`, 0 errors). "Valid" only means
the node graph is well-formed — it does **not** mean they run end to end yet.

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
| OpenAI Chat Model | OpenAI account | `UttpnJOpJjqyZKw6` | Re-authorise if expired |

## Step 5 — Activate in order and test (SPEC.md section 8)

1. **GET /documents** first — read-only, cannot damage anything. Activate,
   then in the app set `USE_MOCK=false` and confirm the dashboard loads real
   rows. (Per-endpoint switching: `n8n_client.py` has one `if settings.use_mock`
   line per function — for now the single flag flips all three, so bring the
   workflows up together or split the flag if you want them staged.)
2. **POST /process-document** — activate, upload a small PDF, confirm one new
   row in the sheet and the file in Drive.
3. **POST /review** — activate, mark that row reviewed, confirm the sheet
   updates and a wrong id returns 404.

## Known gaps (need the Part 1 spec or a decision)

- **DOCX text extraction is not implemented.** n8n's *Extract from File* has no
  DOCX operation. The `/process-document` workflow extracts **PDF** (Extract
  from File) and **TXT** (decoded directly in "Decode file"). A DOCX upload
  currently reaches the extractor with empty text and returns `EMPTY_DOCUMENT`.
  Options: a community DOCX node, or upload to Drive with conversion to a Google
  Doc and export as `text/plain`.
- **No Workflow A / sub-workflow / Workflow C split.** `CONTRACT.md` refers to
  that decomposition and to a **Google Drive trigger** intake path. Everything
  here is folded into the three webhook workflows instead. The "Needs Review"
  rule still lives in exactly one place — the "Finalize fields and status" Code
  node — which is what section 2.1 requires.
- **`Submitted By` from the Drive path.** With no Drive trigger, every row's
  `Submitted By` comes from the webhook body (or `Not found`).
- **`document_id`.** Built as `exec-<n8n execution id>` to match CONTRACT's
  `exec-1043` style. Confirm that is the identifier you want as the stable key.
- **AI model.** "OpenAI Chat Model" is set to `gpt-4o-mini`, temperature 0.
  Change if you prefer another model or the Azure/Gemini credentials.
- **Notifications.** Both IF branches send Gmail (per CONTRACT). Subjects differ
  by urgency; bodies are the summary + action + deadline + file link.
