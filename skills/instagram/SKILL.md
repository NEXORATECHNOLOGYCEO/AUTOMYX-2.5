# Instagram Channel

Connect Automyx to Instagram Direct Messages via the Instagram Graph API.

## Requirements

- **Facebook Business account** connected to an **Instagram Professional** or **Creator** account
- **Facebook App** with these permissions:
  - `instagram_business_basic`
  - `instagram_business_manage_messages`
  - `pages_show_list`
  - `pages_messaging`
- A **Page Access Token** that includes the `instagram_business_manage_messages` permission

## Setup

1. Create a Meta App at https://developers.facebook.com/apps
2. Add the **Instagram** product
3. Connect your Instagram Professional account to a Facebook Page
4. Generate a Page Access Token with the required permissions
5. Set in `.env`:
   ```
   INSTAGRAM_PAGE_ID=17841234567890123
   INSTAGRAM_ACCESS_TOKEN=EAAJ...
   ```

## Run

```bash
python instagram_bot.py
```

## Features

| Capability          | Status      |
|---------------------|-------------|
| Text DMs            | ✅          |
| Image attachments   | ✅ (via file.io fallback) |
| Story replies       | ⏳ planned  |
| Quick replies       | ⏳ planned  |
| Webhook (real-time) | ⏳ needs server |

## Webhook Setup (Recommended)

The polling skeleton in `instagram_bot.py` is for development. For production:

1. Expose `https://your-domain.com/webhook/instagram` (HTTPS required)
2. Verify the webhook at https://developers.facebook.com/apps → Webhooks
3. Subscribe to `messages` field
4. Forward events to `handle_event(event, page_id, token)`

### Example webhook server (Flask)

```python
from flask import Flask, request
from instagram_bot import handle_event
import os

app = Flask(__name__)
PAGE_ID = os.environ["INSTAGRAM_PAGE_ID"]
TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]

@app.post("/webhook/instagram")
def webhook():
    body = request.get_json()
    for entry in body.get("entry", []):
        for event in entry.get("messaging", []):
            handle_event(event, PAGE_ID, TOKEN)
    return "ok", 200
```

## Limits

- Text messages: 1000 chars max
- Image: must be public URL (IG doesn't accept base64 directly) — we use file.io as a temporary public host
- Rate limits: 200 calls/hour per page

## Troubleshooting

- **Token rejected**: regenerate from Graph API Explorer with the right permissions
- **No messages arriving**: confirm the IG account is Professional (not Personal) and linked to a Page
- **Can't send image**: check that file.io is reachable from your server (or replace with S3/your CDN)
