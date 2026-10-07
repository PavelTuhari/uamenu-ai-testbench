# 1. Машина

Windows 10/11 x64. Всё ставится на локальный диск; сетевые диски для
Oracle не годятся. Права администратора нужны **только** для установки
Oracle Free и Instant Client — всё остальное работает под обычным
пользователем, и работать касса должна под ним же (секреты в реестре
привязаны к пользователю Windows).

## 1.1 Что ставить

| Что | Откуда | Зачем |
|---|---|---|
| RAD Studio 19 (Tokyo), C++Builder Win32 | лицензия владельца | собрать `UAMenu.cbproj` (около 20 минут, `msbuild`) |
| Компоненты `Sources/Cmp` + ODAC, DevExpress, EurekaLog | владелец | без них проект не соберётся |
| Oracle Instant Client 19 (basic) | oracle.com, без логина | толстый режим `oracledb` для Python; ходит и в 11.2, и в 23ai |
| Python 3.12 + `pip install oracledb keyring flask cryptography` | python.org | `pypos`, FrontArchive, License26 |
| Oracle AI Database Free (26ai / 23ai) | oracle.com, без логина | локальная база под клон фронта; см. 1.3 |
| Git + `gh` | git-scm.com, cli.github.com | исходники |
| Microsoft Edge | есть в Windows | безголовые снимки дашбордов (не обязательно) |

Проверка одной командой (из корня этого комплекта):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\check-prereqs.ps1
```

Скрипт печатает таблицу «есть / нет» по каждому пункту и ничего не
меняет.

## 1.2 Instant Client и TNS

Распаковать в `C:\oracle\instantclient_19_xx`. Если каталог другой —
задать `ORACLE_CLIENT_DIR`. Файл `tnsnames.ora` положить в каталог,
на который указывает `TNS_ADMIN` (системная переменная), например
`C:\oracle\admin\tnsnames.ora`:

```
FRONT = (DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=<хост-фронта>)(PORT=1521))(CONNECT_DATA=(SERVICE_NAME=<служба>)))
FREELOCAL = (DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=localhost)(PORT=1522))(CONNECT_DATA=(SERVICE_NAME=FREEPDB1)))
```

Касса читает `Server=<имя TNS>` из `cantina.ini`, поэтому имена здесь —
те же, что потом в настройках кассы.

**Внимание:** установщик Oracle Free отказывается ставить, пока задана
`TNS_ADMIN`. Скрипт из 1.3 снимает её на время установки и возвращает;
если ставите вручную — снять самим.

## 1.3 Oracle Free — локальная база

Нужна, чтобы поднять клон фронта из архива и не ходить в чужую базу.
Скрипт [scripts/install-oracle-free.ps1](../scripts/install-oracle-free.ps1)
проверен на Windows 10 с Oracle AI Database Free 26ai (23.26.3). Что он
делает и почему именно так — четыре грабли, на которых установка
останавливалась молча:

| Что случается | Почему | Что делает скрипт |
|---|---|---|
| `setup.exe` отрабатывает 5 минут и выходит с кодом 0, не поставив ничего | он сперва ставит пакет VC++; тот нашёл свою DLL занятой, пометил «нужна перезагрузка», установщик на этом остановился | запускает сам `msiexec /i "...msi" RSP_FILE=... /qn` |
| в журнале `Folder is not secure`, `INSTALLDIR_SECURE_VAL_RES = FAILED` | проверяется **вся цепочка** каталогов назначения: в них не должен писать кто угодно | создаёт цепочку с выключенным наследованием, доступ только `SYSTEM` и администраторам |
| `SEVERE: ... ORACLE_HOME and TNS_ADMIN` | системная `TNS_ADMIN` задана | снимает на время установки, возвращает в `finally` |
| `port ... is not available` при свободном 1521 | проверка видит **любые** соединения с номером 1521, даже к удалённой базе | ставит слушатель на **1522** |

Запуск — от имени администратора, из каталога, куда распакован
дистрибутив (`setup.exe`, `*.msi`, `FREEInstall.rsp` рядом):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-oracle-free.ps1 `
    -InstallerDir D:\OracleFree -InstallDir D:\Oracle26ai\product\26ai -Port 1522
```

Пароль `SYS` скрипт создаёт случайным и кладёт в хранилище учётных данных
Windows (служба `oraclefree:local`, пользователь `SYS`); в журнал
установки он не попадает — журнал вычищается. Своё значение — ключ
`-AskPassword` (ввод с клавиатуры, не отображается).

Проверка после установки:

```powershell
Get-Service OracleServiceFREE, *TNSListener*
netstat -ano | findstr :1522
```

Ожидается: обе службы `Running`, порт `LISTENING`. Контейнер для схем —
`FREEPDB1`.

## 1.4 Пароли — только в хранилище

Ни один инструмент комплекта не принимает пароль аргументом командной
строки и не хранит его в файле. Единый приём — пароль из файла, который
тут же затирается:

```bat
echo пароль> p.txt
python -m frontarchive password <цель> --file p.txt
```

Для `pypos`, `License26` и FrontArchive хранилище общее: службы
`pypos:<алиас>`, `license26:<алиас>`, `frontarchive:<алиас>` в
Credential Manager, пользователь — имя схемы Oracle. Положенный один раз
пароль видят все три.

## 1.5 Что должно получиться

`check-prereqs.ps1` без единого «НЕТ» по обязательным пунктам, Oracle
Free слушает 1522, `python -c "import oracledb, keyring, flask"` молчит,
`tnsping`-аналог — `python -m pypos sql` или `sqlplus` — доходит до базы
фронта (или до локальной, если бэк-офиса на стенде нет).
