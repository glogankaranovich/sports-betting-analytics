#!/bin/bash
# Check if source files changed more recently than their summary files.
# Run manually or via pre-commit hook.

SUMMARY_DIR=".agents/summary"
STALE=()

check() {
  local summary="$1" ; shift
  [ ! -f "$SUMMARY_DIR/$summary" ] && { STALE+=("$summary (missing)"); return; }
  local summary_ts=$(stat -f %m "$SUMMARY_DIR/$summary" 2>/dev/null || stat -c %Y "$SUMMARY_DIR/$summary" 2>/dev/null)
  for src in "$@"; do
    for f in $(find "$src" -name "*.py" -o -name "*.ts" 2>/dev/null | head -50); do
      local src_ts=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null)
      if [ "$src_ts" -gt "$summary_ts" ]; then
        STALE+=("$summary (changed: $f)")
        return
      fi
    done
  done
}

check "benny-trader.md" "backend/benny_trader.py"
check "benny-models.md" "backend/benny/models/"
check "benny-engines.md" "backend/benny/"
check "data-collectors.md" "backend/odds_collector.py" "backend/outcome_collector.py" "backend/player_stats_collector.py" "backend/team_stats_collector.py"
check "backend-services.md" "backend/coaching_memo_generator.py" "backend/notification_service.py" "backend/analysis_generator.py"
check "infrastructure.md" "infrastructure/lib/" "infrastructure/bin/"
check "frontend.md" "frontend/src/"

if [ ${#STALE[@]} -gt 0 ]; then
  echo "⚠️  Stale summary files detected:"
  for s in "${STALE[@]}"; do echo "  - $s"; done
  echo ""
  echo "Update summaries in $SUMMARY_DIR/ and $SUMMARY_DIR/INDEX.md"
  exit 1
else
  echo "✓ All summaries up to date"
  exit 0
fi
