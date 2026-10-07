# Network Config Backup and Change Detector

A Python tool that backs up network device configurations, saves a new
version only when something changes, logs a line-by-line diff and sends
a Telegram alert. Built to catch unplanned or unauthorised configuration
changes before they cause outages.

## Features
- Pulls configs from a file (lab mode) or over SSH (Cisco IOS, via Netmiko)
- Timestamped backups stored per device, only when the config changes
- Unified diff of every change saved to `backups/changes.log`
- Ignores volatile lines (for example "Current configuration : N bytes")
  so they never trigger false alerts
- Telegram alert with device name and number of lines changed
- One failing device does not stop the rest of the run

## Tools
Python 3.8, Netmiko, difflib, Telegram Bot API, Linux, Git

## How to run
git clone https://github.com/fortunemwinzi/network-config-backup.git
cd network-config-backup
python3 -m venv venv && source venv/bin/activate
pip install netmiko
python3 backup.py

## Configure devices
Edit `devices.json`:
{"name": "lab-router-1", "source_file": "sample_configs/lab-router-1.cfg"}

## Security
- `backups/` is git-ignored because real configs contain secrets
- Credentials come from environment variables, never from the code
- Alerts never include config text

## Sample output
<img width="334" height="94" alt="Terminal output" src="https://github.com/user-attachments/assets/ea3f82a6-856d-4674-8bf9-b8ef3c03486d" />

<img width="362" height="110" alt="backup changes log" src="https://github.com/user-attachments/assets/cfde9406-497a-4aaa-8d16-5e16e3e8db73" />

## Example diff
(paste the lines from backups/changes.log here)

## What I learned
- I learned that module builds a diff file by running a pattern-matching algorithm to find similarities between two sequences, tracking where they diverge, and formatting those discrepancies into standard text outputs.
- I learned that volatile lines caused false changes because of how the underlying SequenceMatcher algorithm anchoring system works.
- I learned that config backups must be kept out of GIT because they  introduce severe security, performance, and operational risks.

## Roadmap
- [x] Offline lab mode with change detection and diff log
- [x] Telegram alerts
- [ ] SSH backup from a live Cisco device
- [X] Scheduled runs with cron
- [ ] HTML change report
