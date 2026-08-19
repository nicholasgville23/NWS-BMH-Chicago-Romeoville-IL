"""
KLOT LOTIEM TEXT WORKSTATION - Tkinter GUI Main (network-enabled)
Run: python text_workstation_main.py
This update adds basic TCP network wiring to send messages to a BMH endpoint (config.json IP/port).
- Non-blocking connect/send using threads
- START TX / STOP TX / TRANSMIT buttons wired to network actions
- Basic connection status reporting
Security: this is a simple TCP client for lab/testing only. Do not connect to production devices without safeguards.
"""

import json
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from datetime import datetime
import os
import socket
import threading
import time

BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')


def load_config():
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        print('Failed to load config:', e)
        return {}


class TextWorkstationApp(tk.Tk):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.title('KLOT LOTIEM TEXT WORKSTATION')
        self.geometry('1300x900')

        # Networking state
        self.bmh_sock = None
        self.bmh_connected = False
        self.bmh_lock = threading.Lock()

        self.create_menu()
        self.create_widgets()
        self.create_bindings()

        # in-memory segments and polygons
        self.segments = []
        self.hazard_segments = []
        self.polygons = []

    def create_menu(self):
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label='Restore UI', command=self.restore_ui)
        filemenu.add_separator()
        filemenu.add_command(label='Settings', command=self.open_settings)
        filemenu.add_separator()
        filemenu.add_command(label='Exit', command=self.quit)
        menubar.add_cascade(label='System', menu=filemenu)
        self.config(menu=menubar)

    def create_widgets(self):
        main_pane = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True)

        # Left frame - Compose and Dispatch
        left_frame = ttk.Frame(main_pane, width=800)
        main_pane.add(left_frame, weight=3)

        title = ttk.Label(left_frame, text='KLOT LOTIEM TEXT WORKSTATION', font=('Segoe UI', 14, 'bold'))
        title.pack(anchor='nw', padx=8, pady=6)

        controls_frame = ttk.Frame(left_frame)
        controls_frame.pack(fill=tk.X, padx=8)

        ip_label = ttk.Label(controls_frame, text=f"IP: {self.config.get('ip_address')}:{self.config.get('port')}")
        ip_label.pack(side=tk.LEFT)

        new_msg_btn = ttk.Button(controls_frame, text='New Text Message', command=self.new_text_message)
        new_msg_btn.pack(side=tk.RIGHT)

        # Text widget
        text_frame = ttk.Frame(left_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.text_widget = tk.Text(text_frame, wrap=tk.WORD)
        self.text_widget.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        text_vscroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_widget.yview)
        text_vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_widget['yscrollcommand'] = text_vscroll.set

        # Options
        options_frame = ttk.LabelFrame(left_frame, text='Message Options')
        options_frame.pack(fill=tk.X, padx=8, pady=6)

        self.send_bmh_var = tk.BooleanVar(value=True)
        self.send_email_var = tk.BooleanVar()
        self.send_iembot_var = tk.BooleanVar()
        self.send_web_var = tk.BooleanVar()
        self.wrap_var = tk.BooleanVar(value=True)

        ttk.Checkbutton(options_frame, text='Send to BMH', variable=self.send_bmh_var).pack(side=tk.LEFT, padx=4, pady=2)
        ttk.Checkbutton(options_frame, text='Send to Email', variable=self.send_email_var).pack(side=tk.LEFT, padx=4, pady=2)
        ttk.Checkbutton(options_frame, text='Send to IEMBOT', variable=self.send_iembot_var).pack(side=tk.LEFT, padx=4, pady=2)
        ttk.Checkbutton(options_frame, text='Send to Websites & Outlets', variable=self.send_web_var).pack(side=tk.LEFT, padx=4, pady=2)
        ttk.Checkbutton(options_frame, text='Wrap chat edits (character)', variable=self.wrap_var).pack(side=tk.LEFT, padx=4, pady=2)

        action_frame = ttk.Frame(left_frame)
        action_frame.pack(fill=tk.X, padx=8, pady=6)

        ttk.Button(action_frame, text='Enter Editor Mode', command=self.enter_editor_mode).pack(side=tk.LEFT, padx=4)
        ttk.Button(action_frame, text='AWIPS Header Block', command=self.generate_awips_header).pack(side=tk.LEFT, padx=4)
        ttk.Button(action_frame, text='WarnGen', command=self.open_warngen).pack(side=tk.LEFT, padx=4)
        ttk.Button(action_frame, text='WatchGen', command=self.open_watchgen).pack(side=tk.LEFT, padx=4)
        ttk.Button(action_frame, text='Polygon Tool', command=self.open_polygon_tool).pack(side=tk.LEFT, padx=4)

        ttk.Button(action_frame, text='View Sent Alerts / Edit Sent Alerts', command=self.view_sent_alerts).pack(side=tk.RIGHT, padx=4)

        # Right frame - AWIPS / Tools / BMH Controls
        right_frame = ttk.Frame(main_pane, width=500)
        main_pane.add(right_frame, weight=1)

        # AWIPS tools section
        awips_frame = ttk.LabelFrame(right_frame, text='AWIPS / WarnGen Tools')
        awips_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        ttk.Button(awips_frame, text='WFO LOT', command=lambda: self.show_info('WFO LOT pressed')).pack(anchor='ne')

        # Quick fields
        ttk.Label(awips_frame, text='Product Category / Hazard Codes:').pack(anchor='w', pady=2)
        self.product_entry = ttk.Entry(awips_frame)
        self.product_entry.pack(fill=tk.X, padx=4)

        ttk.Label(awips_frame, text='Addressee:').pack(anchor='w', pady=2)
        self.addressee_entry = ttk.Entry(awips_frame)
        self.addressee_entry.insert(0, self.config.get('default_awips', {}).get('addressee', 'ALL'))
        self.addressee_entry.pack(fill=tk.X, padx=4)

        ttk.Button(awips_frame, text='Generate AWIPS Header', command=self.generate_awips_header).pack(fill=tk.X, padx=4, pady=6)

        # SAME / EAS builder
        sane_frame = ttk.LabelFrame(awips_frame, text='SAME / EAS Builder')
        sane_frame.pack(fill=tk.X, padx=4, pady=6)
        ttk.Label(sane_frame, text='UGC for NE IL:').pack(anchor='w')
        self.ugc_ne_entry = ttk.Entry(sane_frame)
        self.ugc_ne_entry.insert(0, self.config.get('sane_builder', {}).get('ugc_ne_il',''))
        self.ugc_ne_entry.pack(fill=tk.X)
        ttk.Label(sane_frame, text='UGC for NW IN:').pack(anchor='w')
        self.ugc_nw_entry = ttk.Entry(sane_frame)
        self.ugc_nw_entry.insert(0, self.config.get('sane_builder', {}).get('ugc_nw_in',''))
        self.ugc_nw_entry.pack(fill=tk.X)
        ttk.Button(sane_frame, text='SEND SAME ALERT', command=self.send_sane_alert).pack(fill=tk.X, pady=4)

        # BMH Network quick-launch
        bmh_frame = ttk.LabelFrame(right_frame, text='BMH Network')
        bmh_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        ttk.Label(bmh_frame, text=f"Station: {self.config.get('station')}    Location: {self.config.get('location')}").pack(anchor='w', padx=4)
        ttk.Label(bmh_frame, text=f"IP: {self.config.get('ip_address')}:{self.config.get('port')}    Status: {self.config.get('network_status')}").pack(anchor='w', padx=4)

        self.station_list = tk.Listbox(bmh_frame, height=6)
        self.station_list.insert(tk.END, f"{self.config.get('station')} - {self.config.get('location')}")
        self.station_list.pack(fill=tk.X, padx=4, pady=4)
        self.station_list.bind('<Double-Button-1>', self.open_station_controller_from_list)

        ttk.Button(bmh_frame, text='Open BMH Window', command=self.open_bmh_network).pack(fill=tk.X, padx=4, pady=2)

        # Listening area options
        listen_frame = ttk.LabelFrame(bmh_frame, text='Listening Area')
        listen_frame.pack(fill=tk.X, padx=4, pady=6)
        self.listen_filter_var = tk.BooleanVar(value=self.config.get('listening_area', {}).get('enable_filtering', True))
        self.listen_allow_var = tk.BooleanVar(value=self.config.get('listening_area', {}).get('allow_routine_without_fips', True))
        ttk.Checkbutton(listen_frame, text='Enable listening-area filtering', variable=self.listen_filter_var).pack(anchor='w')
        ttk.Checkbutton(listen_frame, text='Allow routine products without FIPS/zone coding', variable=self.listen_allow_var).pack(anchor='w')

        # Bottom status
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X)
        self.status_label = ttk.Label(status_frame, text='Ready')
        self.status_label.pack(side=tk.LEFT, padx=8, pady=4)

    def create_bindings(self):
        # Context menu on text widget
        self.text_menu = tk.Menu(self, tearoff=0)
        self.text_menu.add_command(label='Add Segment', command=self.add_segment)
        self.text_menu.add_command(label='Edit Segment', command=self.edit_segment)
        self.text_menu.add_command(label='Remove Segment', command=self.remove_segment)
        self.text_menu.add_command(label='Combine Segment', command=self.combine_segment)
        self.text_menu.add_separator()
        self.text_menu.add_command(label='Add New Hazard Segment', command=self.add_hazard_segment)
        self.text_menu.add_command(label='Add Hazard to Existing Segment', command=self.add_hazard_to_segment)

        self.text_widget.bind('<Button-3>', self.show_text_context)

    # --- Networking ---
    def bmh_connect(self):
        """Connect to BMH endpoint (non-blocking thread)."""
        if self.bmh_connected:
            self.status('Already connected to BMH')
            return
        t = threading.Thread(target=self._bmh_connect_thread, daemon=True)
        t.start()

    def _bmh_connect_thread(self):
        ip = self.config.get('ip_address')
        port = int(self.config.get('port'))
        self.status(f'Connecting to BMH {ip}:{port}...')
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        try:
            sock.connect((ip, port))
            with self.bmh_lock:
                self.bmh_sock = sock
                self.bmh_connected = True
            self.status(f'Connected to BMH {ip}:{port}')
        except Exception as e:
            try:
                sock.close()
            except: pass
            self.status(f'BMH connect failed: {e}')

    def bmh_disconnect(self):
        with self.bmh_lock:
            if self.bmh_sock:
                try:
                    self.bmh_sock.shutdown(socket.SHUT_RDWR)
                except: pass
                try:
                    self.bmh_sock.close()
                except: pass
                self.bmh_sock = None
            self.bmh_connected = False
        self.status('Disconnected from BMH')

    def bmh_send(self, data: str):
        """Send data to BMH in a background thread."""
        if not self.bmh_connected:
            self.status('Not connected to BMH; starting connection and will send when connected')
            # Connect then send
            def connect_and_send():
                self._bmh_connect_thread()
                # Wait briefly for connection
                for _ in range(10):
                    with self.bmh_lock:
                        if self.bmh_connected:
                            break
                    time.sleep(0.3)
                with self.bmh_lock:
                    if self.bmh_connected and self.bmh_sock:
                        try:
                            self.bmh_sock.sendall(data.encode('utf-8'))
                            self.status('Message sent to BMH')
                        except Exception as e:
                            self.status(f'Failed to send: {e}')
                    else:
                        self.status('Unable to send: not connected')
            threading.Thread(target=connect_and_send, daemon=True).start()
            return

        def send_thread():
            with self.bmh_lock:
                sock = self.bmh_sock
            try:
                sock.sendall(data.encode('utf-8'))
                self.status('Message sent to BMH')
            except Exception as e:
                self.status(f'Failed to send: {e}')

        threading.Thread(target=send_thread, daemon=True).start()

    # --- Actions / stubs ---
    def new_text_message(self):
        self.text_widget.delete('1.0', tk.END)
        self.status('New text message')

    def enter_editor_mode(self):
        messagebox.showinfo('Editor Mode', 'Entered editor mode (stub)')
        self.status('Editor mode')

    def generate_awips_header(self):
        awips = self.config.get('default_awips', {})
        # Simple TTAAii-formatted header with current time (UTC) for TTAAii placeholder
        utc = datetime.utcnow()
        ttaaii = f"TTAA{utc.strftime('%H%M')}"
        header = f"/{ttaaii} {awips.get('CCCC')} {awips.get('BBB')}{awips.get('BBB_version')}\nWSFO: {awips.get('wsfo_id')}\nProduct: {awips.get('product_designator')}\nAddressee: {self.addressee_entry.get()}"
        self.text_widget.insert('1.0', header + '\n\n')
        self.status('AWIPS header generated')

    def open_warngen(self):
        dlg = WarnGenDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self.text_widget.insert(tk.END, '\n[WarnGen] ' + dlg.result + '\n')
            self.status('WarnGen inserted')

    def open_watchgen(self):
        dlg = WatchGenDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self.text_widget.insert(tk.END, '\n[WatchGen] ' + dlg.result + '\n')
            self.status('WatchGen inserted')

    def open_polygon_tool(self):
        dlg = PolygonToolDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self.polygons.append(dlg.result)
            self.text_widget.insert(tk.END, f"\n[Polygon] {dlg.result}\n")
            self.status('Polygon added')

    def view_sent_alerts(self):
        messagebox.showinfo('Sent Alerts', 'Open sent alerts editor (stub)')

    def open_bmh_network(self):
        BMHNetworkWindow(self, self.config)

    def open_station_controller_from_list(self, event):
        selection = self.station_list.curselection()
        if selection:
            item = self.station_list.get(selection[0])
            StationControllerWindow(self, self.config)

    # Text context menu actions
    def show_text_context(self, event):
        try:
            self.text_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.text_menu.grab_release()

    def add_segment(self):
        seg = simpledialog.askstring('Add Segment', 'Enter segment text:')
        if seg:
            self.segments.append(seg)
            self.text_widget.insert(tk.END, '\n[Segment] ' + seg + '\n')
            self.status('Segment added')

    def edit_segment(self):
        if not self.segments:
            messagebox.showwarning('Edit Segment', 'No segments to edit')
            return
        idx = simpledialog.askinteger('Edit Segment', f'Choose segment number (1-{len(self.segments)}):', minvalue=1, maxvalue=len(self.segments))
        if idx:
            new = simpledialog.askstring('Edit Segment', 'New text:', initialvalue=self.segments[idx-1])
            if new is not None:
                self.segments[idx-1] = new
                self.status('Segment edited')

    def remove_segment(self):
        if not self.segments:
            messagebox.showwarning('Remove Segment', 'No segments to remove')
            return
        idx = simpledialog.askinteger('Remove Segment', f'Choose segment number (1-{len(self.segments)}):', minvalue=1, maxvalue=len(self.segments))
        if idx:
            self.segments.pop(idx-1)
            self.status('Segment removed')

    def combine_segment(self):
        if len(self.segments) < 2:
            messagebox.showwarning('Combine', 'Need at least 2 segments')
            return
        idx1 = simpledialog.askinteger('Combine', f'First segment (1-{len(self.segments)}):', minvalue=1, maxvalue=len(self.segments))
        idx2 = simpledialog.askinteger('Combine', f'Second segment (1-{len(self.segments)}):', minvalue=1, maxvalue=len(self.segments))
        if idx1 and idx2:
            combined = self.segments[idx1-1] + ' ' + self.segments[idx2-1]
            # remove higher index first
            for i in sorted([idx1-1, idx2-1], reverse=True):
                self.segments.pop(i)
            self.segments.append(combined)
            self.text_widget.insert(tk.END, '\n[Combined Segment] ' + combined + '\n')
            self.status('Segments combined')

    def add_hazard_segment(self):
        dlg = HazardDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self.hazard_segments.append(dlg.result)
            self.text_widget.insert(tk.END, '\n[Hazard Segment] ' + dlg.result + '\n')
            self.status('Hazard segment added')

    def add_hazard_to_segment(self):
        if not self.segments:
            messagebox.showwarning('Add Hazard', 'No existing segments')
            return
        idx = simpledialog.askinteger('Add Hazard to Segment', f'Choose segment number (1-{len(self.segments)}):', minvalue=1, maxvalue=len(self.segments))
        if idx:
            hazard = simpledialog.askstring('Hazard Text', 'Enter hazard text:')
            if hazard:
                self.segments[idx-1] += '\n[Hazard] ' + hazard
                self.status('Hazard added to segment')

    def restore_ui(self):
        messagebox.showinfo('Restore UI', 'UI restored to default (stub)')
        self.status('UI restored')

    def status(self, msg):
        self.status_label.config(text=f"{datetime.now().strftime('%H:%M:%S')} - {msg}")

    def open_settings(self):
        messagebox.showinfo('Settings', 'Open system settings (stub)')

    def show_info(self, text):
        messagebox.showinfo('Info', text)

    def send_sane_alert(self):
        # Build a simple SAME/EAS message preview using UGC entries
        ugc_ne = self.ugc_ne_entry.get().strip()
        ugc_nw = self.ugc_nw_entry.get().strip()
        msg_preview = f"SAME ALERT PREVIEW:\nNE IL: {ugc_ne}\nNW IN: {ugc_nw}\nCustom Message: {self.text_widget.get('1.0', '1.400').strip()}"
        # placeholder for actual SAME send
        messagebox.showinfo('SAME Alert', msg_preview)
        self.status('SAME alert prepared (not transmitted)')

    # High-level TX controls
    def start_tx(self):
        self.bmh_connect()

    def stop_tx(self):
        self.bmh_disconnect()

    def transmit_text(self, text: str = None):
        if text is None:
            text = self.text_widget.get('1.0', tk.END).strip()
        if not text:
            messagebox.showwarning('Transmit', 'No text to transmit')
            return
        if not self.send_bmh_var.get():
            messagebox.showinfo('Transmit', 'Send to BMH option is not checked')
            return
        # Mark message with simple delimiter for the receiver
        payload = text + '\n\n<END_OF_MESSAGE>\n'
        self.bmh_send(payload)


