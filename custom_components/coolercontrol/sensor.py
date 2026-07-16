from homeassistant.helpers.entity import Entity
from .api import CoolerControlAPI
from .const import DOMAIN

async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    host = discovery_info["host"]
    token = discovery_info["token"]

    api = CoolerControlAPI(host, token)
    status = await api.get_status()

    entities = []

    for dev in status["devices"]:
        uid = dev["uid"]
        hist = dev["status_history"][0]

        # Temps
        for t in hist.get("temps", []):
            entities.append(CoolerControlSensor(api, uid, t["name"], "temp", t["name"]))

        # Channels
        for ch in hist.get("channels", []):
            for key in ["rpm", "duty", "watts", "freq"]:
                if key in ch:
                    entities.append(
                        CoolererControlSensor(api, uid, ch["name"], key, ch["name"])
                    )

    add_entities(entities)


class CoolerControlSensor(Entity):
    def __init__(self, api, uid, name, key, label):
        self.api = api
        self.uid = uid
        self._name = f"{label} {key}"
        self.key = key
        self.label = label
        self._state = None

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    async def async_update(self):
        data = await self.api.get_status(self.uid)
        hist = data["status_history"][0]

        # Temps
        for t in hist.get("temps", []):
            if t["name"] == self.label and self.key == "temp":
                self._state = t["temp"]

        # Channels
        for ch in hist.get("channels", []):
            if ch["name"] == self.label and self.key in ch:
                self._state = ch[self.key]
