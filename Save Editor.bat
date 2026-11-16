@echo off
rem Opens the save editor with the Python beside this folder (..python).
start "" "%~dp0..\python\pythonw.exe" "%~dp0save_editor.pyw"