# --- Dialogs ---
class WarnGenDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title('WarnGen - Warning Generator')
        self.result = None
        ttk.Label(self, text='Warning Type:').pack(anchor='w', padx=8, pady=4)
        self.type_cb = ttk.Combobox(self, values=['Severe Thunderstorm Warning','Tornado Warning','Flash Flood Warning','Special Weather Statement','Extreme Wind Warning'])
        self.type_cb.current(0)
        self.type_cb.pack(fill=tk.X, padx=8)
        ttk.Label(self, text='Call to Action / Text:').pack(anchor='w', padx=8, pady=4)
        self.text = tk.Text(self, height=8)
        self.text.pack(fill=tk.BOTH, padx=8, pady=4)
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(btn_frame, text='Insert', command=self.on_insert).pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text='Cancel', command=self.destroy).pack(side=tk.RIGHT)

    def on_insert(self):
        t = f"{self.type_cb.get()}: {self.text.get('1.0', tk.END).strip()}"
        self.result = t
        self.destroy()


class WatchGenDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title('WatchGen - Watch Generator')
        self.result = None
        ttk.Label(self, text='Watch Type:').pack(anchor='w', padx=8, pady=4)
        self.type_cb = ttk.Combobox(self, values=['Severe Thunderstorm Watch','Tornado Watch','Flood Watch'])
        self.type_cb.current(0)
        self.type_cb.pack(fill=tk.X, padx=8)
        ttk.Label(self, text='Watch Text:').pack(anchor='w', padx=8, pady=4)
        self.text = tk.Text(self, height=6)
        self.text.pack(fill=tk.BOTH, padx=8, pady=4)
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(btn_frame, text='Insert', command=self.on_insert).pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text='Cancel', command=self.destroy).pack(side=tk.RIGHT)

    def on_insert(self):
        t = f"{self.type_cb.get()}: {self.text.get('1.0', tk.END).strip()}"
        self.result = t
        self.destroy()


class PolygonToolDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title('KLOT Polygon Tool')
        self.result = None
        ttk.Label(self, text='Polygon Name:').pack(anchor='w', padx=8, pady=4)
        self.name_entry = ttk.Entry(self)
        self.name_entry.pack(fill=tk.X, padx=8)
        ttk.Label(self, text='Create Type:').pack(anchor='w', padx=8, pady=4)
        self.type_cb = ttk.Combobox(self, values=['Single Storm','Line of Storms'])
        self.type_cb.current(0)
        self.type_cb.pack(fill=tk.X, padx=8)
        ttk.Label(self, text='Enter coordinates (lat,lon) one per line:').pack(anchor='w', padx=8, pady=4)
        self.coords_text = tk.Text(self, height=8)
        self.coords_text.pack(fill=tk.BOTH, padx=8, pady=4)
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(btn_frame, text='Create Polygon', command=self.on_create).pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text='Cancel', command=self.destroy).pack(side=tk.RIGHT)

    def on_create(self):
        name = self.name_entry.get().strip() or 'polygon'
        poly_type = self.type_cb.get()
        coords = [line.strip() for line in self.coords_text.get('1.0', tk.END).splitlines() if line.strip()]
        if not coords:
            messagebox.showwarning('Polygon', 'Enter at least one coordinate')
            return
        self.result = {'name': name, 'type': poly_type, 'coords': coords}
        self.destroy()


class HazardDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title('Build Hazard Segment')
        self.result = None
        ttk.Label(self, text='Hazard Type:').pack(anchor='w', padx=8, pady=4)
        self.type_cb = ttk.Combobox(self, values=['Severe Thunderstorm Warning','Tornado Warning','Flash Flood Warning','Special Weather Statement','Extreme Wind Warning'])
        self.type_cb.current(0)
        self.type_cb.pack(fill=tk.X, padx=8)
        ttk.Label(self, text='Hazard Details:').pack(anchor='w', padx=8, pady=4)
        self.details = tk.Text(self, height=6)
        self.details.pack(fill=tk.BOTH, padx=8, pady=4)
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(btn_frame, text='Add Hazard', command=self.on_add).pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text='Cancel', command=self.destroy).pack(side=tk.RIGHT)

    def on_add(self):
        t = f"{self.type_cb.get()}: {self.details.get('1.0', tk.END).strip()}"
        self.result = t
        self.destroy()


class BMHNetworkWindow(tk.Toplevel):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.parent = parent
        self.title('BMH Network')
        self.geometry('1000x700')
        ttk.Label(self, text='BMH Network Controls', font=('Segoe UI', 12, 'bold')).pack(anchor='nw', padx=8, pady=6)
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(container)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)

        ttk.Label(left, text='Global Network Controls').pack(anchor='nw')
        ttk.Button(left, text='Broadcast Action: Update Periodic Scroll').pack(fill=tk.X, pady=2)

        ttk.Label(left, text='Hazard:').pack(anchor='nw', pady=4)
        for h in ['Severe Thunderstorm Warning','Tornado Warning','Flash Flood Warning','Special Weather Statement','Extreme Wind Warning']:
            ttk.Button(left, text=h, command=lambda h=h: self.insert_hazard_to_text(h)).pack(fill=tk.X, pady=1)

        ttk.Label(left, text='Ticker Text:').pack(anchor='nw', pady=6)
        self.ticker_entry = ttk.Entry(left)
        self.ticker_entry.insert(0, 'Edit the BMH Network Ticker...')
        self.ticker_entry.pack(fill=tk.X)
        ttk.Button(left, text='TRANSMIT', command=self.transmit_ticker).pack(fill=tk.X, pady=6)

        ttk.Label(left, text='SAME Options').pack(anchor='nw', pady=4)
        same_frame = ttk.Frame(left)
        same_frame.pack(fill=tk.X)
        ttk.Button(same_frame, text='SAME RETONE', command=lambda: messagebox.showinfo('SAME','Retone (stub)')).pack(side=tk.LEFT, padx=2)
        ttk.Button(same_frame, text='1050 HZ', command=lambda: messagebox.showinfo('1050Hz','1050 Hz toggle (stub)')).pack(side=tk.LEFT, padx=2)
        ttk.Button(same_frame, text='SILENT INTERRUPT', command=lambda: messagebox.showinfo('Silent','Silent interrupt (stub)')).pack(side=tk.LEFT, padx=2)

        # Right - Station status / controls
        right = ttk.Frame(container)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=8, pady=8)
        ttk.Label(right, text=f"Station Controller - {config.get('station')}", font=('Segoe UI', 11, 'bold')).pack(anchor='nw')

        status_frame = ttk.Frame(right)
        status_frame.pack(fill=tk.X, pady=4)
        ttk.Label(status_frame, text=f"STATION: {config.get('station')} ONLINE").pack(side=tk.LEFT)
        ttk.Button(status_frame, text='Station ID', command=lambda: messagebox.showinfo('ID', config.get('station'))).pack(side=tk.RIGHT)

        # Transmission controls
        tx_frame = ttk.LabelFrame(right, text='Primary Broadcast Control')
        tx_frame.pack(fill=tk.X, pady=8)
        ttk.Button(tx_frame, text='START TX', command=self.parent.start_tx).pack(side=tk.LEFT, padx=4, pady=4)
        ttk.Button(tx_frame, text='STOP TX', command=self.parent.stop_tx).pack(side=tk.LEFT, padx=4, pady=4)
        ttk.Button(tx_frame, text='NEXT PRODUCT', command=lambda: messagebox.showinfo('Next','Next product (stub)')).pack(side=tk.LEFT, padx=4, pady=4)
        ttk.Button(tx_frame, text='RESTART SERVICE', command=lambda: messagebox.showinfo('Restart','Restart service (stub)')).pack(side=tk.LEFT, padx=4, pady=4)

        # Operational modes list
        modes_frame = ttk.LabelFrame(right, text='Operational Modes')
        modes_frame.pack(fill=tk.BOTH, expand=True, pady=8)
        modes = ['Winter Weather','Flooding','Severe Weather','Severe Weather Possible','Off the Air','Station ID Only','Current Time Only','General','Zone Forecast','Severe Weather and Alert Summary']
        self.mode_list = tk.Listbox(modes_frame, height=8)
        for m in modes:
            self.mode_list.insert(tk.END, m)
        self.mode_list.pack(fill=tk.BOTH, expand=True)
        mode_btns = ttk.Frame(modes_frame)
        mode_btns.pack(fill=tk.X, pady=4)
        ttk.Button(mode_btns, text='NEW MODE', command=lambda: messagebox.showinfo('Mode','New mode (stub)')).pack(side=tk.LEFT, padx=2)
        ttk.Button(mode_btns, text='DELETE MODE', command=lambda: messagebox.showinfo('Mode','Delete mode (stub)')).pack(side=tk.LEFT, padx=2)
        ttk.Button(mode_btns, text='RESET MODE', command=lambda: messagebox.showinfo('Mode','Reset mode (stub)')).pack(side=tk.LEFT, padx=2)

        # Static messages
        static_frame = ttk.LabelFrame(right, text='Static Messages')
        static_frame.pack(fill=tk.BOTH, expand=True, pady=8)
        static_ids = ['ADVANCE','EMR_STATION_ID','PREPAREDNESS_ACTIONS','SLGT_STATION_ID','OFF_AIR','STATION_ID','SHORT_ID','LONG_ID','SEVERE_MESSAGE','CURRENT_TIME']
        self.static_list = tk.Listbox(static_frame, height=6)
        for s in static_ids:
            self.static_list.insert(tk.END, s)
        self.static_list.pack(fill=tk.BOTH, expand=True)

        # Live Queue
        live_frame = ttk.LabelFrame(left, text='Live Queue / Player')
        live_frame.pack(fill=tk.X, pady=8)
        ttk.Label(live_frame, text='Current Playing:').pack(anchor='w')
        self.current_play = ttk.Combobox(live_frame, values=static_ids)
        self.current_play.set(static_ids[0])
        self.current_play.pack(fill=tk.X)
        self.queue_len_var = tk.IntVar(value=3)
        ttk.Label(live_frame, textvariable=self.queue_len_var).pack(anchor='w')
        qbtns = ttk.Frame(live_frame)
        qbtns.pack(fill=tk.X, pady=4)
        ttk.Button(qbtns, text='REFRESH NOW', command=lambda: messagebox.showinfo('Refresh','Refresh (stub)')).pack(side=tk.LEFT, padx=2)
        ttk.Button(qbtns, text='READ SELECTED NOW', command=lambda: self.parent.transmit_text(self.current_play.get())).pack(side=tk.LEFT, padx=2)
        ttk.Button(qbtns, text='LOOP SELECTED', command=lambda: messagebox.showinfo('Loop','Loop (stub)')).pack(side=tk.LEFT, padx=2)
        ttk.Button(qbtns, text='STOP LOOP', command=lambda: messagebox.showinfo('Stop','Stop (stub)')).pack(side=tk.LEFT, padx=2)

        # Active Alerts list
        alerts_frame = ttk.LabelFrame(right, text='Active Alerts')
        alerts_frame.pack(fill=tk.BOTH, expand=True, pady=8)
        self.alerts_list = tk.Listbox(alerts_frame, height=6)
        self.alerts_list.insert(tk.END, 'ID123|Severe Thunderstorm Warning|NEW|Expires: 2026-08-19 20:00')
        self.alerts_list.pack(fill=tk.BOTH, expand=True)
        alert_btns = ttk.Frame(alerts_frame)
        alert_btns.pack(fill=tk.X)
        ttk.Button(alert_btns, text='REFRESH LIST', command=lambda: messagebox.showinfo('Refresh','Refresh list (stub)')).pack(side=tk.LEFT, padx=2)
        ttk.Button(alert_btns, text='EDIT SELECTED', command=lambda: messagebox.showinfo('Edit','Edit (stub)')).pack(side=tk.LEFT, padx=2)
        ttk.Button(alert_btns, text='SAME RETONE', command=lambda: messagebox.showinfo('Same','Retone (stub)')).pack(side=tk.LEFT, padx=2)

    def insert_hazard_to_text(self, hazard):
        self.parent.text_widget.insert(tk.END, f"\n[{hazard}]\n")
        self.parent.status('Hazard inserted from BMH controls')

    def transmit_ticker(self):
        txt = self.ticker_entry.get().strip()
        if not txt:
            messagebox.showwarning('Transmit', 'Ticker is empty')
            return
        self.parent.transmit_text(txt)


