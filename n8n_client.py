"""Every outbound call to n8n lives here. No other file imports httpx or knows
a webhook URL. When settings.use_mock is true, each function returns data from
mock.py instead -- switching one endpoint to real calls is deleting one line.

On any failure these functions raise N8nError. It carries a `kind` and a
plain-English `user_message` that main.py can show as-is; the routes never build
error prose from a status code.
"""
from __future__ import annotations

import httpx

import mock
from config import settings

# error_code -> sentence a non-technical employee can act on. From CONTRACT.md s4.
_CODE_MESSAGES = {
    "UNSUPPORTED_FILE_TYPE": "Only PDF, DOCX and TXT files can be processed.",
    "EMPTY_DOCUMENT": (
        "We couldn't find any readable text in that file. It may be a scan or an "
        "image. Try a different file or a text-based PDF."
    ),
    "EXTRACTION_FAILED": (
        "Something went wrong while reading the document. Your file is still "
        "here -- press Retry to try again."
    ),
    "UNAUTHORIZED": (
        "The application isn't set up correctly: the processing service rejected "
        "its access key. This needs whoever configured the app -- it's not "
        "something you can fix here."
    ),
}


class N8nError(Exception):
    def __init__(self, kind: str, user_message: str, *,
                 error_code: str | None = None, http_status: int | None = None):
        super().__init__(user_message)
        self.kind = kind                # timeout | unauthorized | upstream | unreachable | bad_response
        self.user_message = user_message
        self.error_code = error_code
        self.http_status = http_status

    @property
    def retryable(self) -> bool:
        return self.kind in {"timeout", "unreachable"} or self.error_code in {
            "EXTRACTION_FAILED",
        }


def _headers() -> dict:
    return {"x-api-key": settings.secret, "Content-Type": "application/json"}


def _raise_for_error_response(resp: httpx.Response) -> None:
    """Turn a non-2xx n8n response into an N8nError."""
    body = {}
    try:
        body = resp.json()
    except ValueError:
        pass

    code = body.get("error_code") if isinstance(body, dict) else None
    server_msg = body.get("message") if isinstance(body, dict) else None

    if resp.status_code == 401 or code == "UNAUTHORIZED":
        raise N8nError("unauthorized", _CODE_MESSAGES["UNAUTHORIZED"],
                       error_code="UNAUTHORIZED", http_status=resp.status_code)

    if code in _CODE_MESSAGES:
        raise N8nError("upstream", _CODE_MESSAGES[code],
                       error_code=code, http_status=resp.status_code)

    if 400 <= resp.status_code < 500:
        raise N8nError(
            "upstream",
            server_msg or "The processing service rejected the request.",
            http_status=resp.status_code,
        )

    raise N8nError(
        "upstream",
        "The processing service had a problem. Please try again in a few minutes.",
        http_status=resp.status_code,
    )


def _post(path: str, json_body: dict) -> dict | list:
    url = settings.url_for(path)
    try:
        with httpx.Client(timeout=settings.request_timeout_s) as client:
            resp = client.post(url, json=json_body, headers=_headers())
    except (httpx.ConnectError, httpx.ConnectTimeout):
        raise N8nError(
            "unreachable",
            "We can't reach the processing service right now. It may be down or "
            "the address may be wrong. Try again shortly.",
        )
    except httpx.TimeoutException:
        raise N8nError(
            "timeout",
            "The request took longer than 90 seconds. The document may still be "
            "processing in the background -- check the dashboard in a minute, or "
            "press Retry.",
        )
    except httpx.HTTPError:
        raise N8nError(
            "unreachable",
            "We can't reach the processing service right now. Check your "
            "connection and try again shortly.",
        )
    if resp.is_success:
        return resp.json()
    _raise_for_error_response(resp)
    raise AssertionError("unreachable")


def _get(path: str) -> dict | list:
    url = settings.url_for(path)
    try:
        with httpx.Client(timeout=settings.request_timeout_s) as client:
            resp = client.get(url, headers=_headers())
    except (httpx.ConnectError, httpx.ConnectTimeout):
        raise N8nError(
            "unreachable",
            "We can't reach the document log right now. The processing service "
            "may be down. Press Refresh to try again.",
        )
    except httpx.TimeoutException:
        raise N8nError(
            "timeout",
            "The document log took too long to load. Press Refresh to try again.",
        )
    except httpx.HTTPError:
        raise N8nError(
            "unreachable",
            "We can't reach the document log right now. Check your connection "
            "and press Refresh to try again.",
        )
    if resp.is_success:
        return resp.json()
    _raise_for_error_response(resp)
    raise AssertionError("unreachable")


# --- The three endpoints -----------------------------------------------------

def process_document(payload: dict) -> dict:
    if settings.use_mock:
        return mock.process_document(payload)
    return _post(settings.process_path, payload)  # -> real POST /process-document


def list_documents() -> list[dict]:
    if settings.use_mock:
        return mock.list_documents()
    data = _get(settings.documents_path)              # -> real GET /documents
    if not isinstance(data, list):
        raise N8nError(
            "bad_response",
            "The document log came back in an unexpected format. Try again, and "
            "tell whoever set up the app if it keeps happening.",
        )
    return data


def submit_review(payload: dict) -> dict:
    if settings.use_mock:
        try:
            return mock.submit_review(payload)
        except mock.MockNotFound:
            raise N8nError(
                "upstream",
                "That document isn't in the log any more, so it can't be marked "
                "as reviewed. Refresh the dashboard and try again.",
                http_status=404,
            )
    return _post(settings.review_path, payload)       # -> real POST /review


def analyze_document(payload: dict) -> dict:
    """Add-on: a deeper AI-agent write-up of one document. Not part of the core
    contract; the sheet is untouched."""
    if settings.use_mock:
        try:
            return mock.analyze_document(payload)
        except mock.MockNotFound:
            raise N8nError(
                "upstream",
                "That document isn't in the log, so there's nothing to analyse. "
                "Refresh the dashboard and try again.",
                http_status=404,
            )
    return _post(settings.analyze_path, payload)      # -> real POST /analyze
