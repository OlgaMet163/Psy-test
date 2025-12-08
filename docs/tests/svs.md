# Schwartz Value Survey (SVS)

## Назначение
- Оценка ценностных приоритетов по 10 базовым ценностям Шварца (Self-Direction, Stimulation, Hedonism, Achievement, Power, Security, Conformity, Tradition, Benevolence, Universalism).
- Дополнительно считаются 4 укрупнённые группы: Openness to Change, Self-Enhancement, Conservation, Self-Transcendence.

## Формат прохождения
- 20 утверждений на английском, порядок фиксированный.
- Шкала ответов 1–7 (1 = Not at all true of me; 7 = Very true of me).
- В боте показываем вопросы и кнопки на английском; пользователь видит промежуточный прогресс.

## Алгоритм расчёта
1. Для каждого утверждения фиксируем ответ в диапазоне 1–7.
2. Для каждой ценности (код): считаем среднее своих утверждений → `mean`.
3. Перевод в проценты: `percent = ((mean - 1) / 6) * 100`, округляем до 2 знаков.
4. Интервалы (используются в прогресс-баре и подписях):
   - `[0; 13]` — Very low
   - `(13; 31]` — Low
   - `(31; 68]` — Medium
   - `(68; 87]` — High
   - `(87; 100]` — Very high
5. Группы (4 шт.): среднее арифметическое mean по входящим ценностям, затем перевод в проценты по формуле выше.
6. В БД сохраняем проценты и видимость (все публичные). Mean восстанавливается из процента при выдаче результата.

## Кнопки ответов (1–7)
1. Not at all true of me  
2. Rarely true of me  
3. Occasionally true of me  
4. Sometimes true of me  
5. Often true of me  
6. Usually true of me  
7. Very true of me  

## Утверждения и коды
- Openness to Change  
  1. If instructions don’t make sense, you propose a better approach. (SD)  
  2. You enjoy teaching yourself skills without external deadlines. (SD)  
  3. Change (new projects/environments) energizes you more than it drains you. (ST)  
  4. You often choose leisure that includes challenge or a bit of risk. (ST)  
  5. You intentionally build small “treats” into your week. (HE)  
  6. “This will feel good” influences your choices even beyond usefulness. (HE)  
- Self-Enhancement  
  7. External feedback (ratings, praise, benchmarks) boosts your motivation. (AC)  
  8. Over the next year, “leveling up” skills/achievements matters to you. (AC)  
  9. You often set priorities for a group without being asked. (PO)  
  10. You’re comfortable negotiating for what you want, even if it creates tension. (PO)  
- Conservation  
  11. Backup plans and contingencies help you feel calm. (SEC)  
  12. You avoid situations that could “spiral” into chaos or major loss. (SEC)  
  13. Doing things according to stated rules/agreements matters to you. (CO)  
  14. You often hold back blunt honesty to keep relationships smooth. (CO)  
  15. You like keeping annual rituals consistent year to year. (TR)  
  16. “We’ve always done it this way” carries real weight for you. (TR)  
- Self-Transcendence  
  17. Others tend to rely on you at short notice. (BE)  
  18. When someone close is stressed, you quickly shift into support mode. (BE)  
  19. You often think about second-order effects on groups or systems. (UN)  
  20. Ethical/social impact alignment influences which organizations you engage with. (UN)  

## Группы (агрегация mean ценностей)
- Openness to Change = SD, ST, HE  
- Self-Enhancement = AC, PO  
- Conservation = SEC, CO, TR  
- Self-Transcendence = BE, UN  

## Вывод результатов
- Публично показываем все 10 ценностей и 4 группы: mean (/7), percent, диапазон, краткая интерпретация.
- Прогресс-бар окрашен по диапазону (very_low/low → красный, medium → жёлтый, high/very_high → зелёный).
