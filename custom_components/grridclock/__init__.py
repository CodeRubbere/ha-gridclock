"""The Grid Clock integration - 15-minute day-ahead electricity prices from cdn.gridclock.eu."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY, CONF_ZONE, DOMAIN, PLATFORMS
from .coordinator import GridClockCoordinator
from .default import async_apply_default, unregister_default_platform


def _api_key(entry: ConfigEntry) -> str | None:
    return entry.options.get(CONF_API_KEY, entry.data.get(CONF_API_KEY))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Grid Clock from a config entry."""
    zone = entry.data[CONF_ZONE]

    coordinator = GridClockCoordinator(hass, zone, _api_key(entry))
    await coordinator.async_config_entry_first_refresh()

    # Plain hass.data storage (rather than entry.runtime_data) so this
    # loads on older Home Assistant cores too, not just ones where
    # ConfigEntry declares that slot.
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """React to changed options.

    A new bearer key needs a reload (new coordinator). If only the
    "default zone" flag changed, just move the default entities - no reload,
    no extra CDN fetch.
    """
    coordinator: GridClockCoordinator | None = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator is None or coordinator.api_key != _api_key(entry):
        await hass.config_entries.async_reload(entry.entry_id)
        return
    await async_apply_default(hass)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        unregister_default_platform(hass, entry.entry_id)
        # If this zone owned the default entities, hand them to the next zone.
        await async_apply_default(hass)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """A zone was deleted: make sure another zone takes over as default."""
    await async_apply_default(hass, ignore=entry.entry_id)
