# LOTWPS / LOTIEM Unified Tkinter GUI

This branch adds a consolidated Python/Tkinter GUI for the fictional KLOT LOTIEM / LOTWPS weather-message workflow.

## Run

```powershell
python LOTWPS_LOTIEM_GUI.py
```

Or on Windows:

```
RUN_LOTWPS_LOTIEM_GUI.bat
```

## Main Workstation

The **KLOT LOTIEM TEXT WORKSTATION** provides:

- JSON-configured IP address and port
- New Text Message
- Send to BMH / Email / IEMBOT / Websites & Outlets checkboxes
- Character count
- Editor Mode
- AWIPS header fields and automatic generation
- WarnGen and WatchGen dialogs
- Right-click segment editing
- Hazard Segment builder
- KLOT polygon builder with Single Storm / Line of Storms
- AWIPS Active Alerts and sent-alert views
- BMH Network quick controls
- Listening-area controls for Illinois and Indiana

## BMH Network / WXK89

The BMH window provides the requested simulation controls for WXK89 in Valparaiso, Indiana, including operational modes, broadcast cycles, static messages, live queue controls, SAME/EAS preview fields, quick-read internal IDs, manual product control, and active-alert actions.

## Configuration

Primary GUI configuration is stored in `lotwps_lotiem_settings.json`.

The existing repository's `TEXT_WORKSTATION/config.json` remains intact.

## Safety / simulation behavior

The new GUI is intended as a simulation/lab interface. It does not autonomously generate or transmit emergency alerts. Network transmit functions only operate when the configured socket is explicitly connected and **Send to BMH** is enabled.

For any real operational system, use the applicable agency-approved interfaces, authentication, validation, logging, and human authorization controls.
