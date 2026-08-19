KLOT LOTIEM TEXT WORKSTATION GUI skeleton

Files added:
- TEXT_WORKSTATION/config.json  (contains IP, port, station info)
- TEXT_WORKSTATION/text_workstation_main.py  (Tkinter main app)
- TEXT_WORKSTATION/web/index.html  (small web preview)
- TEXT_WORKSTATION/web/app.js

How to run:
1. Open a terminal in the TEXT_WORKSTATION directory.
2. Run: python text_workstation_main.py

Notes:
- This is a functional skeleton with many stubbed actions (dialogs and inserts). It implements the requested structure: AWIPS header, WarnGen/WatchGen dialogs, polygon tool, context menu for segments, and a BMH Network window with station controller.
- Next steps: wire up backend networking, AWIPS header generation formats, WarnGen/WatchGen logic for UGC/ZONE/FIPS, transmission control, and integration with existing BMH services.
