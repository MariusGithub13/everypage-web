"""EveryPage: ask a PDF a question and get one of three verdicts, with the page a person can check.

FOUND       the answer, with quotes that were verified in code to be on the page they name
NOT FOUND   every page was read and examined, so this is a real negative
CANNOT SAY  nothing was found, but some page could not be read or examined; this is not a "no"

Uploads live in a temp folder and are deleted after TTL_MIN minutes. Nothing is kept after that.
"""
import asyncio
import json
import os
import re
import secrets
import shutil
import tempfile
import threading
import time
from collections import defaultdict

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from . import ask as ask_mod
from . import ingest, llm

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES_DIR = os.environ.get("EVERYPAGE_SAMPLES", os.path.join(os.path.dirname(HERE), "samples"))
WORK = os.environ.get("EVERYPAGE_WORK", os.path.join(tempfile.gettempdir(), "everypage"))
MAX_BYTES = int(os.environ.get("EVERYPAGE_MAX_MB", "8")) * 1024 * 1024
MAX_PAGES = int(os.environ.get("EVERYPAGE_MAX_PAGES", "25"))
TTL_MIN = int(os.environ.get("EVERYPAGE_TTL_MIN", "30"))
IP_UPLOADS = int(os.environ.get("EVERYPAGE_IP_UPLOADS", "6"))        # per IP per day
IP_QUESTIONS = int(os.environ.get("EVERYPAGE_IP_QUESTIONS", "40"))   # per IP per day
DAY_BUDGET = float(os.environ.get("EVERYPAGE_DAY_BUDGET_USD", "1.50"))
MAX_Q_CHARS = 300

SAMPLES = {
    "agreement": {"file": "sale-agreement.pdf", "title": "Sale agreement, 6 pages",
                  "note": "Pages 4 and 5 are scans. Page 6 is a scan lying on its side."},
    "damaged": {"file": "sale-agreement-damaged.pdf", "title": "The same agreement, page 6 blurred",
                "note": "Page 6 cannot be read by anyone. Watch what the verdict becomes."},
}

app = FastAPI(title="EveryPage", docs_url=None, redoc_url=None, openapi_url=None)
docs = {}                      # id -> state
lock = threading.Lock()
ingest_gate = threading.Semaphore(1)    # one document is read at a time: OCR is CPU, the box is shared
day = {"date": time.strftime("%Y-%m-%d"), "spent": 0.0, "uploads": defaultdict(int), "questions": defaultdict(int)}


def _roll_day():
    today = time.strftime("%Y-%m-%d")
    if day["date"] != today:
        day.update(date=today, spent=0.0, uploads=defaultdict(int), questions=defaultdict(int))


def _ip(request):
    fwd = request.headers.get("x-forwarded-for", "")
    return (fwd.split(",")[0].strip() or (request.client.host if request.client else "?"))[:60]


def _public(state):
    doc = state.get("doc")
    pages = [{k: p[k] for k in ("n", "method", "rotation", "legibility", "chars", "status")}
             for p in state.get("pages", [])]
    return {"id": state["id"], "name": state["name"], "status": state["status"], "error": state.get("error"),
            "total": state.get("total"), "pages": pages, "sample": state.get("sample", False),
            "readable": doc["readable"] if doc else None, "unreadable": doc["unreadable"] if doc else None,
            "expires_in_min": None if state.get("sample") else max(0, int((state["expires"] - time.time()) / 60))}


def _ingest(state):
    with ingest_gate:
        try:
            state["status"] = "reading"
            total = ingest.page_count(state["pdf"])
            state["total"] = total
            if total > MAX_PAGES:
                raise ValueError("This demo reads documents of up to %d pages; this one has %d." % (MAX_PAGES, total))

            def on_page(page, _total):
                state["pages"].append(page)

            doc = ingest.read_pdf(state["pdf"], on_page=on_page, thumbs_dir=state["dir"])
            state["doc"] = doc
            state["status"] = "ready"
        except ValueError as e:
            state.update(status="error", error=str(e))
        except Exception:
            state.update(status="error", error="This file could not be read as a PDF.")


def _new_state(name, pdf, folder, sample=False):
    sid = secrets.token_urlsafe(9)
    state = {"id": sid, "name": name, "pdf": pdf, "dir": folder, "status": "queued", "pages": [],
             "sample": sample, "expires": time.time() + TTL_MIN * 60, "doc": None}
    with lock:
        docs[sid] = state
    return state


def _load_samples():
    for key, meta in SAMPLES.items():
        pdf = os.path.join(SAMPLES_DIR, meta["file"])
        if not os.path.exists(pdf):
            continue
        folder = os.path.join(WORK, "sample-" + key)
        os.makedirs(folder, exist_ok=True)
        state = {"id": "sample-" + key, "name": meta["title"], "pdf": pdf, "dir": folder, "status": "queued",
                 "pages": [], "sample": True, "expires": float("inf"), "doc": None}
        docs[state["id"]] = state
        _ingest(state)


def _janitor():
    while True:
        time.sleep(60)
        now = time.time()
        with lock:
            dead = [k for k, s in docs.items() if not s.get("sample") and s["expires"] < now]
            for k in dead:
                shutil.rmtree(docs[k]["dir"], ignore_errors=True)
                del docs[k]


