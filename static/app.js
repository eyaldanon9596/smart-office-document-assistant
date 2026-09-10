// One file, three screens: upload, dashboard filtering, detail review.
// No framework. Everything talks to the same-origin /api/* routes.

const MIME_BY_EXT = {
  pdf: "application/pdf",
  txt: "text/plain",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
};

// ---- Upload screen --------------------------------------------------------
const uploadForm = document.getElementById("upload-form");
if (uploadForm) {
  const input = document.getElementById("file-input");
  const summary = document.getElementById("file-summary");
  const errorBox = document.getElementById("upload-error");
  const sendBtn = document.getElementById("send-btn");
  const processing = document.getElementById("processing");
  const dropzone = document.getElementById("dropzone");
  const maxBytes = Number(uploadForm.dataset.maxMb) * 1024 * 1024;
  let sending = false;

  const showError = (msg) => { errorBox.textContent = msg; errorBox.hidden = false; };
  const clearError = () => { errorBox.hidden = true; };

  const describe = () => {
    const f = input.files[0];
    if (!f) { summary.hidden = true; sendBtn.disabled = true; return; }
    summary.hidden = false;
    summary.textContent = `${f.name} — ${(f.size / 1024 / 1024).toFixed(2)} MB`;
    sendBtn.disabled = false;
    clearError();
  };

  input.addEventListener("change", describe);
  ["dragover", "dragenter"].forEach((e) =>
    dropzone.addEventListener(e, (ev) => { ev.preventDefault(); dropzone.classList.add("over"); }));
  ["dragleave", "drop"].forEach((e) =>
    dropzone.addEventListener(e, () => dropzone.classList.remove("over")));
  dropzone.addEventListener("drop", (ev) => {
    ev.preventDefault();
    if (ev.dataTransfer.files.length) { input.files = ev.dataTransfer.files; describe(); }
  });

  uploadForm.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (sending) return;
    const file = input.files[0];
    if (!file) { showError("Choose a file first."); return; }

    const ext = file.name.split(".").pop().toLowerCase();
    const mime = MIME_BY_EXT[ext];
    if (!mime) { showError("Only PDF, DOCX and TXT files can be sent."); return; }
    if (file.size > maxBytes) {
      showError(`That file is ${(file.size / 1024 / 1024).toFixed(1)} MB. The limit is ${uploadForm.dataset.maxMb} MB.`);
      return;
    }

    sending = true;
    sendBtn.disabled = true;
    clearError();
    processing.hidden = false;

    try {
      const base64 = await new Promise((resolve, reject) => {
        const r = new FileReader();
        r.onload = () => resolve(String(r.result).split(",")[1]);
        r.onerror = () => reject(new Error("read failed"));
        r.readAsDataURL(file);
      });
      const res = await fetch("/api/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          file_name: file.name,
          mime_type: mime,
          file_base64: base64,
          submitted_by: document.getElementById("submitted-by").value.trim(),
        }),
      });
      const body = await res.json().catch(() => ({}));
      if (res.ok && body.status !== "error") {
        window.location = "/documents/" + body.document_id;
        return;
      }
      showError(body.message || "The document could not be processed. Please try again.");
    } catch {
      showError("The request could not be completed. Check your connection and try again.");
    }
    processing.hidden = true;
    sendBtn.disabled = false;
    sending = false;
  });
}

// ---- Dashboard filtering ------------------------------------------------
const filters = document.getElementById("filters");
if (filters) {
  const q = document.getElementById("q");
  const selects = ["f-urgency", "f-type", "f-department", "f-status"].map((id) => document.getElementById(id));
  const rows = Array.from(document.querySelectorAll(".doc-row"));
  const noResults = document.getElementById("no-results");
  const count = document.getElementById("result-count");
  const [urg, type, dept, status] = selects;

  const apply = () => {
    const text = q.value.trim().toLowerCase();
    let shown = 0;
    rows.forEach((row) => {
      const d = row.dataset;
      const matchText = !text ||
        d.name.includes(text) || d.sender.includes(text) || d.summary.includes(text);
      const match = matchText &&
        (!urg.value || d.urgency === urg.value) &&
        (!type.value || d.type === type.value) &&
        (!dept.value || d.department === dept.value) &&
        (!status.value || d.status === status.value);
      row.hidden = !match;
      if (match) shown += 1;
    });
    count.textContent = `${shown} of ${rows.length} shown`;
    noResults.hidden = shown !== 0;
  };

  q.addEventListener("input", apply);
  selects.forEach((s) => s.addEventListener("change", apply));
  document.getElementById("clear-filters").addEventListener("click", () => {
    q.value = ""; selects.forEach((s) => (s.value = "")); apply();
  });
  apply();
}

