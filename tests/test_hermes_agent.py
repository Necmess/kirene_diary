from datetime import date
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from hermes import HermesAgent
from hermes.app import build_agent, build_storage
from hermes.commands import format_diary_entries, parse_command
from hermes.config import ConfigError, load_dotenv, load_settings
from hermes.discord_app import (
    DiscordSessionRegistry,
    clip_discord_message,
    discord_memory_scope,
    extract_command_text,
    handle_discord_text,
)
from hermes.mcp_client import DisabledMcpClient, McpClientError
from hermes.memory import DiaryIndexMemory, ProfileMemory
from hermes.tool_router import ToolPolicy, ToolRouter
from storage import LocalMarkdownStorage, NotionStorage


class FakeLLM:
    def __init__(self, response: str = "오늘은 코드 작업을 했다.") -> None:
        self.response = response
        self.calls: list[tuple[str, int]] = []

    def chat(self, system, messages):
        self.calls.append((system, len(messages)))
        return self.response


class HermesAgentTest(unittest.TestCase):
    def test_respond_injects_profile_memory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            profile = ProfileMemory(Path(directory) / "profile.json")
            profile.save({"user_name": "테스트", "preferences": ["짧게 답하기"]})
            llm = FakeLLM()
            agent = HermesAgent(
                llm,
                LocalMarkdownStorage(Path(directory) / "diary"),
                profile_memory=profile,
                diary_index=DiaryIndexMemory(Path(directory) / "index.json"),
            )

            reply = agent.respond("안녕")

            self.assertEqual(reply, "오늘은 코드 작업을 했다.")
            self.assertIn("사용자에 대한 장기 기억", llm.calls[0][0])
            self.assertIn("테스트", llm.calls[0][0])

    def test_write_diary_updates_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            index = DiaryIndexMemory(Path(directory) / "index.json")
            agent = HermesAgent(
                FakeLLM("오늘은 코드 작업을 했다. 구조를 정리했다."),
                LocalMarkdownStorage(Path(directory) / "diary"),
                profile_memory=ProfileMemory(Path(directory) / "profile.json"),
                diary_index=index,
            )

            agent.respond("오늘 코드 작업했어")
            entry, location = agent.write_diary()
            data = index.load()

            self.assertEqual(entry, "오늘은 코드 작업을 했다. 구조를 정리했다.")
            self.assertTrue(location.endswith(".md"))
            self.assertEqual(len(data["entries"]), 1)
            self.assertIn("코드 작업", data["entries"][0]["summary"])
            self.assertIn("일기 인덱스", agent.memory_report())

    def test_diary_draft_can_be_saved_or_discarded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            index = DiaryIndexMemory(Path(directory) / "index.json")
            agent = HermesAgent(
                FakeLLM("초안 내용"),
                LocalMarkdownStorage(Path(directory) / "diary"),
                profile_memory=ProfileMemory(Path(directory) / "profile.json"),
                diary_index=index,
            )

            agent.respond("오늘 테스트했어")
            draft = agent.draft_diary()

            self.assertEqual(draft, "초안 내용")
            self.assertTrue(agent.has_diary_draft())
            self.assertEqual(index.load()["entries"], [])

            saved, location = agent.save_diary_draft()

            self.assertEqual(saved, "초안 내용")
            self.assertTrue(location.endswith(".md"))
            self.assertFalse(agent.has_diary_draft())
            self.assertEqual(len(index.load()["entries"]), 1)

            agent.draft_diary()
            self.assertTrue(agent.discard_diary_draft())
            self.assertFalse(agent.has_diary_draft())

    def test_recent_and_search_diaries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            index = DiaryIndexMemory(Path(directory) / "index.json")
            index.add_entry(date(2026, 7, 1), "diary/2026-07-01.md", "산책을 했다.")
            index.add_entry(date(2026, 7, 2), "diary/2026-07-02.md", "코드 작업을 했다.")
            agent = HermesAgent(
                FakeLLM(),
                LocalMarkdownStorage(Path(directory) / "diary"),
                profile_memory=ProfileMemory(Path(directory) / "profile.json"),
                diary_index=index,
            )

            recent = agent.recent_diaries(limit=1)
            matches = agent.search_diaries("코드")

            self.assertEqual(recent[0]["date"], "2026-07-02")
            self.assertEqual(matches[0]["date"], "2026-07-02")

    def test_manual_profile_updates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            profile = ProfileMemory(Path(directory) / "profile.json")
            agent = HermesAgent(
                FakeLLM(),
                LocalMarkdownStorage(Path(directory) / "diary"),
                profile_memory=profile,
                diary_index=DiaryIndexMemory(Path(directory) / "index.json"),
            )

            agent.set_user_name("테스트")
            agent.remember_preference("짧게 답하기")
            agent.remember_preference("짧게 답하기")
            agent.remember_note("코드 작업을 이어갈 예정")
            agent.remember_avoidance("과장된 위로")
            data = profile.load()

            self.assertEqual(data["user_name"], "테스트")
            self.assertEqual(data["preferences"], ["짧게 답하기"])
            self.assertEqual(data["notes"], ["코드 작업을 이어갈 예정"])
            self.assertEqual(data["avoid"], ["과장된 위로"])
            self.assertIn("피해야 할 것", agent.memory_report())