@app.on_event("startup")
def _startup():
    os.makedirs(WORK, exist_ok=True)
    for name in os.listdir(WORK):          # nothing from a previous run survives a restart
        shutil.rmtree(os.path.join(WORK, name), ignore_errors=True)
    threading.Thread(target=_load_samples, daemon=True).start()
    threading.Thread(target=_janitor, daemon=True).start()


@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
def index():
    with open(os.path.join(HERE, "static", "index.html"), encoding="utf-8") as f:
        return HTMLResponse(f.read(), headers={"Cache-Control": "no-cache"})


@app.get("/healthz")
def healthz():
    _roll_day()
    return {"ok": True, "model": llm.MODEL, "samples_ready": sum(1 for s in docs.values() if s.get("sample") and s["status"] == "ready"),
            "budget_left_usd": round(max(0.0, DAY_BUDGET - day["spent"]), 4)}


@app.get("/api/config")
def config():
    return {"model": llm.MODEL, "max_mb": MAX_BYTES // (1024 * 1024), "max_pages": MAX_PAGES, "ttl_min": TTL_MIN,
            "samples": [{"id": "sample-" + k, "title": v["title"], "note": v["note"]} for k, v in SAMPLES.items()
                        if "sample-" + k in docs]}


@app.post("/api/upload")
async def upload(request: Request, file: UploadFile = File(...)):
    _roll_day()
    ip = _ip(request)
    if day["uploads"][ip] >= IP_UPLOADS:
        raise HTTPException(429, "Daily upload limit reached for this demo. The sample documents still work.")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "This demo accepts PDFs of up to %d MB." % (MAX_BYTES // (1024 * 1024)))
    if not data.startswith(b"%PDF"):
        raise HTTPException(415, "That file is not a PDF.")
    day["uploads"][ip] += 1
    folder = tempfile.mkdtemp(prefix="doc-", dir=WORK)
    pdf = os.path.join(folder, "upload.pdf")
    with open(pdf, "wb") as f:
        f.write(data)
    name = re.sub(r"[^\w .()-]", "_", os.path.basename(file.filename or "document.pdf"))[:80]
    state = _new_state(name, pdf, folder)
    threading.Thread(target=_ingest, args=(state,), daemon=True).start()
    return _public(state)


@app.get("/api/doc/{doc_id}")
def get_doc(doc_id: str):
    state = docs.get(doc_id)
    if not state:
        raise HTTPException(404, "This document has expired or never existed. Upload it again.")
    return _public(state)


@app.get("/api/doc/{doc_id}/page/{n}.png")
def page_image(doc_id: str, n: int):
    state = docs.get(doc_id)
    if not state:
        raise HTTPException(404, "expired")
    path = os.path.join(state["dir"], "p%d.png" % n)
    if not os.path.exists(path):
        raise HTTPException(404, "no preview")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "private, max-age=600"})


jobs = {}


@app.get("/api/progress/{job}")
def get_progress(job: str):
    for k in [k for k, v in jobs.items() if time.time() - v["t"] > 600]:
        jobs.pop(k, None)
    return jobs.get(job) or {"done": None, "total": None}


@app.post("/api/ask")
async def ask(request: Request):
    _roll_day()
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Bad request.")
    doc_id, question = str(body.get("doc_id", "")), str(body.get("question", "")).strip()
    state = docs.get(doc_id)
    if not state:
        raise HTTPException(404, "This document has expired or never existed. Upload it again.")
    if state["status"] != "ready":
        raise HTTPException(409, "The document is still being read.")
    if not (3 <= len(question) <= MAX_Q_CHARS):
        raise HTTPException(400, "Ask a question of 3 to %d characters." % MAX_Q_CHARS)
    ip = _ip(request)
    if day["questions"][ip] >= IP_QUESTIONS:
        raise HTTPException(429, "Daily question limit reached for this demo. Come back tomorrow, or run it yourself: the code is open.")
    if day["spent"] >= DAY_BUDGET:
        raise HTTPException(429, "The demo has used its model budget for today. Come back tomorrow, or run it yourself: the code is open.")
    day["questions"][ip] += 1
    t0 = time.time()
    # 20.10.2026: progress for the page ("page 3 of 6 examined"), keyed by an id the page chooses; and the work runs in
    # a thread, so one visitor's question no longer blocks the server for everyone else while it is examined.
    job = str(body.get("job", ""))
    job = job if re.fullmatch(r"[a-f0-9]{16}", job) else None

    def progress(done, total):
        if job:
            jobs[job] = {"done": done, "total": total, "t": time.time()}
    result = await asyncio.to_thread(ask_mod.ask, state["doc"], question, None, progress)
    if job:
        jobs.pop(job, None)
    day["spent"] += result["cost_usd"]
    result["seconds"] = round(time.time() - t0, 1)
    result["model"] = llm.MODEL
    return JSONResponse(result)



# Devaland accessibility bar (own component, source /opt/devaland/shared/a11y), added 06.10.2026.
_A11Y = {"a11y.js": "text/javascript; charset=utf-8", "a11y.css": "text/css; charset=utf-8"}


@app.get("/a11y.js")
@app.get("/a11y.css")
def _a11y_asset(request: Request):
    name = request.url.path.lstrip("/")
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", name), media_type=_A11Y[name],
                        headers={"Cache-Control": "public, max-age=86400"})
