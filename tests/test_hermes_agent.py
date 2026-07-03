import tempfile
import unittest
from unittest import mock
from pathlib import Path

from hermes import HermesAgent
from hermes.config import load_dotenv, load_settings
from hermes.memory import DiaryIndexMemory, ProfileMemory
from storage import LocalMarkdownStorage


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


if __name__ == "__main__":
    unittest.main()
