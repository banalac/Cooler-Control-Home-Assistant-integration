"""Minimal async client for the CoolerControl daemon (coolercontrold) REST API.

CoolerControl exposes a REST API on the daemon (default port 11987, HTTPS with
a self-signed certificate unless you've configured your own). Access tokens are
sent as a Bearer token in the Authorization header.

Reference: https://docs.coolercontrol.org/daemon/access-protection.html
           https://docs.coolercontrol.org/wiki/scripting.html

Because the exact JSON schema of the daemon isn't officially documented in a
stable spec, this client is intentionally defensive: it fetches whatever the
daemon returns and lets the coordinator/sensor layer walk the structure to
find numeric sensor values, rather than hard-coding brittle field paths.
"""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import ENDPOINT_DEVICES, ENDPOINT_STATUS

_LOGGER = logging.getLogger(__name__)


class CoolerControlApiError(Exception):
    """Raised on any communication/auth error talking to the daemon."""


class CoolerControlAuthError(CoolerControlApiError):
    """Raised when the token is rejected (HTTP 401/403)."""


class CoolerControlApiClient:
    """Talks to a single CoolerControl daemon instance."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        token: str,
        verify_ssl: bool = False,
    ) -> None:
        self._session = session
        self._base_url = f"https://{host}:{port}"
        self._token = token
        self._ssl = None if verify_ssl else False

    @property
    def base_url(self) -> str:
        return self._base_url

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }

    async def _get(self, path: str) -> Any:
        url = f"{self._base_url}{path}"
        try:
            async with self._session.get(
                url, headers=self._headers(), ssl=self._ssl, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status in (401, 403):
                    raise CoolerControlAuthError(
                        f"CoolerControl rejected the access token (HTTP {resp.status})"
                    )
                if resp.status == 404:
                    return None
                resp.raise_for_status()
                if resp.content_type == "application/json":
                    return await resp.json()
                # Some daemon versions may reply text/plain with a JSON body.
                text = await resp.text()
                import json

                try:
                    return json.loads(text)
                except ValueError:
                    return None
        except CoolerControlAuthError:
            raise
        except aiohttp.ClientError as err:
            raise CoolerControlApiError(f"Error communicating with {url}: {err}") from err

    async def async_verify(self) -> None:
        """Raise if the daemon can't be reached / token is invalid."""
        devices = await self._get(ENDPOINT_DEVICES)
        if devices is None:
            raise CoolerControlApiError(
                f"{ENDPOINT_DEVICES} returned nothing – is the URL and daemon version correct?"
            )

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Return the raw device list from GET /devices."""
        data = await self._get(ENDPOINT_DEVICES)
        if data is None:
            return []
        # Some versions wrap the list in {"devices": [...]}, others return
        # a bare list - handle both.
        if isinstance(data, dict) and "devices" in data:
            return data["devices"]
        if isinstance(data, list):
            return data
        return []

    async def async_get_status(self) -> list[dict[str, Any]]:
        """Return live status (temps/channels) merged per device.

        Tries GET /status first (used by the daemon's own UI for polling).
        If that endpoint isn't available on this daemon version, falls back
        to whatever /devices already contains (some versions embed the
        latest status directly on the device object).
        """
        data = await self._get(ENDPOINT_STATUS)
        devices: list[dict[str, Any]] = []
        if isinstance(data, dict) and "devices" in data:
            devices = data["devices"]
        elif isinstance(data, list):
            devices = data

        if devices:
            return devices

        _LOGGER.debug(
            "%s returned nothing usable, falling back to %s for status data",
            ENDPOINT_STATUS,
            ENDPOINT_DEVICES,
        )
        return await self.async_get_devices()
