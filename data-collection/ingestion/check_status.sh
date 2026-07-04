#!/bin/bash
# Quick status check for the mgnrega_employment.py backfill — the only ingestion job
# still running as of 2026-07-04 (gee_pull and rainfall_datagovin have both stopped;
# see docs/progress.md for their final counts).
# Run from anywhere: bash data-collection/ingestion/check_status.sh

MGNREGA_LOG="/tmp/mgnrega_run.log"
MGNREGA_CHECKPOINT="/c/Users/naazi/Downloads/Learn/Google/Cohort 2/Climate Resilience India/data-collection/raw_cache/mgnrega_checkpoint.json"

echo "=== Running python.exe processes ==="
powershell -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object {\$_.CommandLine -like '*mgnrega*'} | Select-Object ProcessId,CreationDate,CommandLine"

echo
echo "=== mgnrega_employment.py ==="
if [ -f "$MGNREGA_CHECKPOINT" ]; then
  python -c "
import json, sys
d = json.load(open(sys.argv[1]))
print(f'{len(d)} / 108 combos complete')
" "$MGNREGA_CHECKPOINT"
fi
echo "-- last 8 log lines --"
tail -8 "$MGNREGA_LOG" 2>/dev/null
