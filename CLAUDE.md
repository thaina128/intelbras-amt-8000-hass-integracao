# Intelbras AMT Home Assistant Integration

## Project Type

This is a **Home Assistant custom integration** distributed via HACS (Home Assistant Community Store).

## Release Process

**IMPORTANT**: HACS requires GitHub releases with version tags for users to install the integration.

### Before Pushing Changes

1. Update version in `custom_components/intelbras_amt/manifest.json`
2. Update `CHANGELOG.md` with changes (follow Keep a Changelog format)
3. Update `README.md` if features/entities/configuration changed
4. Commit all changes
5. Push to GitHub
6. Create a GitHub release with a version tag

### Documentation Requirements

**Every code change MUST include:**
- `CHANGELOG.md` update with the changes made
- `README.md` update if:
  - New entities added/removed
  - Configuration options changed
  - New features added
  - Behavior changed

### Creating a Release

After pushing changes, create a release:

```bash
# Tag the release (use semantic versioning)
git tag -a v1.0.0 -m "Initial release"

# Push the tag
git push origin v1.0.0
```

Then go to GitHub and create a release from the tag:
1. Go to https://github.com/robsonfelix/intelbras-amt-hass-integration/releases
2. Click "Create a new release"
3. Select the tag (e.g., `v1.0.0`)
4. Add release notes (copy from CHANGELOG.md)
5. Publish release

### Version Numbering

Use semantic versioning: `MAJOR.MINOR.PATCH`
- MAJOR: Breaking changes
- MINOR: New features (backwards compatible)
- PATCH: Bug fixes

### HACS Requirements

For HACS compatibility:
- `hacs.json` must exist in repository root
- `manifest.json` must have valid `version` field
- GitHub releases must use version tags (e.g., `v1.0.0`)

## File Structure

```
custom_components/intelbras_amt/
├── __init__.py           # Setup entry
├── manifest.json         # Integration metadata (VERSION HERE)
├── const.py              # Protocol constants
├── server.py             # AMT TCP server (receives panel connections)
├── coordinator.py        # DataUpdateCoordinator
├── config_flow.py        # UI configuration
├── alarm_control_panel.py # Main panel + partition panels
├── binary_sensor.py
├── sensor.py
├── switch.py             # Siren, PGMs
├── button.py             # Bypass open zones, arm stay
├── strings.json
└── translations/
    ├── en.json
    └── pt-BR.json
```

## Deployment

**IMPORTANT**: NEVER copy files directly to `/homeassistant/custom_components/`.

Updates are done exclusively via HACS:
1. Commit and push changes to GitHub
2. Create a GitHub release with version tag
3. In Home Assistant: HACS → Integrations → Intelbras AMT → Update
4. Restart Home Assistant

## Protocol Reference

AMT TCP protocol (Server Mode - panel connects TO Home Assistant):
- Default port: `9009`
- Frame: `[Length] [0xE9] [0x21] [PASSWORD_ASCII] [COMMAND] [0x21] [XOR_CHECKSUM]`
- Checksum: XOR all bytes, then XOR with 0xFF
- Password: ASCII encoding (e.g., "1234" = `0x31 0x32 0x33 0x34`)

Commands:
- Status (full): `0x5B` (54 bytes response)
- Arm: `0x41` ('A')
- Disarm: `0x44` ('D')
- Stay: `0x41 0x50` ('AP')
- Siren on: `0x43`
- Siren off: `0x63`

Heartbeat: Panel sends `0xF7`, server responds with ACK `[0x01] [0xFE] [checksum]`
