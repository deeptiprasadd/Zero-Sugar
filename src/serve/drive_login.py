"""One-time set-up of the Drive storage of D-071, run on the researcher's computer:

    python -m src.serve.drive_login secrets/<the OAuth client file>.json

Opens a Google sign-in in the browser (her own account), asks only for the `drive.file` permission, creates the
folder "ReelMetrics data" and the Sheet "ReelMetrics checks" in her Drive, and writes the token to
`secrets/reelmetrics_google.json` (gitignored). It prints the text to paste into the Streamlit app's Secrets box.
Nothing here goes to GitHub.
"""
from __future__ import annotations

import base64
import hashlib
import http.server
import json
import secrets
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src import config  # noqa: E402
from src.serve.drive_store import DRIVE, HEADER, SCOPES, SHEETS, _session  # noqa: E402

OUT = config.ROOT / "secrets" / "reelmetrics_google.json"


def sign_in(client: dict) -> str:
    """The loopback sign-in for installed apps, with PKCE; returns the refresh token."""
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state, got = secrets.token_urlsafe(16), {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [None])[0] == state:
                got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<p>Signed in. You can close this tab and go back to the terminal.</p>".encode())

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    redirect = f"http://127.0.0.1:{server.server_port}"
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client["client_id"], "redirect_uri": redirect, "response_type": "code",
        "scope": " ".join(SCOPES), "access_type": "offline", "prompt": "consent", "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256"})
    print("A Google sign-in opens in your browser. If it does not, open this address:\n" + url)
    threading.Thread(target=server.handle_request, daemon=True).start()
    webbrowser.open(url)
    while "code" not in got and "error" not in got:
        threading.Event().wait(0.5)
    server.server_close()
    if "error" in got:
        raise SystemExit(f"Sign-in was not completed: {got['error']}")
    tok = requests.post("https://oauth2.googleapis.com/token", data={
        "code": got["code"], "client_id": client["client_id"], "client_secret": client["client_secret"],
        "redirect_uri": redirect, "grant_type": "authorization_code", "code_verifier": verifier}, timeout=30)
    tok.raise_for_status()
    if "refresh_token" not in tok.json():
        raise SystemExit("Google returned no long-lived token; remove the app's access in your Google account and retry")
    return tok.json()["refresh_token"]


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    raw = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    client = raw.get("installed") or raw.get("web") or raw
    cfg = {"client_id": client["client_id"], "client_secret": client["client_secret"]}
    cfg["refresh_token"] = sign_in(client)
    s = _session({**cfg, "folder_id": "-", "sheet_id": "-"})
    folder = s.post(DRIVE, json={"name": "ReelMetrics data", "mimeType": "application/vnd.google-apps.folder"})
    folder.raise_for_status()
    cfg["folder_id"] = folder.json()["id"]
    sheet = s.post(DRIVE, json={"name": "ReelMetrics checks", "mimeType": "application/vnd.google-apps.spreadsheet",
                                "parents": [cfg["folder_id"]]})
    sheet.raise_for_status()
    cfg["sheet_id"] = sheet.json()["id"]
    s.put(f"{SHEETS}/{cfg['sheet_id']}/values/A1?valueInputOption=RAW", json={"values": [HEADER]}).raise_for_status()
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    print(f"\nDone. Folder 'ReelMetrics data' and Sheet 'ReelMetrics checks' are in your Drive.\n"
          f"Token saved to {OUT.relative_to(config.ROOT)} (kept off GitHub).\n\n"
          "Paste these lines into the Streamlit app's Settings > Secrets box:\n\n"
          f"REELMETRICS_GOOGLE = '''{json.dumps(cfg)}'''\n")


if __name__ == "__main__":
    main()
