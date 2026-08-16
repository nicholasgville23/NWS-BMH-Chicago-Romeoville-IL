# NWS-BMH-Chicago-Romeoville-IL

NWS-BMH-Chicago-Romeoville-IL LOTIEM Version of BMH System in Windows 11 with Python, JS, HTML, and CSS, NWSLOT integration for VSCode. KLOT_BMH and KLOT_AWIPS version of the BMH Broadcast Cycle in Python, HTML, CSS, and JavaScript.

- NWS Office: Chicago / Romeoville, Illinois
- NWR Station: WNG689 (Valparaiso / Hebron, Indiana)

## Getting started

Prerequisites: Windows 10/11, [Python 3.12](https://www.python.org/downloads/) installed with the
Tcl/Tk option enabled (the alert dashboard uses `tkinter`), and Git.

```powershell
git clone https://github.com/nicholasgville23/NWS-BMH-Chicago-Romeoville-IL.git
cd NWS-BMH-Chicago-Romeoville-IL

py -3.12 -m venv .venv   # if `py` is unavailable, use the full path to python.exe
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Run the active alerts dashboard

```powershell
python alert_dashboard.py
```

A tkinter window opens and polls `https://api.weather.gov/alerts/active/zone/{zone}` for each zone
listed under `AlertSummary.alertZones` in `config.json`. It needs outbound internet access and a
desktop session (it will not run headless).

`config.json` is not committed yet, so until you add one the dashboard logs `FileNotFoundError`
and stays at `0 active alert(s)`:

```json
{"globalHTTPTimeout": 15, "AlertSummary": {"alertZones": ["ILC031", "ILC197", "INC127"]}}
```

### Look up IEMBot products

```powershell
python -c "import bmh.networking.iembot_lookup as iem; print(iem.__doc__)"
```

`bmh/networking/iembot_lookup.py` is a library module, not a script — import it from your own code.

## Repository layout

| Path | Status | Notes |
| --- | --- | --- |
| `alert_dashboard.py` | runnable | tkinter dashboard for active NWS alerts |
| `bmh/` | package | the Broadcast Message Handler package `WNG689_BMH.py` imports from (see below) |
| `bmh/networking/iembot_lookup.py` | runnable library | IEMBot product lookup helpers |
| `bmh/station_id.py` | broken import | imports `utils.produce_wav_file`, which does not exist in this repo yet |
| `WNG689_BMH.py` | not runnable | still needs `bmh.audio`, `bmh.ui`, `bmh.alerts.product_ids`, and `bmh_station` |
| `KLOT_SERVER.py`, `IEMBOT.py`, `bmh/state.py`, `bmh/station.py`, `bmh/runtime_dispatch.py` | placeholders | single `print()` statements standing in for future modules |
| `application.py`, `bmh/implementation_registry.py`, `MODULARIZATION_REPORT.md`, `alerts.json`, `alert_log.json`, `fips_codes.json`, `forecast_zone_to_fips.json` | empty | 0-byte placeholders |

## Working on the `bmh` package

Python source belongs in `bmh/`, **never** in a `__pycache__/` directory — `__pycache__` holds
compiled `.pyc` files that the interpreter regenerates and may overwrite, so anything you put there
will be lost and will never be importable. It is git-ignored.

The layout `WNG689_BMH.py` expects, and what exists today:

```
bmh/
  __init__.py                 present
  version.py                  present  BMH_VERSION, LOTIEM_VERSION, STATION_BUILD
  state.py                    placeholder -> must define class BMHState
  runtime_dispatch.py         placeholder -> must define invoke(...)
  implementation_registry.py  empty       -> must define IMPLEMETATIONS dict
  station_id.py               present (needs utils.produce_wav_file)
  alerts/
    __init__.py               present
    event_codes.py            present
    product_ids.py            MISSING -> assign_segmented_product_id, build_bmh_product_id,
                                         normalize_product_originator
  networking/
    __init__.py               present
    iembot_lookup.py          present
  audio/silence_detector.py   MISSING -> SafeSilenceDetector
  ui/character_generator.py   MISSING -> CharacterGenerator, get_secondary_monitor_geometry
bmh_station.py                MISSING -> FREQUENCY, LISTENING_COUNTIES, STATION_CODE,
                                         STATION_ID, STATION_LOCATION, STATION_REGION
```

Check your progress by importing rather than running the whole broadcast cycle:

```powershell
python -c "import bmh; print(bmh.BMH_VERSION, bmh.STATION_BUILD)"
python -m py_compile WNG689_BMH.py
```

## Roadmap to a fully running BMH cycle

1. Fill in the modules marked MISSING or placeholder in the `bmh` layout above.
2. Add the missing `utils.produce_wav_file` used by `bmh/station_id.py`.
3. Commit a default `config.json` with the station's `AlertSummary.alertZones`; without it
   `alert_dashboard.py` logs `FileNotFoundError` and shows zero alerts.
4. Populate the empty JSON data files (`fips_codes.json`, `forecast_zone_to_fips.json`).
5. Add the Flask web server and `src/` frontend (HTML/CSS/JS) so the browser dashboard can be served.

## Configuration and secrets

Do not commit credentials (email passwords, SMTP logins, IP addresses) to this repository.
`settings.py` reads them from environment variables; set them in your shell or a local `.env`
file, which `.gitignore` excludes:

```powershell
$env:BMH_EMAIL = "you@example.com"
$env:BMH_EMAIL_USERNAME = "you"
$env:BMH_EMAIL_PASSWORD = "<app password>"
$env:BMH_SMTP_SERVER = "smtp.gmail.com"
$env:BMH_SMTP_PORT = "587"
$env:BMH_LOTIEM_IP = "192.168.1.145"
$env:BMH_IEMBOT_IP = "192.168.1.144"
$env:BMH_COMMAND_PORT = "6000"
```
# KLOT LOTIEM TEXT WORKSTATION: GUI Specification

## Overview
This document defines the KLOT LOTIEM TEXT WORKSTATION, a Python/Tkinter-based control interface for the SeasonalWeather automation suite. It provides a visual frontend for alert composition, broadcast scheduling, and transmitter management.

## System Architecture
The Workstation operates as a client connecting to the SeasonalWeather API.
- **Protocol:** JSON over HTTP
- **Interface:** Python Tkinter (GUI), JavaScript (Webview-rendered maps/polygons)
- **Host:** 192.168.10.144:6000

## Interface Components

### 1. KLOT LOTIEM TEXT WORKSTATION (Main Window)
- **Text Workstation Settings:** Configuration fields for API URL (192.168.10.144:6000) and credentials.
- **Message Composition:**
    - Message Options: [ ] BMH [ ] Email [ ] IEMBOT [ ] Websites/Outlets
    - Wrap chat edits (character count display)
    - **Editor Mode:** AWIPS Header Block generator (WMO TTAAii, CCCC: KLOT, BBB: NOR, Version: A, B, NOR)
    - WSFO ID: CHI (Optional)
    - Product Category: Weather/EAS Selection
    - Product Designator: LOT
    - Addressee: ALL
- **Generator Tools:** WarnGen / WatchGen integration.
- **Hazard Segment Management:**
    - Right-click context: Add, Edit, Remove, Combine Segment
    - "Build Hazard Segment" Dialogue: Weather Generator (Polygon Tool: LAT/LON, Radar View)
- **Operational Controls:** Restore UI, Create Polygon (Single/Line of Storms), WFO LOT Toggle.

### 2. BMH Network Window
- **Global Network Controls:** Broadcast action triggers (Update Periodic Scroll).
- **Hazard Selection:** SVR, TOR, FFW, SWS, EWW.
- **Station Controller (WNG689):**
    - Status: ONLINE (Valparaiso, IN)
    - **SAME/EAS Builder:** UGC mapping (Northeast IL / Northwest IN), Message Body.
    - **Broadcast Controls:** START TX, STOP TX, NEXT PRODUCT.
    - **Modes:** Winter Weather, Flooding, Severe Weather, Severe Possible, Off-Air, Station ID, Time Only, General, Zone Forecast, Alert Summary.
    - **Cycle Management:** NEW, DELETE, RESET modes. Cycle sequencing (1-9).
    - **Available Entries:** @AUTO_ID, @ACTIVE_ALERTS, @SEVERE_DYNAMIC, @PRODUCT:VPZZFP, @PRODUCT:HWOLOT, @PRODUCT:HWOIWX, @AUTO_SEVERE_ID, @NEW_CON_ALERTS, @CAN_EXP_ALERTS.

### 3. Active Queue and Monitoring
- **Live Queue Management:**
    - Refresh, Read Selected, Loop Selected, Stop Loop.
    - Queue Items: ADVANCE, EMR_STATION_ID, PREPAREDNESS_ACTIONS, SLGT_STATION_ID, OFF_AIR, STATION_ID, SHORT_ID, LONG_ID, SEVERE_MESSAGE, CURRENT_TIME.
- **Active Alerts Panel:**
    - Action: NEW, CON, CAN
    - Metadata: Expiry, Summary, SAME RETONE, 1050Hz Tone, Silent Interrupt.
- **Network Monitoring:** System Settings, Exit, Compose and Dispatch (Live Voice/WAV/WarnGen).

## Deployment Requirements
- Python 3.x with `tkinter` and `requests`.
- `config.json` synchronization with the backend service.
- Local network access to `192.168.10.144:6000`.

## Operational Safety
- No automated transmissions without valid WMO headers.
- Polygon tool provides verification of geographic scope before dispatch.
- Listen-area filtering (IL/IN) enforced at the API controller level.

## License

GPL-3.0 — see [LICENSE](LICENSE).
