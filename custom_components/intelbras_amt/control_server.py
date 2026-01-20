"""HTTP control server for CLI access to AMT panel."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import web

from .const import DEFAULT_CONTROL_PORT
from .server import AMTServer

_LOGGER = logging.getLogger(__name__)


class AMTControlServer:
    """HTTP REST API server for controlling AMT panel via CLI."""

    def __init__(self, amt_server: AMTServer, port: int = DEFAULT_CONTROL_PORT) -> None:
        """Initialize the control server.

        Args:
            amt_server: The AMT server instance to control
            port: HTTP port to listen on (default: 9019)
        """
        self._amt_server = amt_server
        self._port = port
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None

    @property
    def port(self) -> int:
        """Return the configured port."""
        return self._port

    async def start(self) -> None:
        """Start the HTTP control server."""
        self._app = web.Application()
        self._setup_routes()

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "0.0.0.0", self._port)
        await site.start()
        _LOGGER.info("AMT control server started on port %s", self._port)

    async def stop(self) -> None:
        """Stop the HTTP control server."""
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
            self._app = None
        _LOGGER.info("AMT control server stopped")

    def _setup_routes(self) -> None:
        """Set up HTTP routes."""
        assert self._app is not None
        self._app.router.add_get("/status", self._handle_status)
        self._app.router.add_get("/connected", self._handle_connected)
        self._app.router.add_post("/command/raw", self._handle_raw_command)
        self._app.router.add_post("/command/arm", self._handle_arm)
        self._app.router.add_post("/command/disarm", self._handle_disarm)
        self._app.router.add_post("/command/stay", self._handle_stay)
        self._app.router.add_post("/command/siren", self._handle_siren)
        self._app.router.add_post("/command/pgm", self._handle_pgm)

    async def _handle_status(self, request: web.Request) -> web.Response:
        """GET /status - Get current panel status."""
        if not self._amt_server.connected:
            return web.json_response(
                {"connected": False, "error": "No panel connected"},
                status=503,
            )

        try:
            status = await self._amt_server.get_status()
            # Convert non-JSON-serializable types
            status_json = self._status_to_json(status)
            return web.json_response({"connected": True, "status": status_json})
        except Exception as e:
            _LOGGER.error("Error getting status: %s", e)
            return web.json_response(
                {"connected": True, "error": str(e)},
                status=500,
            )

    async def _handle_connected(self, request: web.Request) -> web.Response:
        """GET /connected - Check if panel is connected."""
        return web.json_response({"connected": self._amt_server.connected})

    async def _handle_raw_command(self, request: web.Request) -> web.Response:
        """POST /command/raw - Send raw hex command.

        Body: {"command": "41 35", "password": "1234"}
        """
        if not self._amt_server.connected:
            return web.json_response(
                {"success": False, "error": "No panel connected"},
                status=503,
            )

        try:
            data = await request.json()
        except Exception:
            return web.json_response(
                {"success": False, "error": "Invalid JSON body"},
                status=400,
            )

        command = data.get("command")
        if not command:
            return web.json_response(
                {"success": False, "error": "Missing 'command' field"},
                status=400,
            )

        password = data.get("password")
        result = await self._amt_server.send_raw_command(command, password)
        status_code = 200 if result.get("success") else 400
        return web.json_response(result, status=status_code)

    async def _handle_arm(self, request: web.Request) -> web.Response:
        """POST /command/arm - Arm panel/partition.

        Body: {"partition": "A", "stay": false, "password": "1234"}
        """
        if not self._amt_server.connected:
            return web.json_response(
                {"success": False, "error": "No panel connected"},
                status=503,
            )

        try:
            data = await request.json()
        except Exception:
            return web.json_response(
                {"success": False, "error": "Invalid JSON body"},
                status=400,
            )

        partition = data.get("partition")
        stay = data.get("stay", False)
        password = data.get("password")

        try:
            if partition:
                # Arm specific partition
                if stay:
                    await self._amt_server.arm_stay_partition(partition.upper(), password)
                else:
                    await self._amt_server.arm_partition(partition.upper(), password)
            else:
                # Arm main panel
                if stay:
                    await self._amt_server.arm_stay(password)
                else:
                    await self._amt_server.arm(password)

            return web.json_response({"success": True})
        except Exception as e:
            return web.json_response(
                {"success": False, "error": str(e)},
                status=400,
            )

    async def _handle_disarm(self, request: web.Request) -> web.Response:
        """POST /command/disarm - Disarm panel/partition.

        Body: {"partition": "A", "password": "1234"}
        """
        if not self._amt_server.connected:
            return web.json_response(
                {"success": False, "error": "No panel connected"},
                status=503,
            )

        try:
            data = await request.json()
        except Exception:
            return web.json_response(
                {"success": False, "error": "Invalid JSON body"},
                status=400,
            )

        partition = data.get("partition")
        password = data.get("password")

        try:
            if partition:
                await self._amt_server.disarm_partition(partition.upper(), password)
            else:
                await self._amt_server.disarm(password)

            return web.json_response({"success": True})
        except Exception as e:
            return web.json_response(
                {"success": False, "error": str(e)},
                status=400,
            )

    async def _handle_stay(self, request: web.Request) -> web.Response:
        """POST /command/stay - Arm in stay mode.

        Body: {"password": "1234"}
        """
        if not self._amt_server.connected:
            return web.json_response(
                {"success": False, "error": "No panel connected"},
                status=503,
            )

        try:
            data = await request.json()
        except Exception:
            data = {}

        password = data.get("password")

        try:
            await self._amt_server.arm_stay(password)
            return web.json_response({"success": True})
        except Exception as e:
            return web.json_response(
                {"success": False, "error": str(e)},
                status=400,
            )

    async def _handle_siren(self, request: web.Request) -> web.Response:
        """POST /command/siren - Control siren.

        Body: {"action": "on" | "off"}
        """
        if not self._amt_server.connected:
            return web.json_response(
                {"success": False, "error": "No panel connected"},
                status=503,
            )

        try:
            data = await request.json()
        except Exception:
            return web.json_response(
                {"success": False, "error": "Invalid JSON body"},
                status=400,
            )

        action = data.get("action")
        if action not in ("on", "off"):
            return web.json_response(
                {"success": False, "error": "Action must be 'on' or 'off'"},
                status=400,
            )

        try:
            if action == "on":
                await self._amt_server.siren_on()
            else:
                await self._amt_server.siren_off()

            return web.json_response({"success": True})
        except Exception as e:
            return web.json_response(
                {"success": False, "error": str(e)},
                status=400,
            )

    async def _handle_pgm(self, request: web.Request) -> web.Response:
        """POST /command/pgm - Control PGM output.

        Body: {"number": 1, "action": "on" | "off"}
        """
        if not self._amt_server.connected:
            return web.json_response(
                {"success": False, "error": "No panel connected"},
                status=503,
            )

        try:
            data = await request.json()
        except Exception:
            return web.json_response(
                {"success": False, "error": "Invalid JSON body"},
                status=400,
            )

        number = data.get("number")
        action = data.get("action")

        if not isinstance(number, int) or number < 1 or number > 19:
            return web.json_response(
                {"success": False, "error": "PGM number must be 1-19"},
                status=400,
            )

        if action not in ("on", "off"):
            return web.json_response(
                {"success": False, "error": "Action must be 'on' or 'off'"},
                status=400,
            )

        try:
            if action == "on":
                await self._amt_server.activate_pgm(number)
            else:
                await self._amt_server.deactivate_pgm(number)

            return web.json_response({"success": True})
        except Exception as e:
            return web.json_response(
                {"success": False, "error": str(e)},
                status=400,
            )

    def _status_to_json(self, status: dict[str, Any]) -> dict[str, Any]:
        """Convert status dict to JSON-serializable format."""
        result = {}
        for key, value in status.items():
            if isinstance(value, list):
                # Convert lists (zones, PGMs) - include only active ones for compactness
                if key in ("zones_open", "zones_violated", "zones_bypassed",
                          "zones_tamper", "zones_short_circuit", "zones_low_battery"):
                    # Return list of zone numbers that are True
                    result[key] = [i + 1 for i, v in enumerate(value) if v]
                elif key == "pgms":
                    # Return list of PGM numbers that are True
                    result[key] = [i + 1 for i, v in enumerate(value) if v]
                else:
                    result[key] = value
            elif isinstance(value, dict):
                result[key] = value
            else:
                result[key] = value
        return result
