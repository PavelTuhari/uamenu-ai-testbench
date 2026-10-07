# 4. Цены

## 4.1 Как цена попадает в кассу

Цены живут в **бэк-офисе** (`TPR_PRICES_ACT`, прайс-листы
`TMS_PRICE_LISTS`). Во фронт они приходят витриной — материализованным
представлением `MVPR_PRICES_ACT`, построенным через DB link:

```sql
-- user_mviews, MVPR_PRICES_ACT: REFRESH_METHOD=FORCE, REFRESH_MODE=DEMAND
select ... from "BONUS2019_07"."TPR_PRICES_ACT"@"BONUS2019_07.WORLD" p
 where exists (select 0 from "TMS_PRICE_LISTS"@"BONUS2019_07.WORLD" l where l.id = p.pl_id ...)
```

Колонки: `ID, PL_ID, SC, START_DATE, END_DATE, PRICE, NRDOC, FIXED_RANGE,
PROMO_QNT, QNT_FROM, QNT_TO`. Касса читает цены через представление
`VPR_PRICES` поверх этой витрины.

Все 58 витрин фронта — `REFRESH_MODE = DEMAND`: сами они не обновляются.
Обновляет их пакет `UNIREST_MV_V` в схеме фронта:

| Вызов | Что |
|---|---|
| `unirest_mv_v.refersh_mv` (так, с опечаткой — это имя в пакете; есть и `refresh_mv`) | все витрины |
| `unirest_mv_v.refresh_mv_one('MVPR_PRICES_ACT')` | одна витрина |
| `unirest_mv_v.check_conection` | проверка связи с бэк-офисом |

Касса сама зовёт `refersh_mv` при старте, если в `cantina.ini`
`RefreshUnirest=true` (`dtmod.cpp`); иначе при старте идёт
`bar$links.setupAllLinks`.

## 4.2 Обновить цены на стенде с бэк-офисом (путь A)

```sql
begin unirest_mv_v.check_conection; end;
begin unirest_mv_v.refresh_mv_one('MVPR_PRICES_ACT'); end;
select mview_name, last_refresh_date from user_mviews where mview_name = 'MVPR_PRICES_ACT';
```

Ожидается: `last_refresh_date` — только что. Затем контроль по товару
из сценария:

```sql
select sc, price, start_date, end_date, pl_id from vpr_prices where sc = 16110;
```

и в кассе: сценарий `newcheck`, `item,16110,1`, `shot,price,check` —
цена в чеке равна цене из `VPR_PRICES`.

Чтобы **изменить** цену, её меняют в бэк-офисе (это его данные) и
повторяют обновление витрины. Менять `MVPR_PRICES_ACT` напрямую при
живом линке бессмысленно: следующий refresh всё перепишет.

## 4.3 Обновить цены на клоне без бэк-офиса (путь B)

В клоне `MVPR_PRICES_ACT` — обычная таблица со снимком. Цена для
проверки выставляется прямо в ней, в рамках транзакции, и после акта
возвращается:

```sql
-- что было
select id, sc, price, pl_id, start_date, end_date from mvpr_prices_act where sc = 16110 and end_date is null;
-- поставить проверочную цену
update mvpr_prices_act set price = 12.34 where sc = 16110 and end_date is null;
commit;
-- в кассе: newcheck, item,16110,1, shot - в чеке 12.34
-- вернуть
update mvpr_prices_act set price = <старая> where sc = 16110 and end_date is null;
commit;
```

Какой прайс-лист (`PL_ID`) действует для кассы, решает код фронта
(`VPR_PRICES` и настройки магазина в `TMS_INIT_PARAMS`) — **в этом акте
логика выбора прайс-листа не разбиралась**; если у товара несколько строк
с разными `PL_ID`, менять ту, которую `VPR_PRICES` отдаёт для этой кассы:

```sql
select * from vpr_prices where sc = 16110;
```

## 4.4 Проверка шага

| Проверка | Ожидается |
|---|---|
| `select count(*) from vpr_prices` | не ноль |
| цена товара сценария в `vpr_prices` и в чеке кассы | совпадает |
| после изменения цены (бэк-офис + refresh либо клон + update) | касса показывает новую цену в новом чеке |
| возврат цены после акта | `select` отдаёт прежнее значение |

Что здесь **не проверялось** в прошлом акте: обновление через DB link с
живым бэк-офисом на стенде (стенд был без бэк-офиса), отбор прайс-листа
по магазину.
