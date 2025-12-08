from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Sequence, Tuple, Set


@dataclass(frozen=True)
class HoganStatement:
    id: int
    text: str
    reverse: bool = False


@dataclass(frozen=True)
class HoganScaleDefinition:
    id: str
    title: str
    hds_label: str
    statement_ids: Sequence[int]


@dataclass(frozen=True)
class HoganScaleResult:
    scale_id: str
    title: str
    hds_label: str
    mean_score: float
    percent: float
    level_id: str
    level_label: str
    interpretation: str
    visibility: str = "public"

    @property
    def domain_id(self) -> str:
        return self.scale_id

    @property
    def band_id(self) -> str:
        return self.level_id

    @property
    def band_label(self) -> str:
        return self.level_label


@dataclass(frozen=True)
class CoachingBlock:
    style: str  # "paragraph" | "bullet"
    items: List[str]


@dataclass
class CoachingAggregate:
    style: str
    items: List[str]
    seen: Set[str]


@dataclass(frozen=True)
class HoganReport:
    scales: List[HoganScaleResult]
    impression_management: float


STATEMENTS: Sequence[HoganStatement] = [
    HoganStatement(
        1, "When a project hits turbulence, my urgency shows up in my tone."
    ),
    HoganStatement(2, "In tense weeks, small setbacks feel bigger than they should."),
    HoganStatement(3, "Even when provoked, I keep my tone measured.", True),
    HoganStatement(
        4, "When stakes rise, I prefer to gather extra data before committing."
    ),
    HoganStatement(5, "I build contingency plans before I feel comfortable moving."),
    HoganStatement(
        6,
        "I can make a call with incomplete information without replaying it afterward.",
        True,
    ),
    HoganStatement(7, "When pressure climbs, I reduce conversation to stay focused."),
    HoganStatement(
        8, "During crunch time, people may notice I'm harder to read emotionally."
    ),
    HoganStatement(
        9,
        "In stressful periods, I intentionally check in with others even if I'm busy.",
        True,
    ),
    HoganStatement(10, "When things get political, I prefer agreements in writing."),
    HoganStatement(11, "Under stress, I scrutinize others’ intentions more carefully."),
    HoganStatement(
        12, "In high-pressure situations, I assume most people mean well.", True
    ),
    HoganStatement(
        13, "If I disagree, I may comply first and revisit the decision later."
    ),
    HoganStatement(
        14, "When I feel pushed, I stick to my interpretation of the request."
    ),
    HoganStatement(
        15,
        "If I commit to an approach I dislike, I follow through without quiet resistance.",
        True,
    ),
    HoganStatement(
        16, "In critical moments, I trust my judgment more than group consensus."
    ),
    HoganStatement(17, "I can get protective of decisions that have my name on them."),
    HoganStatement(
        18, "Under pressure, I actively look for evidence that I might be wrong.", True
    ),
    HoganStatement(
        19, "To keep momentum, I sometimes bypass steps that feel bureaucratic."
    ),
    HoganStatement(
        20, "When deadlines bite, I'm comfortable taking calculated risks others avoid."
    ),
    HoganStatement(21, "Even in crunch time, I avoid bending process rules.", True),
    HoganStatement(
        22, "In high-stakes work, I increase how much I communicate my progress."
    ),
    HoganStatement(
        23, "When pressure is high, I work harder to make my contributions visible."
    ),
    HoganStatement(
        24,
        "When stressed, I'm fine letting results speak without drawing attention.",
        True,
    ),
    HoganStatement(
        25, "Under stress, I jump to novel angles others haven't considered."
    ),
    HoganStatement(
        26, "I can get absorbed in big ideas and lose track of practical constraints."
    ),
    HoganStatement(
        27, "When pressure rises, I deliberately anchor on concrete facts.", True
    ),
    HoganStatement(
        28,
        "When quality matters, I prefer to personally review or refine the final output.",
    ),
    HoganStatement(
        29, "In crunch time, I step in to ensure details are handled correctly."
    ),
    HoganStatement(
        30,
        "When stressed, I can delegate and accept solutions done differently than I would.",
        True,
    ),
    HoganStatement(
        31, "When stakes are high, I seek early alignment from key stakeholders."
    ),
    HoganStatement(32, "I may say yes quickly to avoid disappointing people."),
    HoganStatement(
        33, "Under pressure, I can say no without needing reassurance.", True
    ),
    HoganStatement(
        34, "In the last year, I can't recall a situation where I spoke too sharply."
    ),
    HoganStatement(35, "I've never had to apologize at work for my tone or approach."),
    HoganStatement(
        36, "No matter the stress level, I always make the perfect decision."
    ),
    HoganStatement(37, "I have never felt defensive when receiving feedback."),
    HoganStatement(38, "I never cut corners—ever—even when time is tight."),
]


