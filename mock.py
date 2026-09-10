"""In-memory stand-in for the n8n workflows, used when USE_MOCK=true.

The responses match CONTRACT.md exactly:
  * process_document() returns the seven business fields nested under "fields".
  * list_documents()   returns them flat, one dict per spreadsheet row.
The module keeps a list that plays the part of the Google Sheet so uploads and
reviews are visible on the dashboard during local testing. Nothing here runs
when USE_MOCK=false.
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

NOT_FOUND = "Not found"
NO_ACTION = "No action found"

_lock = threading.Lock()
_counter = 1043  # mimics n8n execution ids, matching CONTRACT's "exec-1043"


class MockNotFound(Exception):
    """Raised by submit_review when no row matches the document_id (HTTP 404)."""


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row(offset_hours, doc_id, file_name, dtype, sender, summary, action,
         deadline, urgency, dept, status):
    received = datetime(2026, 9, 8, 8, 0, tzinfo=timezone.utc) + timedelta(hours=offset_hours)
    return {
        "document_id": doc_id,
        "received_at": _iso(received),
        "file_name": file_name,
        "file_link": f"https://drive.google.com/file/d/{doc_id}/view",
        "document_type": dtype,
        "sender_or_company": sender,
        "summary": summary,
        "requested_action": action,
        "deadline": deadline,
        "urgency": urgency,
        "department": dept,
        "status": status,
    }


# Seeded oldest-first on purpose: GET /documents returns sheet order and the
# dashboard is responsible for sorting newest-first.
_DOCS: list[dict] = [
    _row(0, "exec-1043", "invoice-4471.pdf", "invoice", "Nordic Supplies Ltd",
         "Invoice for office chairs delivered in February.",
         "Approve and pay invoice 4471", "12 March 2026", "High", "Finance", "Processed"),
    _row(3, "exec-1044", "welcome-pack.txt", "other", "HR Onboarding",
         "New starter welcome pack for the March intake.",
         NO_ACTION, NOT_FOUND, "Low", "HR", "Processed"),
    _row(7, "exec-1045", "sla-complaint.docx", "complaint", "Brightpath Retail",
         "Customer reports repeated late deliveries and asks for a credit note.",
         "Investigate delivery delays and respond within 5 days", "20 March 2026",
         "High", "Support", "Needs Review"),
    _row(11, "exec-1046", "quote-printers.pdf", "quote", "Orbit Office Tech",
         "Quotation for 12 multifunction printers including a 3-year service plan.",
         "Review pricing and confirm by end of quarter", "31 March 2026",
         "Medium", "Sales", "Processed"),
    _row(15, "exec-1047", "board-report-q1.pdf", "report", "Finance Office",
         "Draft first-quarter financial summary for board review.",
         "Circulate to board members before the April meeting", "5 April 2026",
         "Medium", "Management", "Processed"),
    _row(20, "exec-1048", "scan-002.pdf", "other", NOT_FOUND,
         "Scanned document, mostly illegible handwriting.",
         NO_ACTION, NOT_FOUND, "Low", "General", "Needs Review"),
    _row(26, "exec-1049", "maintenance-request.txt", "request", "Facilities Team",
         "Request to fix the air conditioning on the third floor.",
         "Raise a work order with the building manager", "18 March 2026",
         "Medium", "General", "Processed"),
    _row(31, "exec-1050", "contract-renewal-acme.docx", "contract", "Acme Cloud Services",
         "Annual hosting contract renewal with a 4 percent price increase.",
         "Legal to review new terms before signature", "28 March 2026",
         "High", "Management", "Needs Review"),
    _row(36, "exec-1051", "expense-claim-feb.pdf", "request", "Dana Levi",
         "Expense claim for a client visit to Manchester in February.",
         "Approve reimbursement of 214.60", "15 March 2026", "Low", "Finance", "Reviewed"),
    _row(42, "exec-1052", "vendor-invoice-8830.pdf", "invoice", "Peak Logistics",
         "Freight invoice for the February shipment batch.",
         "Match against purchase order and pay", "22 March 2026",
         "Medium", "Finance", "Processed"),
    _row(48, "exec-1053", "policy-update.txt", "other", "HR Policy Group",
         "Updated remote-working policy effective April.",
         "Publish to the staff handbook", NOT_FOUND, "Low", "HR", "Processed"),
    _row(55, "exec-1054", "complaint-billing.docx", "complaint", "Meridian Partners",
         "Client disputes two line items on the January statement.",
         "Reconcile the statement and issue a corrected copy", "19 March 2026",
         "High", "Finance", "Needs Review"),
    _row(60, "exec-1055", "sales-proposal-westside.pdf", "quote", "Westside Group",
         "Proposal for a managed print rollout across four sites.",
         "Prepare a follow-up call with the account owner", "2 April 2026",
         "Medium", "Sales", "Processed"),
    _row(66, "exec-1056", "incident-report.pdf", "report", "Support Desk",
         "Summary of the 6 March service outage and its resolution.",
         "Share the post-incident review with affected clients", "13 March 2026",
         "High", "Support", "Reviewed"),
    _row(73, "exec-1057", "nda-draft.docx", "contract", "Loomis & Yates",
         "Mutual non-disclosure agreement ahead of partnership talks.",
         "Return marked-up copy to their legal team", "25 March 2026",
         "Medium", "Management", "Processed"),
    _row(78, "exec-1058", "timesheet-week10.txt", "other", NOT_FOUND,
         "Weekly timesheet export, no approver named.",
         NO_ACTION, NOT_FOUND, "Low", "General", "Needs Review"),
    _row(85, "exec-1059", "invoice-4489.pdf", "invoice", "Nordic Supplies Ltd",
         "Follow-up invoice for a partial chair delivery in March.",
         "Confirm goods received before payment", "30 March 2026",
         "Medium", "Finance", "Processed"),
    _row(91, "exec-1060", "training-request.txt", "request", "Sam Okafor",
         "Request to attend a two-day project management course.",
         "Check the training budget and approve", "17 March 2026",
         "Low", "HR", "Processed"),
    _row(98, "exec-1061", "escalation-outage.docx", "complaint", "Cedar Financial",
         "Formal escalation over the March outage affecting trading hours.",
         "Director to call the client and agree a remediation plan", "11 March 2026",
         "High", "Management", "Needs Review"),
    _row(104, "exec-1062", "quarterly-forecast.pdf", "report", "Sales Operations",
         "Rolling sales forecast for the next two quarters.",
         "Review assumptions with regional leads", "6 April 2026",
         "Medium", "Sales", "Processed"),
    _row(110, "exec-1063", "supplier-quote-packaging.pdf", "quote", "GreenPack Ltd",
         "Quote for recyclable packaging with volume discounts.",
         "Compare against the current supplier", "3 April 2026",
         "Low", "Finance", "Processed"),
    _row(117, "exec-1064", "hr-grievance.docx", "complaint", NOT_FOUND,
         "Anonymous grievance submission, details withheld.",
         NO_ACTION, NOT_FOUND, "High", "HR", "Needs Review"),
]


def _example_fields_for(file_name: str) -> dict:
    """A plausible extraction result. Varies a little by file name so the demo
    doesn't look canned, but always uses the CONTRACT enum values."""
    name = file_name.lower()
    if "invoice" in name:
        return {
            "document_type": "invoice",
            "sender_or_company": "Nordic Supplies Ltd",
            "summary": "Invoice for office chairs delivered in February.",
            "requested_action": "Approve and pay invoice 4471",
            "deadline": "12 March 2026",
            "urgency": "High",
            "department": "Finance",
        }
    if "complaint" in name or "escalation" in name:
        return {
            "document_type": "complaint",
            "sender_or_company": "Brightpath Retail",
            "summary": "Customer reports repeated late deliveries and asks for a credit note.",
            "requested_action": "Investigate delivery delays and respond within 5 days",
            "deadline": "20 March 2026",
            "urgency": "High",
            "department": "Support",
        }
    if "contract" in name or "nda" in name:
        return {
            "document_type": "contract",
            "sender_or_company": "Acme Cloud Services",
            "summary": "Annual hosting contract renewal with a 4 percent price increase.",
            "requested_action": "Legal to review new terms before signature",
            "deadline": "28 March 2026",
            "urgency": "Medium",
            "department": "Management",
        }
    if "quote" in name or "proposal" in name:
        return {
            "document_type": "quote",
            "sender_or_company": "Orbit Office Tech",
            "summary": "Quotation for 12 multifunction printers including a 3-year service plan.",
            "requested_action": "Review pricing and confirm by end of quarter",
            "deadline": "31 March 2026",
            "urgency": "Medium",
            "department": "Sales",
        }
    if "report" in name:
        return {
            "document_type": "report",
            "sender_or_company": "Finance Office",
            "summary": "Draft first-quarter financial summary for board review.",
            "requested_action": "Circulate to board members before the April meeting",
            "deadline": "5 April 2026",
            "urgency": "Medium",
            "department": "Management",
        }
    # Sparse result: two fields missing -> the sub-workflow would mark Needs Review.
    return {
        "document_type": "other",
        "sender_or_company": NOT_FOUND,
        "summary": "Short note with no clear sender or deadline.",
        "requested_action": NO_ACTION,
        "deadline": NOT_FOUND,
        "urgency": "Low",
        "department": "General",
    }


