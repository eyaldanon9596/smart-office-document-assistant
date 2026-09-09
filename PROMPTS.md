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

No Part 1 spec document exists. The workflows were built to satisfy `CONTRACT.md`
only, wired to the Google Sheets / Drive / Gmail / OpenAI credentials already on
the instance, and left **inactive**. Every value that needs a real id is a
literal placeholder (`REPLACE_WITH_SHEET_ID`, `REPLACE_WITH_DRIVE_FOLDER_ID`,
`REPLACE_WITH_NOTIFY_EMAIL`) and is listed in `N8N_SETUP.md`. They must be
reviewed before activation.
