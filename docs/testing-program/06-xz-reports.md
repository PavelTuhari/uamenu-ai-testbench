<!-- variants: ALL -->
# 6. X- и Z-отчёты, смена

`Ctrl+Shift+F3` X, `Ctrl+Shift+F9` Z → `Tmain::PrintXReport/PrintZReport`
(`fMenu.cpp:1875`) → `DTM->PrintZXReport` (`dtmod.cpp:6409`) →
`FPrinter->PrintZXReport`, журнал `Pk_X_Z_Report.write_log`
(`PosWriteLogXZ=true`). Ключи: `ZXReportByPIN`, `ZXReportByAdminOrInventr`,
`CheckDailySum`, `QueryDailySum`, `CloseByZ` (по умолчанию true — после Z
касса перезапускается), `PrintTMReportAfterX`, `PrintCurrencyReportAfterX/Z`.

## 6.1 Открытие смены

- [ ] «Открытие смены в фиск. принтере» (`miFPOpenDay`) → документ на
      виртуальном принтере, дата и кассир.

## 6.2 X-отчёт

- [ ] После чеков раздела 2 и 5: `Ctrl+Shift+F3`. `selftest: xreport`.
      При `ZXReportByPIN` — PIN.
- [ ] Файл X на виртуальном принтере: выручка по способам оплаты, возвраты,
      внесение/изъятие, число чеков. Снимок `xz-01-x`.
- [ ] Сверить с SQL: `select count(*), sum(suma) from tmdb_comenz where
      trunc(data)=trunc(sysdate) and state = <проведён>` и с «Итоги» (`casa.cpp`).
- [ ] Повторный X — те же цифры, смена не закрыта.

**Ожидается:** X не меняет состояние; цифры совпадают с базой и «Итогами».

## 6.3 Z-отчёт: запреты

- [ ] Отложить чек (`F7`), затем `Ctrl+Shift+F9` → отказ
      (`Unirest_Util.CHECK_RESERV_Z`). Снимок `xz-02-z-refused`.
- [ ] Вернуть и закрыть отложенный чек.
- [ ] В режиме инвентаризации без `ZXReportByAdminOrInventr` → отказ.
- [ ] При `CheckDailySum=true` и расхождении (`pk_x_z_report.check_daily_sum`) →
      предупреждение; записать текст.

## 6.4 Z-отчёт

- [ ] `Ctrl+Shift+F9` → PIN при `ZXReportByPIN`. `selftest: zreport`.
- [ ] Файл Z на виртуальном принтере: итог смены, номер Z. Снимок `xz-03-z`.
- [ ] При `CloseByZ=true` касса перезапустилась; после входа счётчики
      смены нулевые.
- [ ] Меню «Список Z-отчётов» (`uxzlog.cpp`, таблица `txzlog`, `ftype=0`)
      — новая строка с суммой Z.
- [ ] SQL: `select * from txzlog where ftype = 0 order by fdate desc` —
      первая строка = только что снятый Z.
- [ ] Чек после Z → новая смена, нумерация продолжается.

**Ожидается:** Z закрывает смену ровно один раз; журнал и принтер сходятся.

## 6.5 Отчёты терминала

- [ ] «POS Отчет X» и «POS Отчет Z» (раздел 5.3) — после Z кассы; суммы по
      картам в них равны строке «карта» в Z кассы.

## 6.6 Печать диапазона чеков

- [ ] «Печать диапазона чеков» (`BulkReprint.cpp`) — с первого по последний
      чек смены → файлы на принтере по числу чеков.
