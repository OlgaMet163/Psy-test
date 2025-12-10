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
        1, "Если инструкции кажутся нелогичными, вы предлагаете способ получше.", "SD"
    ),
    SvsStatement(
        2, "Вам нравится учиться навыкам самостоятельно, без внешних дедлайнов.", "SD"
    ),
    SvsStatement(
        3,
        "Изменения (новые проекты/среды) скорее заряжают вас, чем выматывают.",
        "ST",
    ),
    SvsStatement(4, "Вы часто выбираете досуг с вызовом или долей риска.", "ST"),
    SvsStatement(5, "Вы намеренно добавляете маленькие «радости» в неделю.", "HE"),
    SvsStatement(
        6, "«Это будет приятно» влияет на ваши решения даже сверх пользы.", "HE"
    ),
    SvsStatement(
        7,
        "Внешняя обратная связь (оценки, похвала, бенчмарки) поднимает мотивацию.",
        "AC",
    ),
    SvsStatement(
        8, "В ближайший год для вас важен «апгрейд» навыков и достижений.", "AC"
    ),
    SvsStatement(9, "Вы часто расставляете приоритеты для группы без просьбы.", "PO"),
    SvsStatement(
        10,
        "Вам комфортно добиваться своего в переговорах, даже если это создаёт напряжение.",
        "PO",
    ),
    SvsStatement(
        11, "Запасные планы и альтернативы помогают вам сохранять спокойствие.", "SEC"
    ),
    SvsStatement(
        12,
        "Вы избегаете ситуаций, которые могут «раскрутиться» в хаос или крупный ущерб.",
        "SEC",
    ),
    SvsStatement(
        13, "Вам важно делать всё по установленным правилам и договорённостям.", "CO"
    ),
    SvsStatement(
        14, "Вы часто сглаживаете прямоту, чтобы удерживать отношения ровными.", "CO"
    ),
    SvsStatement(
        15, "Вам нравится, когда ежегодные ритуалы остаются неизменными.", "TR"
    ),
    SvsStatement(16, "«Мы всегда делали так» для вас имеет вес.", "TR"),
    SvsStatement(17, "Другие часто рассчитывают на вас в короткий срок.", "BE"),
    SvsStatement(
        18,
        "Когда близкий человек в стрессе, вы быстро переключаетесь в режим поддержки.",
        "BE",
    ),
    SvsStatement(
        19, "You often think about second-order effects on groups or systems.", "UN"
    ),
    SvsStatement(
        20,
        "Этическое и социальное влияние влияет на выбор организаций, с которыми вы работаете.",
        "UN",
    ),
]

BANDS: Sequence[Band] = [
    Band("very_low", "Очень низкий", 0, 13, min_inclusive=True),
    Band("low", "Низкий", 13, 31),
    Band("medium", "Средний", 31, 68),
    Band("high", "Высокий", 68, 87),
    Band("very_high", "Очень высокий", 87, 100),
]


def _interp(levels: Sequence[str]) -> Dict[str, str]:
    band_ids = [band.id for band in BANDS]
    if len(levels) != len(band_ids):
        raise ValueError("Interpretations must match number of bands.")
    return dict(zip(band_ids, levels, strict=True))


