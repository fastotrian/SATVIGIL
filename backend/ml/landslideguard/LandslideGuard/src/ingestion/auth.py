"""Secure Copernicus Data Space Ecosystem (CDSE) authentication.

Supports TWO OAuth2 grant types, in this priority order:

  1. **client_credentials** — for scripted / machine access using a
     CDSE OAuth client (Sentinel Hub -> User Settings -> OAuth clients).
     Credentials: CDSE_CLIENT_ID + CDSE_CLIENT_SECRET
     (also accepted: COPERNICUS_CLIENT_ID + COPERNICUS_CLIENT_SECRET).

  2. **password** — for a personal username/password (fallback).
     Credentials: CDSE_USERNAME + CDSE_PASSWORD
     (also accepted: COPERNICUS_USERNAME + COPERNICUS_PASSWORD).

Design points:
  - Credentials NEVER accepted via function arguments or source code.
  - Credentials read ONLY from environment variables and a local
    `.env` file inside the project's `secrets/` directory
    (git-ignored).
  - The client secret / username / password are never logged, echoed,
    or embedded in any response object.
  - Access tokens are held in-memory for the lifetime of a `CDSEAuth`
    instance and refreshed transparently.

Endpoint:
    https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from .errors import ErrorCode, IngestionError


CDSE_TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/"
    "protocol/openid-connect/token"
)
# Public client for the password grant (used only when the client_credentials
# flow is not configured).
DEFAULT_PUBLIC_CLIENT_ID = "cdse-public"
DEFAULT_TIMEOUT_S = 60


# The env-var name pairs we honor, in priority order.
CLIENT_CREDENTIAL_ENV_VARS: tuple[tuple[str, str], ...] = (
    ("CDSE_CLIENT_ID",       "CDSE_CLIENT_SECRET"),
    ("COPERNICUS_CLIENT_ID", "COPERNICUS_CLIENT_SECRET"),
)
PASSWORD_CREDENTIAL_ENV_VARS: tuple[tuple[str, str], ...] = (
    ("CDSE_USERNAME",       "CDSE_PASSWORD"),
    ("COPERNICUS_USERNAME", "COPERNICUS_PASSWORD"),
)

# Backwards-compatibility alias (Module 1 v1 exported this name).
CREDENTIAL_ENV_VARS = PASSWORD_CREDENTIAL_ENV_VARS


@dataclass(frozen=True)
class _ResolvedCredentials:
    grant_type: str          # "client_credentials" or "password"
    # For client_credentials: (client_id, client_secret).
    # For password:            (username,  password).
    principal: str
    secret: str

    # For password grant we always use `cdse-public` as the client_id.
    # For client_credentials the `principal` IS the client_id.
    def client_id(self) -> str:
        if self.grant_type == "client_credentials":
            return self.principal
        return DEFAULT_PUBLIC_CLIENT_ID


@dataclass
class CDSEAuth:
    """Lazy OAuth2 client for CDSE (client_credentials preferred, password fallback).

    Credentials are attached only during `_fetch_token` and never stored on
    the instance beyond what is needed to refresh.
    """
    timeout_s: float = DEFAULT_TIMEOUT_S
    token_url: str = CDSE_TOKEN_URL
    # Optional injected HTTP client (for tests)
    session: object | None = None
    # Internal cache
    _access_token: str | None = field(default=None, repr=False, compare=False)
    _refresh_token: str | None = field(default=None, repr=False, compare=False)
    _expiry_epoch: float = field(default=0.0, repr=False, compare=False)
    _grant_type_used: str | None = field(default=None, repr=False, compare=False)

    # ---- credential loading ----

    @staticmethod
    def _read_env_pair(pairs: tuple[tuple[str, str], ...]
                       ) -> tuple[str, str] | None:
        for k1, k2 in pairs:
            v1, v2 = os.environ.get(k1), os.environ.get(k2)
            if v1 and v2:
                return v1, v2
        return None

    @staticmethod
    def _read_env_file(secrets_dir: Path | None) -> dict[str, str] | None:
        if secrets_dir is None:
            return None
        env_file = Path(secrets_dir) / "cdse.env"
        if not env_file.is_file():
            return None
        data: dict[str, str] = {}
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            data[k.strip()] = v.strip().strip('"').strip("'")
        return data

    def _load_credentials(self, secrets_dir: Path | None
                          ) -> _ResolvedCredentials:
        # Priority: password grant BEFORE client_credentials.
        # Rationale: CDSE Sentinel Hub OAuth clients (sh-*) can query the
        # catalog but cannot download product bytes from the OData $value
        # endpoint. Personal-account password-grant tokens can do BOTH.
        # When the user has configured both, we choose the one that also
        # unlocks downloads. Callers that specifically want a Sentinel
        # Hub-only token can leave client_credentials as the only
        # configured credential.
        # 1. password grant in env
        pw = self._read_env_pair(PASSWORD_CREDENTIAL_ENV_VARS)
        if pw is not None:
            return _ResolvedCredentials("password", pw[0], pw[1])
        # 2. client_credentials in env
        cc = self._read_env_pair(CLIENT_CREDENTIAL_ENV_VARS)
        if cc is not None:
            return _ResolvedCredentials("client_credentials", cc[0], cc[1])
        # 3. cdse.env file — password first, then client_credentials
        file_data = self._read_env_file(secrets_dir)
        if file_data is not None:
            for k1, k2 in PASSWORD_CREDENTIAL_ENV_VARS:
                if file_data.get(k1) and file_data.get(k2):
                    return _ResolvedCredentials(
                        "password", file_data[k1], file_data[k2])
            for k1, k2 in CLIENT_CREDENTIAL_ENV_VARS:
                if file_data.get(k1) and file_data.get(k2):
                    return _ResolvedCredentials(
                        "client_credentials", file_data[k1], file_data[k2])
        raise IngestionError(
            ErrorCode.AUTHENTICATION_FAILED,
            "CDSE credentials not configured. Provide either "
            "(a) CDSE_CLIENT_ID + CDSE_CLIENT_SECRET for the "
            "client_credentials flow (preferred for scripted access), or "
            "(b) CDSE_USERNAME + CDSE_PASSWORD (or COPERNICUS_*) for the "
            "password flow. Set them in the environment, or place them in "
            "a KEY=VALUE cdse.env file in <repo>/secrets/. Credentials are "
            "never accepted via command-line arguments.",
            {"expected_env_vars": {
                "client_credentials": [list(p) for p in CLIENT_CREDENTIAL_ENV_VARS],
                "password":           [list(p) for p in PASSWORD_CREDENTIAL_ENV_VARS],
            }},
        )

    def is_configured(self, secrets_dir: Path | None = None) -> bool:
        """True if credentials of ANY supported grant are readable."""
        try:
            self._load_credentials(secrets_dir)
            return True
        except IngestionError:
            return False

    def configured_grant_type(self, secrets_dir: Path | None = None
                              ) -> str | None:
        """Return which grant type will be used ("client_credentials" or
        "password"). Never returns the credentials themselves."""
        try:
            return self._load_credentials(secrets_dir).grant_type
        except IngestionError:
            return None

    # ---- token acquisition ----

    def _now(self) -> float:
        return time.time()

    def _http_post(self, url: str, data: dict) -> tuple[int, dict]:
        """POST wrapper. Uses `requests` if present, else raises.

        Returns (status_code, parsed_json). Never returns request body or
        request headers to the caller.
        """
        if self.session is not None:
            resp = self.session.post(url, data=data, timeout=self.timeout_s)  # type: ignore[attr-defined]
            code = int(resp.status_code)
            try:
                body = resp.json() if hasattr(resp, "json") else {}
            except Exception:
                body = {}
            return code, body
        try:
            import requests
        except Exception as e:  # pragma: no cover
            raise IngestionError(
                ErrorCode.AUTHENTICATION_FAILED,
                "`requests` library is required for CDSE authentication.",
                {"reason": str(e)}) from e
        try:
            resp = requests.post(url, data=data, timeout=self.timeout_s)
        except Exception as e:
            raise IngestionError(
                ErrorCode.AUTHENTICATION_FAILED,
                "Network error while contacting CDSE identity provider.",
                {"reason": e.__class__.__name__}) from e
        try:
            body = resp.json()
        except Exception:
            body = {}
        return int(resp.status_code), body

    def _apply_token_response(self, body: dict) -> None:
        access = body.get("access_token")
        refresh = body.get("refresh_token")   # None for client_credentials
        expires_in = int(body.get("expires_in", 0))
        if not access:
            # NEVER echo the raw response body: it may quote credential
            # snippets in provider-specific error strings.
            raise IngestionError(
                ErrorCode.AUTHENTICATION_FAILED,
                "CDSE token response did not include an access_token.",
                {"expires_in": expires_in})
        self._access_token = access
        self._refresh_token = refresh
        self._expiry_epoch = self._now() + max(0, expires_in - 60)

    def _fetch_token(self, secrets_dir: Path | None) -> None:
        creds = self._load_credentials(secrets_dir)
        if creds.grant_type == "client_credentials":
            data = {
                "grant_type":    "client_credentials",
                "client_id":     creds.principal,
                "client_secret": creds.secret,
            }
        else:
            data = {
                "grant_type": "password",
                "client_id":  creds.client_id(),
                "username":   creds.principal,
                "password":   creds.secret,
            }
        code, body = self._http_post(self.token_url, data)
        # Drop the sensitive dict promptly so it isn't kept alive on the frame.
        del data, creds
        if code >= 400:
            raise IngestionError(
                ErrorCode.AUTHENTICATION_FAILED,
                f"CDSE token endpoint rejected the credentials "
                f"(HTTP {code}).",
                {"http_status": code,
                 "grant_type": self._grant_type_pending or "?"})
        self._grant_type_used = self._grant_type_pending
        self._apply_token_response(body)

    # We track the grant type being attempted just so the error context can
    # include it (useful when both flows are configured).
    @property
    def _grant_type_pending(self) -> str | None:
        try:
            return self._load_credentials(secrets_dir=None).grant_type
        except IngestionError:
            return None

    def _refresh(self, secrets_dir: Path | None) -> None:
        # client_credentials grants get a fresh access token every time
        # (they don't yield refresh tokens); only password can refresh.
        if not self._refresh_token:
            return self._fetch_token(secrets_dir)
        data = {
            "grant_type":    "refresh_token",
            "refresh_token": self._refresh_token,
            "client_id":     DEFAULT_PUBLIC_CLIENT_ID,
        }
        code, body = self._http_post(self.token_url, data)
        if code >= 400:
            self._access_token = None
            self._refresh_token = None
            return self._fetch_token(secrets_dir)
        self._apply_token_response(body)

    # ---- public API ----

    def get_access_token(self, secrets_dir: Path | None = None) -> str:
        """Return a valid access token, refreshing if needed.

        Callers must NOT persist the returned token; the pipeline layer
        scrubs it after building an Authorization header.
        """
        if self._access_token is None or self._now() >= self._expiry_epoch:
            if self._refresh_token and self._access_token is not None:
                self._refresh(secrets_dir)
            else:
                self._fetch_token(secrets_dir)
        assert self._access_token is not None
        return self._access_token

    def auth_header(self, secrets_dir: Path | None = None) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.get_access_token(secrets_dir)}"}


__all__ = [
    "CDSEAuth", "CDSE_TOKEN_URL",
    "CLIENT_CREDENTIAL_ENV_VARS", "PASSWORD_CREDENTIAL_ENV_VARS",
    "CREDENTIAL_ENV_VARS",
    "DEFAULT_PUBLIC_CLIENT_ID",
]
