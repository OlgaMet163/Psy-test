from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence


@dataclass(frozen=True)
class SvsStatement:
    id: int
    text: str
    value_id: str


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
class ValueDefinition:
    id: str
    title: str
    group_id: str
    statements: Sequence[int]
    interpretations: Dict[str, str]
    visibility: str = "public"


@dataclass(frozen=True)
class GroupDefinition:
    id: str
    title: str
    value_ids: Sequence[str]
    interpretations: Dict[str, str]
    visibility: str = "public"


@dataclass(frozen=True)
class SvsResult:
    domain_id: str
    title: str
    mean_score: float
    percent: float
    band_id: str
    band_label: str
    interpretation: str
    visibility: str
    category: str  # "value" или "group"


STATEMENTS: Sequence[SvsStatement] = [
    SvsStatement(
        1, "If instructions don’t make sense, you propose a better approach.", "SD"
    ),
    SvsStatement(
        2, "You enjoy teaching yourself skills without external deadlines.", "SD"
    ),
    SvsStatement(
        3,
        "Change (new projects/environments) energizes you more than it drains you.",
        "ST",
    ),
    SvsStatement(
        4, "You often choose leisure that includes challenge or a bit of risk.", "ST"
    ),
    SvsStatement(5, "You intentionally build small “treats” into your week.", "HE"),
    SvsStatement(
        6, "“This will feel good” influences your choices even beyond usefulness.", "HE"
    ),
    SvsStatement(
        7,
        "External feedback (ratings, praise, benchmarks) boosts your motivation.",
        "AC",
    ),
    SvsStatement(
        8, "Over the next year, “leveling up” skills/achievements matters to you.", "AC"
    ),
    SvsStatement(9, "You often set priorities for a group without being asked.", "PO"),
    SvsStatement(
        10,
        "You’re comfortable negotiating for what you want, even if it creates tension.",
        "PO",
    ),
    SvsStatement(11, "Backup plans and contingencies help you feel calm.", "SEC"),
    SvsStatement(
        12, "You avoid situations that could “spiral” into chaos or major loss.", "SEC"
    ),
    SvsStatement(
        13, "Doing things according to stated rules/agreements matters to you.", "CO"
    ),
    SvsStatement(
        14, "You often hold back blunt honesty to keep relationships smooth.", "CO"
    ),
    SvsStatement(15, "You like keeping annual rituals consistent year to year.", "TR"),
    SvsStatement(
        16, "“We’ve always done it this way” carries real weight for you.", "TR"
    ),
    SvsStatement(17, "Others tend to rely on you at short notice.", "BE"),
    SvsStatement(
        18, "When someone close is stressed, you quickly shift into support mode.", "BE"
    ),
    SvsStatement(
        19, "You often think about second-order effects on groups or systems.", "UN"
    ),
    SvsStatement(
        20,
        "Ethical/social impact alignment influences which organizations you engage with.",
        "UN",
    ),
]

BANDS: Sequence[Band] = [
    Band("very_low", "Very low", 0, 13, min_inclusive=True),
    Band("low", "Low", 13, 31),
    Band("medium", "Medium", 31, 68),
    Band("high", "High", 68, 87),
    Band("very_high", "Very high", 87, 100),
]


def _interp(levels: Sequence[str]) -> Dict[str, str]:
    band_ids = [band.id for band in BANDS]
    if len(levels) != len(band_ids):
        raise ValueError("Interpretations must match number of bands.")
    return dict(zip(band_ids, levels, strict=True))


