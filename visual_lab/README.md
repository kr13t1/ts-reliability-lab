# Визуальная offline-лаборатория — Issue #25

**Только представление проверенных G2.3/G2.4 результатов; не новый эксперимент.** Генератор `visual_lab.build` не читает исходный raw WISDM, не импортирует детектор и не запускает вычисления G2.3/G2.4. Он сверяет SHA-256, схему CSV, provenance, источник, трёх заранее определённых сценариев, индекс/q и истинную маску; затем создаёт **один автономный HTML** с исходным x, x после freeze, Z, Zhat, ошибкой на i=1190 и тремя случаями. Все PNG встроены прямо в HTML — сервер, подключение к сети и платные службы не нужны.

## Подготовка (единожды, из корня Git checkout)

Из проекта нужен уже **проверенный** сырой файл `data/raw/data_1600_accel_phone.txt` из `G2_RAW_FOR_AUDIT_05.zip`, SHA-256 `40b7f60880b495ccb3c345b9ab11216dfa6bbb2bb887bcb45fb55020278fc22f`. **В viewer этот файл не передаётся**, он нужен только для получения результатов принятого G2.4. В репозиторий raw/ZIP не добавлять.

Windows PowerShell, Python 3.13:

```powershell
py -3.13 -m pip install -r g24/requirements.txt
py -3.13 -m g24.demo --g23-dir g23/example --standing-input data/raw/data_1600_accel_phone.txt --axis x --min-run-samples 3 --output-dir output_g24
py -3.13 -m visual_lab.build --g23-dir g23/example --g24-dir output_g24 --output-dir visual_lab_out
start visual_lab_out/index.html
```

Linux/macOS (если `python` — Python 3.13):

```bash
python -m pip install -r g24/requirements.txt
python -m g24.demo --g23-dir g23/example --standing-input data/raw/data_1600_accel_phone.txt --axis x --min-run-samples 3 --output-dir output_g24
python -m visual_lab.build --g23-dir g23/example --g24-dir output_g24 --output-dir visual_lab_out
xdg-open visual_lab_out/index.html # macOS: open visual_lab_out/index.html
```

Если `output_g24` уже получен корректным CLI, **заново генерировать его не нужно**: выполните только последнюю команду `visual_lab.build`. И G2.4, и viewer **отказываются перезаписывать** непустой выходной каталог; для повторного запуска используйте новый каталог (`visual_lab_out_2`). Viewer в случае ошибок выводит `REJECTED_INPUT`, причину и код завершения `2`; **не создаёт успешный HTML** из отсутствующих или повреждённых входов. `output_g24` без raw/ZIP не возникает автоматически: ничего не симулируется.

Viewer требует **только stdlib Python 3.13** (дополнительные библиотеки не устанавливает). `g24/requirements.txt` в командах выше нужен исходному CLI; не viewer.

## Что видно

- Один экран: синяя **Reference** и оранжевая **Observed** ось x Walking, область инъекции `[1191,2382)`, зелёная **назначенная Z** и фиолетовая **предсказанная Zhat**. Увеличение начала серии делает заметной красную точку **i=1190**, попавшую в Zhat, но отсутствующую в Z.
- Три фиксированных контраста: Walking α=0, Walking α=1, Standing/E без нашей инъекции. TP/FP/FN/TN, precision и recall **читаются из проверенного G2.4 CSV**, нулевые знаменатели показываются как «не определено». Исходные PNG G2.3 и G2.4 можно раскрыть в том же HTML.
- `visual_lab_out/manifest.json`: SHA-256 каждого использованного файла, HTML SHA, Python, Git SHA (или `null` вне checkout), source/provenance и ограничения. Сам исходный `output_g24`, `g23/example` и WISDM raw не переписываются.

## Тесты

```bash
python -m unittest discover -s visual_lab/tests -v
```

Тесты логики и отказов на синтетических фикстурах выполняются без raw. Полные негативные тесты tamper/массивов и HTML snapshot запускаются **только при наличии настоящего `g23/example` и локального `output_g24`**; без них будут явно `skipped`. Для теста вне корня проекта можно указать `VISUAL_LAB_TEST_G23` и `VISUAL_LAB_TEST_G24`. Выполнение тестов над копиями файлов не изменяет оригиналы. Ссылка на исходные определения и границы: `docs/LAB_VISUAL_WALKTHROUGH.md` и `docs/g2/G24_CONSTANT_RUN_BASELINE_SPEC.md`.

## Научные ограничения

Только WISDM subject **1600**: Walking и Standing — разные блоки той же записи, но не установленные независимые сессии. `Z=0` = отсутствие **нашей искусственной инъекции**, не внешняя метка исправного датчика. Физическая единица q неизвестна, полная внешняя SHA-аттестация ZIP UCI не выполнена; **1191 TP ≠ 1191 независимых испытаний**. Здесь нет оценки реальных аппаратных false-alarm, независимого теста, нового алгоритма, восстановления, научной новизны или утверждённой темы ВКР. Full G2 NOT GO, G3 closed. Изображение — объяснимая инженерная демонстрация для НИР-7/Хабра, не научное доказательство.
