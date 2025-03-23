#!/usr/bin/env bash
set -xe

# https://stackoverflow.com/questions/59895/how-do-i-get-the-directory-where-a-bash-script-is-located-from-within-the-script/246128#comment9536277_246128
DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

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
