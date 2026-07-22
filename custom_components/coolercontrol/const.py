"""Constants for the CoolerControl integration."""

DOMAIN = "coolercontrol"

CONF_TOKEN = "token"
CONF_VERIFY_SSL = "verify_ssl"

DEFAULT_PORT = 11987
DEFAULT_VERIFY_SSL = False
DEFAULT_SCAN_INTERVAL = 5  # seconds

# CoolerControl REST endpoints (daemon default port 11987, HTTPS w/ self-signed cert)
ENDPOINT_DEVICES = "/devices"
ENDPOINT_STATUS = "/status"

MANUFACTURER = "CoolerControl"
