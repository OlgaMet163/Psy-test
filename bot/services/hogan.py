from __future__ import annotations

# flake8: noqa: E501

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
        1,
        "Когда в рабочем проекте начинаются сложности, моё напряжение слышно в голосе.",
    ),
    HoganStatement(
        2, "В напряжённые недели небольшие сложности ощущаются сильнее, чем обычно."
    ),
    HoganStatement(3, "Даже когда меня провоцируют, я сохраняю спокойный тон.", True),
    HoganStatement(
        4, "Когда ставки растут, я предпочитаю собрать больше данных перед решением."
    ),
    HoganStatement(5, "Я строю различные запасные планы, прежде чем двигаться дальше."),
    HoganStatement(
        6,
        "Я могу принять решение с неполной информацией и не прокручивать его/тревожиться после.",
        True,
    ),
    HoganStatement(
        7,
        "Когда напряжение в работе растёт, я сокращаю коммуникацию, чтобы сфокусироваться на задаче.",
    ),
    HoganStatement(8, "В период авралов люди замечают, что я менее эмоционален."),
    HoganStatement(
        9,
        "В стрессовые периоды я все равно узнаю, как дела у других, даже если занят.",
        True,
    ),
    HoganStatement(
        10,
        "Когда в коммуникации нарастает напряжение, я возвращаюсь и перепроверяю совместно принятые решения.",
    ),
    HoganStatement(11, "В стрессе я внимательнее присматриваюсь к намерениям других."),
    HoganStatement(
        12,
        "В ситуациях высокого давления я базово считаю, что люди желают мне добра.",
        True,
    ),
    HoganStatement(
        13,
        "Если я не согласен, я могу сначала «кивнуть», а потом вернуться к обсуждению решения.",
    ),
    HoganStatement(
        14,
        "Я продолжаю следовать своему плану молча, даже если внешне согласился с неприятным мне решением.",
    ),
    HoganStatement(
        15,
        "Если я согласился с решением, я следую ему без тихого саботажа.",
        True,
    ),
    HoganStatement(
        16, "В критические моменты я больше доверяю своему мнению, чем мнению группы."
    ),
    HoganStatement(17, "Я могу ревностно защищать решения, на которых стоит моё имя."),
    HoganStatement(
        18, "Под давлением я целенаправленно ищу, где могу ошибаться.", True
    ),
    HoganStatement(
        19,
        "Чтобы быстрее прийти к результату, я пропускаю шаги, которые считаю бюрократией.",
    ),
    HoganStatement(
        20,
        "Когда дедлайны поджимают, мне комфортно идти на просчитанные риски, которых другие избегают.",
    ),
    HoganStatement(
        21,
        "Даже в авральные периоды я избегаю нарушения принятых алгоритмов в процессах.",
        True,
    ),
    HoganStatement(
        22, "В работе с высокими ставками я больше рассказываю о своём прогрессе."
    ),
    HoganStatement(
        23, "Когда давление велико, я стараюсь сделать свой вклад заметным."
    ),
    HoganStatement(
        24,
        "Даже в стрессе я предпочитаю, чтобы моя работа говорила сама за себя и не привлекаю внимание к ней.",
        True,
    ),
    HoganStatement(
        25,
        "В стрессе я рассматриваю задачу под новыми углами, которые ранее не рассматривались.",
    ),
    HoganStatement(
        26, "Я могу увлечься большими идеями и упустить практические ограничения."
    ),
    HoganStatement(
        27,
        "Когда растёт давление, я намеренно опираюсь на проверенные инструкции.",
        True,
    ),
    HoganStatement(
        28,
        "Когда качество критично, я предпочитаю лично изучить или доработать финальный результат.",
    ),
    HoganStatement(
        29,
        "В авральное время я подключаюсь, чтобы убедиться, что детали сделаны верно.",
    ),
    HoganStatement(
        30,
        "Под стрессом я могу делегировать и принять решение, сделанное не так, как сделал бы сам.",
        True,
    ),
    HoganStatement(
        31,
        "Когда ставки высоки, я предпочитаю согласовывать каждое решение с руководством.",
    ),
    HoganStatement(
        32, "Иногда я соглашаюсь слишком быстро, лишь бы не разочаровать людей."
    ),
    HoganStatement(
        33,
        "Под давлением я могу сказать «нет», не нуждаясь в дополнительном одобрении.",
        True,
    ),
    HoganStatement(
        34, "За последний год я не помню, чтобы говорил с кем-то слишком резко."
    ),
    HoganStatement(
        35, "Мне никогда не приходилось извиняться на работе за тон или подход."
    ),
    HoganStatement(36, "Каков бы ни был стресс, я всегда принимаю идеальное решение."),
    HoganStatement(
        37, "Я никогда не чувствовал защитной реакции, получая обратную связь."
    ),
    HoganStatement(
        38, "Я никогда не приносил качество работы в жертву — даже когда времени мало."
    ),
]


