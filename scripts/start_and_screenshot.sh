#!/bin/zsh

# Start the Flask app in the background
FLASK_APP=app.py flask run &

# Wait for the Flask app to start
sleep 5

# Start the Cloudflare tunnel
cloudflared tunnel --url http://localhost:5000 &

# Wait for the tunnel to establish
sleep 5

# Get the tunnel URL (assuming cloudflared outputs it to stdout)
TUNNEL_URL=$(cloudflared tunnel info | grep -o 'https://.*')

# Call the external screenshot service
curl -X POST "https://screenshot-service.example.com/capture" -d "url=$TUNNEL_URL"

# Optionally, kill the background processes after the screenshot is taken
# kill %1 %2
