"""AMT TCP protocol client (ISECNet2)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .const import (
    CONNECTION_TIMEOUT,
    DATA_AC_POWER,
    DATA_ARMED,
    DATA_AUX_OVERLOAD,
    DATA_BATTERY_ABSENT,
    DATA_BATTERY_CONNECTED,
    DATA_BATTERY_LEVEL,
    DATA_BATTERY_LOW,
    DATA_BATTERY_SHORT,
    DATA_COMM_FAILURE,
    DATA_CONNECTED,
    DATA_DATETIME,
    DATA_FIRMWARE,
    DATA_MAX_ZONES,
    DATA_MODEL_ID,
    DATA_MODEL_NAME,
    DATA_PARTITIONS,
    DATA_PGMS,
    DATA_PHONE_LINE_CUT,
    DATA_PROBLEM,
    DATA_SIREN,
    DATA_SIREN_SHORT,
    DATA_SIREN_WIRE_CUT,
    DATA_STAY,
    DATA_TRIGGERED,
    DATA_ZONES_BYPASSED,
    DATA_ZONES_BYPASSED_COUNT,
    DATA_ZONES_LOW_BATTERY,
    DATA_ZONES_OPEN,
    DATA_ZONES_OPEN_COUNT,
    DATA_ZONES_SHORT_CIRCUIT,
    DATA_ZONES_TAMPER,
    DATA_ZONES_VIOLATED,
    DATA_ZONES_VIOLATED_COUNT,
    MAX_PGMS,
    MAX_ZONES_4010,
    MAX_ZONES_LOW_BATTERY,
    MAX_ZONES_SHORT_CIRCUIT,
    MAX_ZONES_TAMPER,
    NACK_MESSAGES,
)

_LOGGER = logging.getLogger(__name__)

# ISECNet2 commands
CMD_AUTH = 0xF0F0
CMD_BYE = 0xF0F1
CMD_STATUS = 0x0B4A
CMD_ARM_DISARM = 0x401E
CMD_PANIC = 0x401A
CMD_PGM = 0x401C
CMD_SIREN_OFF = 0x4019
CMD_BYPASS_ZONE = 0x401F

# ISECNet2 special responses
CMD_ACK = 0xF0FE
CMD_NACK = 0xF0FD
CMD_BUSY = 0xF0F7

# AMT status payload offsets (zero-based, without protocol header)
OFFSET_STATUS = 20
OFFSET_PARTITIONS_START = 21
OFFSET_OPEN_ZONES_START = 38
OFFSET_VIOLATED_ZONES_START = 46
OFFSET_BYPASSED_ZONES_START = 54
OFFSET_TAMPER_STATUS = 71
OFFSET_BATTERY_STATUS = 134

# Panel status bit masks (payload[20])
BIT_STATUS_PROBLEM = 0x01
BIT_STATUS_SIREN = 0x02
BIT_STATUS_ALL_ZONES_CLOSED = 0x04
BIT_STATUS_ZONES_FIRING = 0x08
BIT_STATUS_ZONES_BYPASSED = 0x10

# Partition status bits (payload[21..37])
BIT_PART_ENABLED = 0x80
BIT_PART_STAY_ALT = 0x40
BIT_PART_EXIT_DELAY = 0x20
BIT_PART_READY = 0x10
BIT_PART_ALARM_OCCURRED = 0x08
BIT_PART_TRIGGERED = 0x04
BIT_PART_STAY = 0x02
BIT_PART_ARMED = 0x01

# Battery codes (payload[134])
BATTERY_DEAD = 0x01
BATTERY_LOW = 0x02
BATTERY_MIDDLE = 0x03
BATTERY_FULL = 0x04

# Alarm state (status byte bits 5..6)
ALARM_DISARMED = 0x00
ALARM_PARTIAL = 0x01
ALARM_ALL = 0x03

MODEL_NAMES = {
    0x01: "AMT-8000",
    0x38: "AMT 1016",
    0x39: "AMT 2018",
    0x41: "AMT 4010 SMART",
}


class AMTClientError(Exception):
    """Base exception for AMT client errors."""


class AMTConnectionError(AMTClientError):
    """Connection error."""


class AMTProtocolError(AMTClientError):
    """Protocol error."""


class AMTNackError(AMTClientError):
    """NACK response received from the alarm panel."""

    def __init__(self, nack_code: int, message: str | None = None) -> None:
        """Initialize the NACK error."""
        self.nack_code = nack_code
        self.message = message or NACK_MESSAGES.get(nack_code, f"Erro desconhecido (0x{nack_code:02X})")
        super().__init__(self.message)


class AMTClient:
    """AMT TCP protocol client using ISECNet2."""

    def __init__(self, host: str, port: int, password: str) -> None:
        """Initialize the AMT client."""
        self._host = host
        self._port = port
        self._password = password
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()
        self._connected = False
        self._authenticated = False
        self._auth_password: str | None = None
        self._partition_passwords: dict[str, str] = {}

    def set_partition_passwords(
        self,
        password_a: str | None = None,
        password_b: str | None = None,
        password_c: str | None = None,
        password_d: str | None = None,
    ) -> None:
        """Set partition passwords."""
        if password_a:
            self._partition_passwords["A"] = password_a
        if password_b:
            self._partition_passwords["B"] = password_b
        if password_c:
            self._partition_passwords["C"] = password_c
        if password_d:
            self._partition_passwords["D"] = password_d

    @property
    def connected(self) -> bool:
        """Return connection status."""
        return self._connected

    async def connect(self) -> None:
        """Connect to the AMT alarm panel."""
        if self._connected and self._reader and self._writer:
            return

        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=CONNECTION_TIMEOUT,
            )
            self._connected = True
            self._authenticated = False
            self._auth_password = None
            _LOGGER.debug("Connected to AMT at %s:%s", self._host, self._port)
        except asyncio.TimeoutError as err:
            raise AMTConnectionError(
                f"Connection timeout to {self._host}:{self._port}"
            ) from err
        except OSError as err:
            raise AMTConnectionError(
                f"Connection failed to {self._host}:{self._port}: {err}"
            ) from err

    async def disconnect(self) -> None:
        """Disconnect from the AMT alarm panel."""
        if self._writer:
            try:
                if self._authenticated:
                    bye_packet = self._build_packet(CMD_BYE, b"")
                    self._writer.write(bye_packet)
                    await self._writer.drain()
            except Exception:  # noqa: BLE001
                pass

            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:  # noqa: BLE001
                pass

        self._writer = None
        self._reader = None
        self._connected = False
        self._authenticated = False
        self._auth_password = None

    def _checksum(self, data: bytes) -> int:
        """Calculate ISECNet2 checksum (xor all bytes then xor 0xFF)."""
        checksum = 0
        for byte in data:
            checksum ^= byte
        checksum ^= 0xFF
        return checksum & 0xFF

    def _be16(self, value: int) -> bytes:
        """Encode uint16 big-endian."""
        return bytes([(value >> 8) & 0xFF, value & 0xFF])

    def _from_be16(self, raw: bytes) -> int:
        """Decode uint16 big-endian."""
        return (raw[0] << 8) | raw[1]

    def _normalize_password(self, password: str) -> str:
        """Normalize password to 4 or 6 digits for Contact-ID encoding."""
        digits = "".join(ch for ch in password if ch.isdigit())
        if len(digits) in (4, 6):
            return digits

        # Central accepts fixed-length contact-id digits; default to 6.
        return digits[-6:].rjust(6, "0")

    def _encode_contact_id_digits(self, password: str) -> bytes:
        """Encode password as Contact-ID digits (0 -> 0x0A)."""
        normalized = self._normalize_password(password)
        encoded = []
        for ch in normalized:
            digit = int(ch)
            encoded.append(0x0A if digit == 0 else digit)
        return bytes(encoded)

    def _build_packet(self, command: int, payload: bytes) -> bytes:
        """Build ISECNet2 packet."""
        # dst_id=0x0000, src_id=0x8FFF
        packet_no_checksum = (
            self._be16(0x0000)
            + self._be16(0x8FFF)
            + self._be16(len(payload) + 2)
            + self._be16(command)
            + payload
        )
        return packet_no_checksum + bytes([self._checksum(packet_no_checksum)])

    async def _read_packet(self) -> tuple[int, bytes]:
        """Read exactly one ISECNet2 packet and return (cmd, payload)."""
        if not self._reader:
            raise AMTConnectionError("Not connected")

        try:
            header = await asyncio.wait_for(
                self._reader.readexactly(6),
                timeout=CONNECTION_TIMEOUT,
            )
            body_length = self._from_be16(header[4:6])
            body = await asyncio.wait_for(
                self._reader.readexactly(body_length + 1),
                timeout=CONNECTION_TIMEOUT,
            )
        except asyncio.IncompleteReadError as err:
            raise AMTConnectionError("Connection closed by remote") from err
        except asyncio.TimeoutError as err:
            raise AMTConnectionError("Response timeout") from err
        except OSError as err:
            raise AMTConnectionError(f"Communication error: {err}") from err

        packet = header + body
        if self._checksum(packet) != 0x00:
            raise AMTProtocolError("Invalid checksum in response")

        command = self._from_be16(body[0:2])
        payload = body[2:-1]
        return command, payload

    async def _send_packet(self, command: int, payload: bytes) -> tuple[int, bytes]:
        """Send one packet and read one packet."""
        if not self._writer:
            raise AMTConnectionError("Not connected")

        packet = self._build_packet(command, payload)
        _LOGGER.debug("Sending ISEC packet cmd=0x%04X payload=%s", command, payload.hex())

        try:
            self._writer.write(packet)
            await self._writer.drain()
            response_command, response_payload = await self._read_packet()
            _LOGGER.debug(
                "Received ISEC packet cmd=0x%04X payload=%s",
                response_command,
                response_payload.hex(),
            )
            return response_command, response_payload
        except Exception:
            self._connected = False
            self._authenticated = False
            self._auth_password = None
            raise

    async def _authenticate_locked(self, password: str) -> None:
        """Authenticate current connection using given password."""
        if self._authenticated and self._auth_password == password:
            return

        encoded_password = self._encode_contact_id_digits(password)
        payload = bytes([0x02]) + encoded_password + bytes([0x10])

        response_command, response_payload = await self._send_packet(CMD_AUTH, payload)

        if response_command == CMD_NACK:
            nack_code = response_payload[0] if response_payload else 0x00
            raise AMTNackError(nack_code)

        if response_command != CMD_AUTH:
            raise AMTProtocolError(
                f"Unexpected auth response command: 0x{response_command:04X}"
            )

        if len(response_payload) != 1:
            raise AMTProtocolError("Invalid auth response payload")

        auth_result = response_payload[0]
        if auth_result == 0:
            self._authenticated = True
            self._auth_password = password
            return

        # Known Intelbras auth result codes
        auth_errors = {
            1: "Senha incorreta",
            2: "Versão de software incorreta",
            3: "Central solicitou callback",
            4: "Aguardando permissão do usuário",
        }
        raise AMTProtocolError(auth_errors.get(auth_result, f"Falha de autenticação ({auth_result})"))

    async def _ensure_authenticated_locked(self, password: str) -> None:
        """Ensure connection and authentication are active for given password."""
        if not self._connected:
            await self.connect()

        if self._authenticated and self._auth_password == password:
            return

        if self._authenticated and self._auth_password != password:
            await self.disconnect()
            await self.connect()

        await self._authenticate_locked(password)

    async def _send_command(self, command: int, payload: bytes = b"", password: str | None = None) -> bytes:
        """Send an ISEC command and return payload."""
        cmd_password = password or self._password

        async with self._lock:
            try:
                await self._ensure_authenticated_locked(cmd_password)

                response_command, response_payload = await self._send_packet(command, payload)

                # Some commands may return ACK first and payload on the next packet.
                for _ in range(2):
                    if response_command == CMD_BUSY:
                        raise AMTConnectionError("Central ocupada")

                    if response_command == CMD_NACK:
                        nack_code = response_payload[0] if response_payload else 0x00
                        raise AMTNackError(nack_code)

                    if response_command == command:
                        return response_payload

                    if response_command == CMD_ACK:
                        # ACK is enough for control commands.
                        if command != CMD_STATUS:
                            return response_payload
                        # Status should include full payload; keep waiting once.
                        response_command, response_payload = await self._read_packet()
                        continue

                    raise AMTProtocolError(
                        f"Unexpected response command: 0x{response_command:04X}"
                    )

                raise AMTProtocolError("No status payload received after ACK")

            except (AMTConnectionError, AMTProtocolError, AMTNackError):
                # Force fresh socket on next operation.
                await self.disconnect()
                raise

    def _partition_number(self, partition: str) -> int:
        """Map partition letter to protocol number."""
        mapping = {"A": 1, "B": 2, "C": 3, "D": 4}
        part = partition.upper().strip()
        if part not in mapping:
            raise ValueError(f"Invalid partition: {partition}")
        return mapping[part]

    def _parse_zone_bits(self, zone_bytes: bytes, max_zones: int) -> list[bool]:
        """Parse bit-packed zones to bool list."""
        zones: list[bool] = [False] * max_zones
        for byte_idx, byte in enumerate(zone_bytes):
            for bit in range(8):
                zone_idx = byte_idx * 8 + bit
                if zone_idx >= max_zones:
                    break
                zones[zone_idx] = bool(byte & (1 << bit))
        return zones

    def _parse_partition(self, part_byte: int, fallback_armed: bool = False, fallback_stay: bool = False, fallback_triggered: bool = False) -> dict[str, bool]:
        """Parse one partition status byte."""
        if not (part_byte & BIT_PART_ENABLED):
            return {
                "armed": fallback_armed,
                "stay": fallback_stay,
                "triggered": fallback_triggered,
            }

        return {
            "armed": bool(part_byte & BIT_PART_ARMED),
            "stay": bool(part_byte & BIT_PART_STAY or part_byte & BIT_PART_STAY_ALT),
            "triggered": bool(part_byte & BIT_PART_TRIGGERED or part_byte & BIT_PART_ALARM_OCCURRED),
        }

    def _parse_firmware(self, payload: bytes) -> str:
        """Best-effort firmware parsing."""
        # Some panels prepend one byte before model/version.
        model_candidate = payload[0] if len(payload) > 0 else 0
        if model_candidate in MODEL_NAMES and len(payload) >= 4:
            return f"{payload[1]}.{payload[2]}.{payload[3]}"

        if len(payload) >= 5:
            return f"{payload[2]}.{payload[3]}.{payload[4]}"

        return "unknown"

    def _parse_model(self, payload: bytes) -> tuple[int, str]:
        """Best-effort model parsing."""
        model_id = payload[0] if len(payload) > 0 else 0
        if model_id not in MODEL_NAMES and len(payload) > 1 and payload[1] in MODEL_NAMES:
            model_id = payload[1]

        model_name = MODEL_NAMES.get(model_id, f"Unknown (0x{model_id:02X})")
        return model_id, model_name

    def _parse_response(self, payload: bytes) -> dict[str, Any]:
        """Parse 0x0B4A status payload into coordinator data."""
        if len(payload) < OFFSET_STATUS + 1:
            raise AMTProtocolError(f"Status payload too short: {len(payload)} bytes")

        model_id, model_name = self._parse_model(payload)
        firmware = self._parse_firmware(payload)

        status_byte = payload[OFFSET_STATUS]

        armed_state = (status_byte >> 5) & 0x03
        armed = armed_state in (ALARM_PARTIAL, ALARM_ALL)
        stay = armed_state == ALARM_PARTIAL
        triggered = bool(status_byte & BIT_STATUS_ZONES_FIRING)
        siren = bool(status_byte & BIT_STATUS_SIREN)
        problem = bool(status_byte & BIT_STATUS_PROBLEM)

        part_bytes = payload[OFFSET_PARTITIONS_START : OFFSET_PARTITIONS_START + 4]
        while len(part_bytes) < 4:
            part_bytes += b"\x00"

        partitions = {
            "A": self._parse_partition(part_bytes[0], armed, stay, triggered),
            "B": self._parse_partition(part_bytes[1]),
            "C": self._parse_partition(part_bytes[2]),
            "D": self._parse_partition(part_bytes[3]),
        }

        max_zones = MAX_ZONES_4010
        zones_open = self._parse_zone_bits(
            payload[OFFSET_OPEN_ZONES_START : OFFSET_OPEN_ZONES_START + 8],
            max_zones,
        )
        zones_violated = self._parse_zone_bits(
            payload[OFFSET_VIOLATED_ZONES_START : OFFSET_VIOLATED_ZONES_START + 8],
            max_zones,
        )
        zones_bypassed = self._parse_zone_bits(
            payload[OFFSET_BYPASSED_ZONES_START : OFFSET_BYPASSED_ZONES_START + 8],
            max_zones,
        )

        zones_open_count = sum(zones_open)
        zones_violated_count = sum(zones_violated)
        zones_bypassed_count = sum(zones_bypassed)

        battery_code = payload[OFFSET_BATTERY_STATUS] if len(payload) > OFFSET_BATTERY_STATUS else 0
        battery_level_map = {
            BATTERY_DEAD: 5,
            BATTERY_LOW: 25,
            BATTERY_MIDDLE: 60,
            BATTERY_FULL: 100,
        }
        battery_level = battery_level_map.get(battery_code, 0)
        battery_low = battery_code in (BATTERY_DEAD, BATTERY_LOW)

        tamper_flag = False
        if len(payload) > OFFSET_TAMPER_STATUS:
            tamper_flag = bool(payload[OFFSET_TAMPER_STATUS] & 0x02)

        zones_tamper = [False] * MAX_ZONES_TAMPER
        zones_short_circuit = [False] * MAX_ZONES_SHORT_CIRCUIT
        zones_low_battery = [False] * MAX_ZONES_LOW_BATTERY

        pgms = [False] * MAX_PGMS

        return {
            DATA_CONNECTED: True,
            DATA_MODEL_ID: model_id,
            DATA_MODEL_NAME: model_name,
            DATA_MAX_ZONES: max_zones,
            DATA_FIRMWARE: firmware,
            DATA_ZONES_OPEN: zones_open,
            DATA_ZONES_VIOLATED: zones_violated,
            DATA_ZONES_BYPASSED: zones_bypassed,
            DATA_ZONES_TAMPER: zones_tamper,
            DATA_ZONES_SHORT_CIRCUIT: zones_short_circuit,
            DATA_ZONES_LOW_BATTERY: zones_low_battery,
            DATA_ZONES_OPEN_COUNT: zones_open_count,
            DATA_ZONES_VIOLATED_COUNT: zones_violated_count,
            DATA_ZONES_BYPASSED_COUNT: zones_bypassed_count,
            DATA_PARTITIONS: partitions,
            DATA_ARMED: armed,
            DATA_STAY: stay,
            DATA_TRIGGERED: triggered,
            DATA_AC_POWER: True,
            DATA_BATTERY_CONNECTED: battery_code != BATTERY_DEAD,
            DATA_BATTERY_LEVEL: battery_level,
            DATA_SIREN: siren,
            DATA_PGMS: pgms,
            DATA_PROBLEM: problem or tamper_flag or battery_low,
            DATA_BATTERY_LOW: battery_low,
            DATA_BATTERY_ABSENT: False,
            DATA_BATTERY_SHORT: False,
            DATA_AUX_OVERLOAD: False,
            DATA_SIREN_WIRE_CUT: False,
            DATA_SIREN_SHORT: False,
            DATA_PHONE_LINE_CUT: False,
            DATA_COMM_FAILURE: False,
            DATA_DATETIME: None,
        }

    async def get_status(self) -> dict[str, Any]:
        """Get current status from panel."""
        payload = await self._send_command(CMD_STATUS)
        return self._parse_response(payload)

    async def arm(self, password: str | None = None) -> None:
        """Arm all partitions."""
        await self._send_command(CMD_ARM_DISARM, bytes([0xFF, 0x01]), password)

    async def disarm(self, password: str | None = None) -> None:
        """Disarm all partitions."""
        await self._send_command(CMD_ARM_DISARM, bytes([0xFF, 0x00]), password)

    async def arm_stay(self, password: str | None = None) -> None:
        """Arm all partitions in stay mode."""
        await self._send_command(CMD_ARM_DISARM, bytes([0xFF, 0x02]), password)

    async def arm_partition(self, partition: str, password: str | None = None) -> None:
        """Arm a specific partition."""
        part_num = self._partition_number(partition)
        pwd = password or self._partition_passwords.get(partition.upper()) or self._password
        await self._send_command(CMD_ARM_DISARM, bytes([part_num, 0x01]), pwd)

    async def disarm_partition(self, partition: str, password: str | None = None) -> None:
        """Disarm a specific partition."""
        part_num = self._partition_number(partition)
        pwd = password or self._partition_passwords.get(partition.upper()) or self._password
        await self._send_command(CMD_ARM_DISARM, bytes([part_num, 0x00]), pwd)

    async def arm_stay_partition(self, partition: str, password: str | None = None) -> None:
        """Arm a specific partition in stay mode."""
        part_num = self._partition_number(partition)
        pwd = password or self._partition_passwords.get(partition.upper()) or self._password
        await self._send_command(CMD_ARM_DISARM, bytes([part_num, 0x02]), pwd)

    async def activate_pgm(self, pgm_number: int) -> None:
        """Activate PGM output."""
        if pgm_number < 1 or pgm_number > MAX_PGMS:
            raise ValueError(f"Invalid PGM number: {pgm_number}")
        await self._send_command(CMD_PGM, bytes([pgm_number, 0x01]))

    async def deactivate_pgm(self, pgm_number: int) -> None:
        """Deactivate PGM output."""
        if pgm_number < 1 or pgm_number > MAX_PGMS:
            raise ValueError(f"Invalid PGM number: {pgm_number}")
        await self._send_command(CMD_PGM, bytes([pgm_number, 0x00]))

    async def siren_on(self) -> None:
        """Turn siren on (panic audible)."""
        await self._send_command(CMD_PANIC, bytes([0x01]))

    async def siren_off(self) -> None:
        """Turn siren off."""
        await self._send_command(CMD_SIREN_OFF, bytes([0xFF]))

    async def bypass_zones(self, zone_mask: list[bool]) -> None:
        """Bypass zones according to mask."""
        for zone_idx, enabled in enumerate(zone_mask, start=1):
            if not enabled:
                continue
            await self._send_command(CMD_BYPASS_ZONE, bytes([zone_idx - 1, 0x01]))

    async def bypass_open_zones(self, open_zones: list[bool]) -> None:
        """Bypass all currently open zones."""
        await self.bypass_zones(open_zones)

    async def send_raw_command(
        self,
        command_hex: str,
        password: str | None = None,
    ) -> dict[str, Any]:
        """Send raw ISEC command in hex format.

        Formats accepted:
        - "0B4A" (command only)
        - "0B4A0102" (command + payload)
        - "0B 4A 01 02"
        """
        try:
            clean = command_hex.replace(" ", "").replace("0x", "")
            raw = bytes.fromhex(clean)
            if len(raw) < 2:
                return {"success": False, "error": "Command must be at least 2 bytes"}

            command = (raw[0] << 8) | raw[1]
            payload = raw[2:]
        except ValueError:
            return {"success": False, "error": "Invalid hex command format"}

        try:
            response = await self._send_command(command, payload, password)
            return {
                "success": True,
                "command": f"0x{command:04X}",
                "payload_hex": payload.hex(),
                "response_hex": response.hex(),
            }
        except Exception as err:  # noqa: BLE001
            return {"success": False, "error": str(err)}

    async def test_connection(self) -> bool:
        """Test connectivity and authentication."""
        try:
            await self.get_status()
            return True
        except AMTClientError:
            return False
