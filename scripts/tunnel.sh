#!/bin/bash
# Self-healing Cloudflare tunnel with URL tracking
# Restarts automatically if tunnel dies, writes URL to known location

URL_FILE="/tmp/openkol_tunnel_url.txt"
LOG_FILE="/tmp/cloudflare_tunnel.log"
PORT="${1:-3000}"
NEXT_CONFIG="/Users/aiman/.openclaw/workspace/projects/kreator/next.config.ts"

cleanup() {
    echo "[tunnel] Shutting down..."
    kill $TUNNEL_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

while true; do
    echo "[tunnel] Starting Cloudflare tunnel on port $PORT..."
    
    # Start tunnel, capture output
    cloudflared tunnel --url "http://localhost:$PORT" > "$LOG_FILE" 2>&1 &
    TUNNEL_PID=$!
    
    # Wait for URL to appear
    for i in $(seq 1 30); do
        URL=$(grep -o 'https://[a-z0-9\-]*\.trycloudflare\.com' "$LOG_FILE" 2>/dev/null | head -1)
        if [ -n "$URL" ]; then
            echo "$URL" > "$URL_FILE"
            HOSTNAME=$(echo "$URL" | sed 's|https://||')
            
            # Auto-add to next.config.ts allowedDevOrigins
            if ! grep -q "$HOSTNAME" "$NEXT_CONFIG" 2>/dev/null; then
                sed -i '' "s|allowedDevOrigins: \[|allowedDevOrigins: ['$HOSTNAME', |" "$NEXT_CONFIG"
                echo "[tunnel] Added $HOSTNAME to allowedDevOrigins"
            fi
            
            echo "[tunnel] ✅ Live at: $URL"
            echo "[tunnel] URL saved to: $URL_FILE"
            break
        fi
        sleep 1
    done
    
    if [ -z "$URL" ]; then
        echo "[tunnel] ❌ Failed to get URL after 30s, retrying..."
        kill $TUNNEL_PID 2>/dev/null
        sleep 5
        continue
    fi
    
    # Monitor tunnel health
    while kill -0 $TUNNEL_PID 2>/dev/null; do
        sleep 30
        # Quick health check
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$URL/api/stats" 2>/dev/null)
        if [ "$HTTP_CODE" != "200" ]; then
            echo "[tunnel] ⚠️  Health check failed (HTTP $HTTP_CODE), checking again..."
            sleep 10
            HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$URL/api/stats" 2>/dev/null)
            if [ "$HTTP_CODE" != "200" ]; then
                echo "[tunnel] ❌ Tunnel dead, restarting..."
                kill $TUNNEL_PID 2>/dev/null
                break
            fi
        fi
    done
    
    echo "[tunnel] Tunnel process exited, restarting in 5s..."
    sleep 5
done
