#!/bin/bash
# Start the COI automation loop in the background (survives terminal close).
# Usage: ./start.sh          — start
#        ./start.sh stop     — stop
#        ./start.sh status   — check if running
#        ./start.sh logs     — tail today's log

cd "$(dirname "$0")"
PIDFILE="state/coi.pid"

case "${1:-start}" in
  start)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "Already running (PID $(cat "$PIDFILE"))"
      exit 0
    fi
    mkdir -p state logs
    nohup .venv/bin/python main.py >> logs/stdout.log 2>&1 &
    echo $! > "$PIDFILE"
    echo "Started (PID $!)"
    ;;
  stop)
    if [ -f "$PIDFILE" ]; then
      kill "$(cat "$PIDFILE")" 2>/dev/null && echo "Stopped" || echo "Was not running"
      rm -f "$PIDFILE"
    else
      echo "No PID file — not running?"
    fi
    ;;
  status)
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
      echo "Running (PID $(cat "$PIDFILE"))"
    else
      echo "Not running"
    fi
    ;;
  logs)
    tail -f "logs/coi-$(date +%Y-%m-%d).jsonl"
    ;;
  *)
    echo "Usage: ./start.sh [start|stop|status|logs]"
    ;;
esac
