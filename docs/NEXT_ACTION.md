# Единственное следующее действие — независимый 05 аудит portability PR #28 (LAB-035)

**Активный Issue:** [#27](https://github.com/kr13t1/ts-reliability-lab/issues/27), **implementation PR:** [#28](https://github.com/kr13t1/ts-reliability-lab/pull/28), frozen HEAD `63f7036e87761cb0f0899d0a5e96d355866411eb` (OPEN, NOT MERGED). Истина: [LAB-035](DECISIONS.md), [PROJECT_STATE v1.30](PROJECT_STATE.md), [Windows diagnostic](diagnostics/WINDOWS_VIEWER_20261107.md), [approved engineering contract](specs/WINDOWS_VIEWER_PORTABILITY_CONTRACT_v1.md).

**Текущий реальный статус:** Windows raw-backed `g24.demo PASS_DEMO`, 4/4 G2.4 CSV fixed SHA OK, 3/3 PNG SHA DIFF, исходный strict viewer на Windows `REJECTED_INPUT`. PR #28 добавил opt-in `--g24-png-mode omit` (не читает/не принимает G2.4 PNG, рисует существующие SVG из проверенных CSV), безопасные POSIX/Windows canonical paths с запретом collision/traversal, тесты и README. **Windows end-to-end на новой ветке пока не выполнялся, а исходный strict Linux HTML SHA не подтверждён независимым 05 для нового кода.** Для CI выполнено только fixture/stdlib: Python 3.11/3.13 Linux `compileall PASS`, unittest **23 total, 10 pass, 13 skipped** для каждой версии [Actions #42370177943](https://github.com/kr13t1/ts-reliability-lab/actions/runs/42370177943). Не писать 23/23 PASS.

**Ровно сейчас:** ветка/чат **05**, независимый от автора изменений, делает дельта-аудит PR #28 на frozen SHA и публикует C/M/m + GO/CONDITIONAL GO/NO-GO только **portability presentation-only**. [Передача и тестовый контракт в Issue #27](https://github.com/kr13t1/ts-reliability-lab/issues/27#issuecomment-6706639341):
- Реальный original accepted WISDM / G2.3 / G2.4 CLI и 23 viewer tests без skip, если доступны genuine source/raw; иначе явно указать ограничение.
- Strict Linux default на старых G2.4 PNG: historical HTML SHA `37bb60e254e489c7aa5e40468b6f844a54d272b5956cf74688b14f5c180eb1df`, negative G2.4 PNG swap + provenance attack.
- Portable POSIX/Windows provenance keys, 4/4 fixed CSV, отсутствующие/альтернативные G2.4 PNG: positive SVG HTML/manifest без embedded G2.4 PNG, отрицательная Standing obs_x edit + repaired self-declared SHA, collision/traversal and source SHA verification.
- Без молчаливых правок проверяемого оригинала, без слияния от 05.

**Только после независимого 05:** пользователь на Windows Python3.11.9 скачивает/checkout PR #28 branch, переносит уже подтверждённый `output_g24` и raw в рабочую папку (без редактирования), запускает:
```powershell
python3 -m visual_lab.build --g23-dir g23/example --g24-dir output_g24 --output-dir visual_lab_out_portable --g24-png-mode omit
start visual_lab_out_portable/index.html
```
Только фактический `PASS_PRESENTATION`/HTML + независимый 05 может привести к отдельному GO/merge 00. Если Windows smoke fails — не использовать ручную правку hashes.

**После закрытия #27 (НЕ сейчас):** отдельная задача на действительно интерактивный экран для Хабра (выбор из проверенных сценариев, zoom, toggles, без новых методов), независимый presentation audit, затем редакция/публикация Хабра. Научный метод и новая статья C — будущий Research & Invention после literature check.

**Неприкосновенные статусы:** G1/G2.2/G2.3/G2.4 технические GO, Linux viewer presentation-only GO, Windows viewer NOT GO, **full G2 NOT GO**, **G3 CLOSED**, G4 scout only, G5/G6 закрыты, никакого G2.5.
