# G2_TIMESTAMP_COLLECTOR_SOURCE_02.md — поиск первичного сборщика WISDM 2019

**Ветка 02 / G2.1b, issue [#2](https://github.com/kr13t1/ts-reliability-lab/issues/2)**  
**Дата проверки:** 2026-11-03 · **Версия отчёта:** 1.0 · **Основание:** LAB-018.  
**Итог:** **NOT FOUND** — проверяемый исходный код, формирующий поле `timestamp` в `raw/phone/accel` **именно UCI 507**, не найден. **Происхождение и единица опубликованного timestamp: UNKNOWN**. Это ограниченный отрицательный результат поиска, **не доказательство отсутствия кода где бы то ни было**. G2 остаётся не принятым, G3 не открыт.

## 1. Точный критерий проверки

Объект — *WISDM Smartphone and Smartwatch Activity and Biometrics Dataset* (2019), UCI ID 507, 51 субъект, 18 активностей, файлы `wisdm-dataset/raw/phone/accel/data_<subject>_accel_phone.txt`. Требуется **связать код или авторскую техническую спецификацию с той версией приложения**, которая сформировала эти файлы, и увидеть конкретное выражение для третьего поля `timestamp`.

Не подменять этот объект более ранними наборами **WISDM Activity Prediction / WISDM_ar_v1.1 (36 субъектов, 6 активностей)** или **Actitracker**. Не путать код извлечения признаков из опубликованных raw с кодом первичного сбора.

Критерий CONFIRMED для ns: достоверная идентификация использованной версии приложения **и** однозначная цепочка `Android API/clock → записанная переменная → экспортируемое поле timestamp`, исключающая скрытое масштабирование. Одной документации Android API или совпадения численных масштабов недостаточно.

## 2. Проверенные первоисточники 2019 и границы их содержания

**[S1] UCI 507, карточка автора:** https://archive.ics.uci.edu/dataset/507/wisdm%2Bsmartphone%2B ; DOI https://doi.org/10.24432/C5HK59 . **CONFIRMED:** raw-схема `subject-id, activity-code, timestamp, x, y, z`, номинальные 20 Гц, текстовое определение timestamp как `Unix time (integer)`. **UNKNOWN:** единица исходного целого, точный API, epoch/clock origin, версия приложения; исходник приложения в карточке не указан.

**[S2] Авторское описание WISDM (Gary M. Weiss, 2019):** https://archive.ics.uci.edu/ml/machine-learning-databases/00507/WISDM-dataset-description.pdf (разд. 3, Table 3). **CONFIRMED:** колонка timestamp имеет целочисленный тип, описана как `Linux time`; 20 Гц являются запросом к Android, не гарантией фактической равномерности. **UNKNOWN:** значение «Linux time» как конкретной единицы, clock API и экспорта. Авторский документ не содержит строки кода `timestamp = ...`.

**[S3] Первичная исследовательская статья того же набора:** G. M. Weiss, K. Yoneda, T. Hayajneh, “Smartphone and Smartwatch-Based Biometrics Using Activities of Daily Living”, *IEEE Access* 7 (2019), 133190–133202, DOI https://doi.org/10.1109/ACCESS.2019.2940729 ; доступный текст https://www.researchgate.net/publication/335785947_Smartphone_and_Smartwatch-Based_Biometrics_Using_Activities_of_Daily_Living , разделы III.B–C. **CONFIRMED:** исследователи применяли «customized Android application» для телефонного и часового акселерометра/гироскопа, переносили данные по USB, а timestamp называли `Unix time`. Устройства в исследовании — Google Nexus 5/5X либо Samsung Galaxy S5 (Android 6.0), LG G Watch (Android Wear 1.5). **UNKNOWN:** репозиторий/релиз использованного сборщика, точный вызов получения timestamp, масштаб поля после сохранения. Публикация не предъявляет исходного кода collector.

**[S4] Android Developers:** https://developer.android.com/reference/android/hardware/SensorEvent#timestamp . **CONFIRMED только для API:** `SensorEvent.timestamp` — наносекунды; монотонная шкала соотнесена с `SystemClock.elapsedRealtimeNanos()`. **ASSUMED, не установленное для UCI 507:** приложение 2019 напрямую сохраняло это поле без изменений. Варианты `System.currentTimeMillis()`, преобразованного `event.timestamp` и иной логики не исключены первоисточниками [S1–S3].

## 3. Реально найденный код WISDM-лаборатории: почему это НЕ доказательство для UCI 507

**[C1]** https://github.com/MichaelRZ/Android-Gait-Tracking — публичный Android-проект с README, прямо называющим WISDM Lab Fordham заказчиком. Проверена **точная ревизия** `cda41998914b78ec31ca0319e059dfadacf9503d` (последний просмотренный коммит, 2019-11-05); начальный коммит `8b1c4872d08fa3fedd606b8a5eb05bf5f8fa7f39` датирован 2019-04-28. Манифест сборки `phoneapp/build.gradle` на этой ревизии: `applicationId "com.example.wisdm"`, `versionCode 1`, `versionName "1.0"`. **Это версия найденного альтернативного проекта, не подтверждённая версия сборщика UCI 507.**

Для воспроизведения точных строк в неизменной ревизии:
- [phoneapp/src/main/java/com/example/phoneapp/MainActivity.java, L701–734](https://github.com/MichaelRZ/Android-Gait-Tracking/blob/cda41998914b78ec31ca0319e059dfadacf9503d/phoneapp/src/main/java/com/example/phoneapp/MainActivity.java#L701-L734): `systemTime = System.currentTimeMillis()` в `onSensorChanged` (L704), `difference = systemTime - otherTime` в `getAccelerometer` (L725), в список записывается `(float)(difference)-1000` (L733), одновременно используется `event.values[2]-(9.6f)`. **CONFIRMED для C1:** записанное время относительно старта из миллисекундного системного времени, конвертируемое во float, **а не прямое сохранение `SensorEvent.timestamp`**.
- [тот же файл, L432–435 и L481–492](https://github.com/MichaelRZ/Android-Gait-Tracking/blob/cda41998914b78ec31ca0319e059dfadacf9503d/phoneapp/src/main/java/com/example/phoneapp/MainActivity.java#L432-L435): заголовок `pax,pay,paz,time`, файл `phone_acceleration.csv`, четыре значения в строке с заголовком. **CONFIRMED:** экспорт отличается от шестипольных целочисленных raw `data_1600_accel_phone.txt` UCI 507; отсутствуют поля `subject_id` и `activity_code` в этом экспортном формате.
- [README.md](https://github.com/MichaelRZ/Android-Gait-Tracking/blob/cda41998914b78ec31ca0319e059dfadacf9503d/README.md): описаны управляемая часами запись, GPS, микрофон и CSV по сенсорам. Нет явной связи с набором 51×18, опубликованным как UCI 507.

**Строгое заключение:** код C1 **найден и прочитан**, но **идентичность с фактически применённым collector WISDM 2019 — UNKNOWN / NOT VERIFIED**. Из совпадения лаборатории, года и устройств нельзя выводить общую версию приложения. Из отличия формата можно заключить, что **непосредственный показанный CSV-экспорт C1 не совпадает с опубликованным raw UCI 507**; невозможно исключить неописанную отдельную конверсию, другую ветку или раннюю версию приложения. Поэтому утверждение «UCI 507 timestamp = миллисекунды по C1» **НЕ подтверждено** точно так же, как «UCI 507 timestamp = `SensorEvent.timestamp` ns».

## 4. Проверенные альтернативы и граница поиска

**[H1]** Официальный архив старой лаборатории: https://www.cis.fordham.edu/wisdm/dataset.php — раздел **Activity Prediction**, с версиями `WISDM_ar_v1.1` (36 субъектов, 6 видов активности), и отдельный **Actitracker**. Там же предоставляется код **преобразования** raw в признаки, а не исходник доказанно того же коллектора UCI 507. В историческом `WISDM_ar_v1.1_raw_about.txt` указывается uptime ns, но эта спецификация относится к **другому датасету** и не может подтверждать единицу 2019 (см. копию: https://github.com/brangerbriz/machine-learning-docs/blob/master/data/WISDM_ar_v1.1/WISDM_ar_v1.1_raw_about.txt ). Источник и различие датасетов установлены; перенос масштаба — **ASSUMED, не принят**.

**Фиксация ограниченного поиска (2026-11-03):** прочитаны [S1–S4], секции III.B–C первичной статьи, сайт лаборатории [H1]; поиском GitHub по WISDM+collector, Android, `SensorEvent.timestamp` и веб-поиском по названию набора найден и проверен [C1]. Среди проверенных материалов **не обнаружены** исходный файл, commit/tag/release или авторская спецификация, достоверно связующие сборщик 2019 с его записываемой третьей колонкой. **Не исследованы** частные репозитории, не опубликованные версии и внутренние архивы лаборатории; «не найдено» не означает «не существует».

## 5. Матрица статусов и научно допустимый вывод

| Утверждение | Статус | Основание |
|---|---|---|
| Данные UCI 507 собирало кастомное Android-приложение | **CONFIRMED** | Авторы [S3] |
| Опубликованные TXT содержат целое поле `timestamp` | **CONFIRMED** | [S1–S2], LAB-017 |
| Авторское название времени — «Unix» / «Linux» | **CONFIRMED как документационные формулировки** | [S1–S3] |
| Приложение WISDM 2019 использовало `event.timestamp` | **UNKNOWN** | Нет идентифицированного первичного collector-кода |
| Приложение WISDM 2019 использовало `System.currentTimeMillis()` | **UNKNOWN** | Такой вызов установлен только для [C1], происхождение [C1] не связано с UCI 507 |
| Точное значение `q-unit`, clock origin и абсолютная эпоха UCI 507 | **UNKNOWN** | [S1–S3] не дают доказуемой формулы |
| `q-unit = 1 ns` в raw UCI 507 | **ASSUMED, НЕ CONFIRMED** | Совместимо с масштабом Δq и [S4], но код не установлен |
| У 1601 и 1600/1602 различаются целочисленные Δq | **CONFIRMED** | `data/provenance/G2_MULTI_SUBJECT_PRECHECK.json`, независимый аудит LAB-017 |
| Различие Δq — доказанная аппаратная неисправность | **UNKNOWN / НЕ ДОКАЗАНО** | Нет авторской модели временных меток и независимого physical ground truth |
| [C1] — оригинальный collector данных UCI 507 | **UNKNOWN / NOT VERIFIED** | Ни первичные документы, ни [C1] не устанавливают такое соответствие |

## 6. Условия и передача координатору 00

**Результат G2.1b: `COLLECTOR_SOURCE_NOT_VERIFIED; TIMESTAMP_ORIGIN_UNKNOWN`.** Не повышать ns-гипотезу до CONFIRMED, не конвертировать q в календарный UTC, не утверждать фактическую частоту или потерю отсчётов по условным мс/Гц. Сохранять необработанные `q_i` и разности в целых единицах файла; временные подписи «если ns» допустимы только как оговорённые сценарии.

**Один минимальный возможный способ разрешить UNKNOWN (только после решения 00):** запросить у автора исходный commit/version сборщика, реально использованного для UCI 507, **или** подписанную техническую спецификацию с точным выражением, формирующим поле `timestamp` в `raw/phone/accel`. Сравнить идентичность приложения и выходной схемы; до этого вопрос остаётся открытым. Пользователю не требуется заново скачивать большой ZIP только для ответа о collector-коде.

MAJOR-01 provenance официального ZIP и неопределённость физических сеансов отдельно **не закрыты**. `docs/PROJECT_STATE.md`, `docs/DECISIONS.md`, `docs/NEXT_ACTION.md`, прежний отчёт G2.1, raw и код G1 **не изменены**. Никакого resampling, windowing, train/validation/test, классификации, инъекции, выбора метода или нового этапа G3. Решение о дальнейших шагах принадлежит 00.
