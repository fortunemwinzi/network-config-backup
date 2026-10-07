#!/bin/bash
source "$HOME/.monitor_env" || exit 1
cd "$HOME/network-config-backup" || exit 1
"$HOME/network-config-backup/venv/bin/python" backup.py >> backups/cron.log 2>&1
