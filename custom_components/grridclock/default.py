"""Default-zone handling.

When several bidding zones are configured, one of them can be marked as the
default (options flow checkbox, stored as ``is_default`` in that entry's
options). The default zone gets two extra, *stable* entities:

- ``sensor.grid_clock_default_current_price``
- ``sensor.grid_clock_default_prices``

Their unique_ids are not tied to a config entry, so when the default moves to
another zone the same entity_ids are re-used and just start following the new
zone - automations/dashboards pointing at them keep working unchanged.

Without an explicit choice the first configured zone is the default, so the
default entities exist from the very first zone on and adding a second zone
never silently breaks them.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DEFAULT, DOMAIN

DATA_DEFAULT = f"{DOMAIN}_default"

EntityFactory = Callable[[], list[Entity]]

_FAILED_STATES = (
    ConfigEntryState.SETUP_ERROR,
    ConfigEntryState.SETUP_RETRY,
    ConfigEntryState.FAILED_UNLOAD,
    ConfigEntryState.MIGRATION_ERROR,
)


@dataclass
class _DefaultManager:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    # entry_id -> (that entry's sensor add-callback, factory for default entities)
    platforms: dict[str, tuple[AddEntitiesCallback, EntityFactory]] = field(
        default_factory=dict
    )
    owner: str | None = None
    entities: list[Entity] = field(default_factory=list)


def _manager(hass: HomeAssistant) -> _DefaultManager:
    return hass.data.setdefault(DATA_DEFAULT, _DefaultManager())


def _active_entries(hass: HomeAssistant, ignore: str | None = None) -> list[ConfigEntry]:
    return [
        e
        for e in hass.config_entries.async_entries(DOMAIN)
        if e.disabled_by is None and e.entry_id != ignore
    ]


def preferred_default_entry(
    hass: HomeAssistant, ignore: str | None = None
) -> ConfigEntry | None:
    """The entry that *should* be default: the flagged one, else the first one."""
    entries = _active_entries(hass, ignore)
    if not entries:
        return None
    return next((e for e in entries if e.options.get(CONF_DEFAULT)), entries[0])


def _pick_owner(
    hass: HomeAssistant, mgr: _DefaultManager, ignore: str | None
) -> str | None:
    preferred = preferred_default_entry(hass, ignore)
    if preferred is None:
        return None
    if preferred.entry_id in mgr.platforms:
        return preferred.entry_id
    if preferred.state in _FAILED_STATES:
        # Preferred zone can't load (e.g. CDN error) - fall back to any loaded zone.
        return next(
            (e.entry_id for e in _active_entries(hass, ignore) if e.entry_id in mgr.platforms),
            None,
        )
    # Preferred zone is still loading; it calls async_apply_default once it's ready.
    return None


def register_default_platform(
    hass: HomeAssistant,
    entry_id: str,
    async_add_entities: AddEntitiesCallback,
    factory: EntityFactory,
) -> None:
    """Called from sensor.async_setup_entry for every zone."""
    _manager(hass).platforms[entry_id] = (async_add_entities, factory)


def unregister_default_platform(hass: HomeAssistant, entry_id: str) -> None:
    """Called after a zone's platforms were unloaded.

    If this zone owned the default entities, the platform unload already
    removed them from HA; we only forget about them here.
    """
    mgr = _manager(hass)
    mgr.platforms.pop(entry_id, None)
    if mgr.owner == entry_id:
        mgr.owner = None
        mgr.entities = []


async def async_apply_default(hass: HomeAssistant, ignore: str | None = None) -> None:
    """Make sure the default entities live on the right zone (idempotent)."""
    mgr = _manager(hass)
    async with mgr.lock:
        target = _pick_owner(hass, mgr, ignore)
        if target == mgr.owner:
            return

        # Remove from the old zone first (keeps the entity-registry entry, so
        # the entity_id is re-used when the new zone adds the same unique_id).
        for entity in mgr.entities:
            await entity.async_remove()
        mgr.entities = []
        mgr.owner = None

        if target is None:
            return

        async_add_entities, factory = mgr.platforms[target]
        mgr.entities = factory()
        mgr.owner = target
        async_add_entities(mgr.entities)
