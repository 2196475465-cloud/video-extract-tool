#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/server"
echo "正在启动去水印后端..."
exec python3 -u app.py
