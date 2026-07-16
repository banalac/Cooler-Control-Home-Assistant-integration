"""Number platform for CoolerControl - manual fan/pump duty control (10-100%)."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import CoolerControlApiError, CoolerControlAuthError
from .const import DOMAIN, MANUFACTURER
from .coordinator import CoolerControlCoordinator, CoolerControlFanChannel

_LOGGER = logging.getLogger(__name__)

MIN_DUTY = 10
MAX_DUTY = 100


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up CoolerControl fan-duty number entities from a config entry."""
    coordinator: CoolerControlCoordinator = hass.data[DOMAIN][entry.entry_id]

    known_keys: set[str] = set()

    @callback
    def _add_new_entities() -> None:
        new_entities: list[CoolerControlFanNumber] = []
        for device in coordinator.data.values():
            for channel in device.fan_channels:
                unique_id = f"{entry.entry_id}_{channel.device_uid}_{channel.channel_name}_manual_duty"
                if unique_id in known_keys:
                    continue
                known_keys.add(unique_id)
                new_entities.append(
                    CoolerControlFanNumber(coordinator, entry.entry_id, channel, unique_id, device.type)
                )
        if new_entities:
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class CoolerControlFanNumber(CoordinatorEntity[CoolerControlCoordinator], NumberEntity):
    """A slider (10-100%) that sets a fan/pump channel to a fixed manual duty."""

    _attr_has_entity_name = True
    _attr_native_min_value = MIN_DUTY
    _attr_native_max_value = MAX_DUTY
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "%"
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        coordinator: CoolerControlCoordinator,
        entry_id: str,
        channel: CoolerControlFanChannel,
        unique_id: str,
        device_type: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._device_uid = channel.device_uid
        self._channel_name = channel.channel_name
        self._optimistic_value: float | None = None

        self._attr_unique_id = unique_id
        self._attr_name = f"{channel.label} Manual Duty"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_{channel.device_uid}")},
            name=channel.device_name,
            manufacturer=MANUFACTURER,
            model=device_type,
        )

    @property
    def native_value(self) -> float | None:
        if self._optimistic_value is not None:
            return self._optimistic_value
        device = self.coordinator.data.get(self._device_uid)
        if device is None:
            return None
        for channel in device.fan_channels:
            if channel.channel_name == self._channel_name:
                return channel.current_duty
        return None

    @property
    def available(self) -> bool:
        return super().available and self._device_uid in self.coordinator.data

    async def async_set_native_value(self, value: float) -> None:
        client = self.coordinator.client
        try:
            await client.async_set_fan_speed(self._device_uid, self._channel_name, int(round(value)))
        except CoolerControlAuthError as err:
            raise HomeAssistantError(
                f"A token nem rendelkezik írási joggal: {err}"
            ) from err
        except CoolerControlApiError as err:
            raise HomeAssistantError(f"Nem sikerült beállítani a fordulatszámot: {err}") from err

        # Reflect the new value immediately, then let the next poll confirm it.
        self._optimistic_value = value
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
        self._optimistic_value = None
