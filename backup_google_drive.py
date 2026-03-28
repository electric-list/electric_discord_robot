import asyncio
import importlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


class GoogleDriveBackupManager:
    def __init__(self):
        self._send_counter = 0
        self._lock = asyncio.Lock()
        self._upload_task: asyncio.Task | None = None
        self._pending_upload = False
        self._credentials = None
        self._services = {}

    @staticmethod
    def _is_enabled() -> bool:
        value = str(os.getenv("GDRIVE_BACKUP_ENABLED", "")).strip().lower()
        return value in {"1", "true", "yes", "on"}

    @staticmethod
    def _batch_size() -> int:
        raw = os.getenv("GDRIVE_BACKUP_EVERY_SENDS", "10")
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return 10
        return max(1, value)

    @staticmethod
    def _client_secret_path() -> str | None:
        raw = os.getenv("GDRIVE_CLIENT_SECRET_JSON_PATH")
        if raw is None:
            return None
        value = raw.strip()
        return value or None

    @staticmethod
    def _token_cache_path() -> Path:
        raw = os.getenv("GDRIVE_TOKEN_CACHE_PATH")
        if raw:
            return Path(raw.strip())
        return Path(".cache/gdrive_token.json")

    @staticmethod
    def _folder_id() -> str | None:
        raw = os.getenv("GDRIVE_BACKUP_FOLDER_ID")
        if raw is None:
            return None
        value = raw.strip()
        return value or None

    async def note_send_and_maybe_backup(self, file_path: Path):
        if not self._is_enabled():
            return

        batch_size = self._batch_size()
        should_schedule = False

        async with self._lock:
            self._send_counter += 1
            if self._send_counter >= batch_size:
                self._send_counter = 0
                self._pending_upload = True
                if self._upload_task is None or self._upload_task.done():
                    should_schedule = True

        if should_schedule:
            self._upload_task = asyncio.create_task(self._run_pending_uploads(file_path))

    async def _run_pending_uploads(self, file_path: Path):
        while True:
            async with self._lock:
                if not self._pending_upload:
                    break
                self._pending_upload = False

            try:
                await asyncio.to_thread(self._upload_snapshot_sync, file_path)
            except Exception as exc:
                # Keep this non-fatal for bot operation.
                print(f"[backup] Google Drive upload failed: {exc}")

    async def trigger_backup_now(self, file_path: Path, force: bool = False) -> tuple[bool, str]:
        if not force and not self._is_enabled():
            return False, "Google Drive backup is disabled. Set GDRIVE_BACKUP_ENABLED=true to enable scheduled backups."

        async with self._lock:
            try:
                message = await asyncio.to_thread(self._upload_snapshot_sync, file_path)
                return True, message
            except Exception as exc:
                return False, f"Google Drive upload failed: {exc}"

    def _upload_snapshot_sync(self, file_path: Path) -> str:
        if not file_path.exists():
            return "Backup skipped: progression_data.json does not exist yet."

        client_secret_path = self._client_secret_path()
        if not client_secret_path:
            return "Backup skipped: GDRIVE_CLIENT_SECRET_JSON_PATH is not set. See setup instructions in /backupnow command."

        if not Path(client_secret_path).exists():
            return f"Backup skipped: client_secret.json not found at {client_secret_path}."

        try:
            discovery_module = importlib.import_module("googleapiclient.discovery")
            http_module = importlib.import_module("googleapiclient.http")
            google_auth_oauthlib = importlib.import_module("google_auth_oauthlib.flow")
            google_auth = importlib.import_module("google.auth.transport.requests")
        except ImportError:
            return "Backup skipped: Google Drive dependencies are not installed. Run: pip install -r requirements.txt"

        build = discovery_module.build
        MediaFileUpload = http_module.MediaFileUpload
        InstalledAppFlow = google_auth_oauthlib.InstalledAppFlow
        Request = google_auth.Request

        scopes = ["https://www.googleapis.com/auth/drive.file"]
        token_cache = self._token_cache_path()

        # Try to load cached credentials.
        creds = None
        if token_cache.exists():
            try:
                with open(token_cache, "r", encoding="utf-8") as f:
                    token_data = json.load(f)
                    from google.oauth2.credentials import Credentials
                    creds = Credentials.from_authorized_user_info(token_data, scopes=scopes)
            except Exception:
                creds = None

        # If no valid credentials, perform OAuth 2.0 flow.
        if not creds:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, scopes)
                creds = flow.run_local_server(port=0, open_browser=True)
            except Exception as exc:
                return f"OAuth 2.0 authentication failed. Check your client_secret.json. Details: {exc}"

            # Cache the credentials for future use.
            token_cache.parent.mkdir(parents=True, exist_ok=True)
            with open(token_cache, "w", encoding="utf-8") as f:
                json.dump(json.loads(creds.to_json()), f, indent=2)

        # If credentials are expired, refresh them.
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Update cache with refreshed credentials.
                with open(token_cache, "w", encoding="utf-8") as f:
                    json.dump(json.loads(creds.to_json()), f, indent=2)
            except Exception as exc:
                return f"Failed to refresh credentials: {exc}"

        # Upload to Drive.
        try:
            service = build("drive", "v3", credentials=creds, cache_discovery=False)

            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
            file_name = f"progression_data_{timestamp}.json"
            metadata = {"name": file_name}

            folder_id = self._folder_id()
            if folder_id:
                metadata["parents"] = [folder_id]

            media = MediaFileUpload(str(file_path), mimetype="application/json", resumable=False)
            created = service.files().create(body=metadata, media_body=media, fields="id,name,webViewLink").execute()
            
            result = f"Uploaded: {created.get('name')} (ID: {created.get('id')})\nView: {created.get('webViewLink')}"
            print(f"[backup] {result}")
            return result
        except Exception as exc:
            return f"Google Drive upload failed: {exc}"


manager = GoogleDriveBackupManager()
