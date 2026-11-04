# G24_CONSTANT_RUN_IMPLEMENTATION_AUDIT_05 — независимый аудит технического G2.4

**Аудитор:** ветка 05, 2026-11-04. **Issue:** [#23](https://github.com/kr13t1/ts-reliability-lab/issues/23). **Единственный объект:** [PR #21](https://github.com/kr13t1/ts-reliability-lab/pull/21), frozen HEAD **`99c88cff3970f7b71fabefeb94f7c88f7a662013`**. PR #22 не изучался как реализация и не использовался для вычислений (закрыт без merge).
**Граница:** контракт `docs/g2/G24_CONSTANT_RUN_BASELINE_SPEC.md`, LAB-026/027/028; только 1600/A alpha0, alpha1 и 1600/E без проектной инъекции. G1/G2.2/G2.3 считаются ранее принятыми только в их узких технических границах.
**Вердикт аудитора:** **CONDITIONAL GO только для технического G2.4 на указанном SHA**: основной эксперимент с оригинальными исходниками G2/G2.3 воспроизведён, однако выявлен неконтролируемый отказ на повреждённых метаданных G2.3. **CRITICAL = 0, MAJOR = 1, MINOR = 2**. До отдельного решения 00 **не merge** PR #21; **full G2 NOT GO; G3 CLOSED**.

## 1. Источники и способ независимого выполнения

Непосредственно через GitHub на frozen SHA прочитаны `docs/RESEARCH_LAB_CHARTER_v1.md`, `docs/PROJECT_STATE.md`, `docs/DECISIONS.md` (LAB-025–028; актуальные решения также в main), `docs/NEXT_ACTION.md`, `docs/g2/G24_CONSTANT_RUN_BASELINE_SPEC.md`, `docs/g2/G24_SPEC_REVIEW_00.md`, `docs/g2/G24_STANDING_CONTROL_PRECHECK_02.md`, предыдущий `docs/audits/G23_FREEZE_IMPLEMENTATION_AUDIT_05.md`, `g24/demo.py`, `g24/detector.py`, `g24/evaluate.py`, `g24/configs/g24.json`, оба тестовых файла, README, execution report и все 15 изменённых путей PR #21.

**Git checkout в исполняющем контейнере не создан:** здесь недоступно сетевое `git clone`. Вместо подстановки адаптеров через GitHub-коннектор получены и в отдельном каталоге восстановлены точные байты **оригинальных** `g2/readonly.py`, `g23/freeze.py`, `g24/{demo,detector,evaluate}.py`, исходных конфигов, обоих `g24/tests/test_*.py`, принятой `G2_REAL_SIGNAL_SPEC.md` и pinned precheck. Для каждого сопоставлен рассчитанный на локальных байтах **Git blob SHA-1** с blob на frozen HEAD GitHub, а также SHA-256; всё совпало. Это проверяет *реальные версии функций* и исходники тестов без временных compatible adapters; но **не** является заявлением, что выполнялся полный authenticated Git checkout. Во время выполнения честный `git_sha=null`, `git_dirty=null`.

| Проверенный исходник | SHA-256 локальных исполняемых байтов | Git blob SHA-1 = GitHub |
| --- | --- | --- |
| `g24/demo.py` | `ebe60af4563aa6c4acb99839abb77591c79a684f1084636f278387464735e99c` | `5a715429df25c19d348eaf6ba2b2bbb799d9e69b` |
| `g24/detector.py` | `01b1972ecb4c44d9459bfac713517a8538909f85ed3a6632658e8758508f8a01` | `d1d8aab11055dec8a7bfe8281508550bbfb80dc7` |
| `g24/evaluate.py` | `de067842fcea4736acad6571a7261f77a942a63cf3fcf54f6689f118c3cd1299` | `d70b816c1fc726561d002af05e9a9b4a4be78782` |
| `g2/readonly.py` (принятый) | `f2c8dcc1ac74e0f76706bc34e657cf486e53f1b5c0863ec794f8e3a7a4ef90bc` | `92c7aca3fa5a1d6a75eecf58fddfbff3a1e4bf95` |
| `g23/freeze.py` (принятый) | `b26a887d8896e82a7db776b08b0d959d320e37babb56039710664fd43aa1b87b` | `f8a1c3625048fae5f3cd66c22813abb7643a5ab0` |
| `g24/tests/test_detector.py` | `389659a0b77b4e7db43c15b080c97f303f68882919fb58da65336475c2994ee0` | `090588eefaaca46a5337cad1659cefa721235d53` |
| `g24/tests/test_pipeline.py` | `b236ab2a2d3e5795f4f5b77eaf2fd65e8d0e2a0eb8b2f4d3fec91d7d7534ca55` | `52b57065b12b0d2e4e38ed4b9bbbddb0973a280e` |

Также побайтно совпали с GitHub все три конфигурации, `G2_REAL_SIGNAL_SPEC.md` и JSON precheck, `g24/requirements.txt`. **Дифф PR #21:** 15 добавленных файлов, только `g24/`. Не изменены `g1/`, `g2/`, `g23/`, исходные raw, accepted specs/decisions.

## 2. Настоящие исходные данные и восстановление G2.3 без адаптеров

Прямо прочитан `G2_RAW_FOR_AUDIT_05.zip` из предоставленных общих файлов проекта: **4 373 638 байт**, SHA-256 `7aca931a3af368bae0ac932140aff270f9cd5f0c6c783e393c83c1672628f503`. В нём проверен действительный member `data_1600_accel_phone.txt`: **3 451 789 байт / 64 311 физических строк**, SHA-256 `40b7f60880b495ccb3c345b9ab11216dfa6bbb2bb887bcb45fb55020278fc22f`. Никакой синтетической подмены сырого входа не было.

- A/Walking: subject 1600, полные исходные строки 1..3574, N=3574.
- E/Standing: тот же subject 1600, исходные строки 14292..17863, N=3572; соседние активности D и F, `q_first=241892286783982` и `q_last=242072100924919`; SHA-256 **точных 192 708 байт сегмента** `50edfd731735d54cd76fe4c0a38da914fca7b567ae4e3b3d389f2d687fadb61d`.

**Сначала заново запущен исходный принятый `g23/freeze.py` вместе с реальным `g2/readonly.py`** по тому же raw, получено `PASS_DEMO`. Выходы G2.3: `reference.csv` SHA `8bf61ee71f68e0648ead7bc8eb8b6c44414e28411bd6de65e5f9dadf9c28eb38`; `alpha_0/arrays.csv` SHA `6cf2fd4d19da30d00be7a4878a979c2d3828554715377c3bda5aaf384801f7d5`; `alpha_1/arrays.csv` SHA `df34cf7dc715bf9e928560d26b6fb01f8299349a80e64a84c65f3f20807262f6`. Дополнительно совпали принятые SHA для G2.3 config/selection/results/PNG. Это устраняет центральное ограничение авторского запуска с временными адаптерами. `provenance.json` G2.3 не обязан побайтно совпасть с историческим (реальные CLI paths/Python), но проверен по форме, статусу и SHA всех закреплённых входов.

## 3. Реальные команды, среда и численное воспроизведение

**Среда аудитора:** Linux, Python **3.13.5**, NumPy **2.3.5**, Matplotlib **3.10.8**. Команды исполнялись из корня изолированной побайтно-сверенной source-копии без сетевых служб:

`python -m g23.freeze --input data/raw/data_1600_accel_phone.txt --output-dir g23/example --source-commit bf0e6039a216d6d40c21016f8546aa5b1ae00050`

`python -m unittest discover -s g24/tests -v`

`python -m g24.demo --g23-dir g23/example --standing-input data/raw/data_1600_accel_phone.txt --axis x --min-run-samples 3 --output-dir /mnt/data/g24_audit/run_A`

`python -m g24.demo --g23-dir g23/example --standing-input data/raw/data_1600_accel_phone.txt --axis x --min-run-samples 3 --output-dir /mnt/data/g24_audit/run_B`

**Фактически получено:** G2.3 `PASS_DEMO`; **26 из 26** тестов G2.4 `OK` (все 8 pipeline integration tests **выполнялись**, а не были skipped); оба G2.4 CLI `PASS_DEMO`.

**Независимый математический пересчёт**, отдельный от `g24.detector` и `g24.evaluate`: из всех физических raw-строк ещё раз построены исходные float64 x и десятичные целые q; только для alpha1 заморожены x[1191:2382] на значении x[1190], назначена Z[1191:2382)=1. Максимальные точные последовательности одинаковых x длины >=3 найдены отдельным циклом; Zhat и TP/FP/FN/TN рассчитаны независимо. **Результат:**

| Фиксированный случай | N | TP | FP | FN | TN | n_true | n_pred | precision | recall | injection-relative FPR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: |
| 1600/A, alpha0 | 3574 | 0 | 0 | 0 | 3574 | 0 | 0 | null | null | 0 |
| 1600/A, alpha1 | 3574 | 1191 | 1 | 0 | 2382 | 1191 | 1192 | 1191/1192 = 0.9991610738255033 | 1 | 1/2383 = 0.000419639110365086 |
| 1600/E без инъекции | 3572 | 0 | 0 | 0 | 3572 | 0 | 0 | null | null | 0 |

Единственное предсказанное событие **[1190,2382)**, единственная истинная назначенная инъекция **[1191,2382)**. **Один FP на опорном индексе 1190** неизбежен для определённого правилом маркирования всех точек полного плоского участка. Для двух контролей `recall=null` (нет назначенных положительных точек), `precision=null` (нет предсказанных положительных); это не «100% precision». В `events.json` true-event overlap = 1, non-overlap alarms = 0.

**Поэлементно проверено каждое поле всех трёх вновь созданных `masks.csv` против независимого raw и собственной маски:** 3574 + 3574 + 3572 = **10 720 строк**, точные `source_line`, целые q (без float), `obs_x`, каждый `Zhat_x` и `Z_x`. Итоговый `results.csv` сопоставлен с независимыми счётчиками. Три реально созданных `detection.png` открыты и осмотрены: наблюдаемая ось x и два наложенных ряда масок по индексу, без секунд, без заявлений о природных датчиковых faults. В обоих CLI прогонах побайтно равны **10/10 файлов, кроме provenance**; в provenance закономерно отличаются argv и output-dir.

**Проверка опубликованных в PR #21 результатов:** пересчитанные `results.csv` и оба Walking `masks.csv` имеют те же Git blob SHA, что реальные файлы в `g24/reports/` на frozen GitHub. Для `events.json` смысловые JSON-значения совпадают, но не побайтовая сериализация — см. MINOR-01.

## 4. Негативные случаи и реальный CI

Помимо собственных 26 тестов CLI дополнительно запущен с заведомо испорченными *копиями* входов. Все неуспешные кейсы оставили исходные raw/G2/G2.3 неизменными.

| Негативный вход | Наблюдение |
| --- | --- |
| raw отсутствует | `BLOCKED_INPUT`, exit 2, validation есть, CSV/PNG нет |
| raw изменён на один байт | `BLOCKED_IDENTITY`, exit 2, validation есть, CSV/PNG нет |
| L изменён в pinned config | `REJECTED_CONFIG`, exit 2, нет успешных выходов |
| CLI ось y или L=4 | `REJECTED_CONFIG`, exit 2 |
| каталог G2.3 отсутствует | `BLOCKED_INPUT`, exit 2 |
| изменён G2.3 `alpha_1/arrays.csv` | `BLOCKED_IDENTITY`, exit 2 |
| `validation.json` G2.3 имеет FAIL | `BLOCKED_IDENTITY`, exit 2 |
| **корректный JSON provenance G2.3, но `"files_sha256": null`** | **необработанный `AttributeError`, exit 1, нет `validation.json` — FAIL** |
| provenance G2.3 без поля `files_sha256` | `BLOCKED_IDENTITY`, exit 2 |

GitHub Actions на **точном frozen HEAD**: G1, G2.2, G2.3 — `success` (отдельные upstream workflow, не raw/G2.4 integration). **Workflow G2.4 в PR #21 не добавлен**; `26/26` G2.4 подтверждены здесь локально, а не выдуманы из CI.

## 5. Замечания 05 и условия закрытия

**CRITICAL — 0.** Нарушений математического правила L=3, изменения исходных измерений, подгонки порога, утечек истинной маски в signature детектора или ложных научных claims не найдено.

**MAJOR-01 — необработанный отрицательный случай повреждённого G2.3 provenance.** В `g24/demo.py`, функция `validate_g23_metadata`, выражение `prov.get('files_sha256',{}).get(rel)` выдаёт `AttributeError: 'NoneType' object has no attribute 'get'` при `"files_sha256": null`. Это структурно повреждённый, но синтаксически валидный JSON. Вместо ожидаемого управляемого отказа CLI завершает работу с traceback/exit 1 и **не создаёт обязательных validation/provenance**. При принятом входе проблема не возникает, поэтому основной результат подтверждён. **Условие закрытия:** валидировать типы вложенных provenance-полей **до** обращения к `.get`; выдавать `REJECTED_INPUT` или `BLOCKED_IDENTITY` с `validation.json` / `provenance.json` и без успешных результатов, добавить проверку `null`, списка, строки и отсутствующего поля в unit/integration tests. Повторный аудит — **новый точный commit SHA**, старый frozen audit не повышать до GO автоматически.

**MINOR-01 — опубликованный `g24/reports/events.json` отличается по байтам от настоящего запуска original modules.** GitHub blob авторского файла — `d4e78d14592822f5cc61bee815dcc49872a969d8`; реально воспроизведённый original `g24.demo` создаёт blob `3aa40ced3c688903a76d2b74898dd2f27bade602`. Все математические значения **совпадают**. Различие только в сериализации целых коэффициентов: `0`/`1` в опубликованной версии против `0.0`/`1.0` из `evaluate_mask`. Независимая замена целочисленных float на int в воспроизведённом JSON даёт **ровно авторский Git blob**. **Закрыть:** либо заменить committed summary на фактически генерируемый файл из исправленного frozen-кода, либо явно указать, что это эквивалентная по числам ручная/adapter-сериализация, без обещания byte identity.

**MINOR-02 — нет CI job именно для G2.4.** На head PR #21 upstream G1/G2.2/G2.3 Actions success, но `g24/tests` не запускались в GitHub Actions. **Закрыть:** добавить fixture-only GitHub workflow для `g24/tests` (пропуск реальных raw-интеграционных тестов должен быть честно явно помечен) либо зафиксировать официальный локальный G2.4 test-protocol как минимальный accepted workaround. Отсутствие CI само по себе не опровергает 26/26 локальных тестов.

**Отдельные ограничения проверки, не смешивать с замечаниями к реализованному алгоритму:** код был побайтно удостоверен против frozen GitHub, но запущен в восстановленной без .git исходной копии, а не полноценном `git checkout` (соответственно `git_sha=null`). Для обязательного Git checkout provenance координатору нужна дополнительная репликация в окружении, допускающем checkout именно на SHA. Raw transport identity подтверждена, но **независимой полной remote UCI ZIP attestation нет**, источник q и физические session IDs неизвестны.

## 6. Строгая научная граница и решение

- `Z=0` на A alpha0 и E означает только **«наша инъекция отсутствует»**, не «датчик физически исправен».
- Walking/A и Standing/E — **тот же subject 1600**; независимость сессий не установлена. Одна инъекция и зависимые точки (в том числе 1191 TP) не являются 1191 независимыми испытаниями или оценкой FPR реального оборудования.
- Алгоритм — известная **точная offline constant-run эвристика**, не собственная научная новизна. Нет восстановления, HAR-классификации, predictive reliability, обучения, confidence intervals или физически удостоверенных true faults.
- **Вердикт: CONDITIONAL GO только техническому G2.4 на frozen `99c88cff3970f7b71fabefeb94f7c88f7a662013`.** Условия: исправить MAJOR-01 в новом implementation commit, повторно подтвердить те же raw/CSV/metrics и все негативные отказы, оформить MINOR по JSON/CI; по возможности дополнительно выполнить git checkout SHA. **Не merge PR #21** до решения 00 после дельта-аудита.
- **Full G2 NOT GO; G3 CLOSED.** Этот отчёт не выбирает тему ВКР, не доказывает эффективность на естественных неисправностях и не разрешает новый метод.
- **Ровно один следующий минимальный шаг:** координатор 00 поручает исполнителю PR #21 устранить MAJOR-01 внутри этого G2.4 scope, фиксирует новый HEAD для дельта-аудита 05. Старые raw/G1/G2.2/G2.3 не менять.
