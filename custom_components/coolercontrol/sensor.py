"""Sensor platform for CoolerControl."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import CoolerControlCoordinator, CoolerControlMetric

_LOGGER = logging.getLogger(__name__)

# kind -> (device_class, state_class, unit)
_KIND_MAP: dict[str, tuple[SensorDeviceClass | None, SensorStateClass | None, str | None]] = {
    "temperature": (SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, UnitOfTemperature.CELSIUS),
    "rpm": (None, SensorStateClass.MEASUREMENT, REVOLUTIONS_PER_MINUTE),
    "duty": (None, SensorStateClass.MEASUREMENT, PERCENTAGE),
    "load": (None, SensorStateClass.MEASUREMENT, PERCENTAGE),
    "freq": (SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT, UnitOfFrequency.HERTZ),
    "watts": (SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT),
    "volts": (SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, UnitOfElectricPotential.VOLT),
}

_KIND_SUFFIX = {
    "temperature": "",
    "rpm": "RPM",
    "duty": "Duty",
    "load": "Load",
    "freq": "Frequency",
    "watts": "Power",
    "volts": "Voltage",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up CoolerControl sensors from a config entry."""
    coordinator: CoolerControlCoordinator = hass.data[DOMAIN][entry.entry_id]

    known_keys: set[str] = set()

    @callback
    def _add_new_entities() -> None:
        new_entities: list[CoolerControlSensor] = []
        for device in coordinator.data.values():
            for metric in device.metrics:
                unique_id = f"{entry.entry_id}_{metric.device_uid}_{metric.metric_key}"
                if unique_id in known_keys:
                    continue
                known_keys.add(unique_id)
                new_entities.append(CoolerControlSensor(coordinator, entry.entry_id, metric, unique_id))
        if new_entities:
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class CoolerControlSensor(CoordinatorEntity[CoolerControlCoordinator], SensorEntity):
    """Represents a single temperature/fan/pump reading from CoolerControl."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CoolerControlCoordinator,
        entry_id: str,
        metric: CoolerControlMetric,
        unique_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._device_uid = metric.device_uid
        self._metric_key = metric.metric_key
        self._kind = metric.kind

        self._attr_unique_id = unique_id
        suffix = _KIND_SUFFIX.get(metric.kind, metric.kind)
        # Avoid redundant names like "GPU Load Duty" when the channel's own
        # label already describes the measurement.
        if suffix and suffix.lower() in metric.label.lower():
            self._attr_name = metric.label
        else:
            self._attr_name = f"{metric.label} {suffix}".strip()

        device_class, state_class, unit = _KIND_MAP.get(metric.kind, (None, SensorStateClass.MEASUREMENT, None))
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_{metric.device_uid}")},
            name=metric.device_name,
            manufacturer=MANUFACTURER,
            model=metric.device_type,
        )

    @property
    def native_value(self) -> float | None:
        device = self.coordinator.data.get(self._device_uid)
        if device is None:
            return None
        for metric in device.metrics:
            if metric.metric_key == self._metric_key:
                return metric.value
        return None

    @property
    def available(self) -> bool:
        return super().available and self._device_uid in self.coordinator.data
