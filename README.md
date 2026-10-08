# UAMenu — стенд для стороннего ИИ или инженера

> **In English, briefly.** This is the public kit for deploying the UAMenu
> point-of-sale (C++Builder + Oracle) on an empty Windows machine and
> producing a reproducible test act: set up Oracle, restore a front-office
> schema, configure the DB link to the back office, refresh prices, print
> a receipt on the virtual fiscal printer, run the built-in self-test with
> screenshots. Sources, data and passwords are **not** here — the owner
> hands them over privately (see `docs/00-handover.md`). Everything else
> is: step by step, with expected outputs and with an explicit list of what
> was not verified.

Это открытый комплект для того, кто разворачивает кассу **UAMenu** на
пустом компьютере и снимает по ней акт тестирования — человека или
ИИ-агента. Комплект самодостаточен в части *знаний*: что ставить, в каком
порядке, какими командами проверять, что должно получиться и что
считается сбоем. Он **не содержит** исходников, данных и паролей — это
передаёт владелец отдельно, список в [docs/00-handover.md](docs/00-handover.md).

## Быстрый путь: одна команда и задание для ИИ

Если стенд — это **локальная Oracle Database Free** (бесплатная база с
oracle.com; не путать с облачным «Always Free»), то скачивание свежего
дистрибутива, установку с обходом известных ловушек и импорт копии
кассовой схемы делает один скрипт:

```bat
python scripts\bootstrap_oracle_free.py --work D:\OracleFree --archive D:\handover\front.fza --frontarchive D:\RAD_Tokyo\Sources\FrontArchive
```

Задание для ИИ-агента, который это выполняет и чинит нюансы по ходу,
с экономией токенов: **[AI-TASK.md](AI-TASK.md)**. Всё известное про
локальную Oracle Free — [docs/07-oracle-free-local.md](docs/07-oracle-free-local.md).

## Путь целиком

| Шаг | Документ | Итог шага |
|---|---|---|
| 0 | [00-handover.md](docs/00-handover.md) | получено от владельца всё, без чего не двинуться |
| 1 | [01-machine-setup.md](docs/01-machine-setup.md) | RAD Studio, Instant Client, Python, Oracle Free; `check-prereqs.ps1` зелёный |
| 2 | [02-database.md](docs/02-database.md) | схема фронта поднята из архива, DB link к бэк-офису настроен или осознанно пропущен |
| 3 | [03-till-config.md](docs/03-till-config.md) | `cantina.ini` и `selftest.ini` готовы, пароли в реестре, касса запускается и входит в базу |
| 4 | [04-prices.md](docs/04-prices.md) | цены обновлены из бэк-офиса либо выставлены на стенде, касса их показывает |
| 5 | [05-virtual-fiscal-printer.md](docs/05-virtual-fiscal-printer.md) | чек напечатан виртуальным фискальным принтером, файл чека на диске |
| 6 | [06-test-act.md](docs/06-test-act.md) | акт: сценарий, снимки, журналы, таблица «ожидалось / получено», чего не проверяли |
| 7 | [07-oracle-free-local.md](docs/07-oracle-free-local.md) | всё про локальную Oracle Database Free: что ставится, тихая установка и её ловушки, схема кассы в ней |
| 8 | [08-uamenu-install.md](docs/08-uamenu-install.md) | касса как отдельная папка рядом с UnaDesktop; что в ней лежит; порядок поиска и роль `cantina.ini` |

## Что здесь лежит

```
AI-TASK.md   задание ИИ-агенту: запустить скрипт, починить упавший шаг, отчитаться
docs/        восемь шагов, по одному файлу, с командами и ожидаемым выводом
scripts/     bootstrap_oracle_free.py - скачать, поставить Oracle Free, импортировать схему;
             install-oracle-free.ps1 - тихая установка (его зовёт bootstrap); check-prereqs.ps1 - проверка машины
templates/   cantina.bench.ini - настройки кассы для стенда; selftest.bench.ini - сценарий прогона
```

## Правила, без которых акт не акт

1. **Ничего не делается по памяти.** Каждое утверждение в акте — с
   командой, которая его показала, и с её выводом.
2. **Пароли не попадают ни в файлы, ни в вывод, ни в журналы.** Они лежат
   в хранилище учётных данных Windows и в реестре под DPAPI; в `ini`
   стоят пометки `@secret:`. Если в журнале прогона всплыло значение
   пароля — это сбой акта.
3. **Касса обязана запускаться всегда.** Ни отсутствие лицензии, ни
   недоступный принтер, ни недоступный бэк-офис не имеют права помешать
   запуску. Если касса не поднялась — это ошибка стенда, а не поведение
   продукта.
4. **Пробные записи в общую базу — только с откатом**, либо с уборкой и
   проверкой, что следа не осталось.
5. **«Не проверяли» пишется словами.** Лучше строка «реальный фискальный
   принтер не подключали», чем молчаливый пропуск.

## Рядом

* **[cantina-ini](https://github.com/PavelTuhari/cantina-ini)** — всё про
  файл настроек кассы: справочник ~450 ключей, собранный из исходников,
  порядок поиска файла, хранилище секретов, утилита `cfgtool` и 65
  настоящих `cantina.ini` разных точек с вычищенными паролями и адресами.
  Шаг 3 и шаг 8 здесь — краткая выжимка оттуда.

## Что честно сказать заранее

* Сборка кассы требует **RAD Studio 19 (Tokyo)** и коммерческих
  компонентов (ODAC, DevExpress, EurekaLog) — лицензии владельца, в
  открытом доступе их нет. Без них стенд работает только с готовым
  `UAMenu.exe` от владельца.
* Схема фронт-офиса зависит от общей платформенной схемы `UN4PUBLIC`
  и от бэк-офиса через DB link. Клон на чистом сервере без них поднимается
  и работает, но часть пакетов остаётся невалидной — какие и почему, см.
  шаг 2.
* Этот комплект собран по акту, который делался на машине владельца
  в сентябре 2026 года: Oracle 11.2 как источник, Oracle Free 23ai как
  приёмник, Windows 10. Другие сочетания здесь не проверялись.