class ConfigTest(unittest.TestCase):
    def test_load_dotenv_does_not_override_existing_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "CYRENE_MODEL=from-file\nCYRENE_MAX_TOKENS=512\n",
                encoding="utf-8",
            )
            with mock.patch.dict("os.environ", {"CYRENE_MODEL": "from-env"}, clear=True):
                load_dotenv(env_path)
                settings = load_settings()

            self.assertEqual(settings.model, "from-env")
            self.assertEqual(settings.max_tokens, 512)

    def test_invalid_max_tokens_raises_config_error(self) -> None:
        with mock.patch.dict("os.environ", {"CYRENE_MAX_TOKENS": "nope"}, clear=True):
            with self.assertRaises(ConfigError):
                load_settings()

        with mock.patch.dict("os.environ", {"CYRENE_MAX_TOKENS": "0"}, clear=True):
            with self.assertRaises(ConfigError):
                load_settings()

    def test_notion_storage_requires_credentials(self) -> None:
        with mock.patch.dict("os.environ", {"CYRENE_STORAGE": "notion"}, clear=True):
            with self.assertRaises(ConfigError):
                load_settings()

    def test_notion_settings_load_when_credentials_exist(self) -> None:
        env = {
            "CYRENE_STORAGE": "notion",
            "NOTION_TOKEN": "secret",
            "NOTION_DATABASE_ID": "db",
        }
        with mock.patch.dict("os.environ", env, clear=True):
            settings = load_settings()

        self.assertEqual(settings.storage, "notion")
        self.assertEqual(settings.notion_token, "secret")
        self.assertEqual(settings.notion_database_id, "db")

    def test_discord_settings_load(self) -> None:
        env = {
            "DISCORD_BOT_TOKEN": "token",
            "DISCORD_COMMAND_PREFIX": "!cyrene",
        }
        with mock.patch.dict("os.environ", env, clear=True):
            settings = load_settings()

        self.assertEqual(settings.discord_bot_token, "token")
        self.assertEqual(settings.discord_command_prefix, "!cyrene")

    def test_mcp_settings_load(self) -> None:
        env = {
            "CYRENE_NOTION_TOOL": "mcp",
            "CYRENE_MCP_NOTION_URL": "http://localhost:8765",
            "CYRENE_MCP_TIMEOUT": "9",
            "CYRENE_MCP_NOTION_SEARCH_TOOL": "search",
        }
        with mock.patch.dict("os.environ", env, clear=True):
            settings = load_settings()

        self.assertEqual(settings.notion_tool, "mcp")
        self.assertEqual(settings.mcp_notion_url, "http://localhost:8765")
        self.assertEqual(settings.mcp_timeout, 9)
        self.assertEqual(settings.mcp_notion_search_tool, "search")
        self.assertEqual(settings.mcp_notion_read_tool, "notion_read_page")
        self.assertEqual(settings.mcp_notion_todo_tool, "notion_create_todo")


