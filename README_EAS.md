# KLOT_BMH — Dry-run EAS & Live Voice Test Tools

Overview
- Small test tools for the KLOT_BMH Broadcast Message Handler (BMH) system:
  - `scripts/dry_run_bmh.py` — Tkinter test GUI: compose messages, generate WMO/AWIPS header, generate/send JSON payloads, build/play/send EAS WAVs (TTS or chosen WAV file).
  - `scripts/eas_voice_encoder.py` — CLI EAS WAV builder: 1050 Hz interrupt tone + SAME-like header read by TTS or append a provided WAV.
- These are intended for dry-run / lab testing only. They do NOT perform real SAME FSK encoding or RF transmission.

Prerequisites
- Python 3.10+ (3.11 recommended)
- Optional dependencies:
  - `pyttsx3` (offline TTS): `pip install pyttsx3`
  - `sounddevice` + `soundfile` (if you want to record in-GUI): `pip install sounddevice soundfile`
- On Windows, Tkinter is included with the official CPython installer. For audio playback:
  - Windows: `winsound` (standard)
  - macOS: `afplay` (built-in)
  - Linux: `aplay`, `paplay`, or `xdg-open` (install if missing)

Quick install
1. Clone repo and create venv:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1  # PowerShell
   # OR
   .\.venv\Scripts\activate      # CMD
   ```
2. Install optional TTS:
   ```bash
   pip install pyttsx3
   ```

Run the GUI (simulated listener started by default)
- Start the application:
  ```bash
  python scripts/dry_run_bmh.py
  ```
- GUI buttons:
  - Generate Header: inserts a minimal WMO/AWIPS-like header into message area.
  - Send (Dry-run): prints JSON payload to console.
  - Send (to listener): sends JSON payload to local simulated listener (default 127.0.0.1:5000).
  - Build EAS WAV (TTS): generate WAV with 1050Hz interrupt + SAME-like header read by TTS + message.
  - Choose WAV File: select a pre-recorded WAV to play or send.
  - Play WAV: play the currently selected/generated WAV.
  - Send WAV: send WAV bytes to the simulated BMH listener over TCP.

CLI examples for EAS WAV builder
- Generate a WAV using TTS:
  ```bash
  python scripts/eas_voice_encoder.py --message "Severe thunderstorm warning for your area." --event SVR --location ILZ001 --out ./eas_test.wav
  ```
- Generate a WAV using a pre-recorded WAV for voice (bypass TTS):
  ```bash
  python scripts/eas_voice_encoder.py --message "ignored" --voice-wav ./my_voice.wav --out ./eas_from_file.wav
  ```

End-to-end safe test workflow (lab)
1. Start the GUI (it will start a simulated listener on 127.0.0.1:5000 by default):
   ```bash
   python scripts/dry_run_bmh.py
   ```
2. In the GUI:
   - Edit or paste your test message into the New Text Message area.
   - Click Generate Header to add the WMO/AWIPS-like header.
   - To test text dispatch: click Send (Dry-run) to view JSON, or Send (to listener) to send to the local listener. Observe the console where the script was started — the listener prints received payloads.
3. Test Live Voice / EAS:
   - Build EAS WAV (TTS) (requires pyttsx3) — this creates a WAV in your temp directory starting with a 1050Hz attention tone.
   - Or Choose WAV File to select a prerecorded message (WAV).
   - Play WAV to preview locally.
   - Send WAV to the local simulated listener; the listener prints WAV bytes (or you can extend the listener to save the WAV to disk for inspection).
4. Validate:
   - Confirm the listener received the payload/WAV and that header fields, timestamps, and message text are correct.
   - For WAVs: play the output file directly with your OS player to check audio quality and TTS rendering.

Integration notes & suggestions
- The tools generate a readable SAME-like header for TTS and logging, but do not implement legal SAME formatting or RF encoding. Do not use for on-air broadcasts.
- Keep all real IPs, credentials, and production endpoints out of test configs. Use placeholder addresses in `Text_Workstation_Settings.json` or a `.env`.
- Add a dry-run mode flag to any real dispatch code — it should never send to production without explicit opt-in.

Security & compliance reminder
- Do not broadcast EAS tones, headers, or signals over the air without proper authorization — doing so is illegal in many jurisdictions. Use these tools in isolated lab environments only.
