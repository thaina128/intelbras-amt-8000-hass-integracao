"""DataUpdateCoordinator for Intelbras AMT integration."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import AMTClient, AMTClientError
from .const import (
    DATA_CONNECTED,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    RECONNECT_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class AMTCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for AMT alarm panel data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: AMTClient,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self._reconnect_task: asyncio.Task | None = None
        self._last_data: dict[str, Any] = {DATA_CONNECTED: False}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from AMT alarm panel."""
        try:
            if not self.client.connected:
                await self.client.connect()

            data = await self.client.get_status()
            self._last_data = data
            return data

        except AMTClientError as err:
            _LOGGER.warning("Error communicating with AMT: %s", err)
            # Return last known data with connected=False
            self._last_data[DATA_CONNECTED] = False
            # Schedule reconnect
            self._schedule_reconnect()
            raise UpdateFailed(f"Error communicating with AMT: {err}") from err

    def _schedule_reconnect(self) -> None:
        """Schedule a reconnection attempt."""
        if self._reconnect_task and not self._reconnect_task.done():
            return  # Already scheduled

        async def reconnect() -> None:
            """Attempt to reconnect."""
            await asyncio.sleep(RECONNECT_INTERVAL)
            try:
                await self.client.disconnect()
                await self.client.connect()
                _LOGGER.info("Reconnected to AMT")
                await self.async_request_refresh()
            except AMTClientError as err:
                _LOGGER.warning("Reconnection failed: %s", err)
                self._schedule_reconnect()

        self._reconnect_task = self.hass.async_create_task(reconnect())

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass

        await self.client.disconnect()

    async def async_arm(self, code: str | None = None) -> None:
        """Arm the alarm panel."""
        await self.client.arm(code)
        await self.async_request_refresh()

    async def async_disarm(self, code: str | None = None) -> None:
        """Disarm the alarm panel."""
        await self.client.disarm(code)
        await self.async_request_refresh()

    async def async_arm_stay(self, code: str | None = None) -> None:
        """Arm in stay mode."""
        await self.client.arm_stay(code)
        await self.async_request_refresh()

    async def async_arm_partition(self, partition: str, code: str | None = None) -> None:
        """Arm a specific partition."""
        await self.client.arm_partition(partition, code)
        await self.async_request_refresh()

    async def async_disarm_partition(self, partition: str, code: str | None = None) -> None:
        """Disarm a specific partition."""
        await self.client.disarm_partition(partition, code)
        await self.async_request_refresh()

    async def async_activate_pgm(self, pgm_number: int) -> None:
        """Activate a PGM output."""
        await self.client.activate_pgm(pgm_number)
        await self.async_request_refresh()

    async def async_deactivate_pgm(self, pgm_number: int) -> None:
        """Deactivate a PGM output."""
        await self.client.deactivate_pgm(pgm_number)
        await self.async_request_refresh()

    async def async_bypass_open_zones(self) -> None:
        """Bypass all currently open zones."""
        if self.data and DATA_CONNECTED in self.data:
            from .const import DATA_ZONES_OPEN
            open_zones = self.data.get(DATA_ZONES_OPEN, [])
            await self.client.bypass_open_zones(open_zones)
            await self.async_request_refresh()

    async def async_siren_on(self) -> None:
        """Turn siren on."""
        await self.client.siren_on()
        await self.async_request_refresh()

    async def async_siren_off(self) -> None:
        """Turn siren off."""
        await self.client.siren_off()
        await self.async_request_refresh()
