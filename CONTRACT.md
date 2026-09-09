# CONTRACT.md

The data contract between the application (Part 2) and the n8n workflows (Part 1).

**Rule:** if this contract changes, it changes in three places at once — this file, the n8n
workflows, and the application. Never in two of the three.

---

## 1. Transport and authentication

| Setting | Value |
|---|---|
| Base URL | `https://<instance>.app.n8n.cloud/webhook` (Production URL only) |
| Auth | Header authentication, `x-api-key: <shared secret>` |
| Content type | `application/json` on every request and response |
| Client timeout | 90 seconds |
| Max file size | 10 MB before base64 encoding |

The Test URL (`/webhook-test/`) is never used by the application. It only lives for 120 seconds
after pressing "Listen for test event" and accepts a single request.

The secret is added by the FastAPI server, never by browser code.

---

## 2. Allowed values

These come from Part 1 section 6.1. The application may style them. It must never translate,
rename, shorten, or add to them — including in a Hebrew interface.

| Field | Allowed values |
|---|---|
| `document_type` | `invoice`, `request`, `report`, `complaint`, `contract`, `quote`, `other` |
| `urgency` | `Low`, `Medium`, `High` |
| `department` | `Sales`, `Finance`, `Support`, `HR`, `Management`, `General` |
| `status` | `Processed`, `Needs Review`, `Reviewed` |

Missing information arrives as the literal string `Not found`, except `requested_action`, which
uses `No action found`. Both are displayed as written. Never hidden, never replaced with a guess,
never rendered as an empty cell.

### 2.1 The Needs Review rule

This is business logic. It lives in the n8n sub-workflow, never in the application.

After the Information Extractor returns, count how many of the seven business fields hold
`Not found` or `No action found`.

| Count | Status written to the sheet |
|---|---|
| 0 or 1 | `Processed` |
| 2 or more | `Needs Review` |

`Reviewed` is never written by the automation. It is written only by Workflow C, when a person
presses "Mark as reviewed".

The application displays the status. It does not compute it, and it does not override it.

---

## 3. POST /process-document

### 3.1 Request

| Field | Type | Required | Notes |
|---|---|---|---|
| `file_name` | string | yes | Original name including the extension |
| `mime_type` | string | yes | `application/pdf`, `text/plain`, or the DOCX type |
| `file_base64` | string | yes | Base64 of the file, **without** a `data:` URL prefix |
| `submitted_by` | string | no | Who used the application |

Accepted MIME types:

```
application/pdf
text/plain
application/vnd.openxmlformats-officedocument.wordprocessingml.document
```

Anything else is rejected by the application before the request is sent.

### 3.2 Success response — HTTP 200

```json
{
  "status": "processed",
  "document_id": "exec-1043",
  "file_name": "invoice-4471.pdf",
  "file_link": "https://drive.google.com/file/d/1a2b3c/view",
  "received_at": "2026-03-11T09:24:00Z",
  "fields": {
    "document_type": "invoice",
    "sender_or_company": "Nordic Supplies Ltd",
    "summary": "Invoice for office chairs delivered in February.",
    "requested_action": "Approve and pay invoice 4471",
    "deadline": "12 March 2026",
    "urgency": "High",
    "department": "Finance"
  },
  "notification_sent": true
}
```

The seven business fields are nested under `fields`. They are not at the top level. This is the
single most common mismatch — if the dashboard shows blank cells, compare the real response
against this block before changing anything.

`deadline` is returned exactly as written in the document. It is not normalised to a date format.

`received_at` is ISO 8601 UTC, and the same string is written to the `Received At` column in the
sheet. Both endpoints must return the identical format — otherwise the same document looks
different on the upload screen and on the dashboard.

`notification_sent` is produced inside the sub-workflow, after the Gmail node on both branches of
the IF. The sub-workflow returns it alongside the seven business fields. If it arrives as `null`,
the sub-workflow is not passing it out.

---

## 4. Error response

Returned by every endpoint.

```json
{
  "status": "error",
  "error_code": "UNSUPPORTED_FILE_TYPE",
  "message": "Only PDF, DOCX and TXT files can be processed."
}
```

| `error_code` | HTTP | When | What the application shows |
|---|---|---|---|
| `UNSUPPORTED_FILE_TYPE` | 400 | MIME type is not PDF, DOCX or TXT | Inline message on the upload screen; the file is not sent |
| `EMPTY_DOCUMENT` | 400 | Text extraction produced nothing | Explain there is no readable text and suggest another file |
| `EXTRACTION_FAILED` | 500 | The AI step failed or returned unusable output | Retry button; the file stays in the form |
| `UNAUTHORIZED` | 401 | Missing or wrong secret header | Configuration error — not something the end user can fix |

A timeout is not an error code. The application treats it separately: the request is abandoned
after 90 seconds and a Retry option is offered.

---

## 5. GET /documents

No request body. Returns every row of the Document Processing Log, newest first.

```json
[
  {
    "document_id": "exec-1043",
    "received_at": "2026-03-11T09:24:00Z",
    "file_name": "invoice-4471.pdf",
    "file_link": "https://drive.google.com/file/d/1a2b3c/view",
    "document_type": "invoice",
    "sender_or_company": "Nordic Supplies Ltd",
    "summary": "Invoice for office chairs delivered in February.",
    "requested_action": "Approve and pay invoice 4471",
    "deadline": "12 March 2026",
    "urgency": "High",
    "department": "Finance",
    "status": "Processed"
  }
]
```

Note the shape difference from section 3.2: here the fields are **flat**, because they are
spreadsheet columns. There is no `fields` object. Both shapes are correct; the application must
handle each one where it belongs.

An empty log returns `[]`, not an error.

---

## 6. POST /review

### 6.1 Request

| Field | Type | Required | Notes |
|---|---|---|---|
| `document_id` | string | yes | Must match a Document ID in the sheet |
| `status` | string | yes | `Reviewed` or `Needs Review` |
| `reviewed_by` | string | yes | Name or email of the reviewer |
| `review_note` | string | no | Free text, maximum 200 characters |

### 6.2 Response — HTTP 200

```json
{ "status": "updated", "document_id": "exec-1043" }
```

Returns HTTP 404 with an error object when no row matches the `document_id`.

Rows are matched on `document_id` only. Never on file name — two documents can share a name.

---

## 7. Spreadsheet columns

The Google Sheet named `Document Processing Log` is the single source of truth. The application
holds no database.

| Column | Written by | Notes |
|---|---|---|
| Document ID | Workflow A / sub-workflow | Stable identifier, from the execution id |
| Received At | sub-workflow | |
| File Name | sub-workflow | |
| File Link | sub-workflow | Google Drive link |
| Document Type | AI | |
| Sender / Company | AI | |
| Summary | AI | |
| Requested Action | AI | |
| Deadline | AI | |
| Urgency | AI | |
| Department | AI | |
| Submitted By | Workflow A | `Not found` when the file came through the Drive trigger |
| Status | sub-workflow, then Workflow C | Per the rule in section 2.1 |
| Reviewed By | Workflow C | |
| Review Note | Workflow C | |

All fifteen columns exist before any workflow is built.

`Submitted By` is stored but not shown on the dashboard. It exists so the log can distinguish a
document sent from the application from one dropped into the Drive folder.
