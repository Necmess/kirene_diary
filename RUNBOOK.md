# Runbook

## 1. Clone

```bash
git clone git@github.com:Necmess/kirene_diary.git
cd kirene_diary
cp .env.example .env
```

## 2. Local LLM

```bash
ollama serve
ollama pull gemma4:e4b
```

Set:

```env
CYRENE_MODEL=gemma4:e4b
CYRENE_LLM_URL=http://localhost:11434/api/chat
```

## 3. Discord Bot

In the Discord developer portal:

- Create an application and bot.
- Enable Message Content Intent.
- Invite the bot with permissions to read and send messages.

Set:

```env
DISCORD_BOT_TOKEN=xxx
DISCORD_COMMAND_PREFIX=!키레네
```

Run:

```bash
pip install -r requirements-discord.txt
python discord_bot.py
```

Smoke test:

```text
!키레네 /도움말
!키레네 오늘은 연결 테스트를 했어
!키레네 /일기
!키레네 /저장
```

## 4. Notion MCP Process

Run the Notion MCP server as a separate process from the Discord bot. Keep Notion tokens in the MCP process environment when possible.

Bot process settings:

```env
CYRENE_NOTION_TOOL=mcp
CYRENE_MCP_NOTION_URL=http://localhost:8765
CYRENE_MCP_NOTION_SEARCH_TOOL=notion_search
CYRENE_MCP_NOTION_READ_TOOL=notion_read_page
CYRENE_MCP_NOTION_TODO_TOOL=notion_create_todo
```

MCP process settings:

```env
NOTION_TOKEN=secret_xxx
NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Smoke test:

```text
!키레네 /도구
!키레네 /노션검색 테스트
!키레네 /할일추가 MCP 연결 확인
!키레네 /확인
```

## 5. Safety

Set the local crisis resource region:

```env
CYRENE_SAFETY_REGION=KR
```

Allowed values:

- `KR`
- `US`
- `GLOBAL`

Smoke test with a non-real test phrase before exposing the bot publicly, and verify the response does not role-play or romanticize self-harm.
