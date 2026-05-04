#!/usr/bin/env python3
"""Pull a single file from Google Drive by file ID, atomically replacing the local copy."""
import argparse
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
SCRIPT_DIR = Path(__file__).resolve().parent
CREDENTIALS_PATH = SCRIPT_DIR / "credentials.json"
TOKEN_PATH = SCRIPT_DIR / "token.json"


def get_service():
    """Return an authenticated Drive v3 service. Triggers browser OAuth on first run."""
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                sys.exit(f"Missing {CREDENTIALS_PATH}. See SETUP.md.")
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())
    return build("drive", "v3", credentials=creds)


def pull_file(service, file_id: str, dest: Path) -> dict:
    """Download file_id to dest atomically (write to .tmp, then rename). Returns Drive metadata."""
    meta = service.files().get(
        fileId=file_id, fields="name, modifiedTime, size, mimeType"
    ).execute()
    print(f"{meta['name']}  (modified {meta['modifiedTime']})  ->  {dest}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    request = service.files().get_media(fileId=file_id)
    with tmp.open("wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"  {int(status.progress() * 100)}%", end="\r", flush=True)
    tmp.replace(dest)
    print("  done")
    return meta


def main():
    parser = argparse.ArgumentParser(description="Pull one file from Google Drive by ID.")
    parser.add_argument("file_id", help="Google Drive file ID (the string after /d/ in the share URL)")
    parser.add_argument("dest", help="Local destination path (will overwrite)")
    args = parser.parse_args()

    service = get_service()
    pull_file(service, args.file_id, Path(args.dest))


if __name__ == "__main__":
    main()
