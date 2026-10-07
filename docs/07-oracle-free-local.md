# 7. Oracle Database Free локально — всё, что известно

Собрано по установке на машине владельца (Windows 10 Pro x64 22H2,
Oracle AI Database Free 26ai, сборка 23.26.3, сентябрь 2026) и по
последующей работе с ней. Автоматизирует это
[scripts/bootstrap_oracle_free.py](../scripts/bootstrap_oracle_free.py),
задание для ИИ — [AI-TASK.md](../AI-TASK.md).

## Что это и что не это

* **Oracle Database Free** (раньше XE) — бесплатная локальная база с
  oracle.com, без логина и без лицензионного ключа, можно использовать
  в том числе в бою. Лимиты: 12 ГБ данных, 2 ГБ ОЗУ, 2 потока.
* **Always Free** — облачный тариф Oracle Cloud (OCI), другая вещь.
  Для стенда кассы нужна локальная база.
* Текущая линейка — «26ai» (внутренняя версия 23.x). Файл дистрибутива
  в сентябре 2026: `oracle-ai-database-free-26ai-23.26.3.windows.x64.zip`,
  1,4 ГБ. Имя меняется от выпуска к выпуску — скрипт ищет его на
  странице https://www.oracle.com/database/free/get-started/ по образцу
  `.../db-free/*windows*.zip`.
* Старая `XE 21c` (`OracleXE213_Win64.zip`, 1,97 ГБ) всё ещё лежит на
  oracle.com и официально поддерживает Windows 10; у 26ai в MSI проверка
  ОС только «не Windows 9x/XP/2003» — на Windows 10 ставится.

## Что ставится

| Что | Где |
|---|---|
| Домашний каталог | `<InstallDir>\dbhomeFree` (sqlplus, lsnrctl там в `bin`) |
| Службы | `OracleServiceFREE`, `OracleOraDB23Home1TNSListener`, автозапуск |
| База | контейнер `FREE`, подключаемая `FREEPDB1` — **схемы приложений заводятся в ней** |
| Кодировка | `AL32UTF8` (так в файле ответов) |
| Слушатель | порт из файла ответов; у нас **1522** |
| Пароль SYS/SYSTEM | один на обоих, из файла ответов; скрипт кладёт его в хранилище учётных данных Windows и затирает файл |

Подключение к контейнеру приложений:

```
sys/<пароль>@//localhost:1522/FREEPDB1 as sysdba
<схема>/<пароль>@//localhost:1522/FREEPDB1
```

В `tnsnames.ora`: `FREELOCAL = (DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=localhost)(PORT=1522))(CONNECT_DATA=(SERVICE_NAME=FREEPDB1)))`.

## Тихая установка: как на самом деле

Дистрибутив — InstallShield (`setup.exe`) поверх MSI. Файл ответов
`FREEInstall.rsp` рядом с ними:

```
INSTALLDIR=D:\Oracle26ai\product\26ai\
PASSWORD=<пароль>
LISTENER_PORT=1522
CHAR_SET=AL32UTF8
DB_DOMAIN=
SOFTWARE_ONLY=FALSE
MODIFY_DIRECTORY_PERMISSIONS=TRUE
```

Рабочая команда — **MSI напрямую**, не `setup.exe`:

```
msiexec /i "Oracle AI Database 26ai Free.msi" /qn /L*v install.log RSP_FILE="<путь>\install.rsp" REBOOT=ReallySuppress
```

Четыре причины, по которым иначе не получалось (каждая стоила одной
неудачной попытки):

| Симптом | Причина | Решение |
|---|---|---|
| `setup.exe` работает 5 мин, код 0, ничего не поставлено, нет `install.log` | он сперва ставит VC++ Redistributable; тот нашёл `vcruntime140.dll` занятой другими процессами, записал «нужна перезагрузка», и `setup.exe` на этом остановился | звать `msiexec` на MSI напрямую; перезагрузка не нужна |
| в журнале `INSTALLDIR_SECURE_VAL_RES = FAILED`, `Folder is not secure` | кастом-экшен обходит **все** каталоги пути назначения и требует, чтобы в них не могли писать обычные пользователи; `MODIFY_DIRECTORY_PERMISSIONS=TRUE` этого не спасает для родителей | создать цепочку каталогов заранее: наследование выключено, доступ только `SYSTEM` и `Администраторы`; не класть базу в каталог с общим доступом |
| `SEVERE: Verify that the following environment variables are not set: ORACLE_HOME and TNS_ADMIN` | задана системная `TNS_ADMIN` (на машине с Instant Client она есть почти всегда) | снять на время установки и вернуть; служба установщика читает окружение при старте, поэтому она должна быть остановлена в этот момент (обычно и так) |
| `SEVERE: The provided port for Oracle listener configuration is not available` при свободном 1521 | проверка видит **любое** TCP-соединение с номером 1521, включая исходящие к удалённой базе | `LISTENER_PORT=1522` |

