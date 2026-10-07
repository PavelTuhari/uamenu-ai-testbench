# 2. База фронт-офиса

Касса работает со **схемой фронт-офиса** в Oracle: 171 таблица
(из них 58 — контейнеры материализованных представлений, витрины
бэк-офиса), 114 представлений, 50 пакетов, 44 триггера, DB link к
бэк-офису. Схема опирается на общую платформенную схему `UN4PUBLIC`
(процедуры `MSG`, `SAY`, `WARN`, пакет `ENVUNIREST`, видны через
public-синонимы).

На стенде есть два пути.

## 2.1 Путь A: подключиться к тестовой базе владельца

Проще всего, если владелец даёт сетевой доступ к тестовой схеме фронта.
Тогда база уже «правильная»: `UN4PUBLIC` есть, DB link есть, витрины
обновляются. От вас: строка в `tnsnames.ora` (шаг 1.2) и пароль в
хранилище:

```bat
cd RAD_Tokyo\Sources\FrontArchive
copy targets.sample.ini targets.ini      ; поправить dsn/user/vault под цель
echo пароль> p.txt
python -m frontarchive password front --file p.txt
python -m frontarchive targets           ; связь, версия, число объектов
python -m frontarchive describe front
```

Ожидается: `Oracle Database 11g ... 11.2.0.4.0` (или другая версия
владельца), кодировка `CL8MSWIN1251`, объекты по типам, число невалидных
(в тестовой схеме владельца их 4 — это норма этой схемы, не стенда).

## 2.2 Путь B: клон из архива в локальную Oracle Free

Владелец передаёт архив `.fza` (FrontArchive, шаг 0). Поднимаем схему
клона командой, которая создаёт пользователя, объекты, грузит данные,
ставит индексы и ключи, перекомпилирует и сверяет число строк:

```bat
python -m frontarchive restore <архив>.fza --to free-front --create-schema
```

Цель `free-front` в `targets.ini`:

```ini
[free-front]
title     = Клон фронта на локальной Oracle Free
dsn       = localhost:1522/FREEPDB1
user      = FA_FRONT
vault     = freelocal
sys_vault = freelocal          ; пароль SYS лежит как frontarchive:freelocal / SYS (шаг 1.3)
role      = clone
```

Что ожидать на архиве владельца (170 таблиц без фотографий, 1,32 млн
строк, 13 МБ): около 3 минут, `расхождений 0`, `ошибок DDL 0`. Итог
печатает число невалидных объектов и **чего им не хватает**:

| Состояние сервера | Невалидных | Чего не хватает |
|---|---|---|
| чистая Oracle Free, `UN4PUBLIC` нет | 57 | `MSG` (159 ссылок), `SAY` (48), `ENVUNIREST` (35), `WARN` (9), DB link (7), `DBMS_RLS`/`DBMS_LOCK` (4), исключённая таблица фотографий (1), строгость 23ai к старому коду (3) |
| `UN4PUBLIC` поставлена | 9 | пять пакетов на DB link `ORA64.WORLD`, `UNIREST_POLICY` (grant на `DBMS_RLS`), `PKG_ADMIN_UTILS_POS` (`PLS-00364`), три представления |

Это граница того, что переносится без прав DBA, а не ошибка переноса.
Для кассы это означает: продажи, карты, оплаты и печать работают;
не работает то, что зовёт бэк-офис напрямую.

**Правило платформы:** если `UN4PUBLIC` стоит, её DDL-триггер
`BEFORE_CREATE` не даст создать в клоне пакет `UN$BCOD`
(`ORA-20000: PACKAGE UN$BCOD MUST BE OWNED BY USER UN4PUBLIC`). `restore`
покажет это как отказ — так и должно быть, обходить нельзя.

Материализованные представления в клоне — **обычные таблицы со снимком
данных**: клон не зависит от связи с бэк-офисом. Цены в нём статичны
(шаг 4). Ключ `--mv mv` переносит их как MV — тогда нужен DB link.

## 2.3 DB link к бэк-офису

Витрины фронта (`MV*`) берут данные из бэк-офиса через
`BONUS2019_07.WORLD`:

```sql
select db_link, username, host from user_db_links;
-- BONUS2019_07.WORLD  BONUS2019_07  <TNS-имя бэк-офиса>
```

На клоне линка нет (его описание содержит хеш пароля и не переносится).
Если бэк-офис на стенде есть, линк создаёт **владелец или вы по его
паролю из хранилища** — пароль в SQL не печатать, подставить из файла,
который затем затереть:

```sql
create database link BONUS2019_07.WORLD
  connect to BONUS2019_07 identified by "<пароль из файла>"
  using '<TNS-имя или host:port/service>';

select 1 from dual@BONUS2019_07.WORLD;              -- линк жив
begin unirest_mv_v.check_conection; end;             -- проверка платформы
```

Если бэк-офиса нет — так и пишется в акте: «DB link не настраивался,
витрины статичны». Касса от этого **не перестаёт запускаться**.

## 2.4 Проверка шага

```bat
python -m frontarchive describe free-front
python -m frontarchive settings diff front free-front     ; если доступны обе
```

Ожидается: 170 таблиц, пакеты и представления на месте, невалидных —
как в таблице выше с объяснением причин; `settings diff` сразу после
клона — разниц 0 (в прошлом акте: 186 параметров `TMS_INIT_PARAMS`
одинаковы).

`cantina.ini` кассы, если владелец сохранял его в схему (`ini save`),
приедет вместе с клоном:

```sql
select cantina_ini.get_value('PosID') from dual;
select cantina_ini.get_settings_file() from dual;    -- CLOB с файлом
```

и его можно выложить на диск байт в байт:
`python -m frontarchive ini pull free-front --out C:\bench\ini`.
