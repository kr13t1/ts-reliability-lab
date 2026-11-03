# G2.2 — реальный WISDM: строго read-only

**Контракт:** LAB-020; утверждены только §§2–6 и 8 `docs/g2/G2_REAL_SIGNAL_SPEC.md`. Реальные искусственные повреждения (§7), классификация, окна и ресемплинг **запрещены**. Полный G2 NOT GO, G3 не открыт.

## Источник

UCI [WISDM Smartphone and Smartwatch Activity and Biometrics](https://archive.ics.uci.edu/dataset/507/wisdm%2Bsmartphone%2B) (2019), DOI [10.24432/C5HK59](https://doi.org/10.24432/C5HK59), CC BY 4.0. Программа принимает исключительно неизменённый TXT `wisdm-dataset/raw/phone/accel/data_1600_accel_phone.txt` (допускается извлечённая локальная копия с теми же байтами из ранее проверенного транспортного ZIP). Полный исходный UCI ZIP пока **не** прошёл независимую внешнюю аттестацию. Исходный TXT и ZIP в Git не коммитить.

Фиксированный выбор из precheck: subject `1600`, активность `A = Walking`, полная первая последовательная серия строк **1–3574**, N=3574. Полный TXT: 64 311 строк, 3 451 789 байт, SHA-256 `40b7f60880b495ccb3c345b9ab11216dfa6bbb2bb887bcb45fb55020278fc22f`. Любая ошибка идентичности, границ, формата или timestamp вызывает отказ; другой run никогда автоматически не выбирается.

## Запуск из корня Git-репозитория

```powershell
py -3.13 -m pip install -r g2/requirements.txt
py -3.13 -m pytest -q g2/tests
py -3.13 -m g2.readonly --input "data/raw/data_1600_accel_phone.txt" --output-dir "g2/results/run_001"
```

На Linux/macOS используйте `python` вместо `py -3.13` (Python 3.11+). Зависимости зафиксированы: NumPy 2.3.5, Matplotlib 3.10.8, pytest 9.0.2. Полный 1600 TXT требуется заранее извлечь в локальную папку `data/raw`, которая исключена из Git. `--output-dir` обязан быть новым или пустым.

Путь precheck по умолчанию — `data/provenance/G2_MULTI_SUBJECT_PRECHECK.json`; путь конфига — `g2/configs/g2_readonly.json`. Менять зафиксированные поля контракта запрещено; код откажется, а не выберет другие данные.

Успешный запуск возвращает `PASS_READ_ONLY`; отсутствующий сырой вход — `BLOCKED_INPUT`, иной SHA — `BLOCKED_IDENTITY`. Не формировать искусственный график при отказе.

## Выходы

- `config.json` — закреплённые параметры, без абсолютного локального пути;
- `reference.csv` — 3574 строки `i,source_line,subject,activity,q,x,y,z`, исходные числовые токены и **точный целочисленный** q;
- `selection.json` — полный input SHA, границы run, q endpoints, точные Δq;
- `reference.png` — x/y/z по **индексу** (не времени), без фильтрации и децимации;
- `validation.json` — реальные проверки либо статус отказа;
- `provenance.json` — input/precheck/source hash, версии, SHA результатов, Git SHA и dirty flag, если доступно.

**Проверенный локальный реальный запуск:** см. `g2/reports/EXECUTION_REPORT.md`. Отдельный независимый аудит 05 на точном SHA ещё требуется. После замечаний аудита добавлены негативные проверки структуры precheck и его полного SHA, а также проверка полей provenance. Локально выполнено 39/39 тестов при доступном raw; в GitHub CI тест с реальным raw корректно пропускается (raw не находится в репозитории). Эти тесты не заменяют независимый аудит 05.

## Ограничения

`X_ref` — наблюдаемая запись, а не физически идеальный эталон. `timestamp_unit=UNKNOWN`, `session_id=null`, `physical_continuity=UNKNOWN`, `full_remote_attestation=UNVERIFIED`. Не переводить q в секунды или UTC, не утверждать потери отсчётов или аппаратную неисправность; это **иллюстрация**, не результат ML и не доказательство новизны.

## Исправления по независимому аудиту 05 (после frozen PR #8 SHA `cdbd2208...`)

Новый код дополнительно проверяет полный SHA-256 исходного precheck JSON (`f534d093b003327019dec214c1c332e95c1d413ad25efd7943df4082422e8a57`) и отказывает `BLOCKED_IDENTITY` при изменении корректно структурированного отчёта. Некорректная структура (`{}`, отсутствующие runs, неверные типы) вызывает `REJECTED_INPUT` с `validation.json`, не Python traceback.

В `config.json` и `provenance.json` теперь записан утверждённый source commit спецификации `ae612e338df6a25eb94281cc2b3969cd39824d44`; provenance содержит фактические CLI-аргументы, эквивалентную команду и UCI/DOI/лицензию. Для прямого Python-вызова поля CLI честно остаются `null`, статус `PYTHON_API`. `git_sha=null` означает, что запуск сделан вне Git checkout; это не заполняется задним числом.

После этих изменений необходим короткий дельта-аудит 05 на новом commit. Прежние хеши `reference.csv` и `reference.png` сохранились; `config.json` и `provenance.json` ожидаемо изменились. См. `g2/reports/EXECUTION_REPORT.md`.
