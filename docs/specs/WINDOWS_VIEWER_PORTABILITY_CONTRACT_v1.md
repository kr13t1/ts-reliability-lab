# WINDOWS_VIEWER_PORTABILITY_CONTRACT_v1 — инженерная спецификация, LAB-034

**Статус:** утверждена координатором 00 **только к реализации и 05-аудиту**, не GO для Windows UI. Основание: [диагностический отчёт](../diagnostics/WINDOWS_VIEWER_20261107.md), [предыдущий 05 viewer GO на Linux](https://github.com/kr13t1/ts-reliability-lab/issues/25#issuecomment-6628348140).

## Проблема и запреты

Windows Python 3.11.9, NumPy 2.3.5, Matplotlib 3.10.8 → accepted `g24.demo PASS_DEMO`, 4/4 фиксированных G2.4 CSV SHA совпадают; системные `\\`-ключи `provenance.files_sha256` приводят к `REJECTED_INPUT`; три Windows PNG содержат иные байты, чем frozen Linux fingerprints. Нужно обеспечить **переносимое представление без ослабления независимого source integrity**.

**Не менять** frozen G2.4 detector, параметры, raw WISDM, G2.3 маски, counts, CSV, G24_FIXED_PINS, прежние auditable checks, математические контракты. Без нового ML, repair, G3, G2.5, оптимизации по test. Не смешивать реализованный статический viewer с будущей настоящей интерактивностью.

## Разрешённое поведение (предложенный минимальный контракт)

1. В `visual_lab/` ввести **явный** портативный режим, например `--g24-png-mode omit`; *текущий* strict-default обязан сохранить ранее аудированный Linux результат и запрет неправильных PNG. В portable-режиме viewer **не встраивает, не отображает и не удостоверяет** ни один G2.4 `detection.png`; можно вообще не читать эти bytes. Панель G2.4 PNG заменяется на явное «PNG недоступны в переносимом режиме; показаны SVG из независимо проверенных CSV». Не вписывать непроверенный PNG в HTML/manifest как `validated`. **Ключевой запрет:** никогда не принимать self-declared PNG hash как единственный trust anchor и не пересчитывать frozen pins ради PASS.
2. При проверке self-declared `g24/provenance.json.files_sha256` корректно распознавать два формата относительных ключей (`/` и `\\`) **только как представление одного известного канонического пути**. Перед нормализацией проверить типы ключей/значений, отсутствие абсолютных/traversal/empty paths, неоднозначных имён, повторяющихся canonical names и path-collision. При неоднозначности — `REJECTED_INPUT`; без silently overwriting. G2.3 accepted metadata менять/ослаблять нельзя.
3. **Во всех режимах** `results.csv` + три `masks.csv` должны совпадать с независимо закреплёнными `G24_FIXED_PINS` и проходить прежние проверки Z/Zhat/source_line/q/event/metrics, без выбора из mutable provenance. Для G2.3 должны сохраняться accepted pins и provenance/validation. Portable-графики/SVG и карточки строятся **только** из этих проверенных CSV, обозначены `presentation-only`, `Z=0` ≠ ground-truth clean hardware.
4. Сохранить provenance source SHA исполняемого builder, raw source identity, выходные SHA CSV/HTML и отображаемый режим. Manifest однозначно указывает `G2.4 PNG excluded; not verified or embedded` в portable, и legacy scope в strict. Отказ `REJECTED_INPUT` exit 2 без successful HTML на подменённых trusted CSV, конфликте нормализованных путей и нарушениях схемы.
5. **Не выдавать статическую HTML-галерею за интерактивную лабораторию.** Управление сценарием, zoom/toggle по клику, параметрами и rerun — отдельная следующая работа после этого PR и независимого аудитa.

## Приёмочные испытания

- Legacy Linux strict: original 05-accepted inputs → прежний `PASS_PRESENTATION`, неизменённый HTML SHA должен совпасть с **фактическим ранее аудированным strict-HTML эталоном**, проверяемым по fixture/snapshot тесту 05 (числовой эталон не задан до верификации), прежние 17/17 тестов и adversarial PNG+provenance refusal.
- Fixture для Windows provenance: те же independently pinned 4 CSV, `\\` в G24 self-declared keys, PNG с отличающимися байтами или отсутствующие → portable `PASS_PRESENTATION` с честным **отсутствием любых G2.4 PNG в HTML**, проверяемым SVG сигналом и метриками. Это проверка механизма, не полноценная Windows acceptance без запуска на Windows.
- Два негативных ввода portable: (a) `Standing masks.csv.obs_x` изменён при одновременно пересчитанном mutable provenance SHA → `REJECTED_INPUT`, no HTML; (b) `result.csv` или `masks.csv` изменён независимо от source pins и self-declared checksum → `REJECTED_INPUT`; (c) collision двух self-declared canonical paths → `REJECTED_INPUT`.
- Положительный Windows smoke-test на **подлинном local `output_g24`** отдельно выполняет пользователь: `python3 -m visual_lab.build --g23-dir g23/example --g24-dir output_g24 --output-dir visual_lab_out_portable --g24-png-mode omit`; итог с HTML, stdout, manifest, графиком; если нет запуска, Windows поддержка только кандидат, не принята.
- Тесты/README, renderer/OS/Python provenance, exact SHA PR, независимый 05 **дельта-аудит** на frozen HEAD перед 00 merge.

**Следующая реализация:** ровно один PR, изменения преимущественно `visual_lab/build.py`, `visual_lab/tests/`, `visual_lab/README.md`, без изменения g24. **Один активный Issue**, без параллельного интерактивного UI, Хабр черновик допустим отдельно, но публикация требует честного runnable contract.
