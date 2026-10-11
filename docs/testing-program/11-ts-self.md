<!-- variants: TS SELF -->
# 11. Тачскрин и самообслуживание

`Style=TS`: модули `TS\` (`TS`, `TSController`, `TSDispatcher`, `TSKB`,
`TSPay`, `TSPOSTermIP`, `TSOrdList`), кнопки из `VTS_BUTTONS`; печать идёт
через `TSPayment()` / `POSTermPay()` вместо `F12`. Киоск —
`uSelfService.cpp`, пункт меню при `ShowMenuSelfService=true`.

- [ ] Кнопки экрана совпадают с `select * from vts_buttons order by
      interface_id, pos`. Снимок `ts-01-buttons`.
- [ ] Чек через кнопки: категория → товар → оплата (`selftest: ts,<команда>,<аргумент>`).
- [ ] Клавиатура `TSKB` вводит количество и поиск по названию.
- [ ] Оплата картой с тачскрина (`TSPOSTermIP`) — как 5.3.
- [ ] Киоск: сценарий покупателя без кассира, чек на виртуальный принтер.
- [ ] Экран покупателя (`customer-display.md`): иконки отрисованы, а не
      `"icon-text":"e5…"` — шрифт Material Symbols установлен.
