#!/usr/bin/env bash
# IN-CSE(~/tinyIoT/source/server, 포트 3000, PostgreSQL)를 띄운다. MN은 시작할 때 IN에 등록하므로 IN이 먼저 떠 있어야 한다.
if ss -ltn "sport = :3000" | grep -q LISTEN; then echo "IN already running"; exit 0; fi
sudo -n service postgresql start >/dev/null 2>&1 || true
sudo -n service mosquitto start >/dev/null 2>&1 || true
cd ~/tinyIoT/source/server && setsid nohup ./server > /tmp/in.log 2>&1 < /dev/null &
sleep 3
ss -ltnp "sport = :3000" | tail -1
