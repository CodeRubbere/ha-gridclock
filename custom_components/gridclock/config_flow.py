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
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import CONF_API_KEY, CONF_ZONE, DEFAULT_ZONE, DOMAIN, ZONES
from .coordinator import async_fetch_latest

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
                zone_name = _zone_name(zone, self.hass.config.language)
                return self.async_create_entry(
                    title=f"Grid Clock ({zone_name})",
                    data={CONF_ZONE: zone, CONF_API_KEY: api_key},
                )

        schema = vol.Schema(
            {
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
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return GridClockOptionsFlow()


class GridClockOptionsFlow(OptionsFlow):
    """Let the bearer key be rotated without deleting and re-adding the zone."""

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
                return self.async_create_entry(data={CONF_API_KEY: api_key})

        current = self.config_entry.options.get(
            CONF_API_KEY, self.config_entry.data.get(CONF_API_KEY, "")
        )
        schema = vol.Schema(
            {
                vol.Optional(CONF_API_KEY, default=current or ""): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
