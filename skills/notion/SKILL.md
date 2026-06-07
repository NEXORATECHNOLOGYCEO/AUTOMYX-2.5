# Notion Skill — Automyx v2.5

## Purpose
Connect Automyx to a Notion workspace so the agent can **read, search, summarize, create, and update** Notion pages, databases, and blocks. Use Notion as the **structured memory layer** of Automyx: knowledge base, project tracking, meeting notes, CRM, daily journals, and task management.

## When to Invoke
Use this skill when the user asks to:
- Search information inside a Notion workspace
- Read or summarize a Notion page or database
- Create new pages (notes, tasks, meeting summaries)
- Update page properties (status, dates, assignments)
- Append content to an existing page
- Query a Notion database (filter / sort)
- Sync Automyx's memory with Notion

Do **not** use this skill for local Markdown notes — use `obsidian` or `notion-local` instead.

## Authentication

### Step 1 — Create the Integration
1. Open https://www.notion.so/my-integrations
2. Click **"+ New integration"**
3. Name: `Automyx Agent`
4. Capabilities: `Read content` ✅, `Update content` ✅, `Insert content` ✅
5. Save and copy the **Internal Integration Secret** (starts with `ntn_` or `secret_`)

### Step 2 — Share Pages (CRITICAL)
A Notion integration has **zero access by default**. The user must share each page or database they want Automyx to operate on:
1. Open the target page/database in Notion
2. Click **`...`** (top right) → **`Add connections`**
3. Select `Automyx Agent`

Share parent pages; children inherit permissions.

### Step 3 — Store the Token
The token is stored in `.env` as `NOTION_API_KEY=ntn_...` and loaded automatically by `tools/notion_tools.py`.

Never expose the token to the LLM runtime. Never log it.

## Available Tools (`tools/notion_tools.py`)

| Tool | Description |
|---|---|
| `notion_search(query, filter_type, page_size)` | Search pages or databases. `filter_type` ∈ `{None, "page", "database"}`. |
| `notion_get_page(page_id)` | Fetch a single page's metadata. |
| `notion_get_page_content(page_id, max_blocks)` | Read the block children of a page (returns rich text). |
| `notion_get_database(database_id, filter_obj, sorts, page_size)` | Query a database with optional filters and sorts. |
| `notion_create_page(parent_id, title, content, icon, properties)` | Create a new page. `content` accepts Markdown. |
| `notion_update_page(page_id, properties)` | Update page properties (status, dates, etc.). |
| `notion_append_blocks(page_id, blocks)` | Append raw Notion blocks to a page. |
| `notion_delete_page(page_id)` | Archive a page. |
| `notion_md_to_blocks(md_text)` | Convert Markdown → Notion block list (for batch creation). |

## Common Patterns

### Search for the policy/knowledge page
```
notion_search(query="refund policy")
→ list of pages
notion_get_page_content(page_id=first_hit["id"])
→ read the body and summarize
```

### Create a daily journal entry
```
notion_search(query="Daily Journal")
→ get the parent database id
notion_create_page(
  parent_id=database_id,
  title=datetime.now().strftime("%Y-%m-%d"),
  content="## Top 3 today\n- ...",
  properties={"Status": "Open"}
)
```

### Update task status
```
notion_update_page(
  page_id="...",
  properties={"Status": {"select": {"name": "Done"}}}
)
```

### Append meeting notes
```
md = """
## Meeting 2026-06-06
Attendees: ...
Decisions:
- ...
Action items:
- [ ] Juan: ship v2.5
"""
notion_append_blocks(page_id=meeting_page_id, blocks=notion_md_to_blocks(md))
```

## Notion API Reference

- Base URL: `https://api.notion.com/v1`
- Version header: `Notion-Version: 2022-06-28`
- Rate limit: **3 requests/second** (cache results when possible)
- Auth: `Authorization: Bearer NOTION_API_KEY`

Key endpoints the agent should know:
- `POST /search` — search pages & databases
- `GET  /pages/{id}` — page metadata
- `POST /pages` — create a page
- `PATCH /pages/{id}` — update properties
- `GET  /databases/{id}/query` — query database
- `POST /databases` — create database
- `GET  /blocks/{id}/children` — list block children
- `PATCH /blocks/{id}/children` — append blocks
- `DELETE /blocks/{id}` — delete a block

## Tone of Voice
When responding to the user about Notion operations, be concise:
- ✅ "Page created in **Daily Journal** → `2026-06-06 9:42am`"
- ❌ "I have successfully created a new page in your Daily Journal database. The page has been titled..."

## Errors & Recovery
| Error | Cause | Fix |
|---|---|---|
| `404 object_not_found` | Page not shared with the integration | Tell the user to add the integration via `...` → `Add connections` |
| `401 unauthorized` | Bad token | Ask user to re-paste the token in the Onboard wizard |
| `429 rate_limited` | > 3 req/s | Back off, retry with `time.sleep(1)` |
| `validation_error: body failed validation` | Bad block structure | Use `notion_md_to_blocks()` to convert Markdown safely |
| `unauthorized_domain` | Trying to access a workspace you don't own | Re-share with the integration |

## Privacy & Security
- The Notion token is stored in `.env` and never sent to the LLM provider.
- When a page is created on behalf of the user, mark it with a 🅰 icon (or `created_by_ai: true` checkbox) so the user can audit.
- Always log which page IDs were touched in `aumformbring_data/lessons_learned.json` for traceability.

## Quick Test
After setup, the user can verify with:
```bash
python automix.py chat "busca en notion la página 'Onboarding'"
```

Expected behavior: `notion_search` returns matching pages → LLM summarizes the top result.

---

*This skill is auto-discovered from `skills/notion/SKILL.md` on agent startup. No code changes required to enable it — only `NOTION_API_KEY` in `.env`.*
