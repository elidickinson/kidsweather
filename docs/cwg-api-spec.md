# CWG API: Proposed Changes for kidsweather Integration

## Context

kidsweather fetches the CWG forecast to include in the LLM context. We need:
- The first/latest post as plain text (not HTML)
- A machine-readable timestamp so we can show freshness and skip stale data
- The ability to filter stale posts server-side

## Current Response (`/api/cwg.json`)

```json
{
  "main_headline": "Warm to seasonable with mainly bright skies through Sunday",
  "all_posts_html": "<h1>...</h1><section>...</section>..."
}
```

The only timestamp is a human-readable string buried in the HTML:
`<p style="...">Last fetched: 2/27/2026 4:40 PM EST</p>`

## Proposed Response

Add three fields. No changes to existing fields needed (keep them for backward compat).

```json
{
  "main_headline": "Warm to seasonable with mainly bright skies through Sunday",
  "all_posts_html": "<h1>...</h1><section>...</section>...",

  "latest_post_text": "Happening now: Temperatures slip back into the 40s after sunset...",
  "latest_post_updated_at": "2026-02-27T16:40:00-05:00",
  "latest_post_age_hours": 4.2
}
```

### New Fields

| Field | Type | Description |
|-------|------|-------------|
| `latest_post_text` | `string` | Plain text of the first/most recent post (HTML stripped). Just the body, not the headline. |
| `latest_post_updated_at` | `string` | ISO 8601 timestamp with timezone offset for when this post was last fetched/updated. |
| `latest_post_age_hours` | `float` | Server-computed age in hours (rounded to 1 decimal). Lets clients skip stale data without parsing timestamps. |

### Optional Query Parameter

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `max_age_hours` | `float` | none | If set, return `latest_post_text: null` when the post is older than this many hours. Keeps stale forecasts out of LLM context without client-side logic. |

Example: `/api/cwg.json?max_age_hours=12` would null out `latest_post_text` and `latest_post_age_hours` if the post is >12h old.

## What This Enables on the Client

Once the API ships these fields, the kidsweather `fetch_cwg_forecast()` function simplifies to:

```python
def fetch_cwg_forecast(max_age_hours: int = 12) -> Optional[str]:
    resp = requests.get(f"{CWG_API_URL}?max_age_hours={max_age_hours}", timeout=10)
    data = resp.json()
    text = data.get("latest_post_text")
    if not text:
        return None
    age = data.get("latest_post_age_hours", 0)
    headline = data.get("main_headline", "")
    hours = int(age)
    age_label = f"Posted about {hours} hour{'s' if hours != 1 else ''} ago" if hours >= 1 else "Posted less than an hour ago"
    return f"{headline}\n({age_label})\n{text}"
```

No HTML parsing, no timestamp parsing, no timezone guessing.
