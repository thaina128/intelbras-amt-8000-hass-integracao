"""DataUpdateCoordinator for Intelbras AMT integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import AMTClientError
from .server import AMTServerError
from .const import (
    DATA_CONNECTED,
    DATA_ZONES_OPEN,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class AMTCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for AMT alarm panel data."""

    def __init__(
        self,
        hass: HomeAssistant,
        backend: Any,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.backend = backend
        self._last_data: dict[str, Any] = {DATA_CONNECTED: False}
        # Client mode has connect/disconnect methods and no server lifecycle methods.
        self._is_client_mode = hasattr(backend, "connect") and not hasattr(backend, "start")

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from AMT alarm panel."""
        try:
            if not self.backend.connected and not self._is_client_mode:
                _LOGGER.debug("Panel not connected, waiting for connection...")
                # Return last known data with connected=False
                self._last_data[DATA_CONNECTED] = False
                return self._last_data

            # In client mode, get_status() will initiate the TCP connection when needed.
            data = await self.backend.get_status()
            self._last_data = data
            return data

        except (AMTServerError, AMTClientError) as err:
            _LOGGER.warning("Error communicating with AMT: %s", err)
            # Return last known data with connected=False
            self._last_data[DATA_CONNECTED] = False
            raise UpdateFailed(f"Error communicating with AMT: {err}") from err

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        if hasattr(self.backend, "stop"):
            await self.backend.stop()
        elif hasattr(self.backend, "disconnect"):
            await self.backend.disconnect()

    async def async_arm(self, code: str | None = None) -> None:
        """Arm the alarm panel."""
        await self.backend.arm(code)
        await self.async_request_refresh()

    async def async_disarm(self, code: str | None = None) -> None:
        """Disarm the alarm panel."""
        await self.backend.disarm(code)
        await self.async_request_refresh()

    async def async_arm_stay(self, code: str | None = None) -> None:
        """Arm in stay mode."""
        await self.backend.arm_stay(code)
        await self.async_request_refresh()

    async def async_arm_partition(self, partition: str, code: str | None = None) -> None:
        """Arm a specific partition."""
        await self.backend.arm_partition(partition, code)
        await self.async_request_refresh()

    async def async_arm_stay_partition(self, partition: str, code: str | None = None) -> None:
        """Arm a specific partition in stay mode."""
        if hasattr(self.backend, "arm_stay_partition"):
            await self.backend.arm_stay_partition(partition, code)
        else:
            await self.backend.arm_partition(partition, code)
        await self.async_request_refresh()

    async def async_disarm_partition(self, partition: str, code: str | None = None) -> None:
        """Disarm a specific partition."""
        await self.backend.disarm_partition(partition, code)
        await self.async_request_refresh()

    async def async_activate_pgm(self, pgm_number: int) -> None:
        """Activate a PGM output."""
        await self.backend.activate_pgm(pgm_number)
        await self.async_request_refresh()

    async def async_deactivate_pgm(self, pgm_number: int) -> None:
        """Deactivate a PGM output."""
        await self.backend.deactivate_pgm(pgm_number)
        await self.async_request_refresh()

    async def async_bypass_open_zones(self) -> None:
        """Bypass all currently open zones."""
        if self.data and DATA_CONNECTED in self.data:
            open_zones = self.data.get(DATA_ZONES_OPEN, [])
            await self.backend.bypass_open_zones(open_zones)
            await self.async_request_refresh()

    async def async_siren_on(self) -> None:
        """Turn siren on."""
        await self.backend.siren_on()
        await self.async_request_refresh()

    async def async_siren_off(self) -> None:
        """Turn siren off."""
        await self.backend.siren_off()
        await self.async_request_refresh()
