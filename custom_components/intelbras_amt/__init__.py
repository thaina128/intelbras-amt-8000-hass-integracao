"""Intelbras AMT Alarm integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .client import AMTClient
from .control_server import AMTControlServer
from .server import AMTServer
from .const import (
    CONF_PASSWORD_A,
    CONF_PASSWORD_B,
    CONF_PASSWORD_C,
    CONF_PASSWORD_D,
    CONF_SCAN_INTERVAL,
    DEFAULT_CONTROL_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import AMTCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.ALARM_CONTROL_PANEL,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Intelbras AMT from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    host = (entry.data.get(CONF_HOST) or "").strip()
    port = entry.data[CONF_PORT]
    password = entry.data[CONF_PASSWORD]

    # Client mode: HA connects to panel host:port
    # Server mode: panel connects to HA on port
    if host:
        backend = AMTClient(
            host=host,
            port=port,
            password=password,
        )
        mode = "client"
    else:
        backend = AMTServer(
            port=port,
            password=password,
        )
        await backend.start()
        mode = "server"

    # Set partition passwords if configured
    backend.set_partition_passwords(
        password_a=entry.data.get(CONF_PASSWORD_A),
        password_b=entry.data.get(CONF_PASSWORD_B),
        password_c=entry.data.get(CONF_PASSWORD_C),
        password_d=entry.data.get(CONF_PASSWORD_D),
    )

    # Start control server for CLI access
    control_server = AMTControlServer(backend, DEFAULT_CONTROL_PORT)
    await control_server.start()

    # Get scan interval from options or data
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )

    # Create coordinator
    coordinator = AMTCoordinator(hass, backend, scan_interval)

    # Don't wait for first refresh - panel may not be connected yet
    # The coordinator will return disconnected status until panel connects
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "control_server": control_server,
        "backend": backend,
    }

    # Forward entry setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for options
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    _LOGGER.info(
        "Intelbras AMT integration started in %s mode (%s), control port=%s",
        mode,
        f"{host}:{port}" if host else f"porta {port}",
        DEFAULT_CONTROL_PORT,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator: AMTCoordinator = data["coordinator"]
        control_server: AMTControlServer = data["control_server"]
        await control_server.stop()
        await coordinator.async_shutdown()

    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
