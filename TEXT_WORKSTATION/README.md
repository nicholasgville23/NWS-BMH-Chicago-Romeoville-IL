Updated KLOT LOTIEM TEXT WORKSTATION GUI skeleton

Files updated:
- TEXT_WORKSTATION/config.json  (station changed to WXK89, added listening-area and sane_builder entries)
- TEXT_WORKSTATION/text_workstation_main.py  (enhanced: SAME/EAS builder stub, listening area options, SAME retone/1050Hz buttons, broadcast modes UI, static messages list, live queue controls, SEND SANE ALERT)
- TEXT_WORKSTATION/web/index.html  (default message updated)

How to run:
1. Open a terminal in the TEXT_WORKSTATION directory.
2. Run: python text_workstation_main.py

Notes:
- This keeps actions as stubs where external systems are required. It provides a more complete GUI surface matching the requested controls.
- Next steps: wire SAME/EAS send to actual encoder, integrate START/STOP TX with station services, and implement product cycles persistence.
