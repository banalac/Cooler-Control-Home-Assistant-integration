# CoolerControl Home Assistant Integration

This is a HACS-compatible integration for CoolerControl running on Proxmox or Linux.

## Features
- Automatic device discovery
- CPU/GPU/NVMe/Board temperature sensors
- Power, frequency, load sensors
- Fan RPM + Duty sensors
- Fan control (set duty)
- UI-based configuration (no YAML)

## Installation
1. Add this repository to HACS as a custom repository.
2. Install the integration.
3. Restart Home Assistant.
4. Go to Settings → Devices & Services → Add Integration → CoolerControl.
5. Enter:
   - Host (e.g. 192.168.31.198)
   - API Token (Bearer token)

## Requirements
- CoolerControl backend running on your device
- API enabled
