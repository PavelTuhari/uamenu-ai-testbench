# 3. Настройка кассы

Касса — `UAMenu.exe`, рядом с ним `cantina.ini` и, для автоматического
прогона, `selftest.ini`. Собранный exe берётся у владельца либо
собирается из приватного репозитория:

```bat
call "C:\Program Files (x86)\Embarcadero\Studio\19.0\bin\rsvars.bat"
cd Sources\UAMenu
msbuild UAMenu.cbproj /t:Build /p:Config=Debug /p:Platform=Win32
```

Сборка полная, около 20 минут, результат — `Win32\Debug\UAMenu.exe`.
Исходники в двух кодировках: часть CP1251, часть UTF-8 с BOM; без BOM
компилятор читает кириллицу литералов как ANSI — не «чинить» кодировку.

Куда положить собранную кассу (отдельная папка рядом с UnaDesktop, не
`Program Files`), что из `Win32\Debug` переносить, в каком порядке касса
ищет `cantina.ini` и почему этот файл нельзя брать чужой —
[08-uamenu-install.md](08-uamenu-install.md). Прочитать **до** правки ini.

## 3.1 `cantina.ini`

Полный разбор всех ключей — в открытом репозитории
[cantina-ini](https://github.com/PavelTuhari/cantina-ini), `docs/cantina-ini.md`
(около 450 ключей), там же 65 настоящих примеров файла. Для стенда важен короткий
набор; шаблон — [templates/cantina.bench.ini](../templates/cantina.bench.ini).

| Ключ | Что | Для стенда |
|---|---|---|
| `Server` | TNS-имя базы | `FRONT` или `FREELOCAL` из шага 1.2 |
| `Schema` | схема фронта | имя схемы владельца либо `FA_FRONT` |
| `PosID` | номер кассы | как у владельца в тестовой схеме (в прошлом акте `101`) |
| `FiscalPrinter` | драйвер фискального принтера | `VirtualFP` — виртуальный, шаг 5 |
| `VirtualFPWindowWidth`, `VirtualFPCloseAfterSec`, `VirtualFPLineDelayMs`, `VirtualFPShotAtLine` | окно виртуального чека | `520`, `30`, `180`, `6` |
| `AllowActivateVirtualFP` | пункт меню «включить виртуальный принтер» | `true` |
| `RefreshUnirest` | обновлять витрины при старте через `unirest_mv_v.refersh_mv` | `false` на клоне без DB link, иначе касса будет ждать линк |
| `License26Server`, `License26Key`, `License26Site` | служба лицензий | адрес от владельца либо пусто — 30 дней ознакомительного периода |
| `PosApiKey`, `MIAClientSecret`, `MIAApiKey`, `MIAApiSecrect`, `licenseKey` | ключи внешних служб | **только пометки `@secret:`**, значения — в реестре |

Многие ключи читаются **сначала из базы** (`TMS_INIT_PARAMS`), потом из
файла — например `FiscalPrinter`. Если касса ведёт себя не по файлу,
смотреть параметр в базе:

```sql
select pname, pvalue from tms_init_params where upper(pname) = 'FISCALPRINTER';
```

Сравнить настройки двух баз или двух ini одной командой:
`python -m frontarchive settings diff <a> <b> [--ini]`.

## 3.2 Пароли — в реестр

Касса читает пометки `@secret:<файл>/<секция>/<ключ>` и берёт значение
из реестра пользователя Windows под DPAPI. Перенести:

```bat
cd Sources\UAMenu
python -m pypos secrets migrate Win32\Debug\cantina.ini          ; показать
python -m pypos secrets migrate Win32\Debug\cantina.ini --yes    ; перенести
python -m pypos secrets migrate Win32\Debug\selftest.ini --yes
python -m pypos secrets check Win32\Debug\cantina.ini            ; все пометки читаются
```

Значения никогда не печатаются. Переносить **под тем пользователем
Windows, под которым будет работать касса**. Подробно — `docs/secrets.md`
в приватном репозитории.

## 3.3 `selftest.ini` — автоматический прогон

Если рядом с `UAMenu.exe` лежит `selftest.ini`, касса входит в базу сама
(секция `[Login]`), выполняет сценарий из `[Scenario]`, снимает экраны и
пишет журнал. Шаблон — [templates/selftest.bench.ini](../templates/selftest.bench.ini).

```ini
[Login]
User=Tolik
Password=@secret:selftest.ini/Login/Password
Schema=<схема>
SchemaPassword=@secret:selftest.ini/Login/SchemaPassword
Server=<TNS>

[Test]
OutDir=SelfTest        ; каталог результатов, внутри подкаталог с датой-временем
Screenshots=1
StepDelay=900          ; пауза между шагами, мс
KeepOpenCheck=0        ; 1 - не отменять открытый чек в конце
CloseAfter=1           ; закрыть кассу по окончании
License=0              ; 1 - регистрироваться в службе лицензий как в бою
```

### Язык сценария

Строка `N=команда,аргумент1,аргумент2`. Команды — ровно те, что
понимает `uSelfTest.cpp`:

| Команда | Аргументы | Что делает |
|---|---|---|
| `log,текст` | текст | строка в журнал |
| `wait,мс` | миллисекунды | пауза с живым интерфейсом |
| `shot,имя,форма` | форма: `main`, `check`, `fiscal`, `wallet`, `pay`, `paywin`, `multipay`, `screen`; пусто — активная | снимок `.jpg` в каталог прогона |
| `newcheck` | — | открыть чек |
| `item,код,кол-во` | код товара (SC), количество (по умолчанию 1) | позиция в чек |
| `card,номер,тип` | тип `1` — дисконтная (`TMS_DCARD`), `6` — столовая (`pkg_cards`, `MVMS_CARDS`) | приложить карту |
| `bonus,сумма` | сумма или `max` | списать баллы |
| `pay,сумма` | сумма или `total` | внести оплату наличными |
| `print` | — | напечатать чек; **только виртуальный принтер**, иначе шаг пропускается с записью в журнал |
| `cancel` | — | отменить чек |
| `coupon,штрихкод` / `couponsell,штрихкод` / `couponinfo,штрихкод` | штрихкод купона | погасить / выдать / показать купон |
| `addpay,метод,сумма` | id метода оплаты, сумма | внести оплату выбранным методом |
| `multipay` / `closemultipay` | — | открыть / закрыть окно методов оплаты |
| `paywin` / `closepay` | — | открыть / закрыть окно оплаты наличными |
| `posapi,member,карта` / `posapi,txn` / `posapi,void,причина` | | обращения к POS API лояльности по текущему чеку |
| `simcard,номер,баланс,ставка` | | имитация карты лояльности без сети |
| `walletshow` / `wallet,баланс,ставка` / `walletapply` | | карточка кошелька: показать, задать, списать |
| `mia,сумма` / `miarest,сумма` | | оплата MIA (QR) |
| `ledger,что,карта,...` | | счёт лояльности в местной книге |
| `ts,команда,аргумент` | | команда экрану тачскрина |
| `state` | — | состояние кассы в журнал |

Модальные окна, которые появятся по ходу (предупреждения, подтверждения),
снимает и закрывает сторож прогона — снимки `dialog-N.jpg`, в журнале
их текст.

### Что получается

`Win32\Debug\SelfTest\<ГГГГ-ММ-ДД_ЧЧ-ММ-СС>\`:

```
selftest.log      журнал: вход, каждый шаг, тексты окон, итог "успешно N, с ошибками M"
01-start.jpg      снимок до сценария
NN-<имя>.jpg      снимки шагов shot
dialog-N.jpg      закрытые сторожем окна
NN-finish.jpg     снимок после
```

Рядом с exe: `license.log` (всё, что касса делает по лицензии) и
`VirtualCheckPrinter\ГГГГ_М_Д\VPCheck_ЧЧ_ММ_СС.txt` — чеки виртуального
принтера (шаг 5).

## 3.4 Проверка шага

Запустить `UAMenu.exe` с шаблонным `selftest.ini`, где сценарий —
только `log`, `wait,6000`, `shot,01-main,main`. Ожидается: в
`selftest.log` строка `автовход: кассир ..., схема ..., сервер ...`,
затем `главная форма показана`, итог `успешно 3, с ошибками 0`; в
журнале **нет** значения пароля (проверить поиском по файлу).
