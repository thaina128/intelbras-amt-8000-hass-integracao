"""Buttons for Intelbras AMT integration."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DATA_CONNECTED,
    DATA_MODEL_NAME,
    DOMAIN,
    ENTITY_PREFIX,
)
from .coordinator import AMTCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up buttons from a config entry."""
    coordinator: AMTCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[ButtonEntity] = []

    # Stay mode button
    entities.append(AMTStayButton(coordinator, entry))

    # Bypass open zones button
    entities.append(AMTBypassOpenZonesButton(coordinator, entry))

    # Siren buttons
    entities.append(AMTSirenOffButton(coordinator, entry))
    entities.append(AMTPanicButton(coordinator, entry))

    async_add_entities(entities)


class AMTButtonBase(CoordinatorEntity[AMTCoordinator], ButtonEntity):
    """Base class for AMT buttons."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AMTCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        model_name = "AMT"
        if self.coordinator.data:
            model_name = self.coordinator.data.get(DATA_MODEL_NAME, "AMT")

        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=f"{ENTITY_PREFIX.upper()} (porta {self._entry.data[CONF_PORT]})",
            manufacturer="Intelbras",
            model=model_name,
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not self.coordinator.data:
            return False
        return self.coordinator.data.get(DATA_CONNECTED, False)


class AMTStayButton(AMTButtonBase):
    """Stay mode button."""

    _attr_name = "Armar Stay"
    _attr_icon = "mdi:shield-home"

    def __init__(
        self,
        coordinator: AMTCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the stay button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_stay"

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_arm_stay()


class AMTBypassOpenZonesButton(AMTButtonBase):
    """Bypass open zones button."""

    _attr_name = "Anular Zonas Abertas"
    _attr_icon = "mdi:shield-link-variant"

    def __init__(
        self,
        coordinator: AMTCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the bypass button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_bypass_open_zones"

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_bypass_open_zones()


class AMTSirenOffButton(AMTButtonBase):
    """Turn the siren off."""

    _attr_name = "Desligar Sirene"
    _attr_icon = "mdi:bullhorn-variant-outline"

    def __init__(
        self,
        coordinator: AMTCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the siren off button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_siren_off"

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_siren_off()


class AMTPanicButton(AMTButtonBase):
    """Audible panic.

    Sends an audible PANIC to the panel, which may be reported to a monitoring
    company. Disabled by default.
    """

    _attr_name = "Pânico Sonoro"
    _attr_icon = "mdi:alarm-light"
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: AMTCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the panic button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_panic"

    async def async_press(self) -> None:
        """Handle button press."""
        await self.coordinator.async_siren_on()
