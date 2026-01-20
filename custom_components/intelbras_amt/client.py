"""AMT TCP protocol client."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .const import (
    CMD_ARM,
    CMD_ARM_PARTITION_A,
    CMD_ARM_PARTITION_B,
    CMD_ARM_PARTITION_C,
    CMD_ARM_PARTITION_D,
    CMD_BYPASS,
    CMD_DISARM,
    CMD_DISARM_PARTITION_A,
    CMD_DISARM_PARTITION_B,
    CMD_DISARM_PARTITION_C,
    CMD_DISARM_PARTITION_D,
    CMD_PGM_OFF_PREFIX,
    CMD_PGM_ON_PREFIX,
    CMD_SIREN_OFF,
    CMD_SIREN_ON,
    CMD_STAY,
    CMD_STATUS,
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
    FRAME_SEPARATOR,
    FRAME_START,
    MAX_PGMS,
    MAX_ZONES_2018,
    MAX_ZONES_4010,
    MAX_ZONES_LOW_BATTERY,
    MAX_ZONES_SHORT_CIRCUIT,
    MAX_ZONES_TAMPER,
    MODEL_AMT_2018,
    MODEL_AMT_4010_SMART,
    MODEL_NAMES,
    NACK_MESSAGES,
    OFFSET_BATTERY_LEVEL,
    OFFSET_CENTRAL_STATUS,
    OFFSET_FIRMWARE,
    OFFSET_MODEL_ID,
    OFFSET_PARTITION_AB,
    OFFSET_PARTITION_CD,
    OFFSET_PGM_SIREN_STATUS,
    OFFSET_POWER_STATUS,
    OFFSET_ZONES_BYPASSED_START,
    OFFSET_ZONES_OPEN_START,
    OFFSET_ZONES_VIOLATED_START,
)

_LOGGER = logging.getLogger(__name__)


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
    """AMT TCP protocol client."""

    def __init__(self, host: str, port: int, password: str) -> None:
        """Initialize the AMT client."""
        self._host = host
        self._port = port
        self._password = password
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()
        self._connected = False
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
        if self._connected:
            return

        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=CONNECTION_TIMEOUT,
            )
            self._connected = True
            _LOGGER.info("Connected to AMT at %s:%s", self._host, self._port)
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
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:  # noqa: BLE001
                pass
        self._writer = None
        self._reader = None
        self._connected = False
        _LOGGER.info("Disconnected from AMT")

    def _calculate_checksum(self, data: bytes) -> int:
        """Calculate XOR checksum for the frame."""
        checksum = 0
        for byte in data:
            checksum ^= byte
        return checksum

    def _password_to_bytes(self, password: str) -> bytes:
        """Convert password string to protocol bytes."""
        # Password is encoded as pairs of digits combined into single bytes
        # e.g., "123456" -> [0x12, 0x34, 0x56]
        password = password.ljust(6, "F")[:6]  # Pad with F, truncate to 6
        result = []
        for i in range(0, len(password), 2):
            pair = password[i : i + 2]
            # Convert each char: digit -> value, F -> 0x0F
            high = int(pair[0], 16) if pair[0].upper() in "0123456789ABCDEF" else 0
            low = int(pair[1], 16) if pair[1].upper() in "0123456789ABCDEF" else 0
            result.append((high << 4) | low)
        return bytes(result)

    def _build_frame(self, command: bytes, password: str | None = None) -> bytes:
        """Build a protocol frame with checksum."""
        pwd = password or self._password
        pwd_bytes = self._password_to_bytes(pwd)

        # Frame: [Length] [0xe9] [0x21] [PASSWORD_BYTES] [COMMAND] [0x21] [XOR_CHECKSUM]
        # Length = everything except length byte and checksum
        inner = bytes([FRAME_START, FRAME_SEPARATOR]) + pwd_bytes + command + bytes([FRAME_SEPARATOR])
        length = len(inner) + 1  # +1 for checksum
        frame_without_checksum = bytes([length]) + inner
        checksum = self._calculate_checksum(frame_without_checksum)
        return frame_without_checksum + bytes([checksum])

    async def _send_command(self, command: bytes, password: str | None = None) -> bytes:
        """Send a command and receive the response."""
        async with self._lock:
            if not self._connected:
                await self.connect()

            if not self._writer or not self._reader:
                raise AMTConnectionError("Not connected")

            frame = self._build_frame(command, password)
            _LOGGER.debug("Sending frame: %s", frame.hex())

            try:
                self._writer.write(frame)
                await self._writer.drain()

                # Read response - first byte is length
                header = await asyncio.wait_for(
                    self._reader.read(1),
                    timeout=CONNECTION_TIMEOUT,
                )
                if not header:
                    self._connected = False
                    raise AMTConnectionError("Connection closed by remote")

                length = header[0]
                response = await asyncio.wait_for(
                    self._reader.read(length),
                    timeout=CONNECTION_TIMEOUT,
                )
                _LOGGER.debug("Received response: %s", response.hex())

                # Check for NACK response (error code in the response)
                if len(response) >= 3 and response[0] == FRAME_START:
                    # Check if response contains a NACK code (0xE0-0xEF)
                    if len(response) >= 4 and 0xE0 <= response[3] <= 0xEF:
                        nack_code = response[3]
                        raise AMTNackError(nack_code)

                return response

            except asyncio.TimeoutError as err:
                self._connected = False
                raise AMTConnectionError("Response timeout") from err
            except OSError as err:
                self._connected = False
                raise AMTConnectionError(f"Communication error: {err}") from err

    def _parse_zones(self, data: bytes, offset: int, max_zones: int) -> list[bool]:
        """Parse zone status bytes into a list of booleans."""
        zones = []
        for byte_idx in range(8):  # 8 bytes = 64 zones max
            if offset + byte_idx >= len(data):
                break
            byte = data[offset + byte_idx]
            for bit in range(8):
                zone_num = byte_idx * 8 + bit
                if zone_num >= max_zones:
                    break
                zones.append(bool(byte & (1 << bit)))
        return zones[:max_zones]

    def _parse_partition_status(self, status_byte: int) -> dict[str, bool]:
        """Parse partition status byte."""
        return {
            "armed": bool(status_byte & 0x01),
            "stay": bool(status_byte & 0x02),
            "triggered": bool(status_byte & 0x04),
        }

    def _parse_response(self, data: bytes) -> dict[str, Any]:
        """Parse status response into structured data."""
        if len(data) < 47:
            raise AMTProtocolError(f"Response too short: {len(data)} bytes")

        # Determine model and max zones
        model_id = data[OFFSET_MODEL_ID] if len(data) > OFFSET_MODEL_ID else 0
        model_name = MODEL_NAMES.get(model_id, f"Unknown (0x{model_id:02x})")

        if model_id == MODEL_AMT_4010_SMART:
            max_zones = MAX_ZONES_4010
        elif model_id == MODEL_AMT_2018:
            max_zones = MAX_ZONES_2018
        else:
            max_zones = MAX_ZONES_4010  # Default to max

        # Parse firmware version
        firmware_byte = data[OFFSET_FIRMWARE] if len(data) > OFFSET_FIRMWARE else 0
        firmware_major = (firmware_byte >> 4) & 0x0F
        firmware_minor = firmware_byte & 0x0F
        firmware = f"{firmware_major}.{firmware_minor}"

        # Parse partition status
        part_ab = data[OFFSET_PARTITION_AB] if len(data) > OFFSET_PARTITION_AB else 0
        part_cd = data[OFFSET_PARTITION_CD] if len(data) > OFFSET_PARTITION_CD else 0

        partitions = {
            "A": self._parse_partition_status(part_ab & 0x0F),
            "B": self._parse_partition_status((part_ab >> 4) & 0x0F),
            "C": self._parse_partition_status(part_cd & 0x0F),
            "D": self._parse_partition_status((part_cd >> 4) & 0x0F),
        }

        # Parse central status
        central_status = data[OFFSET_CENTRAL_STATUS] if len(data) > OFFSET_CENTRAL_STATUS else 0
        armed = bool(central_status & 0x08)
        stay = bool(central_status & 0x10)
        triggered = bool(central_status & 0x04)

        # Parse power status
        power_status = data[OFFSET_POWER_STATUS] if len(data) > OFFSET_POWER_STATUS else 0
        ac_power = bool(power_status & 0x01)
        battery_connected = bool(power_status & 0x04)

        # Parse battery level (0-100)
        battery_level = data[OFFSET_BATTERY_LEVEL] if len(data) > OFFSET_BATTERY_LEVEL else 0
        battery_level = min(100, max(0, battery_level))

        # Parse PGM/Siren status
        pgm_siren = data[OFFSET_PGM_SIREN_STATUS] if len(data) > OFFSET_PGM_SIREN_STATUS else 0
        siren = bool(pgm_siren & 0x01)

        # Parse PGMs 1-19 (expanded from 3)
        # First 3 PGMs are in the pgm_siren byte, the rest may be in additional bytes
        pgms = [False] * MAX_PGMS
        pgms[0] = bool(pgm_siren & 0x02)  # PGM 1
        pgms[1] = bool(pgm_siren & 0x04)  # PGM 2
        pgms[2] = bool(pgm_siren & 0x08)  # PGM 3

        # Parse additional PGM bytes if available (bytes 47-49 for PGMs 4-19)
        if len(data) > 47:
            pgm_byte1 = data[47]
            for i in range(8):
                if 3 + i < MAX_PGMS:
                    pgms[3 + i] = bool(pgm_byte1 & (1 << i))
        if len(data) > 48:
            pgm_byte2 = data[48]
            for i in range(8):
                if 11 + i < MAX_PGMS:
                    pgms[11 + i] = bool(pgm_byte2 & (1 << i))

        # Parse problem status - general problem flag
        problem = bool(central_status & 0x10)

        # Parse detailed problem status from power_status and additional bytes
        # These are based on typical AMT protocol definitions
        battery_low = bool(power_status & 0x02)
        battery_absent = not battery_connected
        battery_short = bool(power_status & 0x08)
        aux_overload = bool(power_status & 0x10)

        # Siren and communication problems (may be in additional bytes)
        siren_wire_cut = False
        siren_short = False
        phone_line_cut = False
        comm_failure = False
        if len(data) > 37:
            problem_byte = data[37]
            siren_wire_cut = bool(problem_byte & 0x01)
            siren_short = bool(problem_byte & 0x02)
            phone_line_cut = bool(problem_byte & 0x04)
            comm_failure = bool(problem_byte & 0x08)

        # Parse zone lists
        zones_open = self._parse_zones(data, OFFSET_ZONES_OPEN_START, max_zones)
        zones_violated = self._parse_zones(data, OFFSET_ZONES_VIOLATED_START, max_zones)
        zones_bypassed = self._parse_zones(data, OFFSET_ZONES_BYPASSED_START, max_zones)

        # Calculate zone counts
        zones_open_count = sum(zones_open)
        zones_violated_count = sum(zones_violated)
        zones_bypassed_count = sum(zones_bypassed)

        # Initialize empty arrays for tamper, short-circuit, and low-battery zones
        # These would be populated from extended status commands if available
        zones_tamper = [False] * MAX_ZONES_TAMPER
        zones_short_circuit = [False] * MAX_ZONES_SHORT_CIRCUIT
        zones_low_battery = [False] * MAX_ZONES_LOW_BATTERY

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
            DATA_AC_POWER: ac_power,
            DATA_BATTERY_CONNECTED: battery_connected,
            DATA_BATTERY_LEVEL: battery_level,
            DATA_SIREN: siren,
            DATA_PGMS: pgms,
            DATA_PROBLEM: problem,
            DATA_BATTERY_LOW: battery_low,
            DATA_BATTERY_ABSENT: battery_absent,
            DATA_BATTERY_SHORT: battery_short,
            DATA_AUX_OVERLOAD: aux_overload,
            DATA_SIREN_WIRE_CUT: siren_wire_cut,
            DATA_SIREN_SHORT: siren_short,
            DATA_PHONE_LINE_CUT: phone_line_cut,
            DATA_COMM_FAILURE: comm_failure,
            DATA_DATETIME: None,  # Would be populated from extended status
        }

    async def get_status(self) -> dict[str, Any]:
        """Get the current status of the alarm panel."""
        response = await self._send_command(CMD_STATUS)
        return self._parse_response(response)

    async def arm(self, password: str | None = None) -> None:
        """Arm the alarm panel."""
        await self._send_command(CMD_ARM, password)

    async def disarm(self, password: str | None = None) -> None:
        """Disarm the alarm panel."""
        await self._send_command(CMD_DISARM, password)

    async def arm_stay(self, password: str | None = None) -> None:
        """Arm in stay mode."""
        await self._send_command(CMD_STAY, password)

    async def arm_partition(self, partition: str, password: str | None = None) -> None:
        """Arm a specific partition."""
        commands = {
            "A": CMD_ARM_PARTITION_A,
            "B": CMD_ARM_PARTITION_B,
            "C": CMD_ARM_PARTITION_C,
            "D": CMD_ARM_PARTITION_D,
        }
        if partition not in commands:
            raise ValueError(f"Invalid partition: {partition}")

        pwd = password or self._partition_passwords.get(partition) or self._password
        await self._send_command(commands[partition], pwd)

    async def disarm_partition(self, partition: str, password: str | None = None) -> None:
        """Disarm a specific partition."""
        commands = {
            "A": CMD_DISARM_PARTITION_A,
            "B": CMD_DISARM_PARTITION_B,
            "C": CMD_DISARM_PARTITION_C,
            "D": CMD_DISARM_PARTITION_D,
        }
        if partition not in commands:
            raise ValueError(f"Invalid partition: {partition}")

        pwd = password or self._partition_passwords.get(partition) or self._password
        await self._send_command(commands[partition], pwd)

    async def activate_pgm(self, pgm_number: int) -> None:
        """Activate a PGM output."""
        if pgm_number < 1 or pgm_number > MAX_PGMS:
            raise ValueError(f"Invalid PGM number: {pgm_number}")

        # Format PGM number as two-digit ASCII (01-19)
        if pgm_number < 10:
            command = CMD_PGM_ON_PREFIX + bytes([0x30, 0x30 + pgm_number])  # '01' to '09'
        else:
            command = CMD_PGM_ON_PREFIX + bytes([0x31, 0x30 + (pgm_number - 10)])  # '10' to '19'
        await self._send_command(command)

    async def deactivate_pgm(self, pgm_number: int) -> None:
        """Deactivate a PGM output."""
        if pgm_number < 1 or pgm_number > MAX_PGMS:
            raise ValueError(f"Invalid PGM number: {pgm_number}")

        # Format PGM number as two-digit ASCII (01-19)
        if pgm_number < 10:
            command = CMD_PGM_OFF_PREFIX + bytes([0x30, 0x30 + pgm_number])  # '01' to '09'
        else:
            command = CMD_PGM_OFF_PREFIX + bytes([0x31, 0x30 + (pgm_number - 10)])  # '10' to '19'
        await self._send_command(command)

    async def siren_on(self) -> None:
        """Turn siren on."""
        await self._send_command(CMD_SIREN_ON)

    async def siren_off(self) -> None:
        """Turn siren off."""
        await self._send_command(CMD_SIREN_OFF)

    async def bypass_zones(self, zone_mask: list[bool]) -> None:
        """Bypass zones specified in the mask."""
        # Convert boolean list to bytes (8 zones per byte)
        mask_bytes = []
        for i in range(0, len(zone_mask), 8):
            byte = 0
            for bit in range(8):
                if i + bit < len(zone_mask) and zone_mask[i + bit]:
                    byte |= 1 << bit
            mask_bytes.append(byte)

        command = CMD_BYPASS + bytes(mask_bytes)
        await self._send_command(command)

    async def bypass_open_zones(self, open_zones: list[bool]) -> None:
        """Bypass all currently open zones."""
        await self.bypass_zones(open_zones)

    async def test_connection(self) -> bool:
        """Test the connection to the alarm panel."""
        try:
            await self.get_status()
            return True
        except AMTClientError:
            return False
