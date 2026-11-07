# Единственное следующее действие — независимый аудит PR #29 (Issue #27, LAB-035)

**Авторская реализация готова к независимому аудиту:** [PR #29](https://github.com/kr13t1/ts-reliability-lab/pull/29) — draft, HEAD `cc342624adb69ff31f44f4c9d1c593496246700e`, **NOT MERGED**. Ветка `fix/issue-27-windows-viewer-portability`. Контракт [WINDOWS_VIEWER_PORTABILITY_CONTRACT_v1](specs/WINDOWS_VIEWER_PORTABILITY_CONTRACT_v1.md). Исходный [Windows diagnostic](diagnostics/WINDOWS_VIEWER_20261107.md) объясняет расхождения.

**Проверки автора/CI:** 8/8 GitHub checks success, в том числе Ubuntu/Windows Python 3.11 и 3.13 для raw-independent viewer tests. Интеграционные тесты, зависящие от настоящих `g23/example` и локально сгенерированного `output_g24`, на GitHub **SKIPPED**, их нельзя засчитывать как запущенные. Авторский тест/CI не равен независимому 05.

**Ровно следующий gate:** отдельная **ветка 05** независимо проверяет exact frozen HEAD PR #29 (код, старый strict HTML, fixed trusted CSV pins, portable CSV-only SVG, безопасная обработка `/\\` relative provenance keys, отсутствие G2.4 PNG в portable, reject path collisions/traversal, self-declared provenance rehash tamper, no successful HTML on refusal). Даёт **CRITICAL/MAJOR/MINOR** и **GO/CONDITIONAL GO/NO-GO** только для viewer portability; публикует результат в комментарии [Issue #27](https://github.com/kr13t1/ts-reliability-lab/issues/27) или PR #29. Не менять авторский source.

**После аудита:** настоящий Windows smoke с ранее полученными `output_g24` и `--g24-png-mode omit`, затем решение 00 о merge. До этого PR не объединять и не объявлять полноценный UI готовым. **Интерактивность отдельно после portability**; Хабр приоритетен, однако статический HTML не выдавать за интерактивную лабораторию.

**Статусы:** G1/G2.2/G2.3/G2.4 technical GO; Linux strict viewer presentation-only GO; **Windows portability pending 05 + user smoke**, full G2 NOT GO, G3 CLOSED, G4 scout only, G5/G6 closed.
