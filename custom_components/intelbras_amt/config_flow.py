"""Config flow for Intelbras AMT integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_HOST,
            description={"suggested_value": ""},
        ): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_PASSWORD): str,
    }
)


class AMTConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Intelbras AMT."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = (user_input.get(CONF_HOST) or "").strip()
            port = user_input[CONF_PORT]
            password = user_input[CONF_PASSWORD]

            # Validate port
            if not 1 <= port <= 65535:
                errors["port"] = "invalid_port"
            elif len(password) < 4:
                errors["password"] = "invalid_password"
            else:
                # If host is provided, run in client mode (HA connects to panel).
                # Otherwise, run in server mode (panel connects to HA).
                if host:
                    await self.async_set_unique_id(f"amt_client_{host}_{port}")
                    user_input[CONF_HOST] = host
                else:
                    await self.async_set_unique_id(f"amt_server_{port}")
                    user_input.pop(CONF_HOST, None)

                self._abort_if_unique_id_configured()

                # Add default scan interval
                user_input[CONF_SCAN_INTERVAL] = DEFAULT_SCAN_INTERVAL

                title = f"AMT ({host}:{port})" if host else f"AMT (porta {port})"
                return self.async_create_entry(
                    title=title,
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "default_port": str(DEFAULT_PORT),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return AMTOptionsFlow(config_entry)


class AMTOptionsFlow(OptionsFlow):
    """Handle options flow for Intelbras AMT."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self._config_entry.options.get(
                            CONF_SCAN_INTERVAL,
                            self._config_entry.data.get(
                                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                            ),
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
                }
            ),
        )
