import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_TOKEN
from .const import DOMAIN
from .api import CoolerControlAPI

class CoolerControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            token = user_input[CONF_TOKEN]

            api = CoolerControlAPI(host, token)

            try:
                status = await api.get_status()
                if "devices" not in status:
                    errors["base"] = "invalid_response"
                else:
                    return self.async_create_entry(
                        title=f"CoolerControl ({host})",
                        data=user_input
                    )
            except Exception:
                errors["base"] = "cannot_connect"

        schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_TOKEN): str
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors
        )
