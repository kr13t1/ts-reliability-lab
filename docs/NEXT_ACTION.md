# Единственное следующее исследовательское действие — LAB-037

[Issue #32](https://github.com/kr13t1/ts-reliability-lab/issues/32): ветка 03 готовит `docs/specs/REPAIR_DYNAMICS_PROTOCOL_v1.md` в draft PR, до просмотра новых результатов. Ветка 02 проверяет независимость и происхождение допустимой записи без оценки методов. Протокол фиксирует baseline, информационный режим, RMSE, одну первичную метрику динамики, отрицательный результат, обработку вырожденных случаев и критерии остановки при отсутствии подходящих данных. Затем независимый 05 и отдельное решение 00. Не запускать оценку новой записи до утверждения. Исправить assert trust gates перед расширением pipeline, не менять frozen pilot.

Вход: `explorations/repair_pilot/SPEC.md`, `config.json`, `results.csv`, `summary.csv`, [аудит 05 PR #31](https://github.com/kr13t1/ts-reliability-lab/pull/31#issuecomment-6995524630), устав. Полный G2 NOT GO, G3 CLOSED, G4 scout only, G5/G6 closed. Старые работы отдельно. Публикационный CSS v3 отдельный GO, проверить anonymous deploy; статья Хабра отклонена по п.4.

## Предыдущая задача (история LAB-036)

# Единственное следующее действие — довести один GitHub PR #30 до аудируемого Хабр-комплекта (LAB-036)

**Источник истины:** [PROJECT_STATE.md](PROJECT_STATE.md) LAB-036, [draft PR #30](https://github.com/kr13t1/ts-reliability-lab/pull/30). В PR уже помещены подготовленные `ARTICLE.md` и автономный `demo/index.html`, источник/ограничения, raw-independent checks; их следует читать/редактировать прямо в GitHub. Чистые факты: WISDM subject 1600, controlled freeze X, исходный simple G2.4 baseline, 1191 TP и 1 FP на i=1190. Это инженерная демонстрация, не новая научная проверка.

**Ровно один следующий минимальный проверяемый шаг:** добавить в **тот же** PR #30 исходный `build_demo.py`, соответствующий `template.html` и исправленные raw-dependent tests (старый ZIP имел путь `source_and_tests/index.html` вместо `demo/index.html`), затем выполнить воспроизводимый build/test на source-verified WISDM raw и закрепить stdout, inputs SHA, output HTML SHA, точный PR HEAD. До этого не заявлять full reproducible build или полный 05 GO. Научные G2.4 results, raw и baseline не изменять.

**После результата:** 05 даёт scoped audit **по PR #30 + HEAD без загрузки файлов в другой чат**, затем 00 решает GO/NO-GO для Хабра. Публичный URL отдельного HTML и две иллюстрации — последняя подготовка к публикации; нужна проверка внешнего доступа. Не превращать весь приватный исследовательский repo в публичный без разрешения.

**Отдельные вопросы не блокируют Хабр:** [PR #28](https://github.com/kr13t1/ts-reliability-lab/pull/28) и [PR #29](https://github.com/kr13t1/ts-reliability-lab/pull/29) — два кандидата Windows-переносимости старого статического viewer. На #29 был user Windows `PASS_PRESENTATION/exit 0`, аудит 05 — CONDITIONAL GO, незавершён raw-dependent strict run; ни один PR не merged. Нельзя переносить их вердикты на Habr HTML.

**Запрещено:** вручную пересылать архивы между чатами; выдавать user UI tests за independent 05; заявлять обнаружение реальной поломки шагомера, downstream-risk или новую научную нишу. Full G2 NOT GO, G3 CLOSED, G4 scout only, G5/G6 closed.
