print("Developed and Designed by SPCBHEASguyIN & Official at the NWS in Chicago IL")
# Developed and Designed by SPCBHEASguyIN

from bmh.runtime_dispatch import invoke as _bmh_invoke
from bmh.implementation_registry import IMPLEMENTATIONS as _BMH_IMPLEMENTATIONS

from bmh.version import (
    BMH_VERSION,
    LOTIEM_VERSION,
    STATION_BUILD
)

print(f"LOTIEM Version: {LOTIEM_VERSION}")
print(f"Broadcast Message Handler Version: {BMH_VERSION}")
print(f"Station Build: {STATION_BUILD}")

from bmh.station import (
    FREQUENCY,
    LISTENING_COUNTIES,
    STATION_CODE,
    STATION_ID,
    STATION_LOCATION,
    STATION_REGION
)

from bmh.audio.silence_detector import (
    SafeSilenceDetector
)

from bmh.ui.character_generator import (
    CharacterGenerator,
    get_secondary_monitor_geometry
)

from bmh.alerts.product_ids import (
    assign_segmented_product_id,
    build_bmh_product_id,
    normalize_product_originator
)

# NWS-BMH-Chicago-Romeoville-IL-main/data/resources/runtime/WNG689/WNG689_BMH.py
from bmh.state import BMHState, region_info

bmh_state = BMHState(
    region_info["nws_office"],
    region_info["city"],
    region_info["state"],
    region_info["coverage_areas"],
    region_info["station_code"]
)


def poll_zones():
    return _bmh_invoke(_BMH_IMPLEMENTATIONS["poll_zones"], globals())


import socket
import threading

HOST = "0.0.0.0"  # Listen on all interfaces
PORT = 5000  # Communication port

# Hazard type mappings (full name + shortcode)
hazard_types = {
    "Tornado Warning": "TOR",
    "Severe Thunderstorm Warning": "SVR",
    "Severe Weather Statement": "SVS",
    "Tropical Storm Watch": "TRA",
    "Tropical Storm Warning": "IPW",
    "Hurricane Watch": "HUA",
    "Hurricane Warning": "HUW",
    "Flash Flood Watch": "FFA",
    "Flash Flood Warning": "FFW",
    "Public Information Statement": "PNS",
    "Special Weather Statement": "SPS",
    "Flood Watch": "FLA",
    "Flood Warning": "FLW",
    "Severe Thunderstorm Watch": "SVA",
    "Tornado Watch": "TOA",
    "Special Marine Warning": "SMW",
    "Winter Storm Watch": "WSA",
    "Winter Storm Warning": "WSW",
    "Local Area Emergency": "LAE",
    "Hurricane Local Statement": "HLS",
    "Severe Weather Roundup": "SWR",
    "Wind Advisory": "NPW",
    "Winter Weather Advisory": "WWA",
    "Dense Fog Advisory": "DFA",
    "Extreme Cold Watch": "ECA",
    "Extreme Cold Warning": "ECW",
    "Excessive Heat Watch": "EHA",
    "Excessive Heat Warning": "EHW",
    "Cold Weather Advisory": "CWA",
    "High Wind Watch": "HWA",
    "High Wind Warning": "HWW",
    "Cancellation Message": "CAN",
    "Expiration Message": "EXP",
    "Coastal Waters Forecast": "CWF",
    "Hazardous Weather Outlook": "HWO",
    "Hydrologic Outlook": "HLO",
    "Marine Weather Statement": "MWS",
    "Forecast for Valparaiso and Surrounding Communities": "FVC",
    "Fire Weather Watch": "FWA",
    "Fire Weather Warning": "FWW",
    "Red Flag Warning": "RFW",
    "Precipitation Warning": "PRW",
}


# ---------------------------------------------------------------------------
# Dispatch listener
# ---------------------------------------------------------------------------
class DispatchServer:
    """Threaded TCP server that accepts workstation dispatches."""

    def __init__(self, host=HOST, port=PORT):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server.bind((host, port))
        except OSError as exc:
            print(f"[Dispatch] Failed to bind {host}:{port}: {exc}")
            raise
        self.server.listen(5)
        self._thread = None
        self._running = False

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        print(f"[Dispatch] Listening on {HOST}:{PORT}")

    def _serve(self):
        while self._running:
            try:
                conn, addr = self.server.accept()
            except OSError:
                break
            threading.Thread(target=self._handle, args=(conn, addr), daemon=True).start()

    def _handle(self, conn, addr):
        try:
            with conn:
                data = b""
                while True:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                    if len(data) > 50 * 1024 * 1024:
                        break
                if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
                    print(f"[Dispatch] Received WAV payload ({len(data)} bytes) from {addr[0]}")
                else:
                    text = data.decode("utf-8", errors="replace").strip()
                    print(f"[Dispatch] Received {len(text)} chars from {addr[0]}")
                    if text:
                        preview = text[:120].replace("\n", " ")
                        suffix = "..." if len(text) > 120 else ""
                        print(f"[Dispatch] Payload: {preview}{suffix}")
        except OSError:
            pass

    def stop(self):
        self._running = False
        try:
            self.server.close()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Broadcast / dispatch cycle
# ---------------------------------------------------------------------------
def run_broadcast_cycle():
    """Start the dispatch loop and keep the station alive."""
    bmh_state.running = True
    bmh_state.running = True
    print(f"[BMH] Starting {STATION_ID} broadcast cycle ({STATION_LOCATION})")
    print(f"[BMH] Frequency: {FREQUENCY}")
    print(f"[BMH] Listening counties: {', '.join(LISTENING_COUNTIES)}")
    print(f"[BMH] Region: {STATION_REGION}")

    silence_detector = SafeSilenceDetector()
    character_generator = CharacterGenerator()

    try:
        zones = poll_zones()
        bmh_state.set_alerts(zones.get("zones", []))
        print(f"[BMH] Polled {zones.get('count', 0)} forecast zones for {zones.get('station', STATION_ID)}")
    except Exception as exc:
        print(f"[BMH] Initial zone poll failed: {exc}")

    sample_product_id = build_bmh_product_id(event_code="SPS")
    print(f"[BMH] Sample product ID: {sample_product_id}")

    try:
        while bmh_state.running:
            threading.Event().wait(5)
    except KeyboardInterrupt:
        print("\n[BMH] Interrupted, shutting down.")
    finally:
        bmh_state.stop()
        print("[BMH] Broadcast cycle stopped.")


def main():
    print(f"Starting the BMH Broadcast Cycle for the WNG689 BMH Station in Hebron, or Valparaiso, IN, or Indiana.")
    print(f"Dispatch host: {HOST}:{PORT}")

    server = None
    try:
        server = DispatchServer()
        server.start()
    except OSError as exc:
        print(f"[BMH] Could not start dispatch listener: {exc}")

    try:
        run_broadcast_cycle()
    finally:
        if server is not None:
            server.stop()


import json
import tkinter as tk
from tkinter import ttk, messagebox

# Settings Configuration
WORKSTATION_SETTINGS = {
    "ip_address": "192.168.10.144",
    "port": 6000,
    "app": "KLOT",
    "station_id": "WNG689",
    "location": "Valparaiso, IN"
}

def save_settings():
    with open("text_workstation_settings.json", "w") as f:
        json.dump(WORKSTATION_SETTINGS, f, indent=4)

class KLOTTextWorkstation(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("KLOT LOTIEM TEXT WORKSTATION")
        self.geometry("1000x700")

        # Notebook for Tabs
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill='both', expand=True)

        self.editor_tab = ttk.Frame(self.tabs)
        self.bmh_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.editor_tab, text="Text Editor")
        self.tabs.add(self.bmh_tab, text="BMH Network Controller")

        self._setup_editor()
        self._setup_bmh()

    def _setup_editor(self):
        # AWIPS Header Block
        frame = ttk.LabelFrame(self.editor_tab, text="AWIPS Header Block")
        frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(frame, text="WMO Type (TTAAii):").grid(row=0, column=0)
        self.wmo_entry = ttk.Entry(frame); self.wmo_entry.grid(row=0, column=1)
        ttk.Label(frame, text="CCCC:").grid(row=0, column=2)
        ttk.Entry(frame, textvariable=tk.StringVar(value="KLOT")).grid(row=0, column=3)

        # Options
        options = ["Send to BMH", "Send to Email", "Send to IEMBOT", "Send to Websites"]
        for opt in options:
            ttk.Checkbutton(self.editor_tab, text=opt).pack(anchor='w')

    def _setup_bmh(self):
        # BMH Network Window
        status_frame = ttk.LabelFrame(self.bmh_tab, text="Station Status")
        status_frame.pack(side='left', fill='y')

        ttk.Label(status_frame, text=f"STATION: {WORKSTATION_SETTINGS['station_id']} ONLINE").pack()
        ttk.Label(status_frame, text=f"IP: {WORKSTATION_SETTINGS['ip_address']}:{WORKSTATION_SETTINGS['port']}").pack()

        btn_frame = ttk.Frame(self.bmh_tab)
        btn_frame.pack(side='right', fill='both', expand=True)

        ttk.Button(btn_frame, text="START TX").pack()
        ttk.Button(btn_frame, text="STOP TX").pack()
        ttk.Button(btn_frame, text="RESTART SERVICE").pack()

    def _js_export(self):
        return f"const settings = {json.dumps(WORKSTATION_SETTINGS)};"

if __name__ == "__main__":
    app = KLOTTextWorkstation()
    save_settings()
    # app.mainloop() # Uncomment to launch GUI

if __name__ == "__main__":
    main()