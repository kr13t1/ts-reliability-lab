# Единственное следующее действие — наглядная offline-лаборатория из принятых G2.3/G2.4 (LAB-029)

**Тикет:** [Issue #25](https://github.com/kr13t1/ts-reliability-lab/issues/25). **Роль:** 04 «Код и интерактивная лаборатория». **Work не требуется.** Цель — не писать очередной новый детектор, а сделать видимым то, что уже **математически зафиксировано и независимо технически проверено**.

**Принятые основания:**
- G1 синтетическая модель — технический GO.
- G2.2 raw read-only (WISDM subject=1600, Walking/A) — технический GO.
- G2.3 `g23/` искусственный freeze оси X [1191,2382) и истинная Z — технический GO (LAB-025).
- G2.4 `g24/` baseline A exact `float64` run (`L=3`, `epsilon=0`, offline, `Zhat` из только X_obs) — **технический GO после независимого 05** (LAB-029): original [PR #21](https://github.com/kr13t1/ts-reliability-lab/pull/21) SHA `a242f09eba6c1b2b2dcbe2073665e26580c211a2` merged squash `91bd08c3564e8c335013480274ce2c0c5428acbb`; первоначальный audit PR #24 (исторический CONDITIONAL GO), а итоговый delta review 05 **GO** [Issue #23 comment](https://github.com/kr13t1/ts-reliability-lab/issues/23#issuecomment-6627225305). **Никаких новых замечаний CRITICAL/MAJOR/MINOR** после исправления на новом SHA.

**Немедленно доступный видимый артефакт:** [docs/LAB_VISUAL_WALKTHROUGH.md](LAB_VISUAL_WALKTHROUGH.md), который показывает реальные опубликованные G1/G2.3 PNG, три verified G2.4 результата и точные локальные команды генерации ещё трёх G2.4 PNG. Отдельный UI пока не изготовлен.

**Единственная новая задача 04:** отдельный маленький PR для **presentation-only offline viewer** по входным `g23/example` и локальным `g24` output, строго без замены вычислений, без новых датасетов, типов повреждений, threshold selection, классификации и обучения. Предпочтение статическому HTML/PNG (или простой CLI-галерее) без платных сервисов и новой научной модели. Нужны один экран reference→observed→Z→Zhat, видимый **один boundary FP i=1190** и контроль без инъекции Walking/Standing, понятная легенда, точные ссылки на upstream outputs, реальные тесты/команды, внятные сообщения при отсутствии raw или output. Проверяемый результат — локальный HTML/screenshot и исходники, frozen SHA, readme; 05/00 presentation-review прежде чем merge.

**Границы:** **Full G2 NOT GO, G3 CLOSED**, G4 только литературная разведка, G5/G6 не открыты. 1600/A и 1600/E — один subject; 1191 TP = одна искусственная инъекция, не множество независимых испытаний. `Z=0` означает отсутствие нашей инъекции, **не** доказанную исправность устройства; FPR — injection-relative, не реальная hardware fault false alarm rate. Единицы q, independent session IDs и full UCI remote SHA неизвестны. Три цели по-прежнему: инженерный Хабр, отдельная научная EEG/HFD статья, НИР-7 по C.

**Состояние решений:** [PROJECT_STATE.md](PROJECT_STATE.md) и [DECISIONS.md](DECISIONS.md), LAB-029. Старые заголовки в авторских G2.3/G2.4 README исторические и не заменяют решения 00.