class StationControllerWindow(tk.Toplevel):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.parent = parent
        self.title(f"BMH Station Controller - {config.get('station')}")
        self.geometry('600x400')
        ttk.Label(self, text=f"STATION: {config.get('station')} ONLINE", font=('Segoe UI', 11, 'bold')).pack(anchor='nw', padx=8, pady=6)
        ttk.Label(self, text=f"Location: {config.get('location')}").pack(anchor='nw', padx=8)
        ttk.Label(self, text=f"IP: {config.get('ip_address')}:{config.get('port')}").pack(anchor='nw', padx=8)
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(btn_frame, text='READ NOW', command=lambda: messagebox.showinfo('Read','Read now (stub)')).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text='LOOP PRODUCT', command=lambda: messagebox.showinfo('Loop','Loop (stub)')).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text='STOP LOOP', command=lambda: messagebox.showinfo('Stop','Stop (stub)')).pack(side=tk.LEFT, padx=4)

        # Manual product control
        prod_frame = ttk.LabelFrame(self, text='Manual Product Control')
        prod_frame.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(prod_frame, text='Product ID:').pack(anchor='w')
        self.prod_entry = ttk.Entry(prod_frame)
        self.prod_entry.pack(fill=tk.X)
        btns = ttk.Frame(prod_frame)
        btns.pack(fill=tk.X, pady=4)
        ttk.Button(btns, text='READ NOW', command=lambda: messagebox.showinfo('Read','Read now (stub)')).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text='LOOP PRODUCT', command=lambda: messagebox.showinfo('Loop','Loop (stub)')).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text='STOP LOOP', command=lambda: messagebox.showinfo('Stop','Stop (stub)')).pack(side=tk.LEFT, padx=2)


if __name__ == '__main__':
    cfg = load_config()
    app = TextWorkstationApp(cfg)
    app.mainloop()
