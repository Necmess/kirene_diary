"""키레네 로컬 일기 에이전트.

사용법:
    ollama serve
    ollama pull gemma3:4b
    python main.py

명령어:
    /일기   지금까지의 대화로 일기를 생성하고 저장
    /종료   저장 없이 종료
"""

import os

from hermes import HermesAgent, LocalLLMClient, LocalLLMError
from hermes.memory import DiaryIndexMemory, ProfileMemory
from persona import GREETING
from storage import LocalMarkdownStorage

MODEL = os.environ.get("CYRENE_MODEL", "gemma3:4b")
LLM_URL = os.environ.get("CYRENE_LLM_URL", "http://localhost:11434/api/chat")
MAX_TOKENS = int(os.environ.get("CYRENE_MAX_TOKENS", "1024"))
MEMORY_DIR = os.environ.get("CYRENE_MEMORY_DIR", "memory")

PINK = "\033[95m"
DIM = "\033[2m"
RESET = "\033[0m"


def cyrene_says(text: str) -> None:
    print(f"\n{PINK}키레네{RESET} {text}\n")


def write_diary(agent: HermesAgent) -> None:
    if not agent.can_write_diary():
        cyrene_says("아직 아무 얘기도 못 들었는걸? 오늘 있었던 일부터 들려줘♪")
        return
    print(f"{DIM}(키레네가 일기를 쓰는 중…){RESET}")
    entry, location = agent.write_diary()
    print("\n" + "=" * 50)
    print(entry)
    print("=" * 50)
    cyrene_says(f"오늘의 기억, 여기 남겨뒀어 → {location}\n또 만나자, 약속이다? 잊어버리면 안 돼♪")


def main() -> None:
    llm = LocalLLMClient(model=MODEL, url=LLM_URL, max_tokens=MAX_TOKENS)
    agent = HermesAgent(
        llm=llm,
        storage=LocalMarkdownStorage(),
        profile_memory=ProfileMemory(f"{MEMORY_DIR}/profile.json"),
        diary_index=DiaryIndexMemory(f"{MEMORY_DIR}/diary_index.json"),
    )

    cyrene_says(GREETING)

    while True:
        try:
            user_input = input("나 > ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break
        if not user_input:
            continue
        if user_input in ("/종료", "/exit", "/quit"):
            cyrene_says("이 몸은 작별을 좋아하지 않아. 차라리… 여운을 남기는 건 어떨까?")
            break
        if user_input in ("/일기", "/diary"):
            try:
                write_diary(agent)
            except LocalLLMError as e:
                print(f"{DIM}{e}{RESET}")
            break

        try:
            reply = agent.respond(user_input)
        except LocalLLMError as e:
            print(f"{DIM}{e}{RESET}")
            continue
        cyrene_says(reply)


if __name__ == "__main__":
    main()
