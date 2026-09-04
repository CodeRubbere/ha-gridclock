# Grid Clock — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A custom [Home Assistant](https://www.home-assistant.io/) integration for
[Grid Clock](https://gridclock.eu) — day-ahead electricity prices (ENTSO-E,
41 EU bidding zones) served from `cdn.gridclock.eu`.

## Features

- Config flow setup: pick your bidding zone from a dropdown, with an
  optional bearer API key field (future-proofing — the CDN does not yet
  require authentication).
- Polls `v1/prices/{zone}/latest.json` every hour, plus an immediate fetch
  as soon as a bidding zone is set up (during config flow validation, and
  again on the coordinator's first refresh).
- Two sensors per configured zone, grouped under one device (e.g. "Grid
  Clock NL"):
  - **Current price** (`sensor.grid_clock_<zone>_current_price`) — the price
    for the interval "now" falls into, in ct/kWh.
  - **Prices** (`sensor.grid_clock_<zone>_prices`) — state is the number of
    known intervals; attributes are `prices`
    (`[{"startsAt": ..., "total": ...}, ...]`) and `knownUntil`.
- Ships its own brand icon/logo (`custom_components/gridclock/brand/`),
  picked up automatically by HA's Brands Proxy API (HA 2026.3+) for the
  integration tile in Settings → Devices & Services.

## Installation

### HACS (recommended)

1. In HACS, add this repository as a **custom repository**
   (category: *Integration*): `https://github.com/CodeRubbere/ha-gridclock`.
2. Install "Grid Clock" from HACS.
3. Restart Home Assistant.
4. Settings → Devices & Services → Add Integration → search "Grid Clock".

### Manual

1. Copy `custom_components/gridclock` into `<your HA config dir>/custom_components/gridclock`.
2. Restart Home Assistant.
3. Settings → Devices & Services → Add Integration → search "Grid Clock".

## Configuration

Pick your bidding zone (e.g. Netherlands) and optionally fill in a bearer
API key. The key can be changed later via the integration's options (gear
icon) without removing and re-adding the integration.

## Migrating from an EPEX-based setup

If you're coming from a `sensor.epex_prices`-style setup (e.g. the
`epex_live_sensors.yaml` / `epex_live_helpers.yaml` package pattern), the
`prices` attribute on `sensor.grid_clock_<zone>_prices` deliberately mirrors
that shape, so templates can generally be repointed by swapping the
entity_id. See
[`custom_components/gridclock/README.md`](custom_components/gridclock/README.md)
(Dutch) for the detailed migration notes this integration was originally
built against.

## License

[MIT](LICENSE)
