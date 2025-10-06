#!/bin/bash
set -e

# Load environment variables
if [ -f .env ]; then
    source .env
fi

uv run python -m kidsweather --render page.html

# requires shot-scraper - install with `uv tool install shot-scraper` and `shot-scraper install`
shot-scraper shot -w 1440 -h 2560 --wait 500 page.html -o page.png



# curl -X POST "${PIXASHOT_URL:-https://pixashot-service-492638716942.us-central1.run.app/capture}" -o capture.png \
#   -H "Authorization: Bearer ${PIXASHOT_TOKEN}" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "html_content": '"$(cat page.html | jq -Rs .)"',
#     "format": "png",
#     "full_page": true,
#     "wait_for_network": "idle",
#     "window_width": 1440,
#     "window_height": 2500
#   }'

  curl -X POST -H "Authorization: Bearer ${VISIONECT_API_KEY}" -F "image=@page.png" "${VISIONECT_PUSH_URL:-https://esd-visionect-push.replit.app/upload}"
