#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Active Alerts Dashboard

A tkinter-based graphical dashboard for monitoring active NWS weather alerts
in real-time. Provides:

- Real-time NWS alerts polling with auto-refresh
- Filter by zone, event type, severity
- Severity color-coding and sorting
- Alert detail view with full description
- Integration with the BMH EAS ENDEC module

Utilizes the NWS API (api.weather.gov) for alert data.
"""

import os
import sys
import json
import time
import threading
import logging
import traceback
import requests
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
from enum import Enum

import tkinter as tk
from tkinter import ttk, messagebox, Text, scrolledtext
from tkinter import font as tkfont

log = logging.getLogger("BMH")

# =============================================================================
# Constants
# =============================================================================

# Color scheme
DASHBOARD_COLORS = {
    "bg_dark": "#1a1a2e",
    "bg_medium": "#16213e",
    "bg_light": "#0f3460",
    "accent": "#e94560",
    "success": "#2ecc71",
    "warning": "#f39c12",
    "danger": "#e74c3c",
    "info": "#3498db",
    "text_primary": "#ffffff",
    "text_secondary": "#a0a0b0",
    "text_accent": "#e94560",
    "border": "#2a2a4a",
}

# Severity colors for the dashboard
SEVERITY_COLORS = {
    "extreme": "#e74c3c",    # Red
    "severe": "#e67e22",     # Orange
    "moderate": "#f39c12",   # Yellow
    "minor": "#3498db",      # Blue
    "unknown": "#95a5a6",    # Gray
}

# Urgency colors
URGENCY_COLORS = {
    "immediate": "#e74c3c",
    "expected": "#e67e22",
    "future": "#f39c12",
    "past": "#95a5a6",
    "unknown": "#95a5a6",
}

# Severity sort order (highest first)
SEVERITY_ORDER = {
    "extreme": 0,
    "severe": 1,
    "moderate": 2,
    "minor": 3,
    "unknown": 4,
}


# =============================================================================
# Alert Data Model
# =============================================================================

class AlertData:
    """Represents a single NWS weather alert with display formatting."""
    
    def __init__(self, feature: dict):
        props = feature.get('properties', {})
        self.id = feature.get('id', '')
        self.event = props.get('event', 'Unknown')
        self.headline = props.get('headline', '')
        self.severity = (props.get('severity', 'unknown') or 'unknown').lower()
        self.urgency = (props.get('urgency', 'unknown') or 'unknown').lower()
        self.certainty = (props.get('certainty', 'unknown') or 'unknown').lower()
        self.area_desc = props.get('areaDesc', '')
        self.issued = props.get('issued', '')
        self.expires = props.get('expires', '')
        self.description = props.get('description', '')
        self.instruction = props.get('instruction', '')
        self.event_code = self._extract_event_code(props)
        
        # Parse times
        self.issued_dt = self._parse_time(self.issued)
        self.expires_dt = self._parse_time(self.expires)
    
    def _extract_event_code(self, props: dict) -> str:
        """Extract the 3-letter SAME event code."""
        try:
            awips = props.get('parameters', {}).get('AWIPSidentifier', [])
            if awips:
                return awips[0][:3]
        except Exception:
            pass
        return ''
    
    def _parse_time(self, time_str: str) -> Optional[datetime]:
        """Parse ISO 8601 time string."""
        try:
            if time_str:
                return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        except Exception:
            pass
        return None
    
    @property
    def severity_color(self) -> str:
        return SEVERITY_COLORS.get(self.severity, SEVERITY_COLORS['unknown'])
    
    @property
    def urgency_color(self) -> str:
        return URGENCY_COLORS.get(self.urgency, URGENCY_COLORS['unknown'])
    
    @property
    def severity_score(self) -> int:
        return SEVERITY_ORDER.get(self.severity, 4)
    
    @property
    def is_active(self) -> bool:
        """Check if alert is still active."""
        if self.expires_dt:
            return datetime.now().astimezone() < self.expires_dt
        return True
    
    @property
    def time_remaining(self) -> str:
        """Get human-readable time remaining."""
        if not self.expires_dt:
            return "Unknown"
        remaining = self.expires_dt - datetime.now().astimezone()
        if remaining.total_seconds() <= 0:
            return "Expired"
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    
    def to_summary(self) -> str:
        """Get a one-line summary of this alert."""
        return f"[{self.severity.upper():7}] {self.event} | {self.area_desc[:50]}... | Expires: {self.time_remaining}"
    
    def to_detail(self) -> str:
        """Get full detail text for this alert."""
        return (
            f"{'='*60}\n"
            f"EVENT: {self.event}\n"
            f"SEVERITY: {self.severity.upper()}\n"
            f"URGENCY: {self.urgency.upper()}\n"
            f"CERTAINTY: {self.certainty.upper()}\n"
            f"AREA: {self.area_desc}\n"
            f"ISSUED: {self.issued}\n"
            f"EXPIRES: {self.expires}\n"
            f"{'='*60}\n\n"
            f"DESCRIPTION:\n{self.description}\n"
            + (f"\nINSTRUCTIONS:\n{self.instruction}\n" if self.instruction else "")
        )


# =============================================================================
# Alert Fetcher (Background Thread)
# =============================================================================

class AlertFetcher:
    """
    Background alert fetcher that polls the NWS API for active alerts.
    Runs in its own thread to avoid blocking the UI.
    """
    
    def __init__(self, zones: Optional[List[str]] = None):
        self.zones = zones or []
        self._alerts: List[AlertData] = []
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._callback = None
        self._refresh_interval = 180  # 3 minutes
        self._load_config()
    
    def _load_config(self):
        """Load configuration from config.json."""
        try:
            config = json.load(open('config.json', encoding='utf-8'))
            if not self.zones:
                self.zones = config.get('AlertSummary', {}).get('alertZones', [])
                if not self.zones:
                    self.zones = config.get('EAS_ENDEC', {}).get('alertZones', [])
            self._refresh_interval = max(30, int(config.get('globalHTTPTimeout', 15)) * 2)
        except Exception:
            pass
    
    def set_callback(self, callback):
        """Set the callback function for alert updates."""
        self._callback = callback
    
    def start(self):
        """Start the background fetcher thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._fetch_loop, daemon=True)
        self._thread.start()
        log.info("[AlertDashboard] Alert fetcher started.")
    
    def stop(self):
        """Stop the background fetcher."""
        self._running = False
        log.info("[AlertDashboard] Alert fetcher stopped.")
    
    def _fetch_loop(self):
        """Main fetch loop running in background thread."""
        while self._running:
            try:
                alerts = self._fetch_alerts()
                with self._lock:
                    self._alerts = alerts
                
                if self._callback:
                    self._callback(alerts)
                
            except Exception as e:
                log.error("[AlertDashboard] Fetch error: %s", traceback.format_exc())
            
            # Sleep for the refresh interval
            for _ in range(self._refresh_interval):
                if not self._running:
                    break
                time.sleep(1)
    
    def _fetch_alerts(self) -> List[AlertData]:
        """Fetch alerts from NWS API for configured zones."""
        alerts = []
        seen_ids = set()
        
        try:
            headers = {"User-Agent": "Weather Radio Suite/1.0"}
            timeout = int(json.load(open('config.json', encoding='utf-8')).get('globalHTTPTimeout', 15))
            
            for zone in self.zones:
                try:
                    url = f"https://api.weather.gov/alerts/active/zone/{zone}"
                    response = requests.get(url, timeout=timeout, headers=headers)
                    data = response.json()
                    
                    for feature in data.get('features', []):
                        alert_id = feature.get('id', '')
                        if alert_id not in seen_ids:
                            seen_ids.add(alert_id)
                            alerts.append(AlertData(feature))
                            
                except Exception as zone_err:
                    log.debug("[AlertDashboard] Error fetching zone %s: %s", zone, zone_err)
                    continue
            
            # Sort by severity (most severe first)
            alerts.sort(key=lambda a: (a.severity_score, a.expires_dt or datetime.max))
            
        except Exception as e:
            log.error("[AlertDashboard] Fetch error: %s", traceback.format_exc())
        
        return alerts
    
    def get_alerts(self) -> List[AlertData]:
        """Get the latest fetched alerts."""
        with self._lock:
            return self._alerts.copy()
    
    def get_alert_count_by_severity(self) -> Dict[str, int]:
        """Get alert counts grouped by severity."""
        counts = {"extreme": 0, "severe": 0, "moderate": 0, "minor": 0, "unknown": 0}
        for alert in self.get_alerts():
            severity = alert.severity if alert.severity in counts else "unknown"
            counts[severity] += 1
        return counts


