# Единственное следующее действие — независимый дельта-аудит 05 G2.2 (LAB-022)

**Вход:** GitHub Issue #11: https://github.com/kr13t1/ts-reliability-lab/issues/11 ; implementation PR #8: https://github.com/kr13t1/ts-reliability-lab/pull/8 .
**Новый frozen HEAD:** `01035bcc6793f620c941dbc0926e8de5d4d7dcfc`. Старый исходник первого аудита: `cdbd2208da36a7a103f8bab19f1489219d84a541`, independent audit 05 в `docs/audits/G2_READONLY_IMPLEMENTATION_AUDIT_05.md` (`main`).

**Проверить самостоятельно и подтвердить или опровергнуть закрытие:**

1. **MAJOR-01:** mandatory provenance output — точный approved-spec commit SHA `ae612e338df6a25eb94281cc2b3969cd39824d44`, фактическая команда/argv, UCI 507 / DOI `10.24432/C5HK59` / CC BY 4.0; при `git_sha=null` не приписывать историческому запуску commit.
2. **MAJOR-02:** структурно некорректный `precheck.json` (`{}`, неверные типы/поля) — контролируемый `REJECTED_INPUT` и `validation.json`, без `KeyError`, без выходных CSV/PNG.
3. **MINOR-01:** полная проверка precheck SHA `f534d093b003327019dec214c1c332e95c1d413ad25efd7943df4082422e8a57`; корректный по форме, но изменённый JSON — `BLOCKED_IDENTITY`.
4. **Отсутствие регрессий:** GitHub Actions G1/G2 success; проверка raw input `40b7f60880b495ccb3c345b9ab11216dfa6bbb2bb887bcb45fb55020278fc22f`, 1600/A строки 1–3574; выходной CSV `8bf61ee71f68e0648ead7bc8eb8b6c44414e28411bd6de65e5f9dadf9c28eb38` и PNG `e1943f0206d58df8f5c38cb327dd047e0fe1f7193b41118111890598cef2f2fd` должны оставаться точными на тех же байтах и окружении.

**Выход:** независимый read-only delta-review 05 на точном новом SHA, с описанием реально выполненных команд, CRITICAL/MAJOR/MINOR и GO/CONDITIONAL GO/NO-GO только для технического read-only G2.2. Сохранить отчёт в отдельном PR/комментарии; PR #8 не править и не сливать без решения 00.

**Запрет:** полный G2 остаётся NOT GO; G3 не открыт; §7 с искусственными повреждениями не разрешён. Не изменять G1/raw, не добавлять ML, resampling, windows или инъекции.

**После дельта-аудита:** 00 самостоятельно изучает отчёт и решает, можно ли принять/слить PR #8. Никаких параллельных технических направлений до этой проверки.