VALUE_DEFINITIONS: Sequence[ValueDefinition] = [
    ValueDefinition(
        id="SD",
        title="Самоопределение",
        group_id="openness_change",
        statements=[1, 2],
        interpretations=_interp(
            [
                "Предпочитает структуру автономии; может избегать самонаправленных путей.",
                "Хорошо следует указаниям, но может недоиспользовать собственные идеи.",
                "Балансирует руководство и самостоятельные шаги.",
                "Уверенно управляет своей работой и решениями.",
                "Сильное стремление к автономии и изменениям по собственной инициативе.",
            ]
        ),
    ),
    ValueDefinition(
        id="ST",
        title="Стимуляция",
        group_id="openness_change",
        statements=[3, 4],
        interpretations=_interp(
            [
                "Ищет предсказуемость; перемены обессиливают.",
                "Терпит новизну, но предпочитает стабильность.",
                "Открыт к переменам, когда выгоды ясны.",
                "Регулярно ищет разнообразие и новые вызовы.",
                "Активно преследует новизну и риск ради энергии.",
            ]
        ),
    ),
    ValueDefinition(
        id="HE",
        title="Гедонизм",
        group_id="openness_change",
        statements=[5, 6],
        interpretations=_interp(
            [
                "Редко ставит удовольствие на первое место; фокус на пользе и долге.",
                "Удовольствие вторично по сравнению с функцией.",
                "Балансирует удовольствие и практичность.",
                "Осознанно добавляет удовольствие в рутины.",
                "Ставит удовольствие во главе; следите за долгосрочными целями.",
            ]
        ),
    ),
    ValueDefinition(
        id="AC",
        title="Достижения",
        group_id="self_enhancement",
        statements=[7, 8],
        interpretations=_interp(
            [
                "Низкий фокус на продвижении; внешняя оценка мало влияет.",
                "Цели растут по ситуации, но умеренно.",
                "Стабильная ориентация на прогресс; баланс мастерства и отдыха.",
                "Явный рост-мышление; обратная связь заряжает улучшения.",
                "Сильный драйв к росту статуса и навыков; следите за перегрузом.",
            ]
        ),
    ),
    ValueDefinition(
        id="PO",
        title="Власть",
        group_id="self_enhancement",
        statements=[9, 10],
        interpretations=_interp(
            [
                "Избегает ролей влияния; предпочитает гармонию контролю.",
                "Иногда берёт инициативу, но ограничивает конфликты.",
                "Готов вести при необходимости.",
                "Легко задаёт направление и ведёт переговоры.",
                "Сильный мотив влияния; следите за эффектом на отношения.",
            ]
        ),
    ),
    ValueDefinition(
        id="SEC",
        title="Безопасность",
        group_id="conservation",
        statements=[11, 12],
        interpretations=_interp(
            [
                "Комфорт с волатильностью; мало акцента на защите.",
                "Есть осторожность, но умеренная терпимость к риску.",
                "Балансирует продумывание сценариев и гибкость.",
                "Ценит стабильность и профилактику рисков.",
                "Сильный фокус на безопасности; может чрезмерно избегать неопределённости.",
            ]
        ),
    ),
    ValueDefinition(
        id="CO",
        title="Конформность",
        group_id="conservation",
        statements=[13, 14],
        interpretations=_interp(
            [
                "Оспаривает правила; ставит прямоту выше гармонии.",
                "Выборочно следует правилам; при необходимости прямолинеен.",
                "Адаптируется к правилам, сохраняя гибкость.",
                "Предпочитает ясные правила и ровное общение.",
                "Сильно ориентирован на правила; может подавлять прямоту ради мира.",
            ]
        ),
    ),
    ValueDefinition(
        id="TR",
        title="Традиция",
        group_id="conservation",
        statements=[15, 16],
        interpretations=_interp(
            [
                "Мало привязан к ритуалам; предпочитает инновации.",
                "Сохраняет немного традиций; большинство готов менять.",
                "Удерживает некоторые ритуалы, обновляя практики.",
                "Ценит преемственность и повторяющиеся ритуалы.",
                "Глубоко укоренён в традициях; изменения требуют веских причин.",
            ]
        ),
    ),
    ValueDefinition(
        id="BE",
        title="Доброта",
        group_id="self_transcendence",
        statements=[17, 18],
        interpretations=_interp(
            [
                "Редко сразу включается в поддержку.",
                "Помогает по запросу; бережно расходует ресурс.",
                "Поддерживает, когда возможно; балансирует свои потребности.",
                "Проактивно поддерживает близких под давлением.",
                "Очень надёжен для других; следите за перегрузом.",
            ]
        ),
    ),
    ValueDefinition(
        id="UN",
        title="Универсализм",
        group_id="self_transcendence",
        statements=[19, 20],
        interpretations=_interp(
            [
                "Низкий фокус на широком влиянии; приоритет локальным целям.",
                "Иногда учитывает более широкие эффекты.",
                "Баланс личных и общественных результатов.",
                "Часто взвешивает этические и системные эффекты в решениях.",
                "Сильная глобальная и этическая оптика, направляющая выбор.",
            ]
        ),
    ),
]

GROUP_DEFINITIONS: Sequence[GroupDefinition] = [
    GroupDefinition(
        id="openness_change",
        title="Открытость изменениям",
        value_ids=["SD", "ST", "HE"],
        interpretations=_interp(
            [
                "Предпочитает предсказуемость и внешние планы.",
                "Склонен к стабильности, но оставляет место новизне.",
                "Балансирует структуру и выборочные исследования.",
                "Заряжает автономия, новизна и удовольствие.",
                "Высокая тяга к изменениям; ставьте ограничители для доведения дел.",
            ]
        ),
    ),
    GroupDefinition(
        id="self_enhancement",
        title="Самоутверждение",
        value_ids=["AC", "PO"],
        interpretations=_interp(
            [
                "Низкий драйв к продвижению или влиянию.",
                "Умеренный рост; влияние используется выборочно.",
                "Стабильные достижения и влияние при необходимости.",
                "Явная амбиция и готовность вести.",
                "Сильный мотив статуса и влияния; балансируйте сотрудничеством.",
            ]
        ),
    ),
    GroupDefinition(
        id="conservation",
        title="Сохранение",
        value_ids=["SEC", "CO", "TR"],
        interpretations=_interp(
            [
                "Комфорт с переменами выше потребности в стабильности и ритуалах.",
                "Есть защитные рамки, но гибкость высокая.",
                "Балансирует стабильность, правила и адаптацию.",
                "Ценит безопасность, порядок и преемственность.",
                "Сильная ориентация на сохранение; изменения требуют обоснования.",
            ]
        ),
    ),
    GroupDefinition(
        id="self_transcendence",
        title="Самотрансценденция",
        value_ids=["BE", "UN"],
        interpretations=_interp(
            [
                "Фокус остаётся близко к личным целям.",
                "Помогает, когда возможно; широкий эффект вторичен.",
                "Балансирует личные интересы и заботу о других.",
                "Регулярно учитывает других и общественные эффекты.",
                "Сильная ориентация на сервис и влияние, задающая выбор.",
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
            raise ValueError(f"Missing answers for questions: {sorted(missing)}")
        invalid = [
            (statement_id, value)
            for statement_id, value in answers.items()
            if value not in self.answer_range
        ]
        if invalid:
            raise ValueError(f"Invalid answer values: {invalid}")

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
        return Band("unknown", "Неизвестно", 0, 100, True, True)
