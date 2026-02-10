#!/bin/bash
# Run historical data backfill in parallel across dev, beta, and prod

# Check if API key is provided
if [ -z "$1" ]; then
    echo "Usage: ./run_backfill.sh YOUR_ODDS_API_KEY [YEARS]"
    echo "  YEARS defaults to 0.25 (3 months) if not specified"
    exit 1
fi

API_KEY=$1
YEARS=${2:-0.25}  # Default to 3 months (0.25 years)
SESSION_NAME="backfill-historical"

# Kill existing session if it exists
tmux kill-session -t $SESSION_NAME 2>/dev/null

# Create new session with first window for dev
tmux new-session -d -s $SESSION_NAME -n "dev"
tmux send-keys -t $SESSION_NAME:dev "cd backend && AWS_PROFILE=sports-betting-dev python3 backfill_historical_odds.py --env dev --api-key $API_KEY --years $YEARS" C-m

# Create window for beta
tmux new-window -t $SESSION_NAME -n "beta"
tmux send-keys -t $SESSION_NAME:beta "cd backend && AWS_PROFILE=sports-betting-staging python3 backfill_historical_odds.py --env beta --api-key $API_KEY --years $YEARS" C-m

# Create window for prod
tmux new-window -t $SESSION_NAME -n "prod"
tmux send-keys -t $SESSION_NAME:prod "cd backend && AWS_PROFILE=sports-betting-prod python3 backfill_historical_odds.py --env prod --api-key $API_KEY --years $YEARS" C-m

# Create monitoring window
tmux new-window -t $SESSION_NAME -n "monitor"
tmux send-keys -t $SESSION_NAME:monitor "echo 'Backfill running in parallel...'; echo ''; echo 'Windows:'; echo '  dev  - Development environment'; echo '  beta - Beta/Staging environment'; echo '  prod - Production environment'; echo ''; echo 'Use Ctrl+b then window number to switch'; echo 'Use Ctrl+b d to detach'; echo 'Use tmux attach -t $SESSION_NAME to reattach'" C-m

# Attach to session
tmux select-window -t $SESSION_NAME:monitor
tmux attach-session -t $SESSION_NAME