class CommandTest(unittest.TestCase):
    def test_parse_builtin_commands(self) -> None:
        self.assertEqual(parse_command("/help").kind, "help")
        self.assertEqual(parse_command("/최근").kind, "recent")
        self.assertEqual(parse_command("/일기").kind, "diary")
        self.assertEqual(parse_command("/저장").kind, "save_diary")
        self.assertEqual(parse_command("/초안삭제").kind, "discard_diary")
        self.assertEqual(parse_command("/종료").kind, "exit")
        self.assertEqual(parse_command("/도구").kind, "tool_status")

    def test_parse_profile_and_search_commands(self) -> None:
        profile = parse_command("/선호추가 짧게 답하기")
        search = parse_command("/search 코드")

        self.assertEqual(profile.kind, "profile_update")
        self.assertEqual(profile.profile_action, "preference")
        self.assertEqual(profile.value, "짧게 답하기")
        self.assertEqual(search.kind, "search")
        self.assertEqual(search.value, "코드")
        notion = parse_command("/노션검색 일기")
        self.assertEqual(notion.kind, "notion_search")
        self.assertEqual(notion.value, "일기")
        notion_read = parse_command("/노션읽기 page-id")
        todo = parse_command("/할일추가 테스트")
        self.assertEqual(notion_read.kind, "notion_read")
        self.assertEqual(notion_read.value, "page-id")
        self.assertEqual(todo.kind, "notion_todo")
        self.assertEqual(todo.value, "테스트")

    def test_format_diary_entries(self) -> None:
        text = format_diary_entries(
            [{"date": "2026-07-02", "summary": "코드 작업", "location": "a.md"}],
            "empty",
        )

        self.assertIn("2026-07-02", text)
        self.assertIn("코드 작업", text)
        self.assertEqual(format_diary_entries([], "empty"), "empty")


class NotionStorageTest(unittest.TestCase):
    def test_build_page_payload_uses_minimum_database_schema(self) -> None:
        storage = NotionStorage(token="secret", database_id="db")

        payload = storage._build_page_payload(
            date(2026, 7, 3),
            "첫 문단\n\n둘째 문단",
        )

        self.assertEqual(payload["parent"]["database_id"], "db")
        self.assertIn("Name", payload["properties"])
        self.assertEqual(payload["properties"]["Date"]["date"]["start"], "2026-07-03")
        self.assertEqual(len(payload["children"]), 2)
        self.assertEqual(
            payload["children"][0]["paragraph"]["rich_text"][0]["text"]["content"],
            "첫 문단",
        )

    def test_content_blocks_are_chunked(self) -> None:
        storage = NotionStorage(token="secret", database_id="db")

        blocks = storage._content_to_blocks("a" * 1900)

        self.assertEqual(len(blocks), 2)
        self.assertEqual(
            len(blocks[0]["paragraph"]["rich_text"][0]["text"]["content"]),
            1800,
        )


