"""Results kept in the researcher's own Google Drive (D-071): results only, never videos.

Each finished check becomes one JSON file in the folder "ReelMetrics data" and one row in the Sheet
"ReelMetrics checks". Saving is on only when the token is set (`REELMETRICS_GOOGLE`, a JSON text made by
`python -m src.serve.drive_login`); without it nothing happens. The app asks only for `drive.file`, so it sees the files
it made and nothing else. A Drive failure is logged and never stops a result from showing.

Plain HTTP calls through `google-auth` (no Google client library needed).
"""
from __future__ import annotations

import json
import os
import shutil
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
DRIVE = "https://www.googleapis.com/drive/v3/files"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
SHEETS = "https://sheets.googleapis.com/v4/spreadsheets"
HEADER = ["saved (UTC)", "check id", "platform", "followers", "typical rate", "range low", "range high",
          "Instagram position (of 120)", "hashtags", "share talking", "share of frames with a face", "tips shown",
          "measured on", "speech setting", "seconds", "status"]
_lock = threading.Lock()


def _config() -> dict | None:
    raw = os.environ.get("REELMETRICS_GOOGLE")
    if not raw:
        return None
    try:
        c = json.loads(raw)
        return c if all(c.get(k) for k in ("client_id", "client_secret", "refresh_token", "folder_id", "sheet_id")) \
            else None
    except ValueError:
        return None


def enabled() -> bool:
    return _config() is not None


def _session(c: dict):
    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2.credentials import Credentials
    creds = Credentials(None, refresh_token=c["refresh_token"], client_id=c["client_id"],
                        client_secret=c["client_secret"], token_uri="https://oauth2.googleapis.com/token", scopes=SCOPES)
    return AuthorizedSession(creds)


# ------------------------------------------------------------------------------------------ what is kept
def public_copy(job: dict) -> dict:
    """The job without the caption text, the link, the file name or any folder path (D-071)."""
    j = json.loads(json.dumps(job, default=float))
    inp = j.get("inputs", {})
    for k in ("caption", "link", "upload_path"):
        inp.pop(k, None)
    if inp.get("upload_name") and not str(inp["upload_name"]).startswith("example:"):
        inp["upload_name"] = "uploaded file"
    j.pop("caption_used", None)
    j.pop("link_details", None)
    r = j.get("result") or {}
    (r.get("video") or {}).pop("work", None)
    return j


def sheet_row(job: dict) -> list:
    from src.serve import wording as W
    r = job.get("result") or {}
    b = r.get("base_rate") or {}
    d = r.get("diagnostics") or {}
    value = lambda k: (d.get(k) or {}).get("value")  # noqa: E731
    tips = "; ".join(t["head"] for t in W.worth_testing(r, job.get("platform"))) if r else ""
    return [datetime.now(timezone.utc).isoformat(timespec="seconds"), job["id"], job.get("platform"),
            b.get("followers"), b.get("rate_typical"), *(b.get("rate_80") or [None, None]),
            (r.get("instagram_score") or {}).get("higher_than_pct_of_120"),
            value("hashtag_count"), value("talk_dur_frac"), value("face_present_frac"), tips,
            r.get("measured_on"), r.get("speech_precision"), (r.get("timing") or {}).get("total_sec"),
            job.get("status")]


# ------------------------------------------------------------------------------------------ Drive and Sheet
def save(job: dict) -> None:
    """Upload the job's JSON and add its row; run in the background, failures only logged."""
    c = _config()
    if c is None:
        return
    try:
        with _lock:
            s = _session(c)
            body = json.dumps(public_copy(job), ensure_ascii=False, indent=1).encode("utf-8")
            meta = {"name": f"{job['id']}.json", "parents": [c["folder_id"]], "mimeType": "application/json"}
            boundary = "reelmetrics-boundary"
            payload = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{json.dumps(meta)}\r\n"
                       f"--{boundary}\r\nContent-Type: application/json\r\n\r\n").encode("utf-8") + body + \
                      f"\r\n--{boundary}--".encode("utf-8")
            s.post(UPLOAD, data=payload,
                   headers={"Content-Type": f"multipart/related; boundary={boundary}"}).raise_for_status()
            row = [("" if v is None else v) for v in sheet_row(job)]
            s.post(f"{SHEETS}/{c['sheet_id']}/values/A1:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS",
                   json={"values": [row]}).raise_for_status()
    except Exception:
        print("Drive: the result could not be saved (it is still shown on the page)")
        traceback.print_exc()


def save_in_background(job: dict) -> None:
    if enabled():
        threading.Thread(target=save, args=(job,), daemon=True).start()


def load(job_id: str) -> dict | None:
    """A check's saved JSON, for a result page the restarted server no longer has on its disk."""
    c = _config()
    if c is None or not job_id.replace("-", "").isalnum():
        return None
    try:
        s = _session(c)
        q = f"name = '{job_id}.json' and '{c['folder_id']}' in parents and trashed = false"
        files = s.get(DRIVE, params={"q": q, "fields": "files(id)"}).json().get("files", [])
        if not files:
            return None
        resp = s.get(f"{DRIVE}/{files[0]['id']}", params={"alt": "media"})
        resp.raise_for_status()
        return resp.json()
    except Exception:
        traceback.print_exc()
        return None


# ------------------------------------------------------------------------------------------ never videos
def delete_video_copies(job: dict, upload_path: str | None, video: Path | None, work: Path | None) -> None:
    """Remove the uploaded file, the stored copy and the frames and sound taken from it (D-071)."""
    for p in (upload_path, video):
        if p and Path(p).exists():
            Path(p).unlink(missing_ok=True)
    if upload_path:
        shutil.rmtree(Path(upload_path).parent, ignore_errors=True)
    if work:
        for sub in ("frames", "audio", "media"):
            shutil.rmtree(Path(work) / sub, ignore_errors=True)
