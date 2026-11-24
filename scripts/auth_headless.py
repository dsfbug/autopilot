"""Headless YouTube OAuth helper for machines without a local browser.

Run:  python scripts/auth_headless.py
1. Prints a Google authorization URL.
2. Open it in ANY browser signed into the YouTube channel's Google account.
3. After consent, the browser lands on a localhost page that fails to load.
   Copy the full URL from the address bar and paste it here.
4. The token is saved to .clipper_token.json (same file the CLI uses).

Requires client_secrets.json (OAuth client of type "Desktop app") in the
project root, exactly like the normal `python -m clipper auth` flow.
"""

import re
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]
REDIRECT_URI = "http://localhost:8421/"

root = Path(__file__).resolve().parent.parent
secrets = root / "client_secrets.json"
if not secrets.exists():
    raise SystemExit("client_secrets.json not found in project root. See README setup section.")

flow = InstalledAppFlow.from_client_secrets_file(str(secrets), SCOPES)
flow.redirect_uri = REDIRECT_URI
auth_url, _ = flow.authorization_url(access_type="offline", include_granted_scopes="true", prompt="consent")
print("\nOpen this URL in a browser signed into the channel's Google account:\n")
print(auth_url)
print("\nAfter approving, the browser will fail to load a localhost page.")
print("Copy the FULL address-bar URL and paste it here.\n")
redirected = input("Pasted redirect URL: ").strip()

m = re.search(r"[?&]code=([^&]+)", redirected)
if not m:
    raise SystemExit("No ?code= found in that URL. Make sure you copied the full address after approving.")
flow.fetch_token(code=m.group(1))
(root / ".clipper_token.json").write_text(flow.credentials.to_json())
print(f"\nToken saved to {root / '.clipper_token.json'} - you're authenticated.")
