print("Start the BMH Broadcast Cycle to BACKUP the WNG689 BMH Station in Hebron, or Valparaiso, IN, or Indiana.")

#!/usr/bin/env python3
"""
WNG689: Backup helper (create timestamped ZIPs, TTS announce, rotate old backups).

Usage:
  python scripts/wng689_backup.py [--out-dir backups] [--keep-days 30] [--max-files 60]

Config:
  If Text_Workstation_Settings.json exists and contains "backups" section,
  the script will read defaults from there.
"""
import argparse
import json
import os
import shutil
import socket
import sys
import zipfile
from datetime import datetime, timedelta
from glob import glob
from pathlib import Path

try:
    import pyttsx3
    _HAS_PYTTSX3 = True
except Exception:
    _HAS_PYTTSX3 = False

ROOT = Path.cwd()
CONFIG_FILE = ROOT / "Text_Workstation_Settings.json"

DEFAULTS = {
    "base": str(ROOT / "backups"),
    "retention_days": 30,
    "max_files": 120,
    "include": [
        "Text_Workstation_Settings.json",
        "scripts",
        "config.json",
        "awips_messages.json",
        "received"
    ]
}

def load_config():
    cfg = DEFAULTS.copy()
    if CONFIG_FILE.exists():
        try:
            j = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            b = j.get("backups", {})
            cfg.update({k: b.get(k, cfg[k]) for k in ["base", "retention_days", "max_files"] if k in b})
            if isinstance(b.get("include"), list):
                cfg["include"] = b["include"]
        except Exception:
            pass
    return cfg

def create_backup(out_dir: str, include: list[str], name_prefix="wng689_backup"):
    now = datetime.utcnow()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{name_prefix}_{now.strftime('%Y%m%d_%H%M%S')}.zip"
    path = out_dir / filename
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for entry in include:
            p = Path(entry)
            if not p.exists():
                continue
            if p.is_file():
                zf.write(p, arcname=p.name)
            else:
                for root, _, files in os.walk(p):
                    for f in files:
                        full = Path(root) / f
                        arc = full.relative_to(ROOT)
                        zf.write(full, arcname=str(arc))
    return str(path)

def rotate_backups(base: str, retention_days: int, max_files: int):
    base = Path(base)
    if not base.exists():
        return
    files = sorted(base.glob("*.zip"), key=lambda p: p.stat().st_mtime)
    # delete old by time
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    removed = 0
    for f in files:
        if datetime.utcfromtimestamp(f.stat().st_mtime) < cutoff:
            try:
                f.unlink()
                removed += 1
            except Exception:
                pass
    # trim to max_files
    files = sorted(base.glob("*.zip"), key=lambda p: p.stat().st_mtime)
    if len(files) > max_files:
        for f in files[: len(files) - max_files]:
            try:
                f.unlink()
            except Exception:
                pass
    return removed

def tts_announce(message: str, preferred_voice_substring: str | None = "Paul"):
    if not _HAS_PYTTSX3:
        print("[TTS] pyttsx3 not installed, skipping announce:", message)
        return
    try:
        engine = pyttsx3.init()
        if preferred_voice_substring:
            voices = engine.getProperty("voices") or []
            chosen = None
            for v in voices:
                if preferred_voice_substring.lower() in (v.name or "").lower() or preferred_voice_substring.lower() in (v.id or "").lower():
                    chosen = v
                    break
            if chosen:
                engine.setProperty("voice", chosen.id)
        engine.say(message)
        engine.runAndWait()
    except Exception as e:
        print("[TTS] announce failed:", e)

def main():
    cfg = load_config()
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=cfg["base"])
    parser.add_argument("--keep-days", type=int, default=int(cfg["retention_days"]))
    parser.add_argument("--max-files", type=int, default=int(cfg["max_files"]))
    parser.add_argument("--no-tts", action="store_true")
    args = parser.parse_args()

    try:
        path = create_backup(args.out_dir, cfg["include"])
        rotate_backups(args.out_dir, args.keep_days, args.max_files)
        msg = f"WNG six eight nine backup completed successfully. Backup saved as {os.path.basename(path)}"
        print(msg)
        if not args.no_tts:
            tts_announce(msg, preferred_voice_substring=(cfg.get("default_tts_voice_substring") or "Paul"))
    except Exception as e:
        err = f"Backup failed: {e}"
        print(err)
        if not args.no_tts:
            tts_announce(err, preferred_voice_substring=(cfg.get("default_tts_voice_substring") or "Paul"))
        sys.exit(1)

if __name__ == "__main__":
    main()