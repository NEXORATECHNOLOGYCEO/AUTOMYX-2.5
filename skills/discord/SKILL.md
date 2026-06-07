# Discord Channel

Connect Automyx to Discord as a real bot. Supports DMs, server mentions, slash commands, and image attachments.

## Setup

1. Create a bot at https://discord.com/developers/applications
2. Copy the **Bot Token** and set `DISCORD_BOT_TOKEN=...` in `.env`
3. Enable the **Message Content Intent** under Bot → Privileged Gateway Intents
4. Invite the bot to your server with the `bot` + `applications.commands` scopes

## Run

```bash
python discord_bot.py
```

## Features

| Capability          | Status      |
|---------------------|-------------|
| Text messages       | ✅          |
| Image attachments   | ✅          |
| Slash commands      | ✅ `/status` `/model` |
| DMs                 | ✅          |
| Server mentions     | ✅          |
| Embeds              | ✅          |
| Voice channels      | ⏳ planned  |

## Commands

- `/status` — show agent + gateway state
- `/model <name>` — switch model for this session
- `!ping` — latency check

## Architecture

- Uses `discord.py` v2.3+
- WebSocket connection (no webhook server needed)
- Forwards all messages to `http://127.0.0.1:3500/api/gateway/inbound` with channel="discord"
- Images are downloaded from Discord CDN, base64-encoded, and sent to the gateway

## Troubleshooting

- **Bot doesn't see messages**: enable Message Content Intent
- **Slash commands don't appear**: run `await bot.tree.sync()` in on_ready
- **Gateway connection refused**: make sure `python automix.py gateway` is running
