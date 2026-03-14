#!/bin/bash
# Saathi Web Sandbox — Quick Deploy Script
# Run this on your Mac to start the server and get a public URL.

echo "🙏 Saathi Web Sandbox — Deploying..."
echo ""

# Step 1: Check if server is already running
if lsof -i :8000 > /dev/null 2>&1; then
    echo "⚠️  Port 8000 already in use. Kill existing process? (y/n)"
    read -r answer
    if [ "$answer" = "y" ]; then
        kill $(lsof -ti :8000) 2>/dev/null
        sleep 1
    else
        echo "Exiting."
        exit 1
    fi
fi

# Step 2: Start the FastAPI backend
echo "🚀 Starting Saathi backend on port 8000..."
cd "$(dirname "$0")/backend"
python main.py &
SERVER_PID=$!
sleep 3

# Check if server started
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "❌ Server failed to start. Check errors above."
    exit 1
fi
echo "✅ Server running (PID: $SERVER_PID)"
echo ""

# Step 3: Start ngrok tunnel
echo "🌐 Creating public URL with ngrok..."
echo ""

# Check if pyngrok is available
if python -c "import pyngrok" 2>/dev/null; then
    python -c "
from pyngrok import ngrok
tunnel = ngrok.connect(8000)
print('=' * 50)
print()
print('  🎉 Saathi is LIVE!')
print()
print(f'  🔗 Public URL: {tunnel.public_url}')
print()
print('  Share this URL via WhatsApp for testing.')
print('  Works on any phone or desktop browser.')
print()
print('=' * 50)
print()
print('Press Ctrl+C to stop.')
print()
import signal
signal.pause()
"
else
    echo "⚠️  pyngrok not installed. Install it with:"
    echo "   pip install pyngrok"
    echo ""
    echo "Or install ngrok directly:"
    echo "   brew install ngrok/ngrok/ngrok"
    echo "   ngrok http 8000"
    echo ""
    echo "Meanwhile, Saathi is running locally at:"
    echo "   http://localhost:8000"
    echo ""
    echo "Press Ctrl+C to stop."
    wait $SERVER_PID
fi

# Cleanup
kill $SERVER_PID 2>/dev/null
echo "👋 Saathi stopped."
