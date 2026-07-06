import tempfile
import unittest
from datetime import date
from pathlib import Path

from hermes.agent import HermesAgent
from hermes.memory import DiaryIndexMemory, ProfileMemory, cosine_similarity
from hermes.wiki import ObsidianWiki, extract_tags
from storage import LocalMarkdownStorage


class SequencedFakeLLM:
    """Returns one canned response per call, in order."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, int]] = []

    def chat(self, system, messages):
        self.calls.append((system, len(messages)))
        return self.responses.pop(0) if self.responses else ""


class BrokenLLM:
    def chat(self, system, messages):
        raise RuntimeError("no local model server")


class FakeEmbeddingClient:
    def __init__(self, vector: list[float]) -> None:
        self.vector = vector
        self.calls = 0

    def embed(self, text: str) -> list[float]:
        self.calls += 1
        return self.vector


class ExtractTagsTest(unittest.TestCase):
    def test_parses_comma_separated_tags(self) -> None:
        llm = SequencedFakeLLM(["코딩, 산책, 야근"])

        tags = extract_tags(llm, "오늘은 코딩하고 산책했다.")

        self.assertEqual(tags, ["코딩", "산책", "야근"])

    def test_returns_empty_list_when_llm_unreachable(self) -> None:
        self.assertEqual(extract_tags(BrokenLLM(), "아무 내용"), [])

    def test_respects_tag_limit(self) -> None:
        llm = SequencedFakeLLM(["일, 이, 삼, 사, 오, 육"])

        tags = extract_tags(llm, "내용", limit=3)

        self.assertEqual(tags, ["일", "이", "삼"])


class CosineSimilarityTest(unittest.TestCase):
    def test_identical_vectors_score_one(self) -> None:
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [1.0, 0.0]), 1.0)

    def test_orthogonal_vectors_score_zero(self) -> None:
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0)

    def test_mismatched_lengths_score_zero(self) -> None:
        self.assertEqual(cosine_similarity([1.0], [1.0, 0.0]), 0.0)


class DiaryIndexFindRelatedTest(unittest.TestCase):
    def test_finds_similar_past_entries_above_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            index = DiaryIndexMemory(Path(directory) / "index.json")
            index.add_entry(date(2026, 7, 1), "diary/2026-07-01.md", "산책", embedding=[1.0, 0.0])
            index.add_entry(date(2026, 7, 2), "diary/2026-07-02.md", "코드 작업", embedding=[0.0, 1.0])

            related = index.find_related([1.0, 0.0], exclude_date="2026-07-03", threshold=0.9)

            self.assertEqual(related, ["2026-07-01"])

    def test_excludes_entries_without_embeddings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            index = DiaryIndexMemory(Path(directory) / "index.json")
            index.add_entry(date(2026, 7, 1), "diary/2026-07-01.md", "임베딩 없는 옛 일기")

            related = index.find_related([1.0, 0.0], exclude_date="2026-07-02")

            self.assertEqual(related, [])

    def test_excludes_the_entry_itself(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            index = DiaryIndexMemory(Path(directory) / "index.json")
            index.add_entry(date(2026, 7, 2), "diary/2026-07-02.md", "오늘", embedding=[1.0, 0.0])

            related = index.find_related([1.0, 0.0], exclude_date="2026-07-02")

            self.assertEqual(related, [])


class ObsidianWikiTest(unittest.TestCase):
    def test_write_entry_creates_note_with_frontmatter_tags_and_related_links(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            wiki = ObsidianWiki(directory)

            path = wiki.write_entry(
                "2026-07-06",
                summary="코드 작업을 했다.",
                tags=["코딩", "야근"],
                related_dates=["2026-07-01"],
                external_link="https://notion.so/abc",
            )

            text = path.read_text(encoding="utf-8")
            self.assertIn("date: 2026-07-06", text)
            self.assertIn("tags: [코딩, 야근]", text)
            self.assertIn("[[코딩]]", text)
            self.assertIn("[[2026-07-01]]", text)
            self.assertIn("https://notion.so/abc", text)

    def test_write_entry_creates_tag_pages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            wiki = ObsidianWiki(directory)

            wiki.write_entry("2026-07-06", summary="", tags=["코딩"], related_dates=[])

            tag_path = Path(directory) / "태그" / "코딩.md"
            self.assertTrue(tag_path.exists())

    def test_write_entry_without_tags_or_related_omits_sections(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            wiki = ObsidianWiki(directory)

            path = wiki.write_entry("2026-07-06", summary="그냥 하루", tags=[], related_dates=[])

            text = path.read_text(encoding="utf-8")
            self.assertNotIn("## 태그", text)
            self.assertNotIn("## 관련 일기", text)


class HermesAgentWikiIntegrationTest(unittest.TestCase):
    def test_save_diary_draft_writes_wiki_note_with_tags_and_related_links(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            index = DiaryIndexMemory(base / "index.json")
            index.add_entry(
                date(2026, 7, 1), "diary/2026-07-01.md", "예전 코드 작업", embedding=[1.0, 0.0]
            )

            llm = SequencedFakeLLM(
                ["안녕! 오늘 얘기 들려줘서 고마워.", "오늘은 코드 작업을 했다.", "코딩, 야근"]
            )
            wiki = ObsidianWiki(base / "vault")
            embedding_client = FakeEmbeddingClient([1.0, 0.0])

            agent = HermesAgent(
                llm,
                LocalMarkdownStorage(base / "diary"),
                profile_memory=ProfileMemory(base / "profile.json"),
                diary_index=index,
                wiki=wiki,
                embedding_client=embedding_client,
            )

            agent.respond("오늘 코드 작업했어")
            agent.draft_diary()
            agent.save_diary_draft()

            today = date.today().isoformat()
            note = (base / "vault" / "일기" / f"{today}.md").read_text(encoding="utf-8")
            self.assertIn("코딩", note)
            self.assertIn("2026-07-01", note)
            self.assertEqual(index.load()["entries"][-1]["tags"], ["코딩", "야근"])

    def test_save_diary_draft_without_wiki_configured_skips_wiki_work(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            agent = HermesAgent(
                SequencedFakeLLM(["대화 응답", "일기 초안"]),
                LocalMarkdownStorage(base / "diary"),
                profile_memory=ProfileMemory(base / "profile.json"),
                diary_index=DiaryIndexMemory(base / "index.json"),
            )

            agent.respond("오늘 뭔가 했어")
            agent.draft_diary()
            agent.save_diary_draft()

            self.assertFalse((base / "vault").exists())
            self.assertNotIn("tags", agent.diary_index.load()["entries"][-1])


if __name__ == "__main__":
    unittest.main()
