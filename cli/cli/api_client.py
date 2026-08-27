"""HTTP client for the Digen user-facing skills API + auth endpoints.

Two response conventions are involved:

- User auth endpoints (``/v1/user/*``): ``{"errCode": 0, "errMsg": "success", "data": {...}}``.
  ``errCode`` is authoritative; HTTP status is usually 200 even on failure.
- Skills API (``{AGENT_GATEWAY_PREFIX}/api/v1/skills/*``): the gateway
  forwards the upstream body as-is. Success is the concrete payload (e.g.
  ``builtin`` / ``space`` at the top level), never
    ``{"errCode": 0, "errMsg": "success", "data": ...}``.
  HTTP errors use FastAPI ``{"detail": "..."}``. If the gateway itself
  rejects the request (auth/session) before proxying, it still returns
  ``{"errCode": ..., "errMsg": "..."}``.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx

# Auth stays on the API host root. Skills live on the agent service, which
# the gateway exposes at /v2/gateway/agent (not /api/v1/skills on the host).
AGENT_GATEWAY_PREFIX = "/v2/gateway/agent"
SKILLS_API_PREFIX = f"{AGENT_GATEWAY_PREFIX}/api/v1/skills"

_HTTP_LOG_BODY_LIMIT = 4096
_SKIP_REQUEST_HEADERS = frozenset(
    {"host", "accept-encoding", "connection", "user-agent", "content-length"}
)
_DEFAULT_TOKEN_TTL_SECONDS = 30 * 24 * 3600
_SENSITIVE_HEADERS = frozenset({"authorization", "cookie", "digen-token", "digen-sessionid"})


def parse_digen_token(value: str) -> Tuple[str, Optional[int], Optional[int]]:
    """Split ``{token}:{userId}:{unix}`` if that is the shape; else ``(value, None, None)``."""
    parts = value.split(":")
    if len(parts) >= 3 and parts[-1].isdigit() and parts[-2].isdigit():
        return ":".join(parts[:-2]), int(parts[-2]), int(parts[-1])
    return value, None, None


def compose_digen_token(
    token: str,
    user_id: Optional[int] = None,
    expires_at: Optional[int] = None,
) -> str:
    """Build the ``digen-token`` header: ``{token}:{userId}:{unixExpiry}``."""
    raw, parsed_uid, parsed_exp = parse_digen_token(token)
    uid = user_id if user_id is not None else parsed_uid
    exp = expires_at if expires_at is not None else parsed_exp
    if uid is None:
        uid = 0
    if exp is None:
        exp = int(time.time()) + _DEFAULT_TOKEN_TTL_SECONDS
    return f"{raw}:{uid}:{exp}"


def _mask_header(name: str, value: str) -> str:
    lowered = name.lower()
    if lowered == "digen-token":
        raw, uid, exp = parse_digen_token(value)
        shown = f"{raw[:8]}..." if len(raw) > 8 else raw
        if uid is not None and exp is not None:
            return f"{shown}:{uid}:{exp}"
        return shown
    if lowered == "authorization" and value.lower().startswith("bearer "):
        token = value[7:]
        shown = f"{token[:8]}..." if len(token) > 8 else token
        return f"Bearer {shown}"
    if lowered in _SENSITIVE_HEADERS and len(value) > 8:
        return value[:8] + "..."
    return value


def format_http_trace(resp: httpx.Response, *, body_limit: int = _HTTP_LOG_BODY_LIMIT) -> str:
    """One request/response dump for skills calls (token masked, body truncated)."""
    req = resp.request
    lines = [f">>> {req.method} {req.url}"]
    for key, value in req.headers.items():
        if key.lower() in _SKIP_REQUEST_HEADERS:
            continue
        lines.append(f"    {key}: {_mask_header(key, value)}")
    lines.append(f"<<< HTTP {resp.status_code}")
    body = resp.text
    if len(body) > body_limit:
        body = body[:body_limit] + f"... ({len(resp.content)} bytes)"
    if body:
        for line in body.splitlines() or [body]:
            lines.append(f"    {line}")
    return "\n".join(lines)


class APIError(Exception):
    def __init__(self, status_code: int, detail: str, err_code: Optional[int] = None):
        self.status_code = status_code
        self.detail = detail
        self.err_code = err_code
        super().__init__(f"HTTP {status_code}: {detail}")


class DigenAPIClient:
    """Wraps Digen user auth endpoints (/v1/user/*) and the user skills API (gateway + /api/v1/skills)."""

    def __init__(
        self,
        base_url: str,
        token: Optional[str] = None,
        user_id: Optional[int] = None,
        timeout: float = 30.0,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        http_log: Optional[Callable[[str], None]] = None,
        session_id: Optional[str] = None,
        language: str = "en",
        token_expires_at: Optional[int] = None,
        referer: Optional[str] = None,
    ):
        headers: Dict[str, str] = {
            "Accept": "application/json, text/plain, */*",
            "digen-language": language or "en",
        }
        if token:
            headers["digen-token"] = compose_digen_token(token, user_id, token_expires_at)
        if session_id:
            headers["digen-sessionid"] = session_id
        if referer:
            headers["Referer"] = referer.rstrip("/") + "/"
        self._http_log = http_log
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=httpx.Timeout(timeout, read=300.0),
            transport=transport,
        )

    async def close(self):
        await self._client.aclose()

    @staticmethod
    def _skills_path(*parts: object) -> str:
        extra = "/".join(str(p).strip("/") for p in parts if p is not None and str(p) != "")
        if extra:
            return f"{SKILLS_API_PREFIX}/{extra}"
        return SKILLS_API_PREFIX

    async def _skills_request(self, method: str, *path_parts: object, **kwargs) -> httpx.Response:
        resp = await self._client.request(method, self._skills_path(*path_parts), **kwargs)
        if self._http_log is not None:
            self._http_log(format_http_trace(resp))
        return resp

    def _raise_for_status(self, resp: httpx.Response):
        if resp.status_code >= 400:
            detail = resp.text
            try:
                payload = resp.json()
            except Exception:
                payload = None
            if isinstance(payload, dict):
                # FastAPI uses ``detail``; some gateway errors use ``message``
                # with ``detail: null`` (json.loads → None, which is truthy-false).
                detail = (
                    payload.get("detail")
                    or payload.get("message")
                    or payload.get("errMsg")
                    or detail
                )
            raise APIError(resp.status_code, str(detail) if detail is not None else resp.text)

    def _skills_json(self, resp: httpx.Response) -> Any:
        self._raise_for_status(resp)
        if resp.status_code == 204 or not resp.content:
            return None
        try:
            payload = resp.json()
        except Exception:
            raise APIError(resp.status_code, resp.text or "invalid JSON")
        # Gateway auth failures never reach the agent, so they still come back
        # as {errCode, errMsg}. Success is never that envelope.
        if isinstance(payload, dict):
            err_code = payload.get("errCode")
            if err_code:
                msg = payload.get("errMsg") or payload.get("detail") or "request failed"
                raise APIError(
                    resp.status_code,
                    f"{msg} (errCode={err_code})",
                    err_code=err_code,
                )
        return payload

    def _unwrap_auth_response(self, resp: httpx.Response) -> Dict[str, Any]:
        """Parse a Digen auth-style response, raising APIError on errCode != 0."""
        try:
            payload = resp.json()
        except Exception:
            self._raise_for_status(resp)
            raise APIError(resp.status_code, resp.text)

        err_code = payload.get("errCode")
        if err_code:
            msg = payload.get("errMsg") or "request failed"
            raise APIError(resp.status_code, f"{msg} (errCode={err_code})", err_code=err_code)

        if resp.status_code >= 400:
            self._raise_for_status(resp)

        return payload.get("data") or {}

    # ==================== Auth ====================

    async def login(self, email: str, password: str) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"email": email, "password": password}
        resp = await self._client.post("/v1/user/login", json=payload)
        return self._unwrap_auth_response(resp)

    async def google_exchange(
        self,
        *,
        code: Optional[str] = None,
        client_id: Optional[str] = None,
        credential: Optional[str] = None,
        redirect_url: str,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"redirectURL": redirect_url}
        if code:
            payload["code"] = code
        if client_id:
            payload["clientId"] = client_id
        if credential:
            payload["credenTial"] = credential
        resp = await self._client.post("/v1/user/google/exchange", json=payload)
        return self._unwrap_auth_response(resp)

    async def apple_exchange(
        self,
        *,
        code: str,
        redirect_url: str,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"code": code, "redirectURL": redirect_url}
        resp = await self._client.post("/v1/user/apple/exchange", json=payload)
        return self._unwrap_auth_response(resp)

    # ==================== My skill space ====================

    async def list_my_skills(self) -> Dict[str, Any]:
        resp = await self._skills_request("GET")
        return self._skills_json(resp) or {}

    async def get_skill(self, skill_id: int) -> Dict[str, Any]:
        resp = await self._skills_request("GET", skill_id)
        return self._skills_json(resp)

    async def get_skill_by_slug(self, slug: str) -> Dict[str, Any]:
        resp = await self._skills_request("GET", "by-slug", slug)
        return self._skills_json(resp)

    async def create_skill(
        self,
        *,
        display_name: str,
        description: str = "",
        body: str = "",
        allowed_tools: Optional[List[str]] = None,
        visibility: str = "private",
    ) -> Dict[str, Any]:
        resp = await self._skills_request(
            "POST",
            json={
                "display_name": display_name,
                "description": description,
                "body": body,
                "allowed_tools": allowed_tools or [],
                "visibility": visibility,
            },
        )
        return self._skills_json(resp)

    async def import_skill_zip(self, zip_bytes: bytes, filename: str = "skill.zip", visibility: str = "private") -> Dict[str, Any]:
        """Create a new skill from a zip archive (POST /import-zip)."""
        files = {"file": (filename, zip_bytes, "application/zip")}
        data = {"visibility": visibility}
        resp = await self._skills_request("POST", "import-zip", files=files, data=data)
        return self._skills_json(resp)

    async def update_skill_zip(self, skill_id: int, zip_bytes: bytes, filename: str = "skill.zip") -> Dict[str, Any]:
        """Overwrite a skill's draft from a zip archive (PUT /{id}/import-zip). Draft only."""
        files = {"file": (filename, zip_bytes, "application/zip")}
        resp = await self._skills_request("PUT", skill_id, "import-zip", files=files)
        return self._skills_json(resp)

    async def export_skill_zip(self, skill_id: int) -> bytes:
        resp = await self._skills_request("GET", skill_id, "export", follow_redirects=True)
        self._raise_for_status(resp)
        return resp.content

    async def delete_skill(self, skill_id: int) -> None:
        resp = await self._skills_request("DELETE", skill_id)
        self._raise_for_status(resp)

    async def set_visibility(self, skill_id: int, visibility: str) -> Dict[str, Any]:
        resp = await self._skills_request("PUT", skill_id, "visibility", json={"visibility": visibility})
        return self._skills_json(resp)

    async def cancel_review(self, skill_id: int) -> Dict[str, Any]:
        resp = await self._skills_request("POST", skill_id, "cancel-review")
        return self._skills_json(resp)

    async def set_content_visibility(self, skill_id: int, content_visibility: str) -> Dict[str, Any]:
        resp = await self._skills_request(
            "PUT",
            skill_id,
            "content-visibility",
            json={"content_visibility": content_visibility},
        )
        return self._skills_json(resp)

    async def toggle_skill(self, skill_id: int, enabled: bool) -> Dict[str, Any]:
        resp = await self._skills_request("PUT", skill_id, "toggle", json={"enabled": enabled})
        return self._skills_json(resp)

    # ==================== Market ====================

    async def list_market_categories(self) -> Dict[str, Any]:
        resp = await self._skills_request("GET", "market", "categories")
        return self._skills_json(resp)

    async def list_market(
        self,
        *,
        tab: str = "discover",
        category: Optional[str] = None,
        q: Optional[str] = None,
        sort: str = "featured",
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"tab": tab, "sort": sort, "limit": limit, "offset": offset}
        if category:
            params["category"] = category
        if q:
            params["q"] = q
        resp = await self._skills_request("GET", "market", params=params)
        return self._skills_json(resp)

    async def install_skill(self, skill_id: int) -> Dict[str, Any]:
        resp = await self._skills_request("POST", skill_id, "install")
        return self._skills_json(resp)

    async def uninstall_skill(self, skill_id: int) -> None:
        resp = await self._skills_request("DELETE", skill_id, "install")
        self._raise_for_status(resp)

    async def fork_skill(self, skill_id: int) -> Dict[str, Any]:
        resp = await self._skills_request("POST", skill_id, "fork")
        return self._skills_json(resp)

    async def favorite_skill(self, skill_id: int) -> Dict[str, Any]:
        resp = await self._skills_request("POST", skill_id, "favorite")
        return self._skills_json(resp)

    async def unfavorite_skill(self, skill_id: int) -> None:
        resp = await self._skills_request("DELETE", skill_id, "favorite")
        self._raise_for_status(resp)