SCALE_DEFINITIONS: Sequence[HoganScaleDefinition] = [
    HoganScaleDefinition("VR", "Volatile Reactivity", "Excitable", (1, 2, 3)),
    HoganScaleDefinition("WA", "Worry-Driven Avoidance", "Cautious", (4, 5, 6)),
    HoganScaleDefinition("IW", "Interpersonal Withdrawal", "Reserved", (7, 8, 9)),
    HoganScaleDefinition("CG", "Cynical Guardedness", "Skeptical", (10, 11, 12)),
    HoganScaleDefinition("PP", "Passive Pushback", "Leisurely", (13, 14, 15)),
    HoganScaleDefinition("SI", "Self-Importance", "Bold", (16, 17, 18)),
    HoganScaleDefinition("BP", "Boundary-Pushing", "Mischievous", (19, 20, 21)),
    HoganScaleDefinition("SS", "Spotlight Seeking", "Colorful", (22, 23, 24)),
    HoganScaleDefinition("UT", "Unconventional Thinking", "Imaginative", (25, 26, 27)),
    HoganScaleDefinition("PC", "Perfectionistic Control", "Diligent", (28, 29, 30)),
    HoganScaleDefinition("AD", "Approval Dependence", "Dutiful", (31, 32, 33)),
]

IM_ITEMS: Sequence[int] = (34, 35, 36, 37, 38)

HOGAN_LEVELS: Sequence[Tuple[str, float, float, str]] = (
    ("high", 3.8, 5.0, "High"),
    ("moderate", 3.2, 3.79, "Moderate"),
    ("low", 1.0, 3.19, "Low"),
)

HOGAN_TRAITS_META: Dict[str, Dict[str, str]] = {
    "VR": {
        "description": "emotionally intense, quick to register disappointment",
        "risks": "mood swings, impulsive exits, burning bridges",
        "strengths": "passion, early risk detection, relational standards",
    },
    "WA": {
        "description": "cautious, seeks safety before acting",
        "risks": "analysis paralysis, delay, heavy reassurance needs",
        "strengths": "risk sensing, quality control, thoughtful planning",
    },
    "IW": {
        "description": "withdraws to protect focus",
        "risks": "emotional distance, sparse feedback, perceived coldness",
        "strengths": "calm under stress, independent work, neutrality in conflict",
    },
    "CG": {
        "description": "skeptical, scans for hidden agendas",
        "risks": "trust erosion, accusation loops, defensive tone",
        "strengths": "due diligence, standards defense, fearless questioning",
    },
    "PP": {
        "description": "appears agreeable while resisting covertly",
        "risks": "quiet derailment, vague commitments, simmering resentment",
        "strengths": "boundary protection, non-confrontational pushback",
    },
    "SI": {
        "description": "self-confident, visibility-seeking",
        "risks": "feedback blindness, status battles, overconfidence",
        "strengths": "bold goals, decisive calls, inspirational presence",
    },
    "BP": {
        "description": "risk-taking rule bender",
        "risks": "ethical shortcuts, thrill seeking, compliance gaps",
        "strengths": "agility in crisis, bold experimentation, political savvy",
    },
    "SS": {
        "description": "expressive, craves spotlight",
        "risks": "center-stage behavior, drama, message dilution",
        "strengths": "energy, storytelling, rapid engagement",
    },
    "UT": {
        "description": "imaginative, jumps to novel angles",
        "risks": "drifting from reality, loose priorities, idea overload",
        "strengths": "strategy reframes, creative breakthroughs, future spotting",
    },
    "PC": {
        "description": "perfectionistic controller",
        "risks": "bottlenecks, micromanagement, fatigue",
        "strengths": "precision, reliability, process excellence",
    },
    "AD": {
        "description": "approval-seeking and stakeholder-sensitive",
        "risks": "overcommitment, difficulty saying no, dependency on reassurance",
        "strengths": "service mindset, early expectation sensing, coalition building",
    },
}