VALUE_DEFINITIONS: Sequence[ValueDefinition] = [
    ValueDefinition(
        id="SD",
        title="Self-Direction",
        group_id="openness_change",
        statements=[1, 2],
        interpretations=_interp(
            [
                "Prefers structure over autonomy; may avoid self-directed paths.",
                "Takes direction well but may underuse own ideas.",
                "Balances guidance with independent moves.",
                "Comfortable steering own work and decisions.",
                "Strong drive for autonomy and self-initiated change.",
            ]
        ),
    ),
    ValueDefinition(
        id="ST",
        title="Stimulation",
        group_id="openness_change",
        statements=[3, 4],
        interpretations=_interp(
            [
                "Seeks predictability; may find change de-energizing.",
                "Tolerates some novelty but prefers stability.",
                "Open to change when benefits are clear.",
                "Regularly looks for variety and new challenges.",
                "Actively pursues novelty and risk for energy.",
            ]
        ),
    ),
    ValueDefinition(
        id="HE",
        title="Hedonism",
        group_id="openness_change",
        statements=[5, 6],
        interpretations=_interp(
            [
                "Rarely prioritizes pleasure; focuses on utility and duty.",
                "Pleasure is secondary to function.",
                "Balances enjoyment with practicality.",
                "Deliberately builds enjoyment into routines.",
                "Leads with pleasure signals; protect long-term aims.",
            ]
        ),
    ),
    ValueDefinition(
        id="AC",
        title="Achievement",
        group_id="self_enhancement",
        statements=[7, 8],
        interpretations=_interp(
            [
                "Low focus on advancement; external feedback matters little.",
                "Goal focus rises with context but is moderate.",
                "Steady progress orientation; balances mastery and rest.",
                "Clear growth mindset; feedback energizes improvement.",
                "Highly driven for skill/status gains; watch overextension.",
            ]
        ),
    ),
    ValueDefinition(
        id="PO",
        title="Power",
        group_id="self_enhancement",
        statements=[9, 10],
        interpretations=_interp(
            [
                "Avoids influence roles; prefers harmony over control.",
                "Occasionally steps up but limits conflict.",
                "Comfortable leading when needed.",
                "Readily asserts direction and negotiates for outcomes.",
                "Strong influence motive; manage impact on relationships.",
            ]
        ),
    ),
    ValueDefinition(
        id="SEC",
        title="Security",
        group_id="conservation",
        statements=[11, 12],
        interpretations=_interp(
            [
                "Accepts volatility; low emphasis on safeguards.",
                "Some caution, but risk tolerance is moderate.",
                "Balances contingency thinking with flexibility.",
                "Values stability and proactive risk controls.",
                "Strong security focus; may over-avoid uncertainty.",
            ]
        ),
    ),
    ValueDefinition(
        id="CO",
        title="Conformity",
        group_id="conservation",
        statements=[13, 14],
        interpretations=_interp(
            [
                "Challenges rules; prioritizes candor over harmony.",
                "Selectively follows rules; direct when needed.",
                "Adapts to rules while keeping some flexibility.",
                "Prefers clear rules and smooth interactions.",
                "Strong rule-alignment; may suppress candor to keep peace.",
            ]
        ),
    ),
    ValueDefinition(
        id="TR",
        title="Tradition",
        group_id="conservation",
        statements=[15, 16],
        interpretations=_interp(
            [
                "Little attachment to rituals; favors innovation.",
                "Keeps few traditions; open to change most customs.",
                "Maintains some rituals while updating practices.",
                "Values continuity and repeated rituals.",
                "Deeply anchored in tradition; change needs strong rationale.",
            ]
        ),
    ),
    ValueDefinition(
        id="BE",
        title="Benevolence",
        group_id="self_transcendence",
        statements=[17, 18],
        interpretations=_interp(
            [
                "Rarely steps into immediate support roles.",
                "Offers help when asked; cautious with bandwidth.",
                "Provides support when feasible; balances own needs.",
                "Proactively supports close others under pressure.",
                "Highly reliable for others; watch for overload.",
            ]
        ),
    ),
    ValueDefinition(
        id="UN",
        title="Universalism",
        group_id="self_transcendence",
        statements=[19, 20],
        interpretations=_interp(
            [
                "Low focus on wider impact; prioritizes local goals.",
                "Occasional consideration of broader effects.",
                "Balanced view of personal and societal outcomes.",
                "Often weighs ethical/system effects in choices.",
                "Strong global/ethical lens guiding engagement.",
            ]
        ),
    ),
]

