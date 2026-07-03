import tempfile
import unittest
from pathlib import Path

from hermes import HermesAgent
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


if __name__ == "__main__":
    unittest.main()