COACHING_HEADINGS: Dict[str, Tuple[str, str]] = {
    "VR": ("##", "Excitable (high score)"),
    "WA": ("##", "Cautious (high score)"),
    "IW": ("##", "Reserved (high score)"),
    "CG": ("##", "Skeptical (high score)"),
    "PP": ("##", "Leisurely (high score)"),
    "SI": ("##", "Bold (high score)"),
    "BP": ("##", "Mischievous (high score)"),
    "SS": ("##", "Colorful (high score)"),
    "UT": ("##", "Imaginative (high score)"),
    "PC": ("##", "Diligent (high score)"),
    "AD": ("##", "Dutiful (high score)"),
}

SPORTS_HEADINGS: Dict[str, Tuple[str, str]] = {
    "VR": ("###", "Excitable (High)"),
    "WA": ("###", "Cautious (High)"),
    "IW": ("###", "Reserved (High)"),
    "CG": ("###", "Skeptical (High)"),
    "PP": ("###", "Leisurely (High)"),
    "SI": ("###", "Bold (High)"),
    "BP": ("###", "Mischievous (High)"),
    "SS": ("###", "Colorful (High)"),
    "UT": ("###", "Imaginative (High)"),
    "PC": ("###", "Diligent (High)"),
    "AD": ("###", "Dutiful (High)"),
}


class HoganEngine:
    """Расчёт шкал Hogan DSUSI-SF."""

    answer_range = (1, 2, 3, 4, 5)

    def __init__(
        self,
        scales: Sequence[HoganScaleDefinition] | None = None,
        statements: Sequence[HoganStatement] | None = None,
    ) -> None:
        self.scales = scales or SCALE_DEFINITIONS
        self.statements = statements or STATEMENTS
        self._statements_map = {
            statement.id: statement for statement in self.statements
        }

    def total_questions(self) -> int:
        return len(self.statements)

    def get_statement(self, index: int) -> HoganStatement:
        return self.statements[index]

    def calculate(self, answers: Dict[int, int]) -> HoganReport:
        self._validate_answers(answers)
        scale_results: List[HoganScaleResult] = []
        for scale in self.scales:
            values = [
                self._transform_value(answers[item_id], item_id)
                for item_id in scale.statement_ids
            ]
            mean_score = round(sum(values) / len(values), 2)
            percent = self._to_percent(mean_score)
            level_id, level_label = self._resolve_level(mean_score)
            meta = HOGAN_TRAITS_META[scale.id]
            interpretation = self._build_interpretation(scale, meta, level_id)
            scale_results.append(
                HoganScaleResult(
                    scale_id=scale.id,
                    title=scale.title,
                    hds_label=scale.hds_label,
                    mean_score=mean_score,
                    percent=percent,
                    level_id=level_id,
                    level_label=level_label,
                    interpretation=interpretation,
                )
            )
        im_values = [
            self._transform_value(answers[item_id], item_id) for item_id in IM_ITEMS
        ]
        impression = round(sum(im_values) / len(im_values), 2)
        return HoganReport(scale_results, impression)

    def _validate_answers(self, answers: Dict[int, int]) -> None:
        missing = {statement.id for statement in self.statements} - set(answers.keys())
        if missing:
            raise ValueError(f"Не хватает ответов для вопросов: {sorted(missing)}")
        invalid = [
            (statement_id, value)
            for statement_id, value in answers.items()
            if value not in self.answer_range
        ]
        if invalid:
            raise ValueError(f"Некорректные значения ответов: {invalid}")

    def _transform_value(self, value: int, statement_id: int) -> int:
        statement = self._statements_map[statement_id]
        return 6 - value if statement.reverse else value

    @staticmethod
    def _to_percent(mean_score: float) -> float:
        return round(((mean_score - 1) / 4) * 100, 2)

    @staticmethod
    def _resolve_level(mean_score: float) -> Tuple[str, str]:
        for level_id, min_value, max_value, label in HOGAN_LEVELS:
            if min_value <= mean_score <= max_value:
                return level_id, label
        return "unknown", "Неизвестно"

    @staticmethod
    def _build_interpretation(
        scale: HoganScaleDefinition,
        meta: Dict[str, str],
        level_id: str,
    ) -> str:
        description = meta["description"]
        risks = meta["risks"]
        strengths = meta["strengths"]
        if level_id == "high":
            return (
                f"High {scale.title} ({scale.hds_label}) means {description}. "
                f"Under stress the main watch-outs are {risks}. "
                f"Anchor the strength side: {strengths}."
            )
        if level_id == "moderate":
            return (
                f"Moderate {scale.title} ({scale.hds_label}) shows the pattern surfaces situationally."
                f" Under heavy load it can slide into {risks}, so set guardrails early."
                f" Keep the upside available: {strengths}."
            )
        if level_id == "low":
            return (
                f"Low {scale.title} ({scale.hds_label}) means {description} rarely drives your style."
                f" That lowers risks such as {risks}, yet make sure you can still access {strengths} when needed."
            )
        return "Interpretation is unavailable."