После установки: журнал содержит значения свойств, пароль в нём
маскируется MSI (`**********`), но на всякий случай скрипт вычищает его
по значению. Файл ответов затирается случайными байтами и удаляется.

Время: ~5 мин на MSI, затем создание базы — всего 15–25 мин.

## Проверка

```powershell
Get-Service OracleServiceFREE, *TNSListener*          # Running, Automatic
netstat -ano | findstr :1522                          # LISTENING
& "<InstallDir>\dbhomeFree\bin\sqlplus.exe" -S "sys/<пароль>@//localhost:1522/FREE as sysdba"
  select version from v$instance;                     # 23.0.0.0.0
```

Из Python (Instant Client 19 ходит в 23ai без вопросов):

```python
import oracledb, keyring
oracledb.init_oracle_client(lib_dir=r"C:\oracle\instantclient_19_28")
pw = keyring.get_password("frontarchive:freelocal", "SYS")
c = oracledb.connect(user="sys", password=pw, dsn="localhost:1522/FREEPDB1", mode=oracledb.AUTH_MODE_SYSDBA)
```

## Схема кассы в этой базе

Заводится и наполняется FrontArchive из архива `.fza` (шаг 2):
`restore <архив> --to free-front --create-schema`. Важное про
совместимость, уже учтённое в FrontArchive:

* **Длины строк.** Источник — 11.2 в `CL8MSWIN1251` (байт = знак),
  приёмник — `AL32UTF8`. `VARCHAR2(50)` в байтах не вместит 50
  кириллических знаков → `ORA-12899`. Решение: `alter session set
  nls_length_semantics = 'CHAR'` перед созданием таблиц.
* **Строгость 23ai.** Код, который компилировался на 11.2, может не
  скомпилироваться (`PLS-00364 loop index variable`): это найдёт
  перекомпиляция, объект останется невалидным — в отчёт.
* **Платформенная схема `UN4PUBLIC`.** Без неё 57 объектов клона
  невалидны (зовут `MSG`/`SAY`/`WARN`/`ENVUNIREST`); с ней — 9. Ставит её
  владелец. Её DDL-триггер `BEFORE_CREATE` не даёт создавать пакеты `UN$*`
  в других схемах — это правило платформы, `restore` покажет отказ на
  `UN$BCOD`.
* **DB link к бэк-офису** в клон не переносится (в описании хеш пароля).
  Витрины приезжают таблицами-снимками.
* `DBMS_CRYPTO` на 23ai знает SHA-256 — но пакеты, писанные под 11.2
  (например License26), нарочно считают SHA-1 (`c_hash_alg := 3`): менять
  нельзя, иначе хеши в данных перестанут сходиться.

## Эксплуатация

* Остановить/запустить: `Stop-Service OracleServiceFREE` / `Start-Service`.
* Все пароли (`SYS`, схемы) — в хранилище учётных данных Windows под
  `frontarchive:freelocal` (пользователь = имя схемы). Сменить пароль
  схемы: `alter user ... identified by` под SYS и положить новое значение
  в хранилище (`python -m frontarchive password free-front --file p.txt`).
* Снести: «Программы и компоненты» → Oracle AI Database Free; каталог
  базы потом удалить руками (он закрыт для обычного пользователя).
* Второй экземпляр на машине не ставится; вторая схема — просто второй
  пользователь в `FREEPDB1` (`restore --to <другая цель>`).

## Что не проверялось

Windows 11 и Windows Server; обновление с XE 21c на 26ai; работа базы
после перезагрузки с отложенным обновлением VC++ (у владельца перезагрузка
так и висела, база работала).
