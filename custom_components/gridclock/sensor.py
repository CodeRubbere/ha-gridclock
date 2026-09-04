"""Sensors for Grid Clock.

Two entities per configured zone:

- ``sensor.grid_clock_<zone>_current_price``: the price of the quarter-hour
  (or whatever resolution the zone publishes) that "now" falls into.
- ``sensor.grid_clock_<zone>_prices``: state is the number of known slots;
  its ``prices`` attribute is deliberately the same shape as the
  ``sensor.epex_prices`` entity in home assistant/packages/epex_live_sensors.yaml
  ( ``[{"startsAt": ..., "total": ...}, ...]`` plus ``knownUntil`` ) so that
  package's templates (afname/injectie/cheap-now) can be repointed at this
  sensor by only changing the entity_id.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CONF_ZONE, DOMAIN, PRICE_UNIT, ZONES
from .coordinator import GridClockCoordinator, GridClockData


def _zone_name(zone: str, language: str) -> str:
    lang = "nl" if language.startswith("nl") else "en"
    names = ZONES.get(zone, {})
    return names.get(lang, names.get("en", zone))


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Grid Clock sensors for one config entry."""
    coordinator: GridClockCoordinator = hass.data[DOMAIN][entry.entry_id]
    zone = entry.data[CONF_ZONE]
    zone_name = _zone_name(zone, hass.config.language)

    device_info = DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"Grid Clock {zone_name}",
        manufacturer="Grid Clock",
        model=zone,
        configuration_url="https://gridclock.eu",
    )

    async_add_entities(
        [
            GridClockCurrentPriceSensor(coordinator, entry, zone, device_info),
            GridClockPricesSensor(coordinator, entry, zone, device_info),
        ]
    )


class _GridClockEntity(CoordinatorEntity[GridClockCoordinator]):
    """Shared bits for both Grid Clock sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: GridClockCoordinator,
        entry: ConfigEntry,
        zone: str,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._zone = zone
        self._attr_device_info = device_info
        self._attr_unique_id = f"{entry.entry_id}_{self._id_suffix}"


class GridClockCurrentPriceSensor(_GridClockEntity, SensorEntity):
    """The price of the slot 'now' falls into, in ct/kWh."""

    _id_suffix = "current_price"
    _attr_translation_key = "current_price"
    _attr_native_unit_of_measurement = PRICE_UNIT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2
    _attr_icon = "mdi:currency-eur"

    @property
    def native_value(self) -> float | None:
        data: GridClockData | None = self.coordinator.data
        if data is None:
            return None
        return data.price_at(dt_util.utcnow())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data: GridClockData | None = self.coordinator.data
        if data is None:
            return {}
        return {
            "zone": data.zone,
            "resolution_minutes": data.resolution_minutes,
            "published_at": data.published_at.isoformat() if data.published_at else None,
            "stale": data.stale,
        }


class GridClockPricesSensor(_GridClockEntity, SensorEntity):
    """All known quarter-hour prices (today + tomorrow once published)."""

    _id_suffix = "prices"
    _attr_translation_key = "prices"
    _attr_state_class = None
    _attr_icon = "mdi:chart-timeline-variant"

    @property
    def native_value(self) -> int | None:
        data: GridClockData | None = self.coordinator.data
        if data is None:
            return None
        return len(data.prices)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data: GridClockData | None = self.coordinator.data
        if data is None:
            return {}
        return {
            "zone": data.zone,
            "unit": PRICE_UNIT,
            "resolution_minutes": data.resolution_minutes,
            "published_at": data.published_at.isoformat() if data.published_at else None,
            "stale": data.stale,
            "knownUntil": data.known_until.isoformat() if data.known_until else None,
            "prices": [
                {"startsAt": point.start.isoformat(), "total": point.price}
                for point in data.prices
            ],
        }
