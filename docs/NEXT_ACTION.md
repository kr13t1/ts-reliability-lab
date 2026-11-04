# Единственное следующее действие — посмотреть принятую offline-лабораторию (LAB-032)

**Техническая база принята:** [PR #26](https://github.com/kr13t1/ts-reliability-lab/pull/26), fixed implementation HEAD `db4b124f4e320ec273ec0322139520eefbfa7ec4`, merged squash `35424bd4c80f417c6e7da238a253122052b759a4`. Независимый [delta audit 05](https://github.com/kr13t1/ts-reliability-lab/issues/25#issuecomment-6628348140): **GO только presentation-only**, C/M/m=0/0/0. Код G1/G2.2/G2.3/G2.4 был принят ранее; этот viewer не вводит нового алгоритма или результата.

**Практическая цель:** один раз **лично открыть** единую страницу и оценить, понятно ли что измерялось, что искусственно внесено, что обнаружено, как именно появился FP на `i=1190`. Это user-experience sanity-check, не новый научный эксперимент. **Не создаём новую ветку Work или Issue ради просмотра.**

1. Из репозитория посмотреть уже сохранённые реальные графики и объяснение в [LAB_VISUAL_WALKTHROUGH.md](LAB_VISUAL_WALKTHROUGH.md).
2. Если локально доступен **проверенный raw WISDM** `data/raw/data_1600_accel_phone.txt` (SHA-256 `40b7f60880b495ccb3c345b9ab11216dfa6bbb2bb887bcb45fb55020278fc22f`), из корня checkout выполнить команды из [visual_lab/README.md](../visual_lab/README.md). Windows PowerShell:
```powershell
py -3.13 -m pip install -r g24/requirements.txt
py -3.13 -m g24.demo --g23-dir g23/example --standing-input data/raw/data_1600_accel_phone.txt --axis x --min-run-samples 3 --output-dir output_g24
py -3.13 -m visual_lab.build --g23-dir g23/example --g24-dir output_g24 --output-dir visual_lab_out
start visual_lab_out/index.html
```
Если `output_g24` уже построен из верного raw, запуск `g24.demo` повторять не нужно, достаточно viewer с **новой пустой** output-директорией. Не подменять отсутствующий raw примерами/заглушками. Без raw нельзя утверждать о локальной генерации HTML. PNG, сгенерированные на другой платформе, могут побайтно отличаться и viewer **контролируемо откажет** (это известное ограничение pinned Linux renderer, не доказательство неправильной математики).
3. **Критерий минимальной готовности:** экран показывает Reference/Observed, истинную назначенную Z, предсказанную Zhat, выделенный boundary FP `i=1190` и три фиксированных случая 1600/A alpha0, 1600/A alpha1, 1600/E no injection. Если экран непонятен, записать **одну конкретную правку представления**, не менять результаты/пороги. Никаких новых научных claims.

**Что заблокировано:** **full G2 NOT GO, G3 CLOSED**, G4 только ограниченная научная разведка, G5/G6 закрыты. No new G2.5; реальные hardware fault labels/subject-disjoint test отсутствуют. Инженерный Хабр и НИР-7 могут ссылаться на аудированную демонстрацию, но сами материалы ещё не готовы; старая научная EEG/HFD публикация — отдельный путь. Work не нужен.

**Истина:** [PROJECT_STATE.md](PROJECT_STATE.md) v1.27 и [DECISIONS.md](DECISIONS.md) LAB-032. Исходный 05 проверял побайтно сверенную GitHub source-копию **без .git checkout**, не заявлять обратное.
