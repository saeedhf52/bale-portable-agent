@echo off
chcp 65001 > nul
title Bale Portable AI Agent
echo Starting Bale Portable AI Agent...
python agent_launcher.py %*
pause
