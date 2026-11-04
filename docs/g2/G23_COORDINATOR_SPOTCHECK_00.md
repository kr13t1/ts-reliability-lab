# Координаторский численный spot-check G2.3 (НЕ аудит 05)

**Дата:** 2026-11-04 · **Ссылка на проверяемую реализацию:** [PR #13](https://github.com/kr13t1/ts-reliability-lab/pull/13), frozen HEAD `ac5eed80e169d153b94b5d92ffac38e820e8bed7`. **Тип проверки:** независимый от авторского CSV пересчёт одной величины из локального raw transport, но **НЕ** независимая программная ревизия 05 или проверка опубликованных графиков и всех байт.

**Источник:** `G2_RAW_FOR_AUDIT_05.zip` в доступной проектной среде, member `data_1600_accel_phone.txt`; raw SHA-256 `40b7f60880b495ccb3c345b9ab11216dfa6bbb2bb887bcb45fb55020278fc22f`, 3 451 789 байт, 64 311 физических строк. У файла исходный формат `subject,activity,q,x,y,z;`. Полные официальные bytes удалённого ZIP по-прежнему **UNVERIFIED**.

```python
import hashlib, math, zipfile

archive = "G2_RAW_FOR_AUDIT_05.zip"
with zipfile.ZipFile(archive) as z:
    raw = z.read("data_1600_accel_phone.txt")
assert hashlib.sha256(raw).hexdigest() == (
    "40b7f60880b495ccb3c345b9ab11216dfa6bbb2bb887bcb45fb55020278fc22f"
)
lines = raw.decode("utf-8").splitlines()
assert len(lines) == 64311
rows = [line.rstrip(";").split(",") for line in lines[:3574]]
assert all(s == "1600" and activity == "A" for s, activity, *_ in rows)
x = [float(fields[3]) for fields in rows]
a, b = 1191, 2382
freeze_value = x[a - 1]
errors = [freeze_value - value for value in x[a:b]]
di = math.sqrt(sum(e * e for e in errors) / (b - a))
n_changed = sum(e != 0 for e in errors)
print("freeze_value:", freeze_value)
print("n_changed:", n_changed)
print("D_I:", di)
```

**Фактически исполнено в координаторской среде:** `freeze_value=0.43917847`, `n_changed=1191`, `D_I=3.075384527037127`. Число совпало с авторским `D_I=3.0753845270371265` в пределах погрешности печати floating point. При заданном операторе `D_Z=D_I`, `L_out=0` следует из формального определения, **но ещё требуется независимая проверка кода/CSV фактических выходов**.

**Граница:** это только spot-check арифметики: он не запускал `g23/freeze.py` на frozen GitHub checkout, не сверял каждый выходной CSV/PNG, не проводил 15 тестов, не подменяет независимое 05 GO. Full G2 NOT GO, G3 закрыт.

**Единственный gate:** [Issue #14](https://github.com/kr13t1/ts-reliability-lab/issues/14) — независимый аудит 05 с полными проверками на fixed SHA.