class AppFactoryTest(unittest.TestCase):
    def test_build_storage_uses_local_by_default(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            settings = load_settings()

        self.assertIsInstance(build_storage(settings), LocalMarkdownStorage)

    def test_build_agent_scopes_memory_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict("os.environ", {"CYRENE_MEMORY_DIR": directory}, clear=True):
                settings = load_settings()
            agent = build_agent(settings, memory_scope="discord:123")

            self.assertIn("discord_123", str(agent.profile_memory.path))


class DiscordAdapterTest(unittest.TestCase):
    def test_extract_command_text_from_prefix_or_mention(self) -> None:
        self.assertEqual(
            extract_command_text("!키레네 안녕", prefix="!키레네", bot_user_id="123"),
            "안녕",
        )
        self.assertEqual(
            extract_command_text("<@123> /일기", prefix="!키레네", bot_user_id="123"),
            "/일기",
        )
        self.assertIsNone(
            extract_command_text("그냥 대화", prefix="!키레네", bot_user_id="123")
        )

    def test_clip_discord_message(self) -> None:
        self.assertEqual(clip_discord_message("abc", limit=10), "abc")
        self.assertEqual(len(clip_discord_message("a" * 20, limit=10)), 10)

    def test_session_registry_reuses_agent_per_scope(self) -> None:
        created = []

        def factory(scope):
            created.append(scope)
            return object()

        registry = DiscordSessionRegistry(factory)
        first = registry.get("1")
        second = registry.get("1")

        self.assertIs(first, second)
        self.assertEqual(created, ["1"])

    def test_discord_memory_scope_uses_guild_and_user(self) -> None:
        self.assertEqual(discord_memory_scope("guild", "user"), "discord_guild_user")

    def test_handle_discord_tool_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            agent = HermesAgent(
                FakeLLM(),
                LocalMarkdownStorage(Path(directory) / "diary"),
                profile_memory=ProfileMemory(Path(directory) / "profile.json"),
                diary_index=DiaryIndexMemory(Path(directory) / "index.json"),
            )

            self.assertIn("도구 상태", handle_discord_text(agent, "/도구"))

    def test_handle_discord_drafts_before_save(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            index = DiaryIndexMemory(Path(directory) / "index.json")
            agent = HermesAgent(
                FakeLLM("초안 내용"),
                LocalMarkdownStorage(Path(directory) / "diary"),
                profile_memory=ProfileMemory(Path(directory) / "profile.json"),
                diary_index=index,
            )

            handle_discord_text(agent, "오늘 테스트했어")
            draft_response = handle_discord_text(agent, "/일기")

            self.assertIn("초안 내용", draft_response)
            self.assertEqual(index.load()["entries"], [])

            save_response = handle_discord_text(agent, "/저장")

            self.assertIn("저장 위치", save_response)
            self.assertEqual(len(index.load()["entries"]), 1)


class ToolRouterTest(unittest.TestCase):
    def test_disabled_mcp_client_raises(self) -> None:
        with self.assertRaises(McpClientError):
            DisabledMcpClient().call_tool("search", {})

    def test_notion_search_disabled(self) -> None:
        router = ToolRouter()

        result = router.search_notion("키레네")

        self.assertFalse(result.ok)
        self.assertIn("설정되지 않았습니다", result.message)

    def test_notion_search_routes_to_mcp_tool(self) -> None:
        class FakeMcp:
            def __init__(self):
                self.calls = []

            def call_tool(self, name, arguments):
                self.calls.append((name, arguments))
                return {"content": [{"text": "검색 결과"}]}

        client = FakeMcp()
        router = ToolRouter(
            mcp_client=client,
            notion_enabled=True,
            notion_search_tool="search",
        )

        result = router.search_notion("키레네")

        self.assertTrue(result.ok)
        self.assertEqual(result.message, "검색 결과")
        self.assertEqual(client.calls, [("search", {"query": "키레네"})])

    def test_notion_read_and_todo_route_to_mcp_tools(self) -> None:
        class FakeMcp:
            def __init__(self):
                self.calls = []

            def call_tool(self, name, arguments):
                self.calls.append((name, arguments))
                return {"content": [{"text": "ok"}]}

        client = FakeMcp()
        router = ToolRouter(
            mcp_client=client,
            notion_enabled=True,
            notion_read_tool="read",
            notion_create_todo_tool="todo",
        )

        self.assertTrue(router.read_notion_page("page").ok)
        self.assertTrue(router.create_notion_todo("task").ok)
        self.assertEqual(
            client.calls,
            [("read", {"page": "page"}), ("todo", {"text": "task"})],
        )

    def test_policy_blocks_read_or_create(self) -> None:
        router = ToolRouter(
            mcp_client=object(),
            notion_enabled=True,
            policy=ToolPolicy(allow_read=False, allow_create=False),
        )

        self.assertFalse(router.search_notion("x").ok)
        self.assertFalse(router.read_notion_page("x").ok)
        self.assertFalse(router.create_notion_todo("x").ok)
        self.assertFalse(router.update_notion_page("x", "y").ok)
        self.assertFalse(router.delete_notion_page("x").ok)


if __name__ == "__main__":
    unittest.main()
