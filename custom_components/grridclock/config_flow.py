"""Config flow for Grid Clock."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import CONF_API_KEY, CONF_DEFAULT, CONF_ZONE, DEFAULT_ZONE, DOMAIN, ZONES
from .coordinator import async_fetch_latest
from .default import preferred_default_entry

_LOGGER = logging.getLogger(__name__)


def _zone_options(language: str) -> list[SelectOptionDict]:
    lang = "nl" if language.startswith("nl") else "en"
    return [
        SelectOptionDict(value=code, label=f"{names.get(lang, names['en'])} ({code})")
        for code, names in ZONES.items()
    ]


def _zone_name(code: str, language: str) -> str:
    lang = "nl" if language.startswith("nl") else "en"
    names = ZONES.get(code, {})
    return names.get(lang, names.get("en", code))


def _clear_other_defaults(hass: HomeAssistant, keep_entry_id: str | None) -> None:
    """Only one zone can be default: un-flag every other zone."""
    for other in hass.config_entries.async_entries(DOMAIN):
        if other.entry_id != keep_entry_id and other.options.get(CONF_DEFAULT):
            hass.config_entries.async_update_entry(
                other, options={**other.options, CONF_DEFAULT: False}
            )


async def _async_validate(hass: HomeAssistant, zone: str, api_key: str | None) -> None:
    """Try one real fetch so setup fails fast with a clear reason."""
    session = async_get_clientsession(hass)
    await async_fetch_latest(session, zone, api_key)


class GridClockConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Grid Clock."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            zone = user_input[CONF_ZONE]
            api_key = user_input.get(CONF_API_KEY, "").strip() or None

            await self.async_set_unique_id(zone)
            self._abort_if_unique_id_configured()

            try:
                await _async_validate(self.hass, zone, api_key)
            except PermissionError:
                errors["base"] = "invalid_auth"
            except (aiohttp.ClientError, asyncio.TimeoutError):
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating Grid Clock setup")
                errors["base"] = "unknown"
            else:
                make_default = bool(user_input.get(CONF_DEFAULT, False))
                if make_default:
                    _clear_other_defaults(self.hass, None)
                zone_name = _zone_name(zone, self.hass.config.language)
                return self.async_create_entry(
                    title=f"Grid Clock ({zone_name})",
                    data={CONF_ZONE: zone, CONF_API_KEY: api_key},
                    options={CONF_DEFAULT: make_default},
                )

        fields: dict[Any, Any] = {
            vol.Required(CONF_ZONE, default=DEFAULT_ZONE): SelectSelector(
                SelectSelectorConfig(
                    options=_zone_options(self.hass.config.language),
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_API_KEY, default=""): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
        }
        # The "default zone" choice only means something once there are 2+ zones.
        if self._async_current_entries():
            fields[vol.Optional(CONF_DEFAULT, default=False)] = BooleanSelector()
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(fields), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return GridClockOptionsFlow()


class GridClockOptionsFlow(OptionsFlow):
    """Rotate the bearer key and (with 2+ zones) pick the default zone."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        zone = self.config_entry.data[CONF_ZONE]

        if user_input is not None:
            api_key = user_input.get(CONF_API_KEY, "").strip() or None
            try:
                await _async_validate(self.hass, zone, api_key)
            except PermissionError:
                errors["base"] = "invalid_auth"
            except (aiohttp.ClientError, asyncio.TimeoutError):
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating Grid Clock options")
                errors["base"] = "unknown"
            else:
                # Checkbox is hidden with a single zone: keep the stored flag then.
                make_default = bool(
                    user_input.get(
                        CONF_DEFAULT, self.config_entry.options.get(CONF_DEFAULT, False)
                    )
                )
                if make_default:
                    _clear_other_defaults(self.hass, self.config_entry.entry_id)
                return self.async_create_entry(
                    data={CONF_API_KEY: api_key, CONF_DEFAULT: make_default}
                )

        current = self.config_entry.options.get(
            CONF_API_KEY, self.config_entry.data.get(CONF_API_KEY, "")
        )
        fields: dict[Any, Any] = {
            vol.Optional(CONF_API_KEY, default=current or ""): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
        }
        other_zones = [
            e
            for e in self.hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != self.config_entry.entry_id
        ]
        if other_zones:
            preferred = preferred_default_entry(self.hass)
            is_default = (
                preferred is not None
                and preferred.entry_id == self.config_entry.entry_id
            )
            fields[vol.Optional(CONF_DEFAULT, default=is_default)] = BooleanSelector()
        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(fields), errors=errors
        )
