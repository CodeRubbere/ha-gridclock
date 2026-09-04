"""The Grid Clock integration - 15-minute day-ahead electricity prices from cdn.gridclock.eu."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY, CONF_ZONE, DOMAIN, PLATFORMS
from .coordinator import GridClockCoordinator



async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Grid Clock from a config entry."""
    zone = entry.data[CONF_ZONE]
    api_key = entry.options.get(CONF_API_KEY, entry.data.get(CONF_API_KEY))

    coordinator = GridClockCoordinator(hass, zone, api_key)
    await coordinator.async_config_entry_first_refresh()

    # Plain hass.data storage (rather than entry.runtime_data) so this
    # loads on older Home Assistant cores too, not just ones where
    # ConfigEntry declares that slot.
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options (the bearer key) change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded
