"""
LOTWPS / LOTIEM Unified GUI
---------------------------
A Tkinter-based simulated NWS-style workstation for KLOT/LOTIEM.

The GUI is deliberately explicit about transmission: buttons build previews,
queues, and socket payloads but do not autonomously transmit emergency alerts.
Use only on your own lab/test network.

Run:
    python LOTWPS_LOTIEM_GUI.py
"""
from __future__ import annotations

import json
import os
import socket
import threading
import time
import tkinter as tk
from datetime import datetime, timezone
from tkinter import filedialog, messagebox, simpledialog, ttk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_PATH = os.path.join(BASE_DIR, "lotwps_lotiem_settings.json")
SENT_PATH = os.path.join(BASE_DIR, "lotwps_sent_alerts.json")

HAZARDS = [
    "Severe Thunderstorm Warning", "Tornado Warning",
    "Flash Flood Warning", "Special Weather Statement",
    "Extreme Wind Warning",
]
MODES = [
    "Winter Weather", "Flooding", "Severe Weather",
    "Severe Weather Possible", "Off the Air", "Station ID Only",
    "Current Time Only", "General", "Zone Forecast",
    "Severe Weather and Alert Summary",
]
STATIC_IDS = [
    "ADVANCE", "EMR_STATION_ID", "PREPAREDNESS_ACTIONS",
    "SLGT_STATION_ID", "OFF_AIR", "STATION_ID", "SHORT_ID",
    "LONG_ID", "SEVERE_MESSAGE", "CURRENT_TIME",
    "FORECAST", "OBSERVATIONS", "HWO",
]
CYCLE_ENTRIES = [
    "@AUTO_ID", "@ACTIVE_ALERTS", "@SEVERE_DYNAMIC",
    "@PRODUCT:VPZZFP", "@PRODUCT:HWOLOT", "@PRODUCT:HWOIWX",
    "@AUTO_SEVERE_ID", "@NEW_CON_ALERTS", "@CAN_EXP_ALERTS",
]
DEFAULT_SETTINGS = {
    "app": "KLOT | LOTIEM",
    "ip_address": "192.168.10.144",
    "port": 6000,
    "station_id": "WXK89",
    "station_location": "Valparaiso, Indiana",
    "frequency_mhz": "162.400",
    "network_status": "ONLINE (1)",
    "wfo": "LOT",
    "awips": {
        "type": "TTAAii", "CCCC": "KLOT", "BBB": "NOR",
        "bbb_version": "A", "wsfo_id": "CHI",
        "product_category": "Weather/EAS", "product_designator": "LOT",
        "addressee": "ALL",
    },
    "listening_area": {
        "description": "Illinois and Indiana",
        "enable_filtering": True,
        "allow_routine_without_fips": True,
        "ugc_ne_il": "ILC-",
        "ugc_nw_in": "INC-",
    },
}


def load_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return default.copy() if isinstance(default, dict) else list(default)