SCALE_DEFINITIONS: Sequence[HoganScaleDefinition] = [
    HoganScaleDefinition(
        "VR", "Эмоциональная реактивность", "Эмоциональный", (1, 2, 3)
    ),
    HoganScaleDefinition("WA", "Избегание", "Осторожный", (4, 5, 6)),
    HoganScaleDefinition("IW", "Отстраненность", "Сдержанный", (7, 8, 9)),
    HoganScaleDefinition("CG", "Защитный скепсис", "Скептичный", (10, 11, 12)),
    HoganScaleDefinition("PP", "Пассивное сопротивление", "Непоспешный", (13, 14, 15)),
    HoganScaleDefinition("SI", "Самозначимость", "Самоуверенный", (16, 17, 18)),
    HoganScaleDefinition("BP", "Нарушение границ", "Авантюрный", (19, 20, 21)),
    HoganScaleDefinition("SS", "Жажда внимания", "Яркий", (22, 23, 24)),
    HoganScaleDefinition("UT", "Нетипичное мышление", "Образный", (25, 26, 27)),
    HoganScaleDefinition("PC", "Перфекционизм", "Дотошный", (28, 29, 30)),
    HoganScaleDefinition("AD", "Зависимость от одобрения", "Послушный", (31, 32, 33)),
]

IM_ITEMS: Sequence[int] = (34, 35, 36, 37, 38)

HOGAN_LEVELS: Sequence[Tuple[str, float, float, str]] = (
    ("high", 3.8, 5.0, "Высокий"),
    ("moderate", 3.2, 3.79, "Умеренный"),
    ("low", 1.0, 3.19, "Низкий"),
)

HOGAN_TRAITS_META: Dict[str, Dict[str, str]] = {
    "VR": {
        "description": "эмоционально интенсивный, быстро фиксирует разочарование",
        "risks": "скачки настроения, резкие ответы, импульсивный уход из ситуации",
        "strengths": "быстрая реакция на проблемы, эмоциональная энергия, внимательность к сигналам",
        "low_risks": "может казаться безучастным, недооценивать эмоциональные сигналы других",
        "low_strengths": "ровный тон, устойчивость к стрессу, способность успокаивать",
    },
    "WA": {
        "description": "осторожный, ищет безопасность перед действиями",
        "risks": "паралич анализа, задержки, сильная потребность в подтверждениях",
        "strengths": "чувствительность к рискам, контроль качества, продуманное планирование",
        "low_risks": "поспешные решения без страховки, игнор предупредительных сигналов",
        "low_strengths": "скорость реакции, готовность действовать с минимальными данными",
    },
    "IW": {
        "description": "уходит в себя, чтобы защитить фокус",
        "risks": "эмоциональная дистанция, мало обратной связи, ощущение холодности",
        "strengths": "спокойствие под стрессом, самостоятельная работа, умение не обострять конфликты",
        "low_risks": "перегруз контактами, отвлекаемость, сложнее восстанавливаться в шуме",
        "low_strengths": "доступность, готовность делиться состоянием, тёплая обратная связь",
    },
    "CG": {
        "description": "скептик, сканирует скрытые мотивы",
        "risks": "размывание доверия, циклы обвинений, оборонительный тон",
        "strengths": "проверка фактов, защита стандартов, смелые вопросы",
        "low_risks": "излишняя доверчивость, пропуск скрытых рисков, позднее обнаружение проблем",
        "low_strengths": "доверие по умолчанию, гибкость к чужим идеям, готовность сотрудничать",
    },
    "PP": {
        "description": "выглядит согласным, но сопротивляется скрыто",
        "risks": "тихое торможение, размытые обязательства, скрытое раздражение",
        "strengths": "защита границ, неконфронтационное сопротивление",
        "low_risks": "может идти в открытый конфликт, если не согласен; риск эскалаций",
        "low_strengths": "прозрачность действий, готовность сразу обсуждать возражения",
    },
    "SI": {
        "description": "уверен в себе, стремится быть заметным",
        "risks": "глухота к обратной связи, борьба за статус, излишняя уверенность",
        "strengths": "смелые цели, решительность, умение вдохновлять других",
        "low_risks": "занижение своих достижений, слабая видимость вклада, меньше влияния",
        "low_strengths": "скромность, готовность слушать, фокус на командном результате",
    },
    "BP": {
        "description": "рискующий, может обходить правила",
        "risks": "сомнительные компромиссы, поиск острых ощущений, пробелы в соблюдении требований",
        "strengths": "маневренность в кризисе, смелые эксперименты, чувствительность к обстановке",
        "low_risks": "избегание разумных рисков, замедление из-за страха ошибок",
        "low_strengths": "следование правилам, предсказуемость, надёжность исполнения",
    },
    "SS": {
        "description": "выразительный, тянется к вниманию",
        "risks": "поведение «в центре сцены», драматизация, размывание основного сообщения",
        "strengths": "энергия, сторителлинг, быстрое вовлечение",
        "low_risks": "низкая вовлечённость аудитории, сухое общение, мало эмоционального «топлива»",
        "low_strengths": "фокус на сути, сдержанность, умение не отвлекать от главного",
    },
    "UT": {
        "description": "воображение, быстро переходит к новым углам",
        "risks": "уход от реальности, расплывчатые приоритеты, перегруз идеями",
        "strengths": "переосмысление подходов, креативные прорывы, генерация вариантов",
        "low_risks": "меньше свежих идей, риск застревать в текущей схеме",
        "low_strengths": "опора на факты, прагматичность, последовательность",
    },
    "PC": {
        "description": "перфекционистский контроль",
        "risks": "задержки из-за доработок деталей, микроменеджмент, усталость",
        "strengths": "точность, надёжность, стабильное качество",
        "low_risks": "поспешность, пропуск деталей, вариативное качество",
        "low_strengths": "гибкость, скорость, приемлемый уровень достаточной точности",
    },
    "AD": {
        "description": "ориентирован на одобрение и чувствителен к стейкхолдерам",
        "risks": "перегруз обязательствами, сложность сказать «нет», зависимость от подтверждений",
        "strengths": "сервисный подход, раннее считывание ожиданий, построение коалиций",
        "low_risks": "может игнорировать ожидания других, резкие отказы",
        "low_strengths": "самостоятельность, ясные границы, способность держать курс без одобрения",
    },
}

