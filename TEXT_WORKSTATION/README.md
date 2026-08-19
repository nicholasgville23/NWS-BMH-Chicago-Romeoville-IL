Updated README: added note about network transmit test

How to run the network-enabled GUI:
1. Ensure config.json contains the correct ip_address and port for testing (default 192.168.10.144:6000).
2. Open a terminal in TEXT_WORKSTATION/
3. Run: python text_workstation_main.py

Test transmit flow:
- Open BMH Network window, click START TX to connect (non-blocking)
- Enter or paste text in the main editor or ticker box
- Press TRANSMIT in the BMH Network window or use the Station Controller's controls to READ/LOOP

Notes:
- This implementation uses a simple TCP client (socket). It is intended for lab testing only. The message payload is sent as UTF-8 with a trailing delimiter <END_OF_MESSAGE>.
- When connecting to real broadcast devices, add authentication and secure network controls.
