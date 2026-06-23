"""Microsoft 365 / SharePoint integration via Microsoft Graph (MSAL device code).

Optional. Enables pulling the master deck and example designs straight from
SharePoint/OneDrive share links. Uses the device-code flow so no client secret is
needed — register a public client app in Entra ID with delegated Files.Read.All and
Sites.Read.All, then set GRAPH_CLIENT_ID / GRAPH_TENANT_ID.

If MSAL or config is missing, every method degrades gracefully and the UI falls back
to local file uploads.
"""
from __future__ import annotations

import base64
import os
import threading
from pathlib import Path
from typing import Callable, Dict, Optional

import requests

GRAPH = "https://graph.microsoft.com/v1.0"


def _encode_share_url(url: str) -> str:
    """Graph 'shares' encoding: base64url of the URL, 'u!' prefix, no padding."""
    b64 = base64.urlsafe_b64encode(url.encode("utf-8")).decode("utf-8")
    return "u!" + b64.rstrip("=")


class GraphClient:
    def __init__(self) -> None:
        self.client_id = os.environ.get("GRAPH_CLIENT_ID", "").strip()
        self.tenant_id = os.environ.get("GRAPH_TENANT_ID", "common").strip() or "common"
        self.scopes = (
            os.environ.get("GRAPH_SCOPES", "Files.Read.All Sites.Read.All").split()
        )
        self._token: Optional[str] = None
        self._app = None
        self._lock = threading.Lock()
        self._flow: Optional[Dict] = None

    @property
    def configured(self) -> bool:
        return bool(self.client_id)

    def _ensure_app(self):
        if self._app is not None:
            return self._app
        try:
            import msal  # imported lazily so the server runs without it
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("msal not installed; pip install msal") from exc
        authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self._app = msal.PublicClientApplication(self.client_id, authority=authority)
        return self._app

    # ── device-code auth ──────────────────────────────────────────────────────
    def begin_device_login(self) -> Dict:
        if not self.configured:
            raise RuntimeError("GRAPH_CLIENT_ID not set.")
        app = self._ensure_app()
        flow = app.initiate_device_flow(scopes=self.scopes)
        if "user_code" not in flow:
            raise RuntimeError(f"Failed to start device flow: {flow}")
        with self._lock:
            self._flow = flow
        return {
            "verification_uri": flow.get("verification_uri"),
            "user_code": flow.get("user_code"),
            "message": flow.get("message"),
            "expires_in": flow.get("expires_in"),
        }

    def complete_device_login(self) -> bool:
        """Blocking-ish: poll once for token using the pending flow."""
        with self._lock:
            flow = self._flow
        if not flow:
            return self._token is not None
        app = self._ensure_app()
        result = app.acquire_token_by_device_flow(flow, exit_condition=lambda f: True)
        if "access_token" in result:
            self._token = result["access_token"]
            with self._lock:
                self._flow = None
            return True
        return False

    def _silent_token(self) -> Optional[str]:
        if self._token:
            return self._token
        app = self._ensure_app()
        accounts = app.get_accounts()
        if accounts:
            res = app.acquire_token_silent(self.scopes, account=accounts[0])
            if res and "access_token" in res:
                self._token = res["access_token"]
        return self._token

    @property
    def signed_in(self) -> bool:
        return self._silent_token() is not None

    # ── file access ───────────────────────────────────────────────────────────
    def get_share_metadata(self, share_url: str) -> Dict:
        token = self._silent_token()
        if not token:
            raise RuntimeError("Not signed in to Microsoft 365.")
        share_id = _encode_share_url(share_url)
        r = requests.get(
            f"{GRAPH}/shares/{share_id}/driveItem",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

    def download_share(self, share_url: str, dest: Path) -> Path:
        token = self._silent_token()
        if not token:
            raise RuntimeError("Not signed in to Microsoft 365.")
        share_id = _encode_share_url(share_url)
        r = requests.get(
            f"{GRAPH}/shares/{share_id}/driveItem/content",
            headers={"Authorization": f"Bearer {token}"},
            timeout=120,
            stream=True,
        )
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 16):
                fh.write(chunk)
        return dest


graph = GraphClient()
