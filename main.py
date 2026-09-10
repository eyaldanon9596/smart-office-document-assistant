"""FastAPI app: three page routes for people, three /api/* routes for the
browser's fetch calls. The /api/* routes only add the secret header and hand
the n8n response straight back. All sorting and filtering is display work done
here or in the browser, never asked of n8n.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import n8n_client
from config import settings
from n8n_client import N8nError

app = FastAPI(title="Smart Office Document Assistant")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# A 10 MB file is ~13.3 MB once base64-encoded; give the JSON body real headroom
# so an oversized upload gets our sentence, not a bare 413.
MAX_JSON_BYTES = 15 * 1024 * 1024

# Filter choices come straight from CONTRACT.md section 2 -- fixed lists, never
# derived from the data, so a typo in one row can't add a phantom option.
DOCUMENT_TYPES = ["invoice", "request", "report", "complaint", "contract", "quote", "other"]
URGENCIES = ["Low", "Medium", "High"]
DEPARTMENTS = ["Sales", "Finance", "Support", "HR", "Management", "General"]
STATUSES = ["Processed", "Needs Review", "Reviewed"]

FIELD_LABELS = [
    ("document_type", "Document type"),
    ("sender_or_company", "Sender / Company"),
    ("summary", "Summary"),
    ("requested_action", "Requested action"),
    ("deadline", "Deadline"),
    ("urgency", "Urgency"),
    ("department", "Department"),
]


def _urgency_class(value: str) -> str:
    return {
        "High": "badge badge-high",
        "Medium": "badge badge-medium",
        "Low": "badge badge-low",
    }.get(value, "badge badge-unknown")


templates.env.globals["urgency_class"] = _urgency_class
templates.env.globals["field_labels"] = FIELD_LABELS


@app.middleware("http")
async def _limit_body_size(request: Request, call_next):
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > MAX_JSON_BYTES:
        return JSONResponse(
            status_code=413,
            content={
                "status": "error",
                "message": (
                    "That file is too large to send. The limit is "
                    f"{settings.max_file_mb} MB."
                ),
            },
        )
    return await call_next(request)


def _sort_newest_first(docs: list[dict]) -> list[dict]:
    def key(doc: dict):
        raw = doc.get("received_at", "")
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return datetime.min
    return sorted(docs, key=key, reverse=True)


def _error_page(request: Request, message: str, *, retry_href: str,
                status_code: int = 502) -> HTMLResponse:
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "message": message, "retry_href": retry_href},
        status_code=status_code,
    )


# --- Pages -----------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def upload_screen(request: Request):
    return templates.TemplateResponse(
        "upload.html",
        {"request": request, "max_file_mb": settings.max_file_mb},
    )


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    try:
        docs = n8n_client.list_documents()
    except N8nError as exc:
        return _error_page(request, exc.user_message, retry_href="/dashboard")

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "documents": _sort_newest_first(docs),
            "document_types": DOCUMENT_TYPES,
            "urgencies": URGENCIES,
            "departments": DEPARTMENTS,
            "statuses": STATUSES,
        },
    )


@app.get("/documents/{document_id}", response_class=HTMLResponse)
def document_detail(request: Request, document_id: str):
    try:
        docs = n8n_client.list_documents()
    except N8nError as exc:
        return _error_page(request, exc.user_message, retry_href="/dashboard")

    doc = next((d for d in docs if d.get("document_id") == document_id), None)
    if doc is None:
        return _error_page(
            request,
            f"No document with the id {document_id} is in the log. It may not "
            "have finished processing yet.",
            retry_href="/dashboard",
            status_code=404,
        )

    return templates.TemplateResponse(
        "detail.html",
        {"request": request, "doc": doc, "statuses": STATUSES},
    )


# --- /api/* : pass-through to n8n, secret added here ----------------------

def _api_error(exc: N8nError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status or 502,
        content={
            "status": "error",
            "message": exc.user_message,
            "error_code": exc.error_code,
            "retryable": exc.retryable,
        },
    )


@app.post("/api/process")
async def api_process(request: Request):
    payload = await request.json()
    try:
        return JSONResponse(n8n_client.process_document(payload))
    except N8nError as exc:
        return _api_error(exc)


@app.get("/api/documents")
def api_documents():
    try:
        return JSONResponse(n8n_client.list_documents())
    except N8nError as exc:
        return _api_error(exc)


@app.post("/api/review")
async def api_review(request: Request):
    payload = await request.json()
    try:
        return JSONResponse(n8n_client.submit_review(payload))
    except N8nError as exc:
        return _api_error(exc)


@app.post("/api/analyze")
async def api_analyze(request: Request):
    payload = await request.json()
    try:
        return JSONResponse(n8n_client.analyze_document(payload))
    except N8nError as exc:
        return _api_error(exc)


@app.post("/api/scan-inbox")
async def api_scan_inbox(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    try:
        return JSONResponse(n8n_client.scan_inbox(payload))
    except N8nError as exc:
        return _api_error(exc)
