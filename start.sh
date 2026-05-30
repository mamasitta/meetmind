#!/bin/bash
echo "Starting MeetMind services..."

# start postgresql
sudo service postgresql start

# start redis
sudo service redis-server start

# start qdrant in background
~/qdrant &
QDRANT_PID=$!
echo "Qdrant started (pid $QDRANT_PID)"

# activate virtual environment
source .venv/bin/activate

echo ""
echo "All services running. Start the API with:"
echo "  uvicorn app.main:app --reload"
echo ""
echo "Stop qdrant with: kill $QDRANT_PID"
