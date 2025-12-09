from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence


@dataclass(frozen=True)
class Statement:
    id: int
    text: str


@dataclass(frozen=True)
class DomainItem:
    statement_id: int
    inverted: bool = False


@dataclass(frozen=True)
class Band:
    id: str
    label: str
    min_value: float
    max_value: float
    min_inclusive: bool = False
    max_inclusive: bool = True

    def contains(self, value: float) -> bool:
        lower_ok = (
            value >= self.min_value if self.min_inclusive else value > self.min_value
        )
        upper_ok = (
            value <= self.max_value if self.max_inclusive else value < self.max_value
        )
        return lower_ok and upper_ok


@dataclass(frozen=True)
class DomainDefinition:
    id: str
    title: str
    visibility: str  # "public" or "internal"
    items: Sequence[DomainItem]
    interpretations: Dict[str, str]


@dataclass(frozen=True)
class HexacoResult:
    domain_id: str
    title: str
    percent: float
    band_id: str
    band_label: str
    interpretation: str
    visibility: str


STATEMENTS: List[Statement] = [
    Statement(
        1, "How often do you state your real priorities early in a collaboration?"
    ),
    Statement(
        2,
        "How often do you keep your real priorities private until you see where others are leaning?",
    ),
    Statement(
        3,
        "When rules are clear, how strongly do you prefer they be applied consistently to everyone?",
    ),
    Statement(
        4,
        "When rules are vague, how comfortable are you using the gray area to improve your outcome?",
    ),
    Statement(
        5,
        "Before something important, how often do you mentally rehearse what could go wrong?",
    ),
    Statement(
        6, "Once you have a plan, how easily can you stop revisiting it in your head?"
    ),
    Statement(
        7,
        "How strongly do you feel drawn into other people's highs/lows when you work closely together?",
    ),
    Statement(
        8,
        "How easy is it for you to keep relationships purely functional without emotional carryover?",
    ),
    Statement(
        9,
        "How comfortable are you initiating a conversation with someone high-status you don't know well?",
    ),
    Statement(
        10, "In new groups, how much do you prefer to observe first and speak later?"
    ),
    Statement(
        11, "How often does your enthusiasm show in your voice/pace/expressiveness?"
    ),
    Statement(
        12, "How often do you intentionally keep your energy and expressiveness muted?"
    ),
    Statement(
        13,
        "How easy is it for you to stay composed when someone is slow or repeats the same issue?",
    ),
    Statement(
        14,
        "When things are inefficient, how likely is irritation to leak into your tone?",
    ),
    Statement(
        15,
        "After someone owns a mistake and fixes it, how quickly do you reset with them?",
    ),
    Statement(
        16,
        'Even after a repair, how often do you stay guarded and keep a "mental note"?',
    ),
    Statement(
        17,
        "How consistently do you rely on systems (calendar/lists/checkpoints) to stay on track?",
    ),
    Statement(
        18, "How often do you keep everything in your head and sort it out as you go?"
    ),
    Statement(
        19,
        "When a task is tedious, how reliably do you still complete it without bargaining with yourself?",
    ),
    Statement(
        20, "How often do you need urgency (deadline/pressure) to finish dull tasks?"
    ),
    Statement(
        21,
        "How often do you dig into underlying principles rather than just doing what works?",
    ),
    Statement(
        22, 'How often do you avoid deep dives and prefer "just tell me the steps"?'
    ),
    Statement(
        23,
        "How much do aesthetics (layout, design, presentation) affect your satisfaction with an outcome?",
    ),
    Statement(
        24, "How often do you treat aesthetics as irrelevant as long as it functions?"
    ),
]

BANDS: Sequence[Band] = [
    Band("very_low", "Very low", 0, 13, min_inclusive=True),
    Band("low", "Low", 13, 31),
    Band("medium", "Medium", 31, 68),
    Band("high", "High", 68, 87),
    Band("very_high", "Very high", 87, 100),
]


def _interp(public: bool, levels: List[str]) -> Dict[str, str]:
    """Helper to zip band ids with texts."""
    band_ids = [band.id for band in BANDS]
    if len(levels) != len(band_ids):
        raise ValueError("Interpretations count does not match band count.")
    return dict(zip(band_ids, levels, strict=True))


