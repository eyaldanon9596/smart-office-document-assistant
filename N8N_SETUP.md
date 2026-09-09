# N8N_SETUP.md — finishing and activating the Part 1 workflows

There was no Part 1 specification in the repo, so these workflows were built to
satisfy **`CONTRACT.md` only**. They are created **inactive** and wired to the
Google / OpenAI credentials already on the `psagot` instance. Every value that
depends on your Google Workspace is a literal placeholder. **Review before
activating.**

## What was created

| Workflow | ID | Webhook |
|---|---|---|
| Smart Office — GET /documents | `XgwL6Q0TUJvZuMSj` | `GET  /webhook/documents` |
| Smart Office — POST /process-document | `xSdzr7O5RCANQwRg` | `POST /webhook/process-document` |
| Smart Office — POST /review | `W4uXz3R6dympePtC` | `POST /webhook/review` |

All three validate clean (`n8n_validate_workflow`, 0 errors). "Valid" only means
the node graph is well-formed — it does **not** mean they run end to end yet.

## Step 1 — Header Auth credential (required, could not be created for you)

Creating a credential that holds a secret is blocked for the assistant, so make
it by hand:

1. n8n → **Credentials → New → Header Auth**.
2. Name: **`Smart Office Shared Secret`**
3. Header Name: `x-api-key`
4. Header Value: a secret you choose. A generated starting value is already in
   the app's local `.env` (git-ignored) on the `N8N_SECRET` line — copy it from
   there, or pick your own and update `.env` to match.
5. Open each of the three **Webhook** nodes and select this credential under
   "Authentication → Header Auth". (The workflows already set
   `authentication: headerAuth`; they just need the credential picked.)

The secret is deliberately **not** written into any committed file, so
`git grep` for it finds nothing (SPEC F8).

## Step 2 — Replace the placeholders

| Placeholder | Where | Replace with |
|---|---|---|
| `REPLACE_WITH_SHEET_ID` | Google Sheets nodes in all three workflows | The `Document Processing Log` spreadsheet id |
| `REPLACE_WITH_DRIVE_FOLDER_ID` | "Upload original to Drive" (process-document) | The Drive intake folder id |
| `REPLACE_WITH_NOTIFY_EMAIL` | "Notify (urgent)" and "Notify (normal)" (process-document) | The address that should get processing notifications |

The Google Sheets nodes use resource-locator **id** mode with a placeholder. The
easiest fix: open each Sheets node, switch the Document field to "From list",
pick the sheet — n8n then fills the column schema for the mapper automatically.
Do this for **Read Processing Log** (×2), **Update row**, and **Append row to
Processing Log**.

## Step 3 — Confirm the sheet has the 15 columns

`CONTRACT.md` section 7. The header row must read exactly:

```
Document ID | Received At | File Name | File Link | Document Type |
Sender / Company | Summary | Requested Action | Deadline | Urgency |
Department | Submitted By | Status | Reviewed By | Review Note
```

The Code nodes map to these strings verbatim. If a header differs, fix the
header or the `COLS` map in the Code node — in both places, not one.

## Step 4 — Credentials already wired (verify they are healthy)

| Node | Credential used | Id |
|---|---|---|
| Google Sheets (all) | Google Sheets OAuth2 API | `pHFYlfi7ARohCIG1` |
| Upload original to Drive | Google Drive account | `ca58XKLdnQURD47g` |
| Notify (urgent) / (normal) | Gmail OAuth2 API | `AYgjFyDnQF1fGC7w` |
| OpenAI Chat Model | OpenAI account | `UttpnJOpJjqyZKw6` |

Re-authorise any that show as expired.

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
