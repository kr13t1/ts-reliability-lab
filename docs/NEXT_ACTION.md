# Единственное следующее действие — дельта-аудит 05 визуального PR #26 на новом SHA (LAB-031)

**Исходный контекст:** [Issue #25](https://github.com/kr13t1/ts-reliability-lab/issues/25), [PR #26](https://github.com/kr13t1/ts-reliability-lab/pull/26). **Новый frozen HEAD:** `db4b124f4e320ec273ec0322139520eefbfa7ec4` (**OPEN, NOT MERGED** при фиксации). Предыдущий условно проверенный HEAD: `ec5d108bd4ad7c30391e6976eef12af8f359182a`. Diff — только `visual_lab/build.py`, `visual_lab/tests/test_viewer.py`, `visual_lab/README.md`, 3 коммита.

**Роль 05:** независимый **дельта-аудит presentation-only**, не новый G2/G3 эксперимент. Основной G1/G2.2/G2.3/G2.4 принят технически; обычный viewer на предыдущем SHA был воспроизведён, но отмечен input-trust MAJOR. До проверки нового HEAD статус **READY_FOR_DELTA_PRESENTATION_AUDIT**, **НЕ GO**, PR не сливать.

**Ровно что проверить:**
1. Побайтный source SHA изменённых `visual_lab/`, original `g24.demo` + реальные WISDM input, нормальный `visual_lab.build` (HTML, manifest, при возможности скриншот); отличать полноценный Git checkout от побайтно проверенной source-копии.
2. **Независимо подтвердить авторские G24_FIXED_PINS** для `results.csv`, `1600_A_alpha_0/masks.csv`, `1600_A_alpha_1/masks.csv`, `1600_E_raw/masks.csv` и всех трёх `detection.png`. Standing эталон пересчитать по source-line 14292..17863 и raw SHA `40b7f60880b495ccb3c345b9ab11216dfa6bbb2bb887bcb45fb55020278fc22f`. PNG hashes candidate until independently matched on documented Linux Python/NumPy/Matplotlib stack; если текущий рендеринг отличается по байтам, это controlled `REJECTED_INPUT`, не автоматическое принятие нового SHA.
3. **Обе негативные атаки** в копиях upstream outputs: замена `1600_E_raw/detection.png` на walking freeze PNG + обновление `g24/provenance.json.files_sha256`; изменение `1600_E_raw/masks.csv.obs_x` + такое же обновление self-declared SHA. **Оба не должны завершаться PASS_PRESENTATION или выпускать успешный HTML/manifest**. Правильный upstream должен давать нормальный viewer.
4. Проверить поле `viewer_executed_source_sha256` в manifest против **реальных исполняемых байтов `visual_lab/build.py`**, честно `viewer_git_sha=null` без .git.
5. Выдать **CRITICAL/MAJOR/MINOR и GO/CONDITIONAL GO/NO-GO только презентационной лаборатории** на точном новом HEAD, документировать команды/контрольные файлы/hashes/platform и границы. Отчёт в Issue #25 или отдельном audit PR. Никаких правок PR #26 аудитором.

**Подробное координационное поручение:** [комментарий 00 к Issue #25](https://github.com/kr13t1/ts-reliability-lab/issues/25#issuecomment-6628212767). **После 05** только координатор 00 принимает решение о merge. Work не нужен.

**Границы:** Full G2 NOT GO, G3 CLOSED; никакого G2.5 stage, нового детектора, repair, ML или научных claims. Исходный WISDM может содержать естественные неисправности; `Z=0` означает только отсутствие нашей инъекции. Три цели: честный инженерный Хабр, отдельная проверяемая научная статья EEG/HFD A/B, НИР-7 на воспроизводимых данных C.
