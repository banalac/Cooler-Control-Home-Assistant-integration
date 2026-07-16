import aiohttp
import async_timeout

class CoolerControlAPI:
    def __init__(self, host, token):
        self.host = host
        self.token = token
        self.base = f"http://{host}:11987"

    async def get_status(self, uid=None):
        url = f"{self.base}/status"
        if uid:
            url = f"{self.base}/status/{uid}"

        headers = {"Authorization": f"Bearer {self.token}"}

        async with aiohttp.ClientSession() as session:
            with async_timeout.timeout(10):
                async with session.get(url, headers=headers) as resp:
                    return await resp.json()

    async def set_fan_duty(self, uid, channel, duty):
        url = f"{self.base}/control"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        payload = {
            "uid": uid,
            "channel": channel,
            "duty": duty
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                return await resp.json()