# =============================================================================
# Active Alerts Dashboard GUI
# =============================================================================

class ActiveAlertsDashboard:
    """
    Tkinter-based dashboard for active weather alerts.
    Provides real-time monitoring with filtering and detail views.
    """
    
    def __init__(self, parent: Optional[tk.Tk] = None):
        self.parent = parent
        self.window: Optional[tk.Toplevel] = None
        self.fetcher: Optional[AlertFetcher] = None
        self._setup_done = False
        
        # Filter state
        self._severity_filter = "All"
        self._search_text = ""
    
    def open(self):
        """Open the dashboard window."""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return
        
        self.window = tk.Toplevel(self.parent) if self.parent else tk.Tk()
        self.window.title("Active Alerts Dashboard - NWS Weather Radio Suite")
        self.window.configure(bg=DASHBOARD_COLORS["bg_dark"])
        
        # Window size
        win_width = 1000
        win_height = 700
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        center_x = int(screen_width / 2 - win_width / 2)
        center_y = int(screen_height / 2 - win_height / 2)
        self.window.geometry(f"{win_width}x{win_height}+{center_x}+{center_y}")
        self.window.minsize(800, 600)
        
        # Configure grid
        self.window.grid_rowconfigure(2, weight=1)
        self.window.grid_columnconfigure(0, weight=1)
        
        self._build_ui()
        
        # Start alert fetcher
        self.fetcher = AlertFetcher()
        self.fetcher.set_callback(self._on_alerts_updated)
        self.fetcher.start()
        
        if not self.parent:
            self.window.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        self._setup_done = True
    
    def _build_ui(self):
        """Build the dashboard UI."""
        # Top Bar: Title and summary
        self._build_top_bar()
        
        # Separator
        sep = tk.Frame(self.window, bg=DASHBOARD_COLORS["border"], height=2)
        sep.grid(row=1, column=0, sticky="ew", padx=10)
        
        # Main content: Alert list + detail
        self._build_main_content()
        
        # Bottom: Status bar
        self._build_status_bar()
    
    def _build_top_bar(self):
        """Build the top bar with title and summary stats."""
        top_frame = tk.Frame(self.window, bg=DASHBOARD_COLORS["bg_dark"])
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        top_frame.grid_columnconfigure(1, weight=1)
        
        # Title
        title = tk.Label(
            top_frame,
            text="ACTIVE ALERTS DASHBOARD",
            fg=DASHBOARD_COLORS["text_accent"],
            bg=DASHBOARD_COLORS["bg_dark"],
            font=("Arial", 16, "bold"),
        )
        title.grid(row=0, column=0, sticky="w")
        
        # Severity counts
        counts_frame = tk.Frame(top_frame, bg=DASHBOARD_COLORS["bg_dark"])
        counts_frame.grid(row=0, column=1, sticky="e")
        
        self._count_labels = {}
        for i, (sev, color) in enumerate([
            ("extreme", SEVERITY_COLORS["extreme"]),
            ("severe", SEVERITY_COLORS["severe"]),
            ("moderate", SEVERITY_COLORS["moderate"]),
            ("minor", SEVERITY_COLORS["minor"]),
        ]):
            lbl = tk.Label(
                counts_frame,
                text=f" {sev.capitalize()}: 0 ",
                fg=color,
                bg=DASHBOARD_COLORS["bg_dark"],
                font=("Arial", 9, "bold"),
            )
            lbl.grid(row=0, column=i, padx=(2, 2))
            self._count_labels[sev] = lbl
    
    def _build_main_content(self):
        """Build the main content area with alert list and detail."""
        main_frame = tk.Frame(self.window, bg=DASHBOARD_COLORS["bg_dark"])
        main_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(5, 10))
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=2)
        main_frame.grid_rowconfigure(1, weight=1)
        
        # Filter bar
        filter_frame = tk.Frame(main_frame, bg=DASHBOARD_COLORS["bg_medium"])
        filter_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        
        # Severity filter
        tk.Label(
            filter_frame,
            text="Severity:",
            fg=DASHBOARD_COLORS["text_secondary"],
            bg=DASHBOARD_COLORS["bg_medium"],
            font=("Arial", 9),
        ).pack(side="left", padx=(10, 5), pady=5)
        
        self._severity_var = tk.StringVar(value="All")
        severity_combo = ttk.Combobox(
            filter_frame,
            textvariable=self._severity_var,
            values=["All", "Extreme", "Severe", "Moderate", "Minor"],
            width=12,
            state="readonly",
        )
        severity_combo.pack(side="left", padx=5, pady=5)
        severity_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())
        
        # Search entry
        tk.Label(
            filter_frame,
            text="Search:",
            fg=DASHBOARD_COLORS["text_secondary"],
            bg=DASHBOARD_COLORS["bg_medium"],
            font=("Arial", 9),
        ).pack(side="left", padx=(15, 5), pady=5)
        
        self._search_var = tk.StringVar()
        search_entry = tk.Entry(
            filter_frame,
            textvariable=self._search_var,
            bg=DASHBOARD_COLORS["bg_dark"],
            fg=DASHBOARD_COLORS["text_primary"],
            insertbackground=DASHBOARD_COLORS["text_primary"],
            width=25,
            relief="flat",
        )
        search_entry.pack(side="left", padx=5, pady=5, fill="x", expand=True)
        search_entry.bind("<KeyRelease>", lambda e: self._apply_filters())
        
        # Refresh button
        refresh_btn = tk.Button(
            filter_frame,
            text="⟳ Refresh",
            command=self._manual_refresh,
            bg=DASHBOARD_COLORS["bg_light"],
            fg=DASHBOARD_COLORS["text_primary"],
            relief="flat",
            padx=10,
            cursor="hand2",
        )
        refresh_btn.pack(side="right", padx=10, pady=5)
        
        # Alert List (left panel)
        list_frame = tk.Frame(main_frame, bg=DASHBOARD_COLORS["bg_medium"])
        list_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        list_frame.grid_rowconfigure(1, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        list_title = tk.Label(
            list_frame,
            text="Active Alerts",
            fg=DASHBOARD_COLORS["text_accent"],
            bg=DASHBOARD_COLORS["bg_medium"],
            font=("Arial", 10, "bold"),
        )
        list_title.grid(row=0, column=0, sticky="w", padx=5, pady=(5, 2))
        
        # Alert count
        self._list_count_label = tk.Label(
            list_frame,
            text="0 alerts",
            fg=DASHBOARD_COLORS["text_secondary"],
            bg=DASHBOARD_COLORS["bg_medium"],
            font=("Arial", 8),
        )
        self._list_count_label.grid(row=0, column=0, sticky="e", padx=5, pady=(5, 2))
        
        # Listbox with scrollbar
        list_container = tk.Frame(list_frame, bg=DASHBOARD_COLORS["bg_medium"])
        list_container.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))
        list_container.grid_rowconfigure(0, weight=1)
        list_container.grid_columnconfigure(0, weight=1)
        
        self._alert_listbox = tk.Listbox(
            list_container,
            bg=DASHBOARD_COLORS["bg_dark"],
            fg=DASHBOARD_COLORS["text_primary"],
            selectbackground=DASHBOARD_COLORS["bg_light"],
            selectforeground=DASHBOARD_COLORS["text_primary"],
            font=("Courier New", 9),
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        self._alert_listbox.grid(row=0, column=0, sticky="nsew")
        self._alert_listbox.bind("<<ListboxSelect>>", self._on_alert_select)
        
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self._alert_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._alert_listbox.configure(yscrollcommand=scrollbar.set)
        
        # Detail Panel (right panel)
        detail_frame = tk.Frame(main_frame, bg=DASHBOARD_COLORS["bg_medium"])
        detail_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        detail_frame.grid_rowconfigure(0, weight=1)
        detail_frame.grid_columnconfigure(0, weight=1)
        
        detail_title = tk.Label(
            detail_frame,
            text="Alert Details",
            fg=DASHBOARD_COLORS["text_accent"],
            bg=DASHBOARD_COLORS["bg_medium"],
            font=("Arial", 10, "bold"),
        )
        detail_title.grid(row=0, column=0, sticky="nw", padx=5, pady=(5, 2))
        
        self._detail_text = scrolledtext.ScrolledText(
            detail_frame,
            bg=DASHBOARD_COLORS["bg_dark"],
            fg=DASHBOARD_COLORS["text_primary"],
            font=("Consolas", 9),
            wrap="word",
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=10,
            pady=10,
        )
        self._detail_text.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))
        self._detail_text.insert("1.0", "Select an alert from the list to view details...")
        self._detail_text.config(state="disabled")
        
        # Action buttons for selected alert
        action_frame = tk.Frame(detail_frame, bg=DASHBOARD_COLORS["bg_medium"])
        action_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=(0, 5))
        
        self._broadcast_btn = tk.Button(
            action_frame,
            text="📻 Broadcast via EAS",
            command=self._broadcast_alert,
            bg=DASHBOARD_COLORS["accent"],
            fg=DASHBOARD_COLORS["text_primary"],
            relief="flat",
            padx=10,
            cursor="hand2",
            state="disabled",
        )
        self._broadcast_btn.pack(side="left", padx=5)
        
        self._view_nws_btn = tk.Button(
            action_frame,
            text="🌐 View on weather.gov",
            command=self._view_on_nws,
            bg=DASHBOARD_COLORS["bg_light"],
            fg=DASHBOARD_COLORS["text_primary"],
            relief="flat",
            padx=10,
            cursor="hand2",
            state="disabled",
        )
        self._view_nws_btn.pack(side="left", padx=5)
    
    def _build_status_bar(self):
        """Build the bottom status bar."""
        status_frame = tk.Frame(self.window, bg=DASHBOARD_COLORS["bg_dark"])
        status_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 5))
        status_frame.grid_columnconfigure(0, weight=1)
        
        self._status_label = tk.Label(
            status_frame,
            text="Initializing...",
            fg=DASHBOARD_COLORS["text_secondary"],
            bg=DASHBOARD_COLORS["bg_dark"],
            font=("Arial", 8),
            anchor="w",
        )
        self._status_label.grid(row=0, column=0, sticky="w")
        
        self._refresh_label = tk.Label(
            status_frame,
            text="",
            fg=DASHBOARD_COLORS["text_secondary"],
            bg=DASHBOARD_COLORS["bg_dark"],
            font=("Arial", 8),
            anchor="e",
        )
        self._refresh_label.grid(row=0, column=1, sticky="e")
    
    def _on_alerts_updated(self, alerts: List[AlertData]):
        """Called when alerts are updated from the background fetcher."""
        if not self._setup_done:
            return
        
        try:
            # Update counts
            counts = self.fetcher.get_alert_count_by_severity() if self.fetcher else {}
            if hasattr(self, '_count_labels'):
                for sev, count in counts.items():
                    if sev in self._count_labels:
                        color = SEVERITY_COLORS.get(sev, "#95a5a6")
                        self._count_labels[sev].config(
                            text=f" {sev.capitalize()}: {count} ",
                        )
            
            # Update list
            self._update_alert_list(alerts)
            
            # Update status
            total = len(alerts)
            self._status_label.config(
                text=f"Last updated: {datetime.now().strftime('%I:%M:%S %p')} | "
                     f"{total} active alert(s) | Auto-refresh every {self.fetcher._refresh_interval}s"
            )
            
        except Exception as e:
            log.debug("[AlertDashboard] UI update error: %s", e)
    
    def _update_alert_list(self, alerts: List[AlertData]):
        """Update the alert listbox with filtered alerts."""
        # Apply filters
        filtered = self._apply_filters_to_alerts(alerts)
        
        # Clear and repopulate
        self._alert_listbox.delete(0, "end")
        
        for alert in filtered:
            display_text = f"[{alert.severity.upper():7}] {alert.event[:25]:25s} | {alert.time_remaining:8s} | {alert.area_desc[:30]}"
            self._alert_listbox.insert("end", display_text)
            
            # Color the item based on severity
            severity = alert.severity
            color = SEVERITY_COLORS.get(severity, "#ffffff")
            last_idx = self._alert_listbox.size() - 1
            self._alert_listbox.itemconfig(last_idx, fg=color)
        
        # Update count label
        if hasattr(self, '_list_count_label'):
            self._list_count_label.config(text=f"{len(filtered)} alert(s)")
    
    def _apply_filters_to_alerts(self, alerts: List[AlertData]) -> List[AlertData]:
        """Apply severity and search filters to alerts."""
        filtered = alerts
        
        # Severity filter
        severity = self._severity_var.get().lower() if hasattr(self, '_severity_var') else "all"
        if severity != "all":
            filtered = [a for a in filtered if a.severity == severity]
        
        # Search filter
        search = self._search_var.get().lower() if hasattr(self, '_search_var') else ""
        if search:
            filtered = [
                a for a in filtered
                if search in a.event.lower()
                or search in a.area_desc.lower()
                or search in a.description.lower()
            ]
        
        return filtered
    
    def _apply_filters(self):
        """Apply current filter settings."""
        if self.fetcher:
            alerts = self.fetcher.get_alerts()
            self._update_alert_list(alerts)
    
    def _manual_refresh(self):
        """Manually trigger a refresh."""
        self._status_label.config(text="Manual refresh requested...")
        if self.fetcher:
            # Clear cache and fetch
            threading.Thread(target=self._do_refresh, daemon=True).start()
    
    def _do_refresh(self):
        """Perform the actual refresh in a background thread."""
        try:
            # Force the fetcher to get new data by clearing its internal state
            if self.fetcher:
                # Temporarily set last fetch to old time to force refresh
                alerts = self.fetcher._fetch_alerts()
                self._on_alerts_updated(alerts)
        except Exception as e:
            log.error("[AlertDashboard] Refresh error: %s", e)
    
    def _on_alert_select(self, event):
        """Handle alert selection in the listbox."""
        selection = self._alert_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        alerts = self.fetcher.get_alerts() if self.fetcher else []
        filtered = self._apply_filters_to_alerts(alerts)
        
        if 0 <= index < len(filtered):
            alert = filtered[index]
            self._show_alert_detail(alert)
    
    def _show_alert_detail(self, alert: AlertData):
        """Show the detail of a selected alert."""
        self._detail_text.config(state="normal")
        self._detail_text.delete("1.0", "end")
        
        # Insert with colors
        self._detail_text.insert("end", alert.to_detail())
        
        # Color the severity header
        severity_tag = f"severity_{alert.severity}"
        self._detail_text.tag_config(severity_tag, foreground=alert.severity_color)
        
        self._detail_text.config(state="disabled")
        
        # Enable action buttons
        self._broadcast_btn.config(state="normal")
        self._view_nws_btn.config(state="normal")
        self._selected_alert = alert
    
    def _broadcast_alert(self):
        """Broadcast the selected alert via EAS/BHM."""
        if not hasattr(self, '_selected_alert') or not self._selected_alert:
            return
        
        alert = self._selected_alert
        messagebox.showinfo(
            "Broadcast Alert",
            f"Broadcasting: {alert.event}\n\n"
            f"This would trigger an EAS/EOM broadcast through BMH\n"
            f"for the selected alert.\n\n"
            f"Area: {alert.area_desc}\n"
            f"Expires: {alert.expires}",
        )
    
    def _view_on_nws(self):
        """Open the NWS alert page in a web browser."""
        if not hasattr(self, '_selected_alert') or not self._selected_alert:
            return
        
        import webbrowser
        alert = self._selected_alert
        if alert.id:
            webbrowser.open(alert.id)
    
    def _on_closing(self):
        """Clean up on window close."""
        if self.fetcher:
            self.fetcher.stop()
        if self.window:
            self.window.destroy()


# =============================================================================
# Standalone Entry Point
# =============================================================================

def main():
    """Run the dashboard as a standalone application."""
    root = tk.Tk()
    dashboard = ActiveAlertsDashboard(root)
    dashboard.open()
    root.mainloop()


if __name__ == '__main__':
    main()

