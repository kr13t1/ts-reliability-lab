# G2.2 — фактически выполненный read-only эксперимент (до независимого аудита 05)

**Исследовательский статус:** локально `PASS_READ_ONLY`; полный G2 НЕ GO; G3 закрыт. Только реализация §§2–6 и 8 принятого LAB-020. Никаких инъекций, моделей, окон, фильтрации, ресемплинга.

## Вход и происхождение

Использован **реальный** `data_1600_accel_phone.txt`, неизменённо извлечённый из ранее предоставленного `G2_RAW_FOR_AUDIT_05.zip`. Это транспортные байты аудита, но **не** полная внешняя аттестация большого ZIP с сервера UCI. Проверка исходных байтов проведена заново.

- SHA-256 входа: `40b7f60880b495ccb3c345b9ab11216dfa6bbb2bb887bcb45fb55020278fc22f`;
- Размер 3 451 789 байт, 64 311 исходных строк;
- Выбор без просмотра амплитуд: 1600, A = Walking, полный run строки 1–3574, N=3574; следующая строка 3575 = B;
- Точные q endpoints `252207666810782`, `252387581668153`;
- Точные целочисленные интервалы: 3573 пар, min `50331507`, median `50354004`, max `50378589`, сумма `179914857371`.

**Физические единицы/эпоха q, реальные независимые сессии, число потерянных событий: UNKNOWN.** Нельзя маркировать Δq как наносекунды или аппаратный fault.

## Действительно выполнено

```bash
python -m pytest -q g2/tests/test_readonly.py
python -m g2.readonly --input data/raw/data_1600_accel_phone.txt --output-dir g2/results_local --config g2/configs/g2_readonly.json --precheck data/provenance/G2_MULTI_SUBJECT_PRECHECK.json
```

Python 3.13.5, NumPy 2.3.5, Matplotlib 3.10.8, pytest 9.0.2. **30 из 30 unit tests PASS** (только искусственные фикстуры). Реальный запуск дал **PASS_READ_ONLY** и создал `reference.csv`, `selection.json`, `reference.png`, `validation.json`, `config.json`, `provenance.json`. Второй независимый по запуску каталог получил побайтово идентичные CSV, PNG, selection, config и validation в этом окружении.

| Сохранённый файл | SHA-256 при реальном запуске |
|---|---|
| `reference.csv` | `8bf61ee71f68e0648ead7bc8eb8b6c44414e28411bd6de65e5f9dadf9c28eb38` |
| `reference.png` | `e1943f0206d58df8f5c38cb327dd047e0fe1f7193b41118111890598cef2f2fd` |
| `selection.json` | `ded1e5b64ad4dc054ed7fdeed426f295ff9daeb49a9430a931efe6e945ea80c7` |
| `validation.json` | `f1250bda155b430de5c7c93b40c0e0c8ce654f48bc6e3bbbe52c6bb8986586c2` |

Суммарный SHA-256 **исполняемого исходника** `g2/readonly.py`: `9b7a95f9556b90e03d8becac657f912c75ef63a1073e1e1c52c440746eba1da6`. При отправке GitHub проверено совпадение Git blob исходника с локальным тестированным файлом.

**Ограничение provenance:** запуск произведён вне локального Git checkout; `git_sha=null` в сохранённом `provenance.json`. Приписывать уже выполненному запуску появившийся позже GitHub SHA нельзя. Для 05 нужен read-only аудит на закреплённом PR head SHA и независимое воспроизведение.

**Не выполнено:** внешний UCI checksum, физическая интерпретация timestamp, independent sensor fault truth, тестирование научных ML-гипотез, independent audit 05. Ни одно из этих утверждений не следует из самого графика.

## Проверка исправлений аудита 05 (LAB-022, 2026-11-03; до повторного аудита)

**Исторические результаты выше относятся к старому коду frozen `cdbd2208da36a7a103f8bab19f1489219d84a541` и не переписываются.** В отдельном исправляющем commit изменены только обработка metadata/precheck, тесты, закреплённый конфиг и документация. Реальные исходные данные и визуализация не менялись.

- **MAJOR-01:** `config.json` и `provenance.json` содержат SHA утверждённой спецификации `ae612e338df6a25eb94281cc2b3969cd39824d44`; provenance сохраняет фактические CLI-аргументы и эквивалентную команду, атрибуцию UCI 507, DOI `10.24432/C5HK59`, лицензию CC BY 4.0.
- **MAJOR-02:** malformed `precheck.json`, включая корректный JSON `{}`, обрабатывается как `REJECTED_INPUT` с `validation.json`. Добавлены parameterized тесты структуры.
- **MINOR-01:** полный SHA-256 precheck закреплён `f534d093b003327019dec214c1c332e95c1d413ad25efd7943df4082422e8a57`, изменение корректно структурированного JSON блокирует запуск статусом `BLOCKED_IDENTITY`.
- **Запущено локально:** `python -m pytest -q g2/tests` → **39 passed** в окружении с реальным raw; два самостоятельных CLI-запуска G2.2 после исправления → `PASS_READ_ONLY`. Исходный TXT проверен по полному SHA-256 и метаданным. Второй запуск имеет другую строку CLI, поэтому `provenance.json` *ожидаемо отличается* — он честно записывает каждый отдельный запуск.
- **Неподвижные результаты:** `reference.csv` SHA `8bf61ee71f68e0648ead7bc8eb8b6c44414e28411bd6de65e5f9dadf9c28eb38`; `reference.png` SHA `e1943f0206d58df8f5c38cb327dd047e0fe1f7193b41118111890598cef2f2fd`, идентичны предыдущему аудированному прогону.
- **Новые hashes:** `g2/readonly.py` SHA-256 `f2c8dcc1ac74e0f76706bc34e657cf486e53f1b5c0863ec794f8e3a7a4ef90bc`; `g2/tests/test_readonly.py` `36fed96831b80062f3124398f0ec521692e12c61fe7a773a5c615f2ef6c7534f`; `g2/configs/g2_readonly.json` `296dee4501087ca3c2ae4fe6743739d8f8ec2f2176f4804da9e39cb5622701d6`.
- **Новые выходные хеши первого запуска:** `config.json` `a52e9beb1f862abd416b5d8b8c55f726d9c912e76c9e66440cbd9626385123b7`; `selection.json` `ded1e5b64ad4dc054ed7fdeed426f295ff9daeb49a9430a931efe6e945ea80c7`; `validation.json` `f1250bda155b430de5c7c93b40c0e0c8ce654f48bc6e3bbbe52c6bb8986586c2`. `provenance.json` включает аргументы/путь конкретного запуска и имеет SHA `970880ae0c423b99d12dcb5016928d2d24716630e31ebae054fc6284e1284cd6` для первого каталога; он **не обязан** совпадать при другом `--output-dir`.
- **Граница воспроизведения:** выполнено в локальной рабочей папке вне Git, `git_sha=null` не исправлялся задним числом. До закрытия замечаний требуется независимый reviewer 05 на точном новом head SHA. Нет G2 GO, инъекций §7 или G3.
