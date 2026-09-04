"""DataUpdateCoordinator for Grid Clock."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    API_BASE,
    API_SCHEMA,
    PRICE_UNIT_DIVISOR,
    REQUEST_TIMEOUT,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class PricePoint:
    """One quarter-hour (or whatever resolution the zone publishes) price slot."""

    start: datetime
    price: float  # ct/kWh


@dataclass
class GridClockData:
    """Parsed contents of v1/prices/{zone}/latest.json."""

    zone: str
    resolution_minutes: int
    published_at: datetime | None
    stale: bool
    prices: list[PricePoint]

    @property
    def known_until(self) -> datetime | None:
        """End of the last known price slot."""
        if not self.prices:
            return None
        last = self.prices[-1]
        return last.start + timedelta(minutes=self.resolution_minutes)

    def price_at(self, moment: datetime) -> float | None:
        """Price of the slot that contains ``moment``, or None if unknown."""
        for point in self.prices:
            end = point.start + timedelta(minutes=self.resolution_minutes)
            if point.start <= moment < end:
                return point.price
        return None


def _build_headers(api_key: str | None) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


async def async_fetch_latest(
    session: aiohttp.ClientSession, zone: str, api_key: str | None
) -> dict:
    """Fetch and return the raw latest.json payload for a zone.

    Raises aiohttp.ClientError / asyncio.TimeoutError / ValueError on failure -
    callers translate those into the appropriate HA-facing error.
    """
    url = f"{API_BASE}/{API_SCHEMA}/prices/{zone}/latest.json"
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
    async with session.get(url, headers=_build_headers(api_key), timeout=timeout) as resp:
        if resp.status == 401 or resp.status == 403:
            raise PermissionError(f"Grid Clock CDN rejected the bearer key ({resp.status})")
        resp.raise_for_status()
        return await resp.json(content_type=None)


def _parse(zone: str, payload: dict) -> GridClockData:
    resolution = int(payload["resolution_minutes"])
    published_at = dt_util.parse_datetime(payload.get("published_at", ""))

    points: list[PricePoint] = []
    for day in payload.get("days", []):
        start = dt_util.parse_datetime(day["start"])
        if start is None:
            continue
        for index, raw_value in enumerate(day.get("values", [])):
            slot_start = start + timedelta(minutes=resolution * index)
            points.append(
                PricePoint(start=slot_start, price=raw_value / PRICE_UNIT_DIVISOR)
            )

    points.sort(key=lambda p: p.start)

    return GridClockData(
        zone=zone,
        resolution_minutes=resolution,
        published_at=published_at,
        stale=bool(payload.get("stale", False)),
        prices=points,
    )


class GridClockCoordinator(DataUpdateCoordinator[GridClockData]):
    """Polls cdn.gridclock.eu for one bidding zone."""

    def __init__(self, hass: HomeAssistant, zone: str, api_key: str | None) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"Grid Clock ({zone})",
            update_interval=UPDATE_INTERVAL,
        )
        self.zone = zone
        self.api_key = api_key

    async def _async_update_data(self) -> GridClockData:
        session = async_get_clientsession(self.hass)
        try:
            payload = await async_fetch_latest(session, self.zone, self.api_key)
        except PermissionError as err:
            raise UpdateFailed(str(err)) from err
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise UpdateFailed(f"Could not reach cdn.gridclock.eu: {err}") from err
        except (ValueError, KeyError) as err:
            raise UpdateFailed(f"Unexpected response from cdn.gridclock.eu: {err}") from err

        return _parse(self.zone, payload)
