# Единственное следующее действие — роль 04: реализовать первый ограниченный G2.4 constant-run baseline (LAB-027)

**Тикет:** [Issue #20](https://github.com/kr13t1/ts-reliability-lab/issues/20). **Исполнитель:** ветка 04 «Код и интерактивная лаборатория». Work **не требуется**. **До независимого 05 аудита и отдельного решения 00 нельзя объявлять технический GO для реализации G2.4 или merge код.**

**Принято (вход):**
- G1 синтетический GO; G2.2 реальный read-only технический GO; G2.3 демонстрационный freeze технический GO с независимым аудитом 05.
- Математический контракт `docs/g2/G24_CONSTANT_RUN_BASELINE_SPEC.md` по LAB-026: предиктор видит только `X_obs`; `L=3` точных равных float64 отсчёта (`epsilon=0`), offline maximal constant runs, `Zhat` без знания `Z,X_ref,alpha,a,b`; evaluator отдельно считает TP/FP/FN/TN, precision/recall/FPR с `null` на нулевых знаменателях. Сильные ограничения по идентифицируемости и физическим false alarms.
- **Теперь Standing/E input тоже GO для узкой демонстрации**: [PR #19](https://github.com/kr13t1/ts-reliability-lab/pull/19) frozen `f05b9f92e09b93946c10ef5d62a4a619e07423d2` merged squash `c4cff35467f44bc9e5df523ec2a17e4bd2cfb2a8`; `docs/g2/G24_STANDING_CONTROL_PRECHECK_02.md`. Координатор 00 независимо проверил по байтам source 1600/E строки **14292..17863**, N=3572, region SHA `50edfd731735d54cd76fe4c0a38da914fca7b567ae4e3b3d389f2d687fadb61d`, raw full SHA `40b7f60880b495ccb3c345b9ab11216dfa6bbb2bb887bcb45fb55020278fc22f`. 
- **Три фиксированных случая одного учебного sanity-check:** `1600/A alpha=0`, `1600/A alpha=1` (искусственно заданный freeze x[1191,2382)), `1600/E no injection` (Z=0 только относительно нашей инъекции, не proven-clean sensor).

**Один обязательный выход:** новый изолированный `g24/` с pure `detect_constant_runs` и отдельной `evaluate_mask`, детерминированным CLI, фиксированными конфигами, unit/negative tests, реальными CSV/PNG, plot масок `Zhat` и `Z`, provenance, README и отчётом фактически выполненных команд; один PR, frozen SHA, **не merge**. Ветка 04 не меняет `g1/g2/g23`, data raw, решения или математический контракт, не подбирает `L`, `epsilon` или красивый результат.

**Далее:** независимый 05 аудит только реального кода и вычислений на frozen PR; решение координатора 00 о техническом G2.4 GO или исправлениях.

**Запреты:** full G2 NOT GO; G3–G6 CLOSED (G4 только литературная разведка), нет subject-independent split, обучение/ML/repair/selective reliability/новые методики не разрешены. Q units, independent sessions, remote official UCI ZIP authenticity UNKNOWN/UNVERIFIED. Negative FP/FPR относительно нет нашей инъекции нельзя выдавать за доказанные аппаратные false alarms. Три конечных выхода отдельно: инженерный Хабр, научная EEG/HFD A/B публикация, НИР-7.
