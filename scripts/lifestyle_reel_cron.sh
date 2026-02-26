#!/bin/bash
cd /root/openclaw
source .venv/bin/activate
source .env
python3 scripts/lifestyle_reel.py 2>&1