HOGAN_MODERATE_META: Dict[str, str] = {
    "VR": "Эмоции заметны, но зависят от контекста: можете как сдерживаться, так и реагировать ярче при сильном давлении.",
    "WA": "Осторожность варьируется: в знакомых темах двигаетесь быстрее, в неопределённости замедляетесь и ищете факты.",
    "IW": "Можете чередовать включённость и дистанцию: в фокусе уходите в себя, в спокойной среде даёте больше обратной связи.",
    "CG": "Скепсис ситуативен: больше вопросов, когда ставки высоки, и больше доверия при прозрачных правилах.",
    "PP": "Иногда принимаете решения вслух, иногда откладываете обсуждение; стиль зависит от давления и доверия к людям.",
    "SI": "Проявляете уверенность выборочно: можете занимать центр внимания или уйти в тень, если это полезно для задачи.",
    "BP": "Готовность рисковать зависит от сроков и ставки: экспериментируете там, где видите выгоду, и удерживаете рамки в регламенте.",
    "SS": "То усиливаете заметность, то сохраняете сдержанность — подстраиваетесь под аудиторию и формат задачи.",
    "UT": "Гибко переключаетесь между креативом и прагматикой: добавляете идеи, если есть время, и опираетесь на факты в цейтноте.",
    "PC": "Иногда уходите в детали, иногда ускоряетесь за счёт допуска к «достаточно хорошо» — в зависимости от ценности результата.",
    "AD": "Ищете одобрение по ключевым решениям, но можете действовать автономно, если уверены в курсе или ресурсах.",
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
        # Проверочные пункты IM: считаем долю максимальных (социально-желательных) ответов.
        im_values = [1 if answers[item_id] == 5 else 0 for item_id in IM_ITEMS]
        impression = round(sum(im_values) / len(im_values), 2)  # 0.0–1.0
        return HoganReport(scale_results, impression)

    def _validate_answers(self, answers: Dict[int, int]) -> None:
        missing = {statement.id for statement in self.statements} - set(answers.keys())
        if missing:
            raise ValueError(f"Missing answers for questions: {sorted(missing)}")
        invalid = [
            (statement_id, value)
            for statement_id, value in answers.items()
            if value not in self.answer_range
        ]
        if invalid:
            raise ValueError(f"Invalid answer values: {invalid}")

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
                f"<b>Ключевые риски в стрессе</b>: {risks}."
                f"\n<b>Сильные стороны</b>: {strengths}."
            )
        if level_id == "moderate":
            moderate_text = HOGAN_MODERATE_META.get(
                scale.id, f"{scale.title} проявляется умеренно и зависит от контекста."
            )
            return moderate_text
        if level_id == "low":
            low_risks = meta.get("low_risks", risks)
            low_strengths = meta.get("low_strengths", strengths)
            return (
                f"<b>Ключевые риски в стрессе</b>: {low_risks}."
                f"\n<b>Сильные стороны</b>: {low_strengths}."
            )
        return "Интерпретация недоступна."


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
