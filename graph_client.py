"""
graph_client.py
---------------
Microsoft Graph client for the COI automation.

Auth: client credentials flow (app-only). The Azure app registration must
have Application permissions Mail.ReadWrite + Mail.Send with admin consent.
All mail operations run against /users/{COI_MAILBOX}/... (app-only tokens
can't use /me/).
"""

import time

import requests

import config

TOKEN_URL = (
    f"https://login.microsoftonline.com/{config.AZURE_TENANT_ID}/oauth2/v2.0/token"
)
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 3


class GraphError(Exception):
    """Raised when a Graph call fails after retries."""


class GraphClient:
    def __init__(self, mailbox=None):
        self.mailbox = mailbox or config.COI_MAILBOX
        self._token = None
        self._token_expires_at = 0

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------
    def _get_token(self):
        if self._token and time.time() < self._token_expires_at - 120:
            return self._token
        resp = requests.post(
            TOKEN_URL,
            data={
                "client_id": config.AZURE_CLIENT_ID,
                "client_secret": config.AZURE_CLIENT_SECRET,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            },
            timeout=30,
        )
        if resp.status_code != 200:
            raise GraphError(
                f"Token request failed: HTTP {resp.status_code}: {resp.text[:400]}"
            )
        body = resp.json()
        self._token = body["access_token"]
        self._token_expires_at = time.time() + int(body.get("expires_in", 3600))
        return self._token

    def _request(self, method, url, **kwargs):
        """HTTP with auth + retry on transient failures. Returns Response."""
        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            headers = kwargs.pop("headers", {}) or {}
            headers["Authorization"] = f"Bearer {self._get_token()}"
            try:
                resp = requests.request(
                    method, url, headers=headers, timeout=kwargs.pop("timeout", 60),
                    **kwargs,
                )
            except requests.RequestException as e:
                last_error = f"Request error: {e}"
                if attempt < MAX_RETRIES:
                    time.sleep(2 ** attempt)
                    continue
                raise GraphError(last_error)

            if resp.status_code == 401 and attempt < MAX_RETRIES:
                # Token may have been revoked/expired early — force refresh
                self._token = None
                continue

            if resp.status_code in RETRYABLE_STATUS and attempt < MAX_RETRIES:
                retry_after = resp.headers.get("Retry-After")
                wait = int(retry_after) if retry_after else 2 ** attempt
                last_error = f"HTTP {resp.status_code}: {resp.text[:300]}"
                time.sleep(min(wait, 120))
                continue

            return resp
        raise GraphError(last_error or "Max retries exceeded")

    def _mb(self, path):
        return f"{GRAPH_BASE}/users/{self.mailbox}{path}"

    # ------------------------------------------------------------------
    # Reading mail
    # ------------------------------------------------------------------
    def list_inbox_since(self, iso_datetime, top=25):
        """New inbox messages received strictly after iso_datetime (UTC ISO),
        oldest first."""
        resp = self._request(
            "GET",
            self._mb("/mailFolders/inbox/messages"),
            params={
                "$filter": f"receivedDateTime gt {iso_datetime}",
                "$orderby": "receivedDateTime asc",
                "$top": top,
            },
        )
        if resp.status_code != 200:
            raise GraphError(f"list_inbox_since failed: {resp.status_code}: {resp.text[:400]}")
        return resp.json().get("value", [])

    def search_by_conversation(self, conv_id):
        if not conv_id:
            return []
        resp = self._request(
            "GET",
            self._mb("/messages"),
            params={
                "$filter": f"conversationId eq '{conv_id}'",
                "$orderby": "conversationId,sentDateTime asc",
                "$top": 50,
            },
        )
        if resp.status_code != 200:
            return []
        return resp.json().get("value", [])

    def get_message_headers(self, msg_id):
        if not msg_id:
            return []
        resp = self._request(
            "GET",
            self._mb(f"/messages/{msg_id}"),
            params={"$select": "internetMessageHeaders,internetMessageId"},
        )
        if resp.status_code != 200:
            return []
        return resp.json().get("internetMessageHeaders", []) or []

    def find_message_by_internet_id(self, internet_msg_id):
        if not internet_msg_id:
            return None
        resp = self._request(
            "GET",
            self._mb("/messages"),
            params={
                "$filter": f"internetMessageId eq '{internet_msg_id}'",
                "$top": 1,
            },
        )
        if resp.status_code != 200:
            return None
        results = resp.json().get("value", [])
        return results[0] if results else None

    def list_attachments(self, msg_id):
        resp = self._request("GET", self._mb(f"/messages/{msg_id}/attachments"))
        if resp.status_code != 200:
            raise GraphError(
                f"list_attachments failed: {resp.status_code}: {resp.text[:400]}"
            )
        return resp.json().get("value", [])

    def mark_read(self, msg_id):
        resp = self._request(
            "PATCH",
            self._mb(f"/messages/{msg_id}"),
            json={"isRead": True},
        )
        return resp.status_code == 200

    # ------------------------------------------------------------------
    # Sending mail
    # ------------------------------------------------------------------
    def reply_to_message(self, msg_id, message_obj):
        """POST /messages/{id}/reply — message_obj is the Graph 'message'
        payload (body, toRecipients, ccRecipients, attachments)."""
        resp = self._request(
            "POST",
            self._mb(f"/messages/{msg_id}/reply"),
            json={"message": message_obj},
            timeout=120,
        )
        return resp.status_code in (200, 202), resp

    def send_mail(self, message_obj):
        """POST /sendMail — brand new email (not threaded)."""
        resp = self._request(
            "POST",
            self._mb("/sendMail"),
            json={"message": message_obj, "saveToSentItems": "true"},
            timeout=120,
        )
        return resp.status_code in (200, 202), resp