class HoganInsights:
    """Извлекает выдержки из методических файлов Hogan."""

    def __init__(
        self,
        coaching_path: Path | None = None,
        sports_path: Path | None = None,
    ) -> None:
        base_dir = Path(__file__).resolve().parents[2]
        self.coaching_path = Path(
            coaching_path or (base_dir / "docs" / "Hogan and coaching.md")
        )
        self.sports_path = Path(
            sports_path or (base_dir / "docs" / "Hogan and sports.md")
        )
        self._coaching_sections: Dict[str, Dict[str, CoachingBlock]] = {}
        self._coaching_heading_order: List[str] = []

    def get_excerpt(self, trait_id: str, context: str, max_chars: int = 1800) -> str:
        if context == "coaching":
            heading = COACHING_HEADINGS.get(trait_id)
            source_text = self._load_text(self.coaching_path)
        else:
            heading = SPORTS_HEADINGS.get(trait_id)
            source_text = self._load_text(self.sports_path)
        if not heading:
            return ""
        level_token, title = heading
        raw_section = self._extract_section(source_text, level_token, title)
        return self._prepare_excerpt(raw_section, max_chars)

    def build_coaching_guide(self, trait_ids: Sequence[str]) -> str:
        if not trait_ids:
            return ""
        aggregated: Dict[str, CoachingAggregate] = {}
        for trait_id in trait_ids:
            blocks = self._get_coaching_blocks(trait_id)
            if not blocks:
                continue
            for heading, block in blocks.items():
                entry = aggregated.setdefault(
                    heading,
                    CoachingAggregate(style=block.style, items=[], seen=set()),
                )
                for item in block.items:
                    normalized = self._normalize_item(item)
                    if normalized in entry.seen:
                        continue
                    entry.items.append(item.strip())
                    entry.seen.add(normalized)

        if not aggregated:
            return ""

        lines: List[str] = []
        for heading in self._coaching_heading_order:
            entry = aggregated.get(heading)
            if not entry or not entry.items:
                continue
            lines.append(f"<b>{heading}</b>")
            rendered_items = (
                entry.items
                if entry.style == "bullet"
                else self._paragraphs_to_bullets(entry.items)
            )
            for item in rendered_items:
                lines.append(f"• {item}")
            lines.append("")

        if not lines:
            for heading, entry in aggregated.items():
                if not entry.items:
                    continue
                lines.append(f"<b>{heading}</b>")
                rendered_items = (
                    entry.items
                    if entry.style == "bullet"
                    else self._paragraphs_to_bullets(entry.items)
                )
                for item in rendered_items:
                    lines.append(f"• {item}")
                lines.append("")

        return "\n".join(lines).strip()

    @staticmethod
    @lru_cache(maxsize=4)
    def _load_text(path: Path) -> str:
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _extract_section(text: str, heading_prefix: str, title: str) -> str:
        pattern = re.compile(
            rf"^{re.escape(heading_prefix)}\s+{re.escape(title)}\s*$", re.MULTILINE
        )
        match = pattern.search(text)
        if not match:
            return ""
        start = match.end()
        # Следующий заголовок того же уровня
        pattern_next = re.compile(rf"^{re.escape(heading_prefix)}\s+", re.MULTILINE)
        next_match = pattern_next.search(text, pos=start)
        end = next_match.start() if next_match else len(text)
        return text[start:end].strip()

    @staticmethod
    def _prepare_excerpt(section: str, max_chars: int) -> str:
        if not section:
            return ""
        cleaned = section.strip()
        cleaned = (
            cleaned.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        cleaned = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", cleaned)
        if len(cleaned) <= max_chars:
            return cleaned
        trimmed = cleaned[:max_chars]
        cutoff = trimmed.rfind("\n\n")
        if cutoff > max_chars * 0.6:
            trimmed = trimmed[:cutoff]
        return trimmed.rstrip() + "\n…"

    def _get_coaching_blocks(self, trait_id: str) -> Dict[str, CoachingBlock]:
        if trait_id not in self._coaching_sections:
            heading = COACHING_HEADINGS.get(trait_id)
            if not heading:
                self._coaching_sections[trait_id] = {}
            else:
                level_token, title = heading
                source_text = self._load_text(self.coaching_path)
                raw_section = self._extract_section(source_text, level_token, title)
                self._coaching_sections[trait_id] = self._parse_coaching_section(
                    raw_section
                )
        return self._coaching_sections.get(trait_id, {})

    def _parse_coaching_section(self, section: str) -> Dict[str, CoachingBlock]:
        if not section:
            return {}
        pattern = re.compile(r"\*\*(.+?)\*\*\s*:?", re.MULTILINE)
        matches = list(pattern.finditer(section))
        if not matches:
            return {}
        blocks: Dict[str, CoachingBlock] = {}
        for idx, match in enumerate(matches):
            heading = match.group(1).strip()
            start = match.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(section)
            body = section[start:end].strip()
            block = self._build_coaching_block(body)
            if not block:
                continue
            blocks[heading] = block
            self._register_coaching_heading(heading)
        return blocks

    def _build_coaching_block(self, body: str) -> CoachingBlock | None:
        if not body:
            return None
        has_bullets = any(
            line.strip().startswith("- ") for line in body.splitlines() if line.strip()
        )
        if has_bullets:
            items: List[str] = []
            for line in body.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith("- "):
                    items.append(stripped[2:].strip())
                elif items:
                    items[-1] = f"{items[-1]} {stripped}"
            cleaned = [self._collapse_whitespace(item) for item in items if item]
            if cleaned:
                return CoachingBlock("bullet", cleaned)
            return None

        statements = self._split_text_to_bullets(body)
        if statements:
            return CoachingBlock("bullet", statements)
        return None

    def _register_coaching_heading(self, heading: str) -> None:
        if heading not in self._coaching_heading_order:
            self._coaching_heading_order.append(heading)

    @staticmethod
    def _collapse_whitespace(text: str) -> str:
        return " ".join(text.split())

    @staticmethod
    def _normalize_item(text: str) -> str:
        return " ".join(text.split()).strip().lower()

    def _paragraphs_to_bullets(self, paragraphs: Sequence[str]) -> List[str]:
        items: List[str] = []
        for paragraph in paragraphs:
            items.extend(self._split_text_to_bullets(paragraph))
        return items

    def _split_text_to_bullets(self, text: str) -> List[str]:
        if not text:
            return []
        normalized = text.strip()
        if not normalized:
            return []
        chunks = re.split(r"\n+\s*", normalized)
        sentences: List[str] = []
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            parts = re.split(r";|\.\s+(?=[A-ZА-Я])", chunk)
            for part in parts:
                clean = part.strip(" -—.;,")
                if not clean:
                    continue
                collapsed = self._collapse_whitespace(clean)
                if self._is_separator(collapsed):
                    continue
                sentences.append(collapsed)
        return sentences

    def source_name(self, context: str) -> str:
        return (
            self.coaching_path.name if context == "coaching" else self.sports_path.name
        )

    @staticmethod
    def _is_separator(text: str) -> bool:
        if not text:
            return True
        stripped = text.strip()
        if not stripped:
            return True
        return all(ch in "-—–_" for ch in stripped)
