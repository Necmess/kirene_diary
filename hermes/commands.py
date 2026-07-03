"""Command parsing for the CLI."""

from dataclasses import dataclass
from typing import Literal

CommandKind = Literal[
    "chat",
    "diary",
    "save_diary",
    "discard_diary",
    "confirm",
    "cancel",
    "reset_session",
    "exit",
    "help",
    "memory_report",
    "profile_update",
    "recent",
    "search",
    "tool_status",
    "notion_search",
    "notion_read",
    "notion_todo",
]


@dataclass(frozen=True)
class ParsedCommand:
    kind: CommandKind
    value: str = ""
    profile_action: str = ""


HELP_TEXT = """\
명령어

[일기]
- /일기, /diary: 지금까지의 대화로 일기 초안 생성
- /저장, /save: 마지막 일기 초안 저장
- /초안삭제, /discard: 마지막 일기 초안 삭제

[기억]
- /기억, /memory: 저장된 장기 기억과 일기 인덱스 확인
- /최근, /recent: 최근 일기 인덱스 보기
- /일기검색 검색어, /search query: 일기 인덱스 검색
- /이름 이름, /name name: 사용자 이름 저장
- /기억추가 내용, /remember text: 장기 기억 메모 추가
- /선호추가 내용, /prefer text: 선호하는 응답 방식 추가
- /회피추가 내용, /avoid text: 피해야 할 응답 방식 추가

[Notion/MCP]
- /도구, /tools: 외부 도구 연결 상태 확인
- /노션검색 검색어, /notion query: Notion MCP 검색
- /노션읽기 페이지, /notion-read page: Notion MCP 페이지 읽기
- /할일추가 내용, /todo text: Notion MCP 할 일 추가 초안
- /확인, /confirm: 대기 중인 외부 쓰기 작업 실행
- /취소, /cancel: 대기 중인 외부 쓰기 작업 취소

[세션]
- /세션초기화, /reset: 현재 대화 세션 초기화
- /종료, /exit, /quit: 저장 없이 종료
"""


def parse_command(user_input: str) -> ParsedCommand:
    text = user_input.strip()
    if text in ("/종료", "/exit", "/quit"):
        return ParsedCommand(kind="exit")
    if text in ("/세션초기화", "/reset"):
        return ParsedCommand(kind="reset_session")
    if text in ("/확인", "/confirm"):
        return ParsedCommand(kind="confirm")
    if text in ("/취소", "/cancel"):
        return ParsedCommand(kind="cancel")
    if text in ("/도움말", "/help"):
        return ParsedCommand(kind="help")
    if text in ("/기억", "/memory"):
        return ParsedCommand(kind="memory_report")
    if text in ("/최근", "/recent"):
        return ParsedCommand(kind="recent")
    if text in ("/도구", "/tools"):
        return ParsedCommand(kind="tool_status")
    if text in ("/일기", "/diary"):
        return ParsedCommand(kind="diary")
    if text in ("/저장", "/save"):
        return ParsedCommand(kind="save_diary")
    if text in ("/초안삭제", "/discard"):
        return ParsedCommand(kind="discard_diary")

    for prefix in ("/일기검색 ", "/search "):
        if text.startswith(prefix):
            return ParsedCommand(kind="search", value=text[len(prefix) :].strip())
    for prefix in ("/노션검색 ", "/notion "):
        if text.startswith(prefix):
            return ParsedCommand(kind="notion_search", value=text[len(prefix) :].strip())
    for prefix in ("/노션읽기 ", "/notion-read "):
        if text.startswith(prefix):
            return ParsedCommand(kind="notion_read", value=text[len(prefix) :].strip())
    for prefix in ("/할일추가 ", "/todo "):
        if text.startswith(prefix):
            return ParsedCommand(kind="notion_todo", value=text[len(prefix) :].strip())

    profile_commands = {
        "/이름 ": "name",
        "/name ": "name",
        "/기억추가 ": "note",
        "/remember ": "note",
        "/선호추가 ": "preference",
        "/prefer ": "preference",
        "/회피추가 ": "avoidance",
        "/avoid ": "avoidance",
    }
    for prefix, action in profile_commands.items():
        if text.startswith(prefix):
            return ParsedCommand(
                kind="profile_update",
                value=text[len(prefix) :].strip(),
                profile_action=action,
            )

    return ParsedCommand(kind="chat", value=text)


def format_diary_entries(entries: list[dict], empty_message: str) -> str:
    if not entries:
        return empty_message
    lines = []
    for entry in entries:
        date = entry.get("date", "unknown")
        summary = entry.get("summary", "")
        location = entry.get("location", "")
        line = f"- {date}"
        if summary:
            line += f": {summary}"
        if location:
            line += f" ({location})"
        lines.append(line)
    return "\n".join(lines)
