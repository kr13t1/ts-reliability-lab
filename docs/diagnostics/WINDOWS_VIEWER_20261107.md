# Windows viewer compatibility — подтверждённая диагностика входов, 2026-11-07

**Статус:** фактический отчёт из пользовательского Windows-запуска; **это не независимый аудит 05**, не новые измерения и не новый эксперимент по качеству детектора. Источник — локально выполненный read-only `windows_lab_diagnostic.py`; его пользовательский JSON имеет SHA-256 `54aa24614cf4e51b7cbc111f3010be97aa6a01cf2d51d7869a4622e50ba63b2d` (4605 B). Переданные числовые данные перепроверены формальной проверкой JSON в координационной сессии; запуск на Windows не воспроизводился координатором.

## Среда и неизменный accepted G2.4

- Windows 10 build 26200, Python **3.11.9**, NumPy **2.3.5**, Matplotlib **3.10.8**.
- `data_1600_accel_phone.txt`: SHA-256 `40b7f60880b495ccb3c345b9ab11216dfa6bbb2bb887bcb45fb55020278fc22f` совпадает с эталоном.
- `g24/validation.json`: **PASS_DEMO**; `raw_sha`, `standing_segment_sha`, `g23_output_sha`, `stage_separation`, `three_cases`, `no_parameter_tuning` все **PASS**. Только три заданных случая, без статистики независимых датчиков и аппаратных меток.
- `visual_lab/build.py` SHA-256 `1f3aaa409c65e33f166490f6607114766126d3aaa4f3a55ef30d98f5d666f456` соответствует ранее независимому 05 presentation HEAD `db4b124...`. Отчёт сообщает `g24/demo.py` SHA-256 `b2f2389d5298bdc7832e21693f6b0f37f2cd521c8aa9302fd64097f02bd39449`; не путать SHA-256 содержимого с Git blob SHA.

## Проверенные входные байты

| G2.4 output | Windows SHA-256 | Сравнение с pinned Linux |
| --- | --- | --- |
| `results.csv` | `abde1e1c95da63c0e7eb829defcc54babd34b7462053026f70ed3682269f83b4` | **OK** |
| `1600_A_alpha_0/masks.csv` | `d582599adcb81efab436e5306bd68071741932dc750d222dbbe5bd3cb4d55438` | **OK** |
| `1600_A_alpha_1/masks.csv` | `95ef70fe8330973c0dbbe4894b561ae8f9faf8861f40a41770394a2301c5b0a7` | **OK** |
| `1600_E_raw/masks.csv` | `4c0bcdd6665c0dcf20697de66bdab128680a78f4059689f20824f8bb5ec10642` | **OK** |
| `1600_A_alpha_0/detection.png` | `b00958ab42000626ea3af76b2b6a28156238d444a719d6027966b14d46435f7c` | **DIFF** |
| `1600_A_alpha_1/detection.png` | `1f97c7d6ca39ca62c2bd5ac8686775f34aae42e3df10ca9a73ce6c7ebf800d41` | **DIFF** |
| `1600_E_raw/detection.png` | `4ad16ba8b50173facf135dc4c81187620fb1394bb8b2d19704f59f1a8ff05bfa` | **DIFF** |

**Фактические JSON-ключи** `g24/provenance.json.files_sha256` — `1600_A_alpha_0\\masks.csv`, `1600_A_alpha_1\\masks.csv`, `1600_E_raw\\masks.csv`. `visual_lab.build` ожидает `1600_A_alpha_0/masks.csv` и т.д. В Windows JSON для G24 оригинальный `g24/demo.py` формирует `str(p.relative_to(out))`, поэтому путь системно-зависим. До чтения PNG viewer отвергает маску.

**Наблюдаемый отказ:** `python3 -m visual_lab.build --g23-dir g23/example --g24-dir output_g24 --output-dir <empty>` → `REJECTED_INPUT`, exit **2**, detail `G2.4 provenance/hash mismatch: 1600_A_alpha_0/masks.csv`, `index.html` не создаётся.

**Интерпретация, НЕ новый факт:** разница PNG-байтов при совпадении CSV возможна из-за платформы/версии Python/rendering, но не даёт права автоматически признать такие PNG подлинными. Принятые Linux SHA fixed-source неизменны; доказана только байтовая несовместимость. Не исправлять input JSON/хеши вручную. Отдельный статический preview не удовлетворяет интерактивному критерию.

**Инженерное следствие:** минимальный интерфейс должен либо проверять PNG против одобренного эталона и отказывать, либо явно **не использовать/не представлять неподтверждённые G2.4 PNG**, строя отображение из independently pinned CSV. При этом строгая legacy Linux-ветка остаётся неизменной. Требуется отдельный PR + независимый 05. Full G2 NOT GO, G3 CLOSED.
