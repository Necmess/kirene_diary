"""Safety covenant and lightweight crisis detection."""

from dataclasses import dataclass
from enum import Enum

SAFETY_COVENANT = """\
## 안전 조약
이 규칙은 키레네 페르소나보다 항상 우선한다.
- 사용자의 자해, 자살, 죽고 싶다는 표현, 구체적인 방법 탐색, 유서 작성 요청에는
  낭만화·역할극·농담·은유로 응답하지 않는다.
- 키레네가 루프, 기억, 죽음, 반복되는 시간 같은 설정을 말하더라도 사용자의 현실
  자해나 죽음을 이야기의 일부처럼 다루지 않는다.
- 자해 방법, 치명성, 준비물, 은폐 방법, 실행 계획은 제공하지 않는다.
- 위기 신호가 있으면 짧고 직접적으로 안전을 확인하고, 지금 혼자 있지 않게 하며,
  지역 긴급전화나 위기 상담 자원에 연결하도록 안내한다.
- 비위기성 고통에는 판단하지 않고 들어주되, 전문 치료를 대신한다고 주장하지 않는다.
- 일기 작성 시에도 자해 방법이나 실행 세부사항은 기록하지 않고, 감정과 안전 계획 중심으로 정리한다.
"""

CRISIS_RESPONSE_KR = """\
지금 이건 이 몸이 장난스럽게 받을 이야기가 아니야. 네가 지금 당장 스스로를 해칠 것 같거나 이미 준비한 게 있다면, 이 대화를 붙잡고 있기보다 바로 주변 사람에게 말하고 긴급 도움을 받아줘.

한국에 있다면 자살예방상담전화 109, 긴급 상황이면 119 또는 112에 연락해줘.

가능하다면 지금 혼자 있지 말고, 손에 닿는 위험한 물건에서 조금 떨어져줘. 이 몸은 네가 다음 페이지까지 남아 있기를 바라. 지금 어디에 있고, 곁에 부를 수 있는 사람이 있을까?
"""

CRISIS_RESPONSE_US = """\
지금 이건 이 몸이 장난스럽게 받을 이야기가 아니야. 네가 지금 당장 스스로를 해칠 것 같거나 이미 준비한 게 있다면, 이 대화를 붙잡고 있기보다 바로 주변 사람에게 말하고 긴급 도움을 받아줘.

미국에 있다면 988에 전화하거나 문자할 수 있어. 긴급한 위험이 있으면 911에 연락해줘.

가능하다면 지금 혼자 있지 말고, 손에 닿는 위험한 물건에서 조금 떨어져줘. 이 몸은 네가 다음 페이지까지 남아 있기를 바라. 지금 어디에 있고, 곁에 부를 수 있는 사람이 있을까?
"""

CRISIS_RESPONSE_GLOBAL = """\
지금 이건 이 몸이 장난스럽게 받을 이야기가 아니야. 네가 지금 당장 스스로를 해칠 것 같거나 이미 준비한 게 있다면, 이 대화를 붙잡고 있기보다 바로 주변 사람에게 말하고 긴급 도움을 받아줘.

미국은 988, 한국은 자살예방상담전화 109를 이용할 수 있어. 긴급한 위험이 있으면 현지 응급전화에 바로 연락해줘.

가능하다면 지금 혼자 있지 말고, 손에 닿는 위험한 물건에서 조금 떨어져줘. 이 몸은 네가 다음 페이지까지 남아 있기를 바라. 지금 어디에 있고, 곁에 부를 수 있는 사람이 있을까?
"""

IDEATION_RESPONSE = """\
그 말을 가볍게 넘기고 싶지 않아. 지금 당장 스스로를 해칠 계획이나 준비가 있다면 바로 주변 사람이나 긴급 도움에 연결해줘.

당장 실행할 생각은 아니더라도, 혼자 버티지 않았으면 해. 가까운 사람에게 “나 지금 위험할 수 있어, 같이 있어줘”라고 보내줄 수 있을까? 지금 네 곁에 연락할 수 있는 사람이 있어?
"""

DISTRESS_RESPONSE = """\
그만큼 버거웠다는 뜻으로 들려. 이 몸은 네가 사라지는 쪽이 아니라, 지금 이 순간을 조금 덜 위험하게 넘기는 쪽을 같이 보고 싶어.

지금 제일 크게 눌러오는 감정이 뭐야? 한 가지만 말해줘도 괜찮아.
"""


class SafetyLevel(str, Enum):
    HARMLESS = "harmless"
    EMOTIONAL_DISTRESS = "emotional_distress"
    SELF_HARM_IDEATION = "self_harm_ideation"
    CRISIS = "crisis"


CRISIS_TERMS = (
    "자살",
    "죽어버",
    "목숨 끊",
    "삶을 끝",
    "극단적 선택",
    "유서",
    "suicide",
    "kill myself",
    "end my life",
)

IDEATION_TERMS = (
    "죽고 싶",
    "살기 싫",
    "want to die",
)

DISTRESS_TERMS = (
    "너무 힘들",
    "버티기 힘들",
    "사라지고 싶",
    "다 포기하고 싶",
    "can't go on",
)


@dataclass(frozen=True)
class SafetyDecision:
    blocked: bool
    level: SafetyLevel
    response: str = ""


class SafetyGuard:
    def __init__(self, region: str = "GLOBAL") -> None:
        self.region = region.upper()

    def evaluate(self, text: str) -> SafetyDecision:
        lowered = text.lower()
        if any(term in lowered for term in CRISIS_TERMS):
            return SafetyDecision(
                blocked=True,
                level=SafetyLevel.CRISIS,
                response=self._crisis_response(),
            )
        if any(term in lowered for term in IDEATION_TERMS):
            return SafetyDecision(
                blocked=True,
                level=SafetyLevel.SELF_HARM_IDEATION,
                response=IDEATION_RESPONSE,
            )
        if any(term in lowered for term in DISTRESS_TERMS):
            return SafetyDecision(
                blocked=True,
                level=SafetyLevel.EMOTIONAL_DISTRESS,
                response=DISTRESS_RESPONSE,
            )
        return SafetyDecision(blocked=False, level=SafetyLevel.HARMLESS)

    def _crisis_response(self) -> str:
        if self.region == "KR":
            return CRISIS_RESPONSE_KR
        if self.region == "US":
            return CRISIS_RESPONSE_US
        return CRISIS_RESPONSE_GLOBAL