// ---- Detail: review submission ----------------------------------------
const reviewForm = document.getElementById("review-form");
if (reviewForm) {
  const note = document.getElementById("review-note");
  const noteCount = document.getElementById("note-count");
  const message = document.getElementById("review-message");
  const reviewedBy = document.getElementById("reviewed-by");
  let saving = false;

  note.addEventListener("input", () => { noteCount.textContent = `${note.value.length} / 200`; });

  reviewForm.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (saving) return;
    const status = (ev.submitter && ev.submitter.dataset.status) || "Reviewed";
    if (!reviewedBy.value.trim()) {
      message.hidden = false;
      message.className = "inline-message error";
      message.textContent = "Enter your name or email before saving.";
      return;
    }
    saving = true;
    reviewForm.querySelectorAll("button").forEach((b) => (b.disabled = true));
    try {
      const res = await fetch("/api/review", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          document_id: reviewForm.dataset.documentId,
          status,
          reviewed_by: reviewedBy.value.trim(),
          review_note: note.value.trim(),
        }),
      });
      const body = await res.json().catch(() => ({}));
      if (res.ok && body.status !== "error") {
        message.hidden = false;
        message.className = "inline-message ok";
        message.textContent = "Saved. Taking you back to the dashboard…";
        setTimeout(() => (window.location = "/dashboard"), 900);
        return;
      }
      message.hidden = false;
      message.className = "inline-message error";
      message.textContent = body.message || "The update could not be saved. Please try again.";
    } catch {
      message.hidden = false;
      message.className = "inline-message error";
      message.textContent = "The update could not be sent. Check your connection and try again.";
    }
    reviewForm.querySelectorAll("button").forEach((b) => (b.disabled = false));
    saving = false;
  });
}

// ---- Detail: AI analysis add-on --------------------------------------
const analyzeBtn = document.getElementById("analyze-btn");
if (analyzeBtn) {
  const statusBox = document.getElementById("analysis-status");
  const outBox = document.getElementById("analysis-output");
  let running = false;

  // Minimal markdown: **bold**, "* " bullets, "**Heading**" lines, blank-line paras.
  const render = (text) => {
    const esc = (s) => s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
    const inline = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    let html = "";
    let inList = false;
    for (const raw of text.split("\n")) {
      const line = raw.trim();
      const heading = line.match(/^\*\*(.+?)\*\*:?$/);
      if (!line) { if (inList) { html += "</ul>"; inList = false; } continue; }
      if (heading) {
        if (inList) { html += "</ul>"; inList = false; }
        html += "<h4>" + inline(heading[1]) + "</h4>";
      } else if (line.startsWith("* ") || line.startsWith("- ")) {
        if (!inList) { html += "<ul>"; inList = true; }
        html += "<li>" + inline(line.slice(2)) + "</li>";
      } else {
        if (inList) { html += "</ul>"; inList = false; }
        html += "<p>" + inline(line) + "</p>";
      }
    }
    if (inList) html += "</ul>";
    return html;
  };

  analyzeBtn.addEventListener("click", async () => {
    if (running) return;
    running = true;
    analyzeBtn.disabled = true;
    analyzeBtn.textContent = "Analyzing…";
    statusBox.hidden = false;
    statusBox.className = "inline-message";
    statusBox.textContent = "Reading the file and writing the briefing…";
    outBox.hidden = true;
    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_id: analyzeBtn.dataset.documentId }),
      });
      const body = await res.json().catch(() => ({}));
      if (res.ok && body.analysis) {
        statusBox.hidden = true;
        outBox.hidden = false;
        outBox.innerHTML = render(body.analysis);
      } else {
        statusBox.className = "inline-message error";
        statusBox.textContent = body.message || "The analysis could not be completed. Please try again.";
      }
    } catch {
      statusBox.className = "inline-message error";
      statusBox.textContent = "The analysis could not be sent. Check your connection and try again.";
    }
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "Analyze again";
    running = false;
  });
}