def _status_for(fields: dict) -> str:
    missing = sum(
        1 for v in fields.values() if v in (NOT_FOUND, NO_ACTION)
    )
    return "Needs Review" if missing >= 2 else "Processed"


def process_document(payload: dict) -> dict:
    """Mimics POST /process-document. Appends a row to the fake sheet."""
    global _counter
    with _lock:
        _counter += 1
        doc_id = f"exec-{_counter}"
        now = _iso(datetime.now(timezone.utc))
        file_name = payload.get("file_name") or "document.pdf"
        fields = _example_fields_for(file_name)
        status = _status_for(fields)
        file_link = f"https://drive.google.com/file/d/{doc_id}/view"

        self_row = {
            "document_id": doc_id,
            "received_at": now,
            "file_name": file_name,
            "file_link": file_link,
            **fields,
            "status": status,
        }
        _DOCS.append(self_row)

    return {
        "status": "processed",
        "document_id": doc_id,
        "file_name": file_name,
        "file_link": file_link,
        "received_at": now,
        "fields": fields,
        "notification_sent": True,
    }


def list_documents() -> list[dict]:
    """Mimics GET /documents. Returns a copy in sheet order (oldest first)."""
    with _lock:
        return [dict(row) for row in _DOCS]


def submit_review(payload: dict) -> dict:
    """Mimics POST /review. Updates the row in place, or raises MockNotFound."""
    doc_id = payload.get("document_id")
    with _lock:
        for row in _DOCS:
            if row["document_id"] == doc_id:
                row["status"] = payload.get("status", row["status"])
                row["reviewed_by"] = payload.get("reviewed_by", "")
                row["review_note"] = payload.get("review_note", "")
                return {"status": "updated", "document_id": doc_id}
    raise MockNotFound(doc_id)


def analyze_document(payload: dict) -> dict:
    """Mimics the /analyze add-on. Canned briefing so the button works offline."""
    doc_id = payload.get("document_id")
    with _lock:
        row = next((r for r in _DOCS if r["document_id"] == doc_id), None)
    if row is None:
        raise MockNotFound(doc_id)

    sender = row["sender_or_company"]
    analysis = (
        f"**What this document is**\n"
        f"A {row['document_type']} from {sender}, handled by the "
        f"{row['department']} department. {row['summary']} "
        f"Requested action: {row['requested_action']}. Deadline: {row['deadline']}.\n\n"
        f"**About the sender**\n"
        f"{sender} is the party that issued this document. (Mock mode returns a "
        f"placeholder here — the live add-on asks the AI agent to profile the "
        f"company.)\n\n"
        f"**Line items**\n"
        f"* Mock mode does not re-read the file, so individual line items are not "
        f"listed. Run against the live automation to see each charge explained.\n\n"
        f"**Worth a closer look**\n"
        f"* Urgency is {row['urgency']} and the status is {row['status']}.\n\n"
        f"**Recommended next step**\n"
        f"Open the original file and confirm the amounts before acting."
    )
    return {"document_id": doc_id, "analysis": analysis}