DOMAINS: Sequence[DomainDefinition] = [
    DomainDefinition(
        id="honesty_humility",
        title="Honesty-Humility",
        visibility="public",
        items=[
            DomainItem(1),
            DomainItem(2, True),
            DomainItem(3),
            DomainItem(4, True),
        ],
        interpretations=_interp(
            True,
            [
                "Very low Honesty-Humility signals a transactional mindset—useful for hard bargaining, yet it can trigger distrust quickly.",
                "Low scores show pragmatic self-protection. You stay focused on outcomes but may appear calculating or guarded.",
                "Mid-range indicates situational transparency: you can switch between openness and realism, though signals might seem mixed.",
                "High Honesty-Humility builds trust effortlessly; just watch that you do not give away leverage or boundaries by default.",
                "Very high scores highlight principled, altruistic behavior. People rely on your ethics, but others may overuse your goodwill.",
            ],
        ),
    ),
    DomainDefinition(
        id="neurotism",
        title="Neurotism",
        visibility="public",
        items=[
            DomainItem(5),
            DomainItem(6, True),
            DomainItem(7),
            DomainItem(8, True),
        ],
        interpretations=_interp(
            True,
            [
                "Very low Neurotism means calm and steady under pressure; just watch for blind spots around other people's emotional needs.",
                "Low Neurotism keeps composure with minimal turbulence. Build quick self-checks so unspoken stress does not accumulate.",
                "Mid-range Neurotism balances sensitivity with resilience—expect mood swings here and there, and plan simple recovery rituals.",
                "High Neurotism signals heightened vigilance and emotional charge. Use structure, body anchors, and reality checks to stay grounded.",
                "Very high Neurotism brings deep empathy but also faster overwhelm. Protect sleep, pacing, and social support so intensity remains useful.",
            ],
        ),
    ),
    DomainDefinition(
        id="extraversion",
        title="Extraversion",
        visibility="public",
        items=[
            DomainItem(9),
            DomainItem(10, True),
            DomainItem(11),
            DomainItem(12, True),
        ],
        interpretations=_interp(
            True,
            [
                "Very low Extraversion favors focused solo work; invest extra effort in signaling availability to new partners.",
                "Low scores mean selective social energy. Thoughtful tempo helps, yet cold signals can slow trust.",
                "Mid-range flexes between outreach and recharge. Just clarify your cadence so others know when to engage.",
                "High Extraversion fuels momentum and influence; remember to leave airtime for quiet contributors.",
                "Very high scores indicate constant visibility and drive. Schedule recovery to avoid dominating or burning out.",
            ],
        ),
    ),
    DomainDefinition(
        id="agreeableness",
        title="Agreeableness",
        visibility="public",
        items=[
            DomainItem(13),
            DomainItem(14, True),
            DomainItem(15),
            DomainItem(16, True),
        ],
        interpretations=_interp(
            True,
            [
                "Very low Agreeableness means tough negotiating strength—great for defining boundaries, risky if empathy is absent.",
                "Low scores keep emotions in check and focus on logic. Add a quick acknowledgment of feelings to maintain rapport.",
                "Mid-range balances support with realism. Monitor how fast you toggle so expectations stay clear.",
                "High Agreeableness calms conflict and brings warmth; guard your bandwidth so yeses remain intentional.",
                "Very high scores mobilize communities around care. Pair it with firm limits to prevent emotional overload.",
            ],
        ),
    ),
    DomainDefinition(
        id="conscientiousness",
        title="Conscientiousness",
        visibility="public",
        items=[
            DomainItem(17),
            DomainItem(18, True),
            DomainItem(19),
            DomainItem(20, True),
        ],
        interpretations=_interp(
            True,
            [
                "Very low Conscientiousness favors improvisation and rapid pivots; set lightweight checkpoints so chaos stays useful.",
                "Low scores value freedom of schedule. Watch recurring delays by adding simple external cues.",
                "Mid-range blends planning with spontaneity. Double-check long projects where structure fades over time.",
                "High Conscientiousness sustains quality and reliability; practice flexible re-planning for surprise events.",
                "Very high scores reflect meticulous control. Great for standards, but perfectionism can squeeze recovery.",
            ],
        ),
    ),
    DomainDefinition(
        id="openness",
        title="Openness to Experience",
        visibility="public",
        items=[
            DomainItem(21),
            DomainItem(22, True),
            DomainItem(23),
            DomainItem(24, True),
        ],
        interpretations=_interp(
            True,
            [
                "Very low Openness prizes proven playbooks. Build deliberate windows for new data so you do not miss emerging signals.",
                "Low scores mean careful adoption of change. Let trusted peers curate experiments to shorten the learning curve.",
                "Mid-range toggles between standards and novelty. Clarify which mode you are in to avoid half-finished ideas.",
                "High Openness fuels creativity and reframing; pair it with decision cadences to land commitments.",
                "Very high scores chase new inputs constantly. Anchor on a few priorities so iteration still ships.",
            ],
        ),
    ),
]


class HexacoEngine:
    """Расчёт баллов и интерпретаций HEXACO (two-facet)."""

    answer_range = (1, 2, 3, 4, 5)

    def __init__(self, domains: Sequence[DomainDefinition] | None = None) -> None:
        self.domains = domains or DOMAINS
        self.statements = STATEMENTS

    def total_questions(self) -> int:
        return len(self.statements)

    def get_statement(self, index: int) -> Statement:
        return self.statements[index]

    def calculate(self, answers: Dict[int, int]) -> List[HexacoResult]:
        self._validate_answers(answers)
        results: List[HexacoResult] = []
        for domain in self.domains:
            percent = self._calculate_percent(domain, answers)
            band = self._resolve_band(percent)
            interpretation = domain.interpretations.get(band.id, "")
            results.append(
                HexacoResult(
                    domain_id=domain.id,
                    title=domain.title,
                    percent=percent,
                    band_id=band.id,
                    band_label=band.label,
                    interpretation=interpretation,
                    visibility=domain.visibility,
                )
            )
        return results

    def _validate_answers(self, answers: Dict[int, int]) -> None:
        missing = {item.id for item in self.statements} - set(answers.keys())
        if missing:
            raise ValueError(f"Missing answers for questions: {sorted(missing)}")
        invalid = [
            (statement_id, value)
            for statement_id, value in answers.items()
            if value not in self.answer_range
        ]
        if invalid:
            raise ValueError(f"Invalid answer values: {invalid}")

    def _calculate_percent(
        self, domain: DomainDefinition, answers: Dict[int, int]
    ) -> float:
        total = 0
        for item in domain.items:
            value = answers[item.statement_id]
            total += self._transform_value(value, item.inverted)
        n = len(domain.items)
        # Нормализация: ((S - N) / (4N)) * 100
        percent = ((total - n) / (4 * n)) * 100
        return max(0.0, min(100.0, round(percent, 2)))

    @staticmethod
    def _transform_value(value: int, inverted: bool) -> int:
        return 6 - value if inverted else value

    def _resolve_band(self, percent: float) -> Band:
        for band in BANDS:
            if band.contains(percent):
                return band
        return Band("unknown", "Unknown", 0, 100, True, True)