GROUP_DEFINITIONS: Sequence[GroupDefinition] = [
    GroupDefinition(
        id="openness_change",
        title="Openness to Change",
        value_ids=["SD", "ST", "HE"],
        interpretations=_interp(
            [
                "Prefers predictability and externally guided plans.",
                "Leans to stability with some room for novelty.",
                "Balances structure with selective exploration.",
                "Energized by autonomy, novelty, and enjoyment.",
                "Strong change appetite; add guardrails for follow-through.",
            ]
        ),
    ),
    GroupDefinition(
        id="self_enhancement",
        title="Self-Enhancement",
        value_ids=["AC", "PO"],
        interpretations=_interp(
            [
                "Low drive for advancement or influence.",
                "Modest growth focus; influence used sparingly.",
                "Steady achievement and influence when needed.",
                "Clear ambition and readiness to lead.",
                "High status/influence motive; balance with collaboration.",
            ]
        ),
    ),
    GroupDefinition(
        id="conservation",
        title="Conservation",
        value_ids=["SEC", "CO", "TR"],
        interpretations=_interp(
            [
                "Comfort with change outweighs need for stability/rituals.",
                "Some guardrails, but flexibility stays high.",
                "Balances stability, rules, and adaptation.",
                "Values safety, order, and continuity.",
                "Strong conservation; change needs strong justification.",
            ]
        ),
    ),
    GroupDefinition(
        id="self_transcendence",
        title="Self-Transcendence",
        value_ids=["BE", "UN"],
        interpretations=_interp(
            [
                "Focus stays close to personal goals.",
                "Helps when possible; broader impact is secondary.",
                "Balances self-interest with care for others.",
                "Regularly considers others and societal effects.",
                "Strong service/impact lens guiding choices.",
            ]
        ),
    ),
]


class SvsEngine:
    """Расчёт по Schwartz Value Survey (1–7, 20 items)."""

    answer_range = tuple(range(1, 8))

    def __init__(
        self,
        values: Sequence[ValueDefinition] | None = None,
        groups: Sequence[GroupDefinition] | None = None,
        statements: Sequence[SvsStatement] | None = None,
    ) -> None:
        self.values = values or VALUE_DEFINITIONS
        self.groups = groups or GROUP_DEFINITIONS
        self.statements = statements or STATEMENTS
        self._value_map = {value.id: value for value in self.values}
        self._group_map = {group.id: group for group in self.groups}

    def total_questions(self) -> int:
        return len(self.statements)

    def get_statement(self, index: int) -> SvsStatement:
        return self.statements[index]

    def calculate(self, answers: Dict[int, int]) -> List[SvsResult]:
        self._validate_answers(answers)
        value_results = [self._calculate_value(value, answers) for value in self.values]
        group_results = [
            self._calculate_group(group, value_results) for group in self.groups
        ]
        return value_results + group_results

    def _validate_answers(self, answers: Dict[int, int]) -> None:
        missing = {item.id for item in self.statements} - set(answers.keys())
        if missing:
            raise ValueError(f"Не хватает ответов для вопросов: {sorted(missing)}")
        invalid = [
            (statement_id, value)
            for statement_id, value in answers.items()
            if value not in self.answer_range
        ]
        if invalid:
            raise ValueError(f"Некорректные значения ответов: {invalid}")

    def _calculate_value(
        self, definition: ValueDefinition, answers: Dict[int, int]
    ) -> SvsResult:
        mean_score = self._mean_for_statements(definition.statements, answers)
        percent = self._mean_to_percent(mean_score)
        band = self._resolve_band(percent)
        interpretation = definition.interpretations.get(band.id, "")
        return SvsResult(
            domain_id=definition.id,
            title=definition.title,
            mean_score=mean_score,
            percent=percent,
            band_id=band.id,
            band_label=band.label,
            interpretation=interpretation,
            visibility=definition.visibility,
            category="value",
        )

    def _calculate_group(
        self, definition: GroupDefinition, value_results: Sequence[SvsResult]
    ) -> SvsResult:
        relevant = [
            res for res in value_results if res.domain_id in definition.value_ids
        ]
        if not relevant:
            raise ValueError(f"Не найдены значения для группы {definition.id}")
        mean_score = round(
            sum(result.mean_score for result in relevant) / len(relevant), 2
        )
        percent = self._mean_to_percent(mean_score)
        band = self._resolve_band(percent)
        interpretation = definition.interpretations.get(band.id, "")
        return SvsResult(
            domain_id=f"group_{definition.id}",
            title=definition.title,
            mean_score=mean_score,
            percent=percent,
            band_id=band.id,
            band_label=band.label,
            interpretation=interpretation,
            visibility=definition.visibility,
            category="group",
        )

    @staticmethod
    def _mean_for_statements(
        statement_ids: Sequence[int], answers: Dict[int, int]
    ) -> float:
        values = [answers[statement_id] for statement_id in statement_ids]
        return round(sum(values) / len(values), 2)

    @staticmethod
    def _mean_to_percent(mean_score: float) -> float:
        return max(0.0, min(100.0, round(((mean_score - 1) / 6) * 100, 2)))

    def _resolve_band(self, percent: float) -> Band:
        for band in BANDS:
            if band.contains(percent):
                return band
        return Band("unknown", "Unknown", 0, 100, True, True)
