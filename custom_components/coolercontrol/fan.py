from homeassistant.components.fan import FanEntity
from .api import CoolerControlAPI
from .const import DOMAIN

async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    host = discovery_info["host"]
    token = discovery_info["token"]

    api = CoolerControlAPI(host, token)
    status = await api.get_status()

    fans = []

    for dev in status["devices"]:
        uid = dev["uid"]
        hist = dev["status_history"][0]

        for ch in hist.get("channels", []):
            if "rpm" in ch:
                fans.append(CoolerControlFan(api, uid, ch["name"]))

    add_entities(fans)


class CoolerControlFan(FanEntity):
    def __init__(self, api, uid, name):
        self.api = api
        self.uid = uid
        self._name = name
        self._duty = 0

    @property
    def name(self):
        return f"{self._name}"

    @property
    def percentage(self):
        return self._duty

    async def async_set_percentage(self, percentage):
        self._duty = percentage
        await self.api.set_fan_duty(self.uid, self._name, percentage)

    async def async_update(self):
        data = await self.api.get_status(self.uid)
        hist = data["status_history"][0]

        for ch in hist.get("channels", []):
            if ch["name"] == self._name:
                self._duty = ch["duty"]
