"""Discord adapter for the Cyrene diary agent.

Requires:
    pip install discord.py
"""

from collections.abc import Callable

from .agent import HermesAgent
from .app import build_agent
from .commands import HELP_TEXT, format_diary_entries, parse_command
from .config import ConfigError, Settings
from .llm import LocalLLMError


def run_discord_bot(settings: Settings) -> None:
    if not settings.discord_bot_token:
        raise ConfigError("DISCORD_BOT_TOKEN 환경변수가 필요합니다.")
    try:
        import discord
    except ImportError as exc:
        raise RuntimeError("discord.py가 필요합니다. pip install discord.py") from exc

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    sessions = DiscordSessionRegistry(lambda scope: build_agent(settings, scope))

    @client.event
    async def on_ready():
        print(f"Discord 로그인 완료: {client.user}")

    @client.event
    async def on_message(message):
        if message.author.bot:
            return
        content = extract_command_text(
            message.content,
            prefix=settings.discord_command_prefix,
            bot_user_id=str(client.user.id) if client.user else "",
        )
        if content is None:
            return
        guild_id = str(message.guild.id) if message.guild else "dm"
        agent = sessions.get(discord_memory_scope(guild_id, str(message.author.id)))
        response = handle_discord_text(agent, content)
        if response:
            await message.channel.send(clip_discord_message(response))

    client.run(settings.discord_bot_token)


class DiscordSessionRegistry:
    def __init__(self, factory: Callable[[str], HermesAgent]) -> None:
        self.factory = factory
        self.sessions: dict[str, HermesAgent] = {}

    def get(self, scope: str) -> HermesAgent:
        if scope not in self.sessions:
            self.sessions[scope] = self.factory(scope)
        return self.sessions[scope]


def handle_discord_text(agent: HermesAgent, text: str) -> str:
    command = parse_command(text)
    if command.kind == "exit":
        return "Discord에서는 세션을 계속 열어둘게. 필요하면 다시 불러줘♪"
    if command.kind == "reset_session":
        agent.reset_session()
        return "현재 대화 세션을 비웠어. 장기 기억과 저장된 일기는 그대로야♪"
    if command.kind == "confirm":
        return agent.confirm_pending_action()
    if command.kind == "cancel":
        return agent.cancel_pending_action()
    if command.kind == "help":
        return HELP_TEXT
    if command.kind == "memory_report":
        return agent.memory_report()
    if command.kind == "recent":
        return format_diary_entries(
            agent.recent_diaries(), "아직 저장된 일기 인덱스가 없습니다."
        )
    if command.kind == "search":
        if not command.value:
            return "검색어를 함께 입력해줘."
        return format_diary_entries(agent.search_diaries(command.value), "검색 결과가 없습니다.")
    if command.kind == "tool_status":
        return agent.tool_status()
    if command.kind == "notion_search":
        return agent.search_notion(command.value)
    if command.kind == "notion_read":
        return agent.read_notion_page(command.value)
    if command.kind == "notion_todo":
        return agent.stage_notion_todo(command.value)
    if command.kind == "profile_update":
        if not command.value:
            return "저장할 내용을 함께 입력해줘."
        update_profile(agent, command.profile_action, command.value)
        return "기억에 저장했어♪"
    if command.kind == "diary":
        if not agent.can_write_diary():
            return "아직 아무 얘기도 못 들었는걸? 오늘 있었던 일부터 들려줘♪"
        try:
            entry = agent.draft_diary()
        except LocalLLMError as exc:
            return str(exc)
        return f"{entry}\n\n괜찮으면 /저장 이라고 말해줘♪"
    if command.kind == "save_diary":
        try:
            entry, location = agent.save_diary_draft()
        except ValueError:
            return "아직 저장할 일기 초안이 없어. 먼저 /일기 로 초안을 만들자♪"
        return f"{entry}\n\n저장 위치: {location}"
    if command.kind == "discard_diary":
        if agent.discard_diary_draft():
            return "초안은 지워뒀어. 다시 쓰고 싶으면 /일기 라고 말해줘♪"
        return "지울 초안은 없어."

    try:
        return agent.respond(command.value)
    except LocalLLMError as exc:
        return str(exc)


def update_profile(agent: HermesAgent, action: str, value: str) -> None:
    if action == "name":
        agent.set_user_name(value)
    elif action == "note":
        agent.remember_note(value)
    elif action == "preference":
        agent.remember_preference(value)
    elif action == "avoidance":
        agent.remember_avoidance(value)
    else:
        raise ValueError(f"지원하지 않는 프로필 동작입니다: {action}")


def extract_command_text(content: str, prefix: str, bot_user_id: str) -> str | None:
    stripped = content.strip()
    markers = [prefix]
    if bot_user_id:
        markers.extend([f"<@{bot_user_id}>", f"<@!{bot_user_id}>"])
    for marker in markers:
        if marker and stripped.startswith(marker):
            return stripped[len(marker) :].strip()
    return None


def discord_memory_scope(guild_id: str, user_id: str) -> str:
    return f"discord_{guild_id}_{user_id}"


def clip_discord_message(text: str, limit: int = 1900) -> str:
    if "긴급" in text or "988" in text or "109" in text:
        limit = max(limit, 1900)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"
