from fastapi import APIRouter, File, UploadFile, Form
from app.core.activity_logger import ActivityLogger
from app.core.pii_scrubber import PIIScrubber
import asyncio
import os
import httpx
import json

LLM_GUARD_URL = os.getenv("LLM_GUARD_URL", "http://localhost:8001/api/v1/scan")
FILE_SANDBOX_URL = os.getenv("FILE_SANDBOX_URL", "http://localhost:8003/analyze")

# Document extensions whose text content will be deep-scanned by the text analyzer
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".html", ".htm", ".doc", ".txt", ".rtf"}

# Text-guard check types to run on extracted document content (run in parallel)
TEXT_ANALYSIS_CHECKS = [
    ("phishing",     "🔗 Phishing / Social Engineering"),
    ("credentials",  "🔑 Credential / Secret Leak"),
    ("injection",    "💉 Prompt Injection Attempt"),
]

router = APIRouter()


async def _run_text_check(
    client: httpx.AsyncClient,
    text: str,
    check_type: str,
    label: str,
) -> tuple[int, list[str]]:
    """
    Send extracted document text to LLM Guard for one check_type.
    Returns (risk_score, alerts_with_label).
    """
    try:
        res = await client.post(
            LLM_GUARD_URL,
            json={"text": text, "check_type": check_type},
        )
        if res.status_code == 200:
            data = res.json()
            score = data.get("risk_score", 0)
            raw_alerts = data.get("alerts", [])
            labeled_alerts = []
            if raw_alerts:
                labeled_alerts.append(f"{label}:")
                labeled_alerts.extend(raw_alerts)
            return score, labeled_alerts
        else:
            return 0, [f"LLM Guard Error ({check_type}): HTTP {res.status_code}"]
    except Exception as exc:
        return 0, [f"LLM Guard Error ({check_type}): {exc}"]


@router.post("/scan-file")
async def scan_file(file: UploadFile = File(...), enable_network: bool = Form(False)):
    """
    Attachment Verification (Pharming / Malware / Content Threats)

    Pipeline
    ────────
    Step 1  Upload file → FileSandbox (Docker).
            For PDF / DOCX / HTML the sandbox reads the document text
            BEFORE running it in the container, and returns it as
            'extracted_text' in the response.

    Step 2  Sandbox behavioral log → LLM Guard (check_type='sandbox_log').
            Analyses file-system accesses, spawned processes, network calls.

    Step 3  If extracted_text is present, pass it through THREE parallel
            text-analyzer checks via LLM Guard:
              • phishing    — deceptive links, fake urgency, spoofed domains
              • credentials — API keys, passwords, tokens hidden in the doc
              • injection   — prompt-injection payloads embedded in content
            All three run concurrently (asyncio.gather) to save time.

    Step 4  Merge: final risk_score = max(all scores).
            Alerts from every pass are combined and labeled.
    """
    risk_score = 0
    alerts: list[str] = []
    extracted_text: str | None = None
    text_analysis_results: list[dict] = []
    file_ext = os.path.splitext(file.filename)[1].lower()  # Always set — needed by logger

    try:
        content = await file.read()

        async with httpx.AsyncClient(timeout=60.0) as client:

            # ── Step 1: FileSandbox ─────────────────────────────────────────
            sandbox_res = await client.post(
                FILE_SANDBOX_URL,
                data={"enable_network": str(enable_network).lower()},
                files={"file": (file.filename, content, file.content_type)},
            )

            if sandbox_res.status_code != 200:
                alerts.append(f"Sandbox Error: HTTP {sandbox_res.status_code}")
            else:
                sandbox_log = sandbox_res.json()
                extracted_text = sandbox_log.get("extracted_text") or None

                # ── Step 2: Sandbox behavioral log → LLM Guard ─────────────
                behavioral_log = {
                    k: v for k, v in sandbox_log.items() if k != "extracted_text"
                }
                llm_res = await client.post(
                    LLM_GUARD_URL,
                    json={"text": json.dumps(behavioral_log, indent=2), "check_type": "sandbox_log"},
                )

                if llm_res.status_code == 200:
                    llm_data = llm_res.json()
                    sandbox_risk = llm_data.get("risk_score", 0)
                    risk_score = max(risk_score, sandbox_risk)
                    sandbox_alerts = llm_data.get("alerts", [])
                    if sandbox_alerts:
                        alerts.append("📦 Sandbox Behavioral Analysis:")
                        alerts.extend(sandbox_alerts)
                else:
                    alerts.append(f"LLM Guard Error (sandbox_log): HTTP {llm_res.status_code}")
                    risk_score = max(
                        risk_score, min(sandbox_log.get("risk_score", 0) * 10, 100)
                    )

                # ── Step 3: Text Analyzer — parallel content checks ─────────
                if extracted_text and file_ext in DOCUMENT_EXTENSIONS:
                    # PII-scrub for safe logging only; full text goes to LLM
                    scrubbed_preview = PIIScrubber.scrub(extracted_text[:200])
                    print(
                        f"[File Guard] Running text analysis on "
                        f"'{file.filename}' — preview: {scrubbed_preview}..."
                    )

                    # Build a consistent prompt prefix for all checks
                    doc_prompt = (
                        f"[Source document: {file.filename} ({file_ext.upper()})]\n\n"
                        f"--- Extracted Text ---\n{extracted_text}"
                    )

                    # Fire all check types concurrently
                    tasks = [
                        _run_text_check(client, doc_prompt, check_type, label)
                        for check_type, label in TEXT_ANALYSIS_CHECKS
                    ]
                    results = await asyncio.gather(*tasks)

                    for (check_type, label), (check_score, check_alerts) in zip(
                        TEXT_ANALYSIS_CHECKS, results
                    ):
                        risk_score = max(risk_score, check_score)
                        alerts.extend(check_alerts)
                        text_analysis_results.append(
                            {
                                "check": check_type,
                                "label": label,
                                "risk_score": check_score,
                                "alerts": check_alerts,
                            }
                        )

                    # Summary line if everything looked clean
                    if not any(r["alerts"] for r in text_analysis_results):
                        alerts.append(
                            f"📄 Document text scanned ({file_ext.upper()}) — "
                            f"no threats found across {len(TEXT_ANALYSIS_CHECKS)} checks."
                        )

    except Exception as exc:
        print(f"[File Guard] Pipeline error: {exc}")
        alerts.append("Failed to reach isolated sandbox or LLM environment.")

    final_score = min(risk_score, 100)

    ActivityLogger.log_activity(
        "File Guard",
        file_ext.lstrip(".") or "file",
        final_score,
        alerts,
    )

    return {
        "filename": file.filename,
        "risk_score": final_score,
        "alerts": alerts,
        "is_safe": final_score < 50,
        "content_scanned": extracted_text is not None,
        "text_analysis": text_analysis_results,   # per-check breakdown
    }

