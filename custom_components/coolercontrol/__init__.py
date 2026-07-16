from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery import async_load_platform
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    await async_load_platform(hass, "sensor", DOMAIN, entry.data, entry)
    await async_load_platform(hass, "fan", DOMAIN, entry.data, entry)

    return True