def save_json(path: str, value) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(value, fh, indent=2)
    os.replace(tmp, path)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.settings = load_json(SETTINGS_PATH, DEFAULT_SETTINGS)
        self.title("LOTWPS | LOTIEM — KLOT LOTIEM TEXT WORKSTATION")
        self.geometry("1480x960")
        self.minsize(1180, 760)
        self.protocol("WM_DELETE_WINDOW", self.on_exit)

        self.socket_lock = threading.Lock()
        self.sock = None
        self.connected = False
        self.tx_running = False
        self.segments: list[str] = []
        self.hazard_segments: list[dict] = []
        self.polygons: list[dict] = []
        self.sent_alerts: list[dict] = load_json(SENT_PATH, [])
        self.queue: list[str] = []
        self.looping = False

        self._vars()
        self._styles()
        self._menu()
        self._main_ui()
        self._context_menu()
        self._refresh_counts()
        self.after(500, self._heartbeat)

    def _vars(self):
        aw = self.settings.get("awips", {})
        la = self.settings.get("listening_area", {})
        self.send_bmh = tk.BooleanVar(value=True)
        self.send_email = tk.BooleanVar(value=False)
        self.send_iembot = tk.BooleanVar(value=False)
        self.send_web = tk.BooleanVar(value=False)
        self.wrap_chars = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="READY — Simulation/Lab Controller")
        self.hazard_var = tk.StringVar(value=HAZARDS[0])
        self.mode_var = tk.StringVar(value=MODES[2])
        self.wmo_type_var = tk.StringVar(value=aw.get("type", "TTAAii"))
        self.cccc_var = tk.StringVar(value=aw.get("CCCC", "KLOT"))
        self.bbb_var = tk.StringVar(value=aw.get("BBB", "NOR"))
        self.bbb_version_var = tk.StringVar(value=aw.get("bbb_version", "A"))
        self.wsfo_var = tk.StringVar(value=aw.get("wsfo_id", "CHI"))
        self.category_var = tk.StringVar(value=aw.get("product_category", "Weather/EAS"))
        self.designator_var = tk.StringVar(value=aw.get("product_designator", "LOT"))
        self.addressee_var = tk.StringVar(value=aw.get("addressee", "ALL"))
        self.ugc_ne_var = tk.StringVar(value=la.get("ugc_ne_il", "ILC-"))
        self.ugc_nw_var = tk.StringVar(value=la.get("ugc_nw_in", "INC-"))
        self.listen_filter = tk.BooleanVar(value=la.get("enable_filtering", True))
        self.listen_routine = tk.BooleanVar(value=la.get("allow_routine_without_fips", True))

    def _styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Section.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure("Danger.TButton", font=("Segoe UI", 10, "bold"))

    def _menu(self):
        bar = tk.Menu(self)
        sysm = tk.Menu(bar, tearoff=False)
        sysm.add_command(label="Restore UI", command=self.restore_ui)
        sysm.add_command(label="Settings", command=self.open_settings)
        sysm.add_separator()
        sysm.add_command(label="Exit Station", command=self.on_exit)
        bar.add_cascade(label="System", menu=sysm)
        comp = tk.Menu(bar, tearoff=False)
        comp.add_command(label="New Text Message", command=self.new_message)
        comp.add_command(label="Live Voice Message / WAV", command=self.voice_message)
        comp.add_command(label="WarnGen", command=self.open_warngen)
        comp.add_command(label="WatchGen", command=self.open_watchgen)
        bar.add_cascade(label="Compose and Dispatch", menu=comp)
        self.config(menu=bar)

    def _main_ui(self):
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True, padx=8, pady=8)

        header = ttk.Frame(root)
        header.pack(fill="x")
        ttk.Label(header, text="KLOT LOTIEM TEXT WORKSTATION", style="Title.TLabel").pack(side="left")
        ttk.Label(
            header,
            text=f"LOTWPS → LOTIEM   |   {self.settings.get('ip_address')}:{self.settings.get('port')}   |   WFO {self.settings.get('wfo', 'LOT')}",
        ).pack(side="right")

        panes = ttk.Panedwindow(root, orient="horizontal")
        panes.pack(fill="both", expand=True, pady=8)

        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=3)
        panes.add(right, weight=2)

        self._workstation(left)
        self._tools(right)

        bottom = ttk.Frame(root)
        bottom.pack(fill="x")
        ttk.Label(bottom, textvariable=self.status_var).pack(side="left")
        self.char_label = ttk.Label(bottom, text="0 chars")
        self.char_label.pack(side="right")

    def _workstation(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill="x")
        ttk.Button(top, text="New Text Message", command=self.new_message).pack(side="left")
        ttk.Button(top, text="Enter Editor Mode", command=self.enter_editor_mode).pack(side="left", padx=4)
        ttk.Button(top, text="View Sent Alerts / Edit Sent Alerts", command=self.view_sent_alerts).pack(side="right")

        opts = ttk.LabelFrame(parent, text="Message Options", style="Section.TLabelframe")
        opts.pack(fill="x", pady=6)
        for text, var in [
            ("Send to BMH", self.send_bmh), ("Send to Email", self.send_email),
            ("Send to IEMBOT", self.send_iembot), ("Send to Websites & Outlets", self.send_web),
            ("Wrap chat edits (character)", self.wrap_chars),
        ]:
            ttk.Checkbutton(opts, text=text, variable=var, command=self._refresh_counts).pack(side="left", padx=5, pady=4)

        editor = ttk.LabelFrame(parent, text="Message Editor", style="Section.TLabelframe")
        editor.pack(fill="both", expand=True)
        self.text = tk.Text(editor, wrap="word", undo=True, font=("Consolas", 11))
        self.text.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(editor, command=self.text.yview)
        sb.pack(side="right", fill="y")
        self.text.configure(yscrollcommand=sb.set)
        self.text.bind("<<Modified>>", self._on_modified)

        aw = ttk.LabelFrame(parent, text="AWIPS Header Block", style="Section.TLabelframe")
        aw.pack(fill="x", pady=6)
        grid = ttk.Frame(aw)
        grid.pack(fill="x", padx=4, pady=4)
        fields = [
            ("WMO Type:", self.wmo_type_var), ("CCCC:", self.cccc_var),
            ("BBB:", self.bbb_var), ("BBB Version:", self.bbb_version_var),
            ("WSFO ID (Optional):", self.wsfo_var), ("Product Category:", self.category_var),
            ("Product Designator:", self.designator_var), ("Addressee:", self.addressee_var),
        ]
        for i, (label, var) in enumerate(fields):
            ttk.Label(grid, text=label).grid(row=i//4*2, column=i%4, sticky="w", padx=4)
            ttk.Entry(grid, textvariable=var, width=18).grid(row=i//4*2+1, column=i%4, sticky="ew", padx=4, pady=(0, 3))
        for c in range(4):
            grid.columnconfigure(c, weight=1)
        ttk.Button(aw, text="Generate Automatically", command=self.generate_awips).pack(anchor="e", padx=6, pady=3)

        actions = ttk.Frame(parent)
        actions.pack(fill="x", pady=4)
        ttk.Button(actions, text="WarnGen", command=self.open_warngen).pack(side="left", padx=2)
        ttk.Button(actions, text="WatchGen", command=self.open_watchgen).pack(side="left", padx=2)
        ttk.Button(actions, text="KLOT Polygon Tool", command=self.open_polygon_tool).pack(side="left", padx=2)
        ttk.Button(actions, text="Build Hazard Segment", command=self.build_hazard).pack(side="left", padx=2)
        ttk.Button(actions, text="Restore UI", command=self.restore_ui).pack(side="left", padx=2)
        ttk.Button(actions, text="BMH Network", command=self.open_bmh).pack(side="right", padx=2)
        ttk.Button(actions, text="AWIPS Active Alerts - Unified", command=self.open_alerts).pack(side="right", padx=2)

    def _tools(self, parent):
        aw = ttk.LabelFrame(parent, text="AWIPS WarnGen Tools Section", style="Section.TLabelframe")
        aw.pack(fill="both", expand=True)
        top = ttk.Frame(aw)
        top.pack(fill="x", padx=5, pady=5)
        ttk.Button(top, text="WFO LOT", command=lambda: self.status("WFO LOT selected")).pack(side="left")
        ttk.Label(top, text="Product / Hazard:").pack(side="left", padx=6)
        ttk.Combobox(top, textvariable=self.hazard_var, values=HAZARDS, state="readonly", width=30).pack(side="left")

        ttk.Label(aw, text="Polygon Tool — LAT...LON coordinates").pack(anchor="w", padx=5)
        self.poly_list = tk.Listbox(aw, height=7)
        self.poly_list.pack(fill="x", padx=5)
        ttk.Button(aw, text="Create Polygon: Single Storm / Line of Storms", command=self.open_polygon_tool).pack(fill="x", padx=5, pady=3)

        bmh = ttk.LabelFrame(aw, text="BMH Network / WXK89", style="Section.TLabelframe")
        bmh.pack(fill="both", expand=True, padx=5, pady=6)
        ttk.Label(bmh, text="Station ID: WXK89").pack(anchor="w", padx=5)
        ttk.Label(bmh, text="Location: Valparaiso, Indiana   |   Frequency: 162.400 MHz").pack(anchor="w", padx=5)
        ttk.Label(bmh, text=f"Network: {self.settings.get('ip_address')}:{self.settings.get('port')}   |   {self.settings.get('network_status')}").pack(anchor="w", padx=5)
        ttk.Button(bmh, text="Double Click / Open BMH Station Controller", command=self.open_station).pack(fill="x", padx=5, pady=5)
        ttk.Button(bmh, text="Transmit Preview (requires Send to BMH)", command=self.transmit).pack(fill="x", padx=5, pady=2)
        ttk.Button(bmh, text="Start / Connect TX", command=self.connect_bmh).pack(fill="x", padx=5, pady=2)
        ttk.Button(bmh, text="STOP TX / Disconnect", command=self.disconnect_bmh).pack(fill="x", padx=5, pady=2)
        ttk.Button(bmh, text="View Sent Alerts / Edit Sent Alerts", command=self.view_sent_alerts).pack(fill="x", padx=5, pady=2)

        la = ttk.LabelFrame(aw, text="Listening Area", style="Section.TLabelframe")
        la.pack(fill="x", padx=5, pady=5)
        ttk.Checkbutton(la, text="Enable listening-area filtering", variable=self.listen_filter).pack(anchor="w")
        ttk.Checkbutton(la, text="Allow routine products without FIPS or zone coding", variable=self.listen_routine).pack(anchor="w")
        ttk.Label(la, text="Scope: Illinois and Indiana").pack(anchor="w")

    def _context_menu(self):
        self.ctx = tk.Menu(self, tearoff=False)
        self.ctx.add_command(label="Add Segment", command=self.add_segment)
        self.ctx.add_command(label="Edit Segment", command=self.edit_segment)
        self.ctx.add_command(label="Remove Segment", command=self.remove_segment)
        self.ctx.add_command(label="Combine Segment", command=self.combine_segment)
        self.ctx.add_separator()
        self.ctx.add_command(label="Add New Hazard Segment", command=self.build_hazard)
        self.ctx.add_command(label="Add Hazard to Existing Segment", command=self.add_hazard_existing)
        self.text.bind("<Button-3>", self._popup)

    def _popup(self, event):
        self.ctx.tk_popup(event.x_root, event.y_root)

    def _on_modified(self, _event=None):
        if self.text.edit_modified():
            self._refresh_counts()
            self.text.edit_modified(False)

    def _refresh_counts(self):
        try:
            n = len(self.text.get("1.0", "end-1c"))
            self.char_label.config(text=f"{n} chars")
        except Exception:
            pass

    def status(self, message):
        self.status_var.set(f"{datetime.now().strftime('%H:%M:%S')} — {message}")

    def new_message(self):
        self.text.delete("1.0", "end")
        self.segments.clear()
        self.hazard_segments.clear()
        self.status("New Text Message")
        self._refresh_counts()

    def enter_editor_mode(self):
        self.status("Editor Mode enabled")

    def generate_awips(self):
        now = datetime.now(timezone.utc)
        aw = self.settings.get("awips", {})
        ttaaii = f"{now:%H%M}"  # UI placeholder for the TTAAii field
        header = (
            f"{self.wmo_type_var.get() or 'TTAAii'} {ttaaii} {self.cccc_var.get().strip() or 'KLOT'} "
            f"{self.bbb_var.get().strip() or 'NOR'}{self.bbb_version_var.get().strip() or 'A'}\n"
            f"WSFO ID: {self.wsfo_var.get().strip()}\n"
            f"Product Category: {self.category_var.get().strip()}\n"
            f"Product Designator: {self.designator_var.get().strip() or 'LOT'}\n"
            f"Addressee: {self.addressee_var.get().strip() or 'ALL'}\n\n"
        )
        self.text.insert("1.0", header)
        self.status("AWIPS header generated from workstation fields")

    def add_segment(self):
        value = simpledialog.askstring("Add Segment", "Segment text:", parent=self)
        if value:
            self.segments.append(value)
            self.text.insert("end", value + "\n")
            self.status("Segment added")

    def _segment_pick(self, title):
        if not self.segments:
            messagebox.showinfo(title, "No segments are available.", parent=self)
            return None
        return simpledialog.askinteger(title, f"Segment number (1-{len(self.segments)}):",
                                       minvalue=1, maxvalue=len(self.segments), parent=self)

    def edit_segment(self):
        idx = self._segment_pick("Edit Segment")
        if idx:
            new = simpledialog.askstring("Edit Segment", "New segment text:",
                                         initialvalue=self.segments[idx-1], parent=self)
            if new is not None:
                self.segments[idx-1] = new
                self.status(f"Segment {idx} edited")

    def remove_segment(self):
        idx = self._segment_pick("Remove Segment")
        if idx:
            self.segments.pop(idx-1)
            self.status(f"Segment {idx} removed")

    def combine_segment(self):
        if len(self.segments) < 2:
            messagebox.showinfo("Combine Segment", "At least two segments are needed.", parent=self)
            return
        a = self._segment_pick("Combine Segment — First")
        b = self._segment_pick("Combine Segment — Second")
        if a and b and a != b:
            combined = self.segments[a-1] + "\n" + self.segments[b-1]
            for i in sorted([a-1, b-1], reverse=True):
                self.segments.pop(i)
            self.segments.append(combined)
            self.text.insert("end", combined + "\n")
            self.status("Segments combined")

    def build_hazard(self):
        HazardDialog(self, self.hazard_var.get(), self._hazard_result)

    def _hazard_result(self, data):
        self.hazard_segments.append(data)
        self.text.insert("end", f"\n[{data['hazard']}]\n{data['details']}\n")
        self.status("Hazard segment built")

    def add_hazard_existing(self):
        idx = self._segment_pick("Add Hazard to Existing Segment")
        if idx:
            dlg = HazardDialog(self, self.hazard_var.get(), lambda d: self._add_to(idx, d))
            self.wait_window(dlg)

    def _add_to(self, idx, data):
        self.segments[idx-1] += f"\n[{data['hazard']}] {data['details']}"
        self.status(f"Hazard added to segment {idx}")

    def open_warngen(self):
        GeneratorDialog(self, "WarnGen — Warning Generator", HAZARDS,
                        lambda kind, body: self._insert_generator(kind, body))

    def open_watchgen(self):
        GeneratorDialog(self, "WatchGen — Watch Generator",
                        ["Severe Thunderstorm Watch", "Tornado Watch", "Flood Watch"],
                        lambda kind, body: self._insert_generator(kind, body))

    def _insert_generator(self, kind, body):
        self.text.insert("end", f"\n[{kind}]\n{body}\n")
        self.status(f"{kind} content inserted")

    def open_polygon_tool(self):
        PolygonDialog(self, self._polygon_result)

    def _polygon_result(self, poly):
        self.polygons.append(poly)
        self.poly_list.insert("end", f"{poly['name']} — {poly['type']} — {len(poly['coords'])} vertices")
        self.text.insert("end", f"\n[Polygon {poly['type']}]\n" + "\n".join(poly["coords"]) + "\n")
        self.status("Polygon created")

    def open_bmh(self):
        BMHWindow(self)

    def open_station(self):
        StationController(self)

    def open_alerts(self):
        ActiveAlertsWindow(self)

    def voice_message(self):
        path = filedialog.askopenfilename(parent=self, title="Select WAV Audio File",
                                          filetypes=[("WAV audio", "*.wav"), ("All files", "*.*")])
        if path:
            self.status(f"Live Voice Message queued: {os.path.basename(path)} (WAV)")

    def view_sent_alerts(self):
        SentAlertsWindow(self)

    def connect_bmh(self):
        if self.connected:
            self.status("BMH already connected")
            return
        host = self.settings.get("ip_address", "192.168.10.144")
        port = int(self.settings.get("port", 6000))
        def worker():
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(4)
            try:
                s.connect((host, port))
            except OSError as exc:
                self.status(f"BMH connection not established: {exc}")
                try: s.close()
                except OSError: pass
                return
            with self.socket_lock:
                self.sock = s
                self.connected = True
            self.status(f"BMH connected: {host}:{port}")
        threading.Thread(target=worker, daemon=True).start()

    def disconnect_bmh(self):
        with self.socket_lock:
            s = self.sock
            self.sock = None
            self.connected = False
        if s:
            try: s.close()
            except OSError: pass
        self.tx_running = False
        self.status("TX stopped / BMH disconnected")

    def transmit(self, payload=None):
        payload = (payload if payload is not None else self.text.get("1.0", "end-1c")).strip()
        if not payload:
            messagebox.showwarning("Transmit", "There is no message text.", parent=self)
            return
        if not self.send_bmh.get():
            self.status("Preview only — Send to BMH is unchecked")
            messagebox.showinfo("BMH Preview", payload[:4000], parent=self)
            return
        with self.socket_lock:
            s = self.sock
        if not s:
            messagebox.showinfo("BMH Preview", "BMH is not connected. The payload is not transmitted.\n\n" + payload[:4000], parent=self)
            self.status("Transmit blocked — BMH is not connected")
            return
        data = (payload + "\n<END_OF_MESSAGE>\n").encode("utf-8")
        def worker():
            try:
                s.sendall(data)
                record = {"time_utc": datetime.now(timezone.utc).isoformat(), "payload": payload}
                self.sent_alerts.append(record)
                save_json(SENT_PATH, self.sent_alerts)
                self.status("Message payload sent to configured BMH socket")
            except OSError as exc:
                self.status(f"Transmit failed: {exc}")
        threading.Thread(target=worker, daemon=True).start()

    def restore_ui(self):
        self.geometry("1480x960")
        self.status("UI restored")

    def open_settings(self):
        SettingsDialog(self)

    def save_settings_from_dialog(self, values):
        self.settings.update(values)
        save_json(SETTINGS_PATH, self.settings)
        self.status("Settings saved")

    def _heartbeat(self):
        self.status_var.set(self.status_var.get())
        self.after(1500, self._heartbeat)

    def on_exit(self):
        self.disconnect_bmh()
        self.destroy()


class GeneratorDialog(tk.Toplevel):
    def __init__(self, parent, title, choices, callback):
        super().__init__(parent)
        self.title(title)
        self.geometry("620x420")
        self.callback = callback
        ttk.Label(self, text=title, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=8)
        ttk.Label(self, text="Type:").pack(anchor="w", padx=10)
        self.kind = ttk.Combobox(self, values=choices, state="readonly")
        self.kind.current(0)
        self.kind.pack(fill="x", padx=10, pady=4)
        ttk.Label(self, text="Warning / Watch Text and Call to Action:").pack(anchor="w", padx=10)
        self.body = tk.Text(self, height=14, wrap="word")
        self.body.pack(fill="both", expand=True, padx=10, pady=4)
        ttk.Button(self, text="Insert", command=self.submit).pack(side="right", padx=10, pady=8)
        ttk.Button(self, text="Cancel", command=self.destroy).pack(side="right", pady=8)

    def submit(self):
        self.callback(self.kind.get(), self.body.get("1.0", "end-1c").strip())
        self.destroy()


class HazardDialog(tk.Toplevel):
    def __init__(self, parent, default_hazard, callback):
        super().__init__(parent)
        self.title("Build Hazard Segment — Weather Generator")
        self.geometry("650x430")
        self.callback = callback
        ttk.Label(self, text="Hazard Segment", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=8)
        ttk.Label(self, text="Hazard:").pack(anchor="w", padx=10)
        self.hazard = ttk.Combobox(self, values=HAZARDS, state="readonly")
        self.hazard.set(default_hazard)
        self.hazard.pack(fill="x", padx=10)
        ttk.Label(self, text="Details / Call to Action:").pack(anchor="w", padx=10, pady=(8,0))
        self.details = tk.Text(self, height=10, wrap="word")
        self.details.pack(fill="both", expand=True, padx=10)
        ttk.Button(self, text="Add Hazard", command=self.submit).pack(side="right", padx=10, pady=8)
        ttk.Button(self, text="Cancel", command=self.destroy).pack(side="right", pady=8)
        self.grab_set()

    def submit(self):
        self.callback({"hazard": self.hazard.get(), "details": self.details.get("1.0", "end-1c").strip()})
        self.destroy()


class PolygonDialog(tk.Toplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("KLOT Polygon Tool")
        self.geometry("760x560")
        self.callback = callback
        ttk.Label(self, text="KLOT Polygon Tool", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=8)
        row = ttk.Frame(self); row.pack(fill="x", padx=10)
        ttk.Label(row, text="Name:").pack(side="left")
        self.name = ttk.Entry(row); self.name.pack(side="left", fill="x", expand=True, padx=5)
        ttk.Label(row, text="Create:").pack(side="left", padx=4)
        self.kind = ttk.Combobox(row, values=["Single Storm", "Line of Storms"], state="readonly", width=20)
        self.kind.set("Single Storm"); self.kind.pack(side="left")
        ttk.Label(self, text="LAT...LON (one vertex per line):").pack(anchor="w", padx=10, pady=(8,0))
        self.coords = tk.Text(self, height=18, font=("Consolas", 10))
        self.coords.pack(fill="both", expand=True, padx=10)
        ttk.Button(self, text="Create Polygon", command=self.submit).pack(side="right", padx=10, pady=8)
        ttk.Button(self, text="Cancel", command=self.destroy).pack(side="right", pady=8)
        self.grab_set()

    def submit(self):
        coords = [x.strip() for x in self.coords.get("1.0", "end-1c").splitlines() if x.strip()]
        if not coords:
            messagebox.showwarning("Polygon", "Enter at least one LAT...LON vertex.", parent=self)
            return
        self.callback({"name": self.name.get().strip() or "Polygon", "type": self.kind.get(), "coords": coords})
        self.destroy()


class SettingsDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("LOTWPS / LOTIEM Settings")
        self.geometry("540x420")
        self.grab_set()
        fields = [
            ("IP Address", str(app.settings.get("ip_address", ""))),
            ("IP Port", str(app.settings.get("port", 6000))),
            ("Station ID", str(app.settings.get("station_id", "WXK89"))),
            ("Station Location", str(app.settings.get("station_location", "Valparaiso, Indiana"))),
            ("Frequency MHz", str(app.settings.get("frequency_mhz", "162.400"))),
        ]
        self.entries = {}
        for label, value in fields:
            row = ttk.Frame(self); row.pack(fill="x", padx=10, pady=5)
            ttk.Label(row, text=label, width=20).pack(side="left")
            ent = ttk.Entry(row); ent.insert(0, value); ent.pack(side="left", fill="x", expand=True)
            self.entries[label] = ent
        ttk.Label(self, text="Settings are stored in lotwps_lotiem_settings.json").pack(anchor="w", padx=10, pady=8)
        ttk.Button(self, text="Save", command=self.save).pack(side="right", padx=10)
        ttk.Button(self, text="Cancel", command=self.destroy).pack(side="right")

    def save(self):
        values = {
            "ip_address": self.entries["IP Address"].get().strip(),
            "port": int(self.entries["IP Port"].get().strip()),
            "station_id": self.entries["Station ID"].get().strip(),
            "station_location": self.entries["Station Location"].get().strip(),
            "frequency_mhz": self.entries["Frequency MHz"].get().strip(),
        }
        self.app.save_settings_from_dialog(values)
        self.destroy()


class BMHWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("BMH Network — WXK89")
        self.geometry("1220x820")
        self._build()

    def _build(self):
        outer = ttk.Frame(self); outer.pack(fill="both", expand=True, padx=8, pady=8)
        left = ttk.Frame(outer); right = ttk.Frame(outer)
        left.pack(side="left", fill="both", expand=True, padx=(0,4))
        right.pack(side="right", fill="both", expand=True, padx=(4,0))

        net = ttk.LabelFrame(left, text="Global Network Controls")
        net.pack(fill="x", pady=3)
        ttk.Button(net, text="Update Periodic Scroll", command=lambda: self._msg("Periodic scroll updated")).pack(side="left", padx=4, pady=4)
        self.ticker = ttk.Entry(net)
        self.ticker.insert(0, "Edit the BMH Network ticker text")
        self.ticker.pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(net, text="TRANSMIT", command=self._ticker_tx).pack(side="right", padx=4)

        hz = ttk.LabelFrame(left, text="Hazard")
        hz.pack(fill="x", pady=3)
        for hazard in HAZARDS:
            ttk.Button(hz, text=hazard, command=lambda h=hazard: self._add_hazard(h)).pack(fill="x", padx=4, pady=1)

        weather = ttk.LabelFrame(left, text="Weather Message")
        weather.pack(fill="both", expand=True, pady=3)
        ttk.Label(weather, text="Hazard Category:").pack(anchor="w", padx=4)
        self.hazard = ttk.Combobox(weather, values=HAZARDS, state="readonly")
        self.hazard.set(HAZARDS[0]); self.hazard.pack(fill="x", padx=4)
        ttk.Label(weather, text="Warning Message / Call to Action Text:").pack(anchor="w", padx=4, pady=(5,0))
        self.body = tk.Text(weather, height=8)
        self.body.pack(fill="both", expand=True, padx=4)
        ttk.Button(weather, text="Update Periodic Scroll", command=lambda: self._msg("Weather scroll updated")).pack(fill="x", padx=4, pady=2)

        same = ttk.LabelFrame(left, text="SAME / EAS Builder")
        same.pack(fill="x", pady=3)
        ttk.Label(same, text="UGC — Northeast IL:").grid(row=0, column=0, sticky="w", padx=4)
        ttk.Entry(same, textvariable=self.app.ugc_ne_var).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Label(same, text="UGC — Northwest IN:").grid(row=1, column=0, sticky="w", padx=4)
        ttk.Entry(same, textvariable=self.app.ugc_nw_var).grid(row=1, column=1, sticky="ew", padx=4)
        ttk.Label(same, text="Custom Message:").grid(row=2, column=0, sticky="nw", padx=4)
        self.same_msg = tk.Text(same, height=4)
        self.same_msg.insert("1.0", "This is a test.")
        self.same_msg.grid(row=2, column=1, sticky="ew", padx=4)
        ttk.Button(same, text="SEND SAME ALERT", command=self._same_preview).grid(row=3, column=1, sticky="e", padx=4, pady=4)
        same.columnconfigure(1, weight=1)

        station = ttk.LabelFrame(right, text="BMH Station Controller — WXK89")
        station.pack(fill="x")
        ttk.Label(station, text="STATION: WXK89 ONLINE").pack(anchor="w", padx=4, pady=2)
        ttk.Label(station, text="Valparaiso, Indiana | 162.400 MHz").pack(anchor="w", padx=4)
        tx = ttk.Frame(station); tx.pack(fill="x", pady=4)
        ttk.Button(tx, text="START TX", command=self.app.connect_bmh).pack(side="left", padx=2)
        ttk.Button(tx, text="STOP TX", command=self.app.disconnect_bmh).pack(side="left", padx=2)
        ttk.Button(tx, text="NEXT PRODUCT", command=lambda: self._msg("Next product requested")).pack(side="left", padx=2)
        ttk.Button(tx, text="RESTART SERVICE", command=lambda: self._msg("Service restart requested")).pack(side="left", padx=2)

        modes = ttk.LabelFrame(right, text="Operational Modes")
        modes.pack(fill="both", expand=True, pady=3)
        self.mode_list = tk.Listbox(modes, height=9)
        for m in MODES: self.mode_list.insert("end", m)
        self.mode_list.pack(fill="both", expand=True, padx=4)
        buttons = ttk.Frame(modes); buttons.pack(fill="x", pady=3)
        ttk.Button(buttons, text="NEW MODE", command=lambda: self._mode_add()).pack(side="left")
        ttk.Button(buttons, text="DELETE MODE", command=lambda: self._mode_delete()).pack(side="left", padx=3)
        ttk.Button(buttons, text="RESET MODE", command=lambda: self._mode_reset()).pack(side="left")

        cycle = ttk.LabelFrame(right, text="Broadcast Cycles")
        cycle.pack(fill="x", pady=3)
        ttk.Label(cycle, text="Available Entries:").pack(anchor="w", padx=4)
        self.cycle_list = ttk.Combobox(cycle, values=CYCLE_ENTRIES, state="readonly")
        self.cycle_list.set(CYCLE_ENTRIES[0]); self.cycle_list.pack(fill="x", padx=4)
        ttk.Label(cycle, text="Cycle Order: 1  2  3  4  5  6  7  8  9").pack(anchor="w", padx=4, pady=2)
        cb = ttk.Frame(cycle); cb.pack(fill="x")
        for label in ["NEW MODE", "DELETE MODE", "RESET MODE"]:
            ttk.Button(cb, text=label, command=lambda l=label: self._msg(l)).pack(side="left", padx=2)

        static = ttk.LabelFrame(right, text="Static Messages")
        static.pack(fill="both", expand=True, pady=3)
        self.static = tk.Listbox(static, height=6)
        for sid in STATIC_IDS: self.static.insert("end", sid)
        self.static.pack(fill="both", expand=True, padx=4)

        live = ttk.LabelFrame(right, text="Live Queue")
        live.pack(fill="x", pady=3)
        self.current = ttk.Combobox(live, values=STATIC_IDS, state="readonly")
        self.current.set("ADVANCE"); self.current.pack(fill="x", padx=4, pady=2)
        ttk.Label(live, text=f"Queue Length: {len(self.app.queue)}").pack(anchor="w", padx=4)
        lb = ttk.Frame(live); lb.pack(fill="x")
        ttk.Button(lb, text="REFRESH NOW", command=lambda: self._msg(f"Queue length: {len(self.app.queue)}")).pack(side="left", padx=2)
        ttk.Button(lb, text="READ SELECTED NOW", command=self._read_selected).pack(side="left", padx=2)
        ttk.Button(lb, text="LOOP SELECTED", command=lambda: self._msg("Loop selected")).pack(side="left", padx=2)
        ttk.Button(lb, text="STOP LOOP", command=lambda: self._msg("Stop loop")).pack(side="left", padx=2)

        quick = ttk.LabelFrame(right, text="Quick Read Internal IDs")
        quick.pack(fill="x", pady=3)
        for sid in ["STATION_ID","CURRENT_TIME","SVR_STATION_ID","SEVERE_MESSAGE","NWSLOT","SUMMARY","EMR_STATION_ID","PREPAREDNESS_ACTIONS"]:
            ttk.Button(quick, text=sid, command=lambda s=sid: self._quick_read(s)).pack(side="left", padx=2, pady=2)

        manual = ttk.LabelFrame(right, text="Manual Product Control")
        manual.pack(fill="x", pady=3)
        row = ttk.Frame(manual); row.pack(fill="x")
        self.product = ttk.Entry(row); self.product.insert(0, "LOT_PRODUCT_ID"); self.product.pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(row, text="READ NOW", command=self._read_product).pack(side="left")
        ttk.Button(row, text="LOOP PRODUCT", command=lambda: self._msg("Loop product")).pack(side="left", padx=2)
        ttk.Button(row, text="STOP LOOP", command=lambda: self._msg("Stop loop")).pack(side="left")

        alerts = ttk.LabelFrame(right, text="Active Alerts")
        alerts.pack(fill="both", expand=True, pady=3)
        self.alerts = tk.Listbox(alerts, height=5)
        self.alerts.pack(fill="both", expand=True, padx=4)
        ab = ttk.Frame(alerts); ab.pack(fill="x")
        for label in ["REFRESH LIST","EDIT SELECTED","SAME RETONE","1050 HZ","SILENT INTERRUPT"]:
            ttk.Button(ab, text=label, command=lambda l=label: self._msg(l)).pack(side="left", padx=2)

        products = ttk.LabelFrame(right, text="@Products")
        products.pack(fill="x", pady=3)
        self.products = ttk.Combobox(products, values=CYCLE_ENTRIES, state="readonly")
        self.products.set(CYCLE_ENTRIES[0]); self.products.pack(fill="x", padx=4, pady=3)

    def _msg(self, value):
        messagebox.showinfo("BMH Network", value, parent=self)

    def _add_hazard(self, hazard):
        self.hazard.set(hazard)
        self.app.text.insert("end", f"\n[{hazard}]\n")
        self.app.status(f"{hazard} selected in BMH")

    def _ticker_tx(self):
        self.app.transmit(self.ticker.get())

    def _same_preview(self):
        body = self.same_msg.get("1.0", "end-1c").strip()
        preview = (
            f"UGC NE IL: {self.app.ugc_ne_var.get()}\n"
            f"UGC NW IN: {self.app.ugc_nw_var.get()}\n"
            f"Custom: {body}"
        )
        messagebox.showinfo("SAME / EAS Preview", preview, parent=self)

    def _read_selected(self):
        sid = self.current.get()
        self.app.queue.append(sid)
        self.app.status(f"Queued internal product {sid}")

    def _quick_read(self, sid):
        self.app.text.insert("end", f"\n[{sid}]\n")
        self.app.status(f"Quick Read selected: {sid}")

    def _read_product(self):
        pid = self.product.get().strip()
        self.app.queue.append(pid)
        self.app.status(f"Manual product queued: {pid}")

    def _mode_add(self):
        value = simpledialog.askstring("New Mode", "Mode name:", parent=self)
        if value:
            self.mode_list.insert("end", value)

    def _mode_delete(self):
        sel = self.mode_list.curselection()
        if sel:
            self.mode_list.delete(sel[0])

    def _mode_reset(self):
        self.mode_list.delete(0, "end")
        for m in MODES: self.mode_list.insert("end", m)


class StationController(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("BMH Station Controller — WXK89")
        self.geometry("700x520")
        ttk.Label(self, text="STATION: WXK89 ONLINE", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=8)
        ttk.Label(self, text="Valparaiso, Indiana | 162.400 MHz").pack(anchor="w", padx=10)
        ttk.Label(self, text=f"IP: {app.settings.get('ip_address')}:{app.settings.get('port')}").pack(anchor="w", padx=10)
        self._buttons()

    def _buttons(self):
        f = ttk.Frame(self); f.pack(fill="x", padx=10, pady=10)
        for label, cmd in [
            ("START TX", self.app.connect_bmh), ("STOP TX", self.app.disconnect_bmh),
            ("NEXT PRODUCT", lambda: self.app.status("Next product requested")),
            ("RESTART SERVICE", lambda: self.app.status("Restart service requested")),
        ]:
            ttk.Button(f, text=label, command=cmd).pack(side="left", padx=2)

        same = ttk.LabelFrame(self, text="SAME / EAS Builder")
        same.pack(fill="x", padx=10, pady=8)
        ttk.Label(same, text="UGC NE IL").grid(row=0, column=0, sticky="w", padx=4)
        ttk.Entry(same, textvariable=self.app.ugc_ne_var).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Label(same, text="UGC NW IN").grid(row=1, column=0, sticky="w", padx=4)
        ttk.Entry(same, textvariable=self.app.ugc_nw_var).grid(row=1, column=1, sticky="ew", padx=4)
        ttk.Label(same, text="Custom Message").grid(row=2, column=0, sticky="nw", padx=4)
        txt = tk.Text(same, height=5); txt.insert("1.0","This is a test."); txt.grid(row=2, column=1, sticky="ew")
        ttk.Button(same, text="SEND SAME ALERT", command=lambda: messagebox.showinfo("SAME", "Preview only — verify UGC and message before any external use.", parent=self)).grid(row=3, column=1, sticky="e", padx=4, pady=4)
        same.columnconfigure(1, weight=1)


class ActiveAlertsWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("AWIPS Active Alerts — Unified")
        self.geometry("980x560")
        self.tree = ttk.Treeview(self, columns=("id","summary","action","expires"), show="headings")
        for col, text, w in [("id","ID",120),("summary","Summary",430),("action","Action",100),("expires","Expires",240)]:
            self.tree.heading(col, text=text); self.tree.column(col, width=w)
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)
        for item in self.app.sent_alerts:
            self.tree.insert("", "end", values=(item.get("id",""), item.get("summary","Sent message"), item.get("action","NEW"), item.get("expires","")))
        bar = ttk.Frame(self); bar.pack(fill="x", padx=8, pady=4)
        ttk.Button(bar, text="REFRESH LIST", command=self.refresh).pack(side="left")
        ttk.Button(bar, text="EDIT SELECTED", command=self.edit).pack(side="left", padx=3)
        ttk.Button(bar, text="SAME RETONE", command=lambda: self._info("SAME RETONE")).pack(side="left")
        ttk.Button(bar, text="1050 HZ", command=lambda: self._info("1050 Hz")).pack(side="left", padx=3)
        ttk.Button(bar, text="SILENT INTERRUPT", command=lambda: self._info("Silent interrupt")).pack(side="left")

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for item in self.app.sent_alerts:
            self.tree.insert("", "end", values=(item.get("id",""), item.get("summary","Sent message"), item.get("action","NEW"), item.get("expires","")))

    def edit(self):
        self._info("Selected alert editor opened as a simulation placeholder.")

    def _info(self, title):
        messagebox.showinfo(title, "Simulation control — no automatic alert transmission is performed.", parent=self)


class SentAlertsWindow(ActiveAlertsWindow):
    def __init__(self, app):
        super().__init__(app)
        self.title("View Sent Alerts / Edit Sent Alerts")


if __name__ == "__main__":
    if not os.path.exists(SETTINGS_PATH):
        save_json(SETTINGS_PATH, DEFAULT_SETTINGS)
    App().mainloop()
