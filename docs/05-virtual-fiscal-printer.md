# 5. Виртуальный фискальный принтер

У кассы есть драйвер `VirtualFP` (`Drivers/FiscalPrintDevice/VirtualFP`):
печатает чек не в устройство, а в файл и в окно на экране. Это штатный
режим для стенда — на снимках кассы в этом режиме сверху видна строка
`Regim printer virtual!!!`.

## 5.1 Включить

Параметр `FiscalPrinter` читается **сначала из базы** (`TMS_INIT_PARAMS`),
потом из `cantina.ini`:

```ini
[General]
FiscalPrinter=VirtualFP
VirtualFPWindowWidth=520
VirtualFPCloseAfterSec=30
VirtualFPLineDelayMs=180
VirtualFPShotAtLine=6
AllowActivateVirtualFP=true
```

Если в базе стоит другой драйвер, он победит файл — проверить:

```sql
select pname, pvalue from tms_init_params where upper(pname) = 'FISCALPRINTER';
```

`AllowActivateVirtualFP=true` добавляет в меню кассы пункт включения
виртуального принтера на ходу — удобно, когда в базе прописан реальный.

## 5.2 Куда печатает

Рядом с `UAMenu.exe`:

```
VirtualCheckPrinter\
  2026_9_26\
    VPCheck_16_45_57.txt
```

Каталог на день (`ГГГГ_М_Д`, без ведущих нулей), файл на чек
(`VPCheck_ЧЧ_ММ_СС.txt`). Содержимое — текст чека, как он ушёл бы на
ленту:

```
------------------BEGIN_CHECK--------------------
<кассир>

<наименование товара 1>
***<наименование товара 2>
<наименование товара 3>
		 paid amount: 264.35
Bon <номер чека>.<касса>.<сервер>
<подвал>
                      003 Articole
------------------END_CHECK--------------------
```

Строка `Bon` — номер чека, номер кассы (`PosID`) и номер сервера; это
же число — в журнале самотеста (`чек N напечатан эмулятором`).

Второй выход — окно чека на экране (`uFiscalView`): строки появляются с
задержкой `VirtualFPLineDelayMs`, окно закрывается через
`VirtualFPCloseAfterSec`. Самотест снимает его шагом `shot,имя,fiscal`;
`VirtualFPShotAtLine` — после какой строки снимать.

## 5.3 Напечатать чек сценарием

Минимальный сценарий, который доводит чек до печати:

```ini
[Scenario]
1=log,=== chek na virtualnom printere ===
2=newcheck
3=item,16110,1
4=item,100516,2
5=shot,01-goods,check
6=pay,total
7=print
8=wait,2500
9=shot,02-receipt,fiscal
```

Шаг `print` работает **только** с виртуальным принтером: с реальным он
пропускается с записью `шаг print пропущен: текущий принтер не
виртуальный` — это защита, чтобы прогон не печатал на настоящую ленту.

## 5.4 Проверка шага

| Проверка | Ожидается |
|---|---|
| `selftest.log` | строка `чек N напечатан эмулятором` |
| `VirtualCheckPrinter\<день>\VPCheck_*.txt` | новый файл; внутри `BEGIN_CHECK`, позиции сценария, `paid amount`, `Bon N.<PosID>.<сервер>` |
| снимок `02-receipt.jpg` | окно чека с теми же строками |
| число позиций в подвале (`Articole`) | равно числу шагов `item` |

Что **не проверялось**: печать на реальных фискальных устройствах
(Datecs, Mercury, Elicom, IKC, TCP-сокет) — на стенде их нет; Z-отчёты и
смены виртуального принтера.
