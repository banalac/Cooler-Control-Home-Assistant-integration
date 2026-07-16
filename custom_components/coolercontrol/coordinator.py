"""DataUpdateCoordinator for CoolerControl."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CoolerControlApiClient, CoolerControlApiError, CoolerControlAuthError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class CoolerControlMetric:
    """A single numeric reading discovered on a device (one temp, one fan, ...)."""

    device_uid: str
    device_name: str
    device_type: str
    metric_key: str  # stable-ish key used to build the unique_id, e.g. "temp_liquid" or "channel_pump_rpm"
    label: str  # human friendly label, e.g. "Liquid" or "Pump"
    kind: str  # "temperature" | "rpm" | "duty" | "load" | "freq" | "watts" | "volts" | "other"
    value: float


@dataclass
class CoolerControlDevice:
    uid: str
    name: str
    type: str
    metrics: list[CoolerControlMetric] = field(default_factory=list)


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _extract_status_block(device: dict[str, Any]) -> dict[str, Any]:
    """Find the most recent status block for a device, regardless of daemon shape."""
    history = device.get("status_history")
    if isinstance(history, list) and history:
        last = history[-1]
        if isinstance(last, dict):
            return last
    status = device.get("status")
    if isinstance(status, dict):
        return status
    # Some daemon versions may put temps/channels directly on the device dict.
    return device


def _parse_device(device: dict[str, Any], name_lookup: dict[str, str] | None = None) -> CoolerControlDevice | None:
    uid = device.get("uid")
    if not uid:
        return None

    dtype = device.get("type", "Unknown")
    type_index = device.get("type_index", "")

    # /status doesn't include a friendly "name" field on some daemon versions -
    # prefer the name from /devices (via name_lookup), then whatever the device
    # dict itself carries, and finally fall back to "<type> <type_index>".
    name = (name_lookup or {}).get(uid) or device.get("name") or f"{dtype} {type_index}".strip()

    parsed = CoolerControlDevice(uid=uid, name=name, type=dtype)
    status = _extract_status_block(device)

    # Temperatures: list of {"name": ..., "temp": ...}
    for temp in status.get("temps", []) or []:
        if not isinstance(temp, dict):
            continue
        label = temp.get("name") or "Temp"
        val = _as_float(temp.get("temp"))
        if val is None:
            continue
        key = f"temp_{label}"
        parsed.metrics.append(
            CoolerControlMetric(uid, name, dtype, key, label, "temperature", val)
        )

    # Channels (fans/pumps): list of {"name": ..., "rpm": ..., "duty": ..., "freq": ..., "watts": ...}
    for channel in status.get("channels", []) or []:
        if not isinstance(channel, dict):
            continue
        label = channel.get("name") or "Channel"
        for field_name, kind in (
            ("rpm", "rpm"),
            ("duty", "duty"),
            ("freq", "freq"),
            ("watts", "watts"),
            ("volts", "volts"),
            ("load", "load"),
        ):
            val = _as_float(channel.get(field_name))
            if val is None:
                continue
            key = f"channel_{label}_{field_name}"
            parsed.metrics.append(
                CoolerControlMetric(uid, name, dtype, key, label, kind, val)
            )

    if not parsed.metrics:
        _LOGGER.debug(
            "No temps/channels recognised for device '%s' (uid=%s); raw keys: %s",
            name,
            uid,
            list(device.keys()),
        )

    return parsed


class CoolerControlCoordinator(DataUpdateCoordinator[dict[str, CoolerControlDevice]]):
    """Polls the daemon on a fixed interval and exposes parsed devices."""

    def __init__(
        self, hass: HomeAssistant, client: CoolerControlApiClient, update_interval: timedelta
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, CoolerControlDevice]:
        try:
            raw_devices = await self.client.async_get_status()
            device_list = await self.client.async_get_devices()
        except CoolerControlAuthError as err:
            raise UpdateFailed(str(err)) from err
        except CoolerControlApiError as err:
            raise UpdateFailed(str(err)) from err

        # /devices carries the friendly name (e.g. "NZXT Kraken 2023") that
        # /status often omits; build a uid -> name lookup to merge them.
        name_lookup: dict[str, str] = {}
        for dev in device_list:
            if isinstance(dev, dict) and dev.get("uid") and dev.get("name"):
                name_lookup[dev["uid"]] = dev["name"]

        devices: dict[str, CoolerControlDevice] = {}
        for raw in raw_devices:
            if not isinstance(raw, dict):
                continue
            parsed = _parse_device(raw, name_lookup)
            if parsed is not None:
                devices[parsed.uid] = parsed

        if not devices:
            _LOGGER.warning(
                "CoolerControl returned no parsable devices. Check that the token has "
                "at least read-only access and that %s / %s respond as expected.",
                "/status",
                "/devices",
            )

        return devices
