#!/usr/bin/env bash
set -xe

[ ! -f requirements.txt ] && echo "requirements.txt not found" && exit
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt

WS_PATH="$1"
[ -z "$WS_PATH" ] && read -p "Enter your Autoware workspace path: " WS_PATH
echo "[Unit]
Description=autoware_workspace_snapshot_tool
[Service]
WorkingDirectory=
ExecStart=$(pwd)/.venv/bin/python3 $(pwd)/main.py \"$WS_PATH\"
Restart=always
[Install]
WantedBy=default.target" > ~/.config/systemd/user/autoware_workspace_snapshot_tool.service
systemctl --user daemon-reload
systemctl --user enable --now autoware_workspace_snapshot_tool.service
