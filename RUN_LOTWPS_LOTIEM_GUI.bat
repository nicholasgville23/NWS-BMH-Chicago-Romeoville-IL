@echo off
cd /d "%~dp0"
py -3 LOTWPS_LOTIEM_GUI.py
if errorlevel 1 python LOTWPS_LOTIEM_GUI.py
