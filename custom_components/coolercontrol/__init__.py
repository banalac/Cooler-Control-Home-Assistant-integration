"""The CoolerControl integration."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CoolerControlApiClient
from .const import CONF_TOKEN, CONF_VERIFY_SSL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import CoolerControlCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up CoolerControl from a config entry."""
    verify_ssl = entry.data.get(CONF_VERIFY_SSL, False)
    session = async_get_clientsession(hass, verify_ssl=verify_ssl)

    client = CoolerControlApiClient(
        session,
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data[CONF_TOKEN],
        verify_ssl=verify_ssl,
    )

    coordinator = CoolerControlCoordinator(
        hass, client, update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL)
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
