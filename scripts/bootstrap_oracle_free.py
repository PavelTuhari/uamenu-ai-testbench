# -*- coding: utf-8 -*-
r"""Oracle Database Free на этой машине + кассовая схема из архива. Одной командой.

    python scripts\bootstrap_oracle_free.py --work D:\OracleFree ^
        --archive D:\handover\front.fza --frontarchive D:\RAD_Tokyo\Sources\FrontArchive

Шаги (каждый пропускается, если уже сделан; любой можно пропустить ключом):

  1. url        найти на oracle.com свежий дистрибутив Oracle Database Free для Windows
  2. download   скачать с докачкой (1,4 ГБ)
  3. extract    распаковать (zipfile, без 7-Zip)
  4. client     Oracle Instant Client, если его нет (нужен Python-инструментам)
  5. install    установить базу: install-oracle-free.ps1 от имени администратора (окно UAC)
  6. restore    создать схему и восстановить архив .fza средствами FrontArchive
  7. verify     проверить: службы, порт, подключение, число объектов

Паролей в скрипте нет: SYS создаётся установщиком случайным и ложится в
хранилище учётных данных Windows (frontarchive:freelocal / SYS), пароль
схемы клона - туда же (frontarchive:freelocal / <схема>).

Полностью автономным это быть не может: UAC нажимает человек, у oracle.com
меняются имена файлов, у машины свои особенности. Поэтому каждый шаг
отдельный, печатает, что именно он сделал и чем закончилось, и падает с
подсказкой, что смотреть. Чинить - только упавший шаг, потом запуск с
--skip-<сделанные>.
"""
from __future__ import unicode_literals
import sys, io, os, re, json, time, socket, zipfile, argparse, subprocess, urllib.request

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = "https://www.oracle.com/database/free/get-started/"
URL_PATTERN = re.compile(r"https://download\.oracle\.com/otn-pub/otn_software/db-free/"
                         r"[A-Za-z0-9._-]*(?:windows|WINDOWS)[A-Za-z0-9._-]*\.zip")
CLIENT_URL = "https://download.oracle.com/otn_software/nt/instantclient/instantclient-basic-windows.zip"
VAULT = "freelocal"          # frontarchive:freelocal - так его ищет FrontArchive
UA = {"User-Agent": "Mozilla/5.0 (uamenu-ai-testbench bootstrap)"}


def say(text):
    print(time.strftime("%H:%M:%S") + "  " + text, flush=True)


def fail(step, text, hint):
    say("СБОЙ на шаге %s: %s" % (step, text))
    say("что смотреть: " + hint)
    say("после исправления: повторить с --skip-<сделанные шаги>")
    sys.exit(10)


def http_head_size(url):
    req = urllib.request.Request(url, method="HEAD", headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return int(r.headers.get("Content-Length") or 0), r.geturl()

# -------------------------------------------------------------------- 1. url ---

def find_url(explicit):
    if explicit:
        return explicit
    say("ищу дистрибутив на " + PAGE)
    try:
        with urllib.request.urlopen(urllib.request.Request(PAGE, headers=UA), timeout=60) as r:
            html = r.read().decode("utf-8", "replace")
    except Exception as error:
        fail("url", "страница oracle.com не прочиталась: %s" % error,
             "сеть/прокси; либо передать ссылку вручную: --url https://download.oracle.com/otn-pub/otn_software/db-free/<файл>.windows.x64.zip")
    found = sorted(set(URL_PATTERN.findall(html)))
    if not found:
        fail("url", "на странице нет ссылки на Windows-дистрибутив",
             "Oracle переделал страницу. Открыть %s, найти 'Windows x64' zip и передать --url" % PAGE)
    url = found[-1]
    say("дистрибутив: " + url.rsplit("/", 1)[-1])
    return url

# --------------------------------------------------------------- 2. download ---

def download(url, work):
    os.makedirs(work, exist_ok=True)
    path = os.path.join(work, url.rsplit("/", 1)[-1])
    try:
        total, _ = http_head_size(url)
    except Exception as error:
        fail("download", "HEAD не прошёл: %s" % error, "сеть; ссылка могла устареть - шаг url заново без --skip-url")
    have = os.path.getsize(path) if os.path.isfile(path) else 0
    if total and have == total:
        say("уже скачан: %s, %.1f МБ" % (os.path.basename(path), total / 1048576.0))
        return path
    say("качаю %.1f МБ%s" % (total / 1048576.0, " (докачка с %.1f МБ)" % (have / 1048576.0) if have else ""))
    req = urllib.request.Request(url, headers=dict(UA, **({"Range": "bytes=%d-" % have} if have else {})))
    with urllib.request.urlopen(req, timeout=120) as r, open(path, "ab" if have else "wb") as f:
        done = have
        last = time.time()
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if time.time() - last > 15:
                say("  %.0f%%" % (100.0 * done / total if total else 0))
                last = time.time()
    if total and os.path.getsize(path) != total:
        fail("download", "размер не сошёлся: %d из %d" % (os.path.getsize(path), total),
             "повторить шаг - докачает; если не сходится упорно, удалить файл")
    say("скачан: " + os.path.basename(path))
    return path

# ---------------------------------------------------------------- 3. extract ---

def extract(zip_path, work):
    if os.path.isfile(os.path.join(work, "setup.exe")) and any(n.lower().endswith(".msi") for n in os.listdir(work)):
        say("уже распакован: setup.exe и .msi на месте")
        return
    say("распаковываю " + os.path.basename(zip_path))
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(work)
    if not os.path.isfile(os.path.join(work, "setup.exe")):
        # дистрибутив мог лежать в подкаталоге
        for root, _, files in os.walk(work):
            if "setup.exe" in files and root != work:
                fail("extract", "setup.exe оказался в %s" % root,
                     "передать --work %s и продолжить с --skip-url --skip-download --skip-extract" % root)
        fail("extract", "после распаковки нет setup.exe", "посмотреть содержимое %s" % work)
    say("распакован в " + work)

# ----------------------------------------------------------------- 4. client ---

def ensure_client():
    for cand in (os.environ.get("ORACLE_CLIENT_DIR", ""), r"C:\oracle\instantclient_19_28", r"C:\oracle\instantclient"):
        if cand and os.path.isfile(os.path.join(cand, "oci.dll")):
            say("Instant Client есть: " + cand)
            os.environ["ORACLE_CLIENT_DIR"] = cand
            return cand
    found = [os.path.join(r"C:\oracle", d) for d in (os.listdir(r"C:\oracle") if os.path.isdir(r"C:\oracle") else [])
             if d.lower().startswith("instantclient")]
    for cand in found:
        if os.path.isfile(os.path.join(cand, "oci.dll")):
            say("Instant Client есть: " + cand)
            os.environ["ORACLE_CLIENT_DIR"] = cand
            return cand
    say("Instant Client не найден - качаю basic с oracle.com")
    target = r"C:\oracle\instantclient"
    zpath = os.path.join(os.path.dirname(target), "instantclient-basic-windows.zip")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    try:
        req = urllib.request.Request(CLIENT_URL, headers=UA)
        with urllib.request.urlopen(req, timeout=120) as r, open(zpath, "wb") as f:
            f.write(r.read())
        with zipfile.ZipFile(zpath) as z:
            names = z.namelist()
            z.extractall(os.path.dirname(target))
        inner = os.path.join(os.path.dirname(target), names[0].split("/")[0])
        if os.path.isdir(inner) and inner != target:
            if os.path.isdir(target):
                import shutil; shutil.rmtree(target)
            os.rename(inner, target)
    except Exception as error:
        fail("client", "Instant Client не скачался/не распаковался: %s" % error,
             "скачать basic zip вручную с oracle.com, распаковать в C:\\oracle\\instantclient, задать ORACLE_CLIENT_DIR")
    os.environ["ORACLE_CLIENT_DIR"] = target
    say("Instant Client: %s (задайте ORACLE_CLIENT_DIR=%s постоянно)" % (target, target))
    return target

# ---------------------------------------------------------------- 5. install ---

def service_running(name):
    r = subprocess.run(["sc", "query", name], capture_output=True, text=True)
    return "RUNNING" in r.stdout


def port_open(port):
    s = socket.socket()
    s.settimeout(2)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def install(work, install_dir, port):
    if service_running("OracleServiceFREE") and port_open(port):
        say("база уже стоит: OracleServiceFREE работает, порт %d слушается" % port)
        return
    ps1 = os.path.join(HERE, "install-oracle-free.ps1")
    if not os.path.isfile(ps1):
        fail("install", "нет %s" % ps1, "запускать из комплекта uamenu-ai-testbench целиком")
    say("запускаю установщик от имени администратора - ПОДТВЕРДИТЕ ОКНО UAC; это 10-25 минут")
    status = os.path.join(work, "install-status.txt")
    args = ("Start-Process powershell -Verb RunAs -Wait -ArgumentList "
            "'-NoProfile','-ExecutionPolicy','Bypass','-File','%s',"
            "'-InstallerDir','%s','-InstallDir','%s','-Port','%d','-VaultService','frontarchive:%s'"
            % (ps1, work, install_dir, port, VAULT))
    r = subprocess.run(["powershell", "-NoProfile", "-Command", args], capture_output=True, text=True)
    if r.returncode != 0 and "cancel" in (r.stderr or "").lower():
        fail("install", "окно UAC отклонено", "повторить шаг и нажать Да")
    if os.path.isfile(status):
        for line in open(status, encoding="utf-8", errors="replace").read().splitlines()[-8:]:
            say("  " + line)
    for _ in range(12):
        if service_running("OracleServiceFREE") and port_open(port):
            break
        time.sleep(10)
    if not service_running("OracleServiceFREE"):
        fail("install", "служба OracleServiceFREE не работает",
             "журнал %s и %s: искать SEVERE / Return value 3; типовые причины описаны в docs/01-machine-setup.md"
             % (status, os.path.join(work, "install.log")))
    if not port_open(port):
        fail("install", "порт %d не слушается" % port, "служба слушателя *TNSListener*; lsnrctl status из каталога базы")
    say("база стоит: OracleServiceFREE работает, порт %d слушается" % port)

# ---------------------------------------------------------------- 6. restore ---

def write_targets(work, port, schema):
    path = os.path.join(work, "targets.ini")
    text = ("; создано bootstrap_oracle_free.py\n"
            "[free-front]\n"
            "title     = Клон фронта на локальной Oracle Free\n"
            "dsn       = localhost:%d/FREEPDB1\n"
            "user      = %s\n"
            "vault     = %s\n"
            "sys_vault = %s\n"
            "role      = clone\n\n"
            "[archive]\n"
            "dir = %s\n" % (port, schema, VAULT, VAULT, os.path.join(work, "archives")))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def run_fa(frontarchive, targets, *cmd):
    env = dict(os.environ, FRONTARCHIVE_TARGETS=targets, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, "-m", "frontarchive"] + list(cmd), cwd=frontarchive,
                       env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def restore(archive, frontarchive, work, port, schema, wipe):
    if not archive or not os.path.isfile(archive):
        fail("restore", "нет архива .fza (--archive)", "архив передаёт владелец, см. docs/00-handover.md")
    if not frontarchive or not os.path.isfile(os.path.join(frontarchive, "frontarchive", "restore.py")):
        fail("restore", "нет FrontArchive (--frontarchive <RAD_Tokyo>/Sources/FrontArchive)",
             "доступ к приватному репозиторию RAD_Tokyo, ветка feature/front-archive")
    targets = write_targets(work, port, schema)
    say("восстанавливаю %s в схему %s" % (os.path.basename(archive), schema))
    cmd = ["restore", archive, "--to", "free-front", "--create-schema"] + (["--wipe"] if wipe else [])
    code, out = run_fa(frontarchive, targets, *cmd)
    for line in out.strip().splitlines()[-14:]:
        say("  " + line)
    if code != 0:
        if "уже" in out and "объектов" in out:
            fail("restore", "схема не пуста", "повторить с --wipe, если старый клон не нужен")
        fail("restore", "restore вернул %d" % code,
             "вывод выше; типовое - нет пароля SYS в хранилище (шаг install), нет Instant Client (шаг client)")
    say("схема восстановлена")
    return targets

# ----------------------------------------------------------------- 7. verify ---

def verify(frontarchive, targets, port):
    say("проверка")
    checks = [("служба OracleServiceFREE", service_running("OracleServiceFREE")),
              ("порт %d" % port, port_open(port))]
    if frontarchive and targets and os.path.isfile(targets):
        code, out = run_fa(frontarchive, targets, "describe", "free-front")
        checks.append(("describe free-front", code == 0))
        for line in out.strip().splitlines()[:6]:
            say("  " + line)
        code, out = run_fa(frontarchive, targets, "ini", "show", "free-front")
        checks.append(("cantina.ini в схеме (пакет CANTINA_INI)", code == 0))
        if code == 0:
            for line in out.strip().splitlines()[:3]:
                say("  " + line)
    bad = [n for n, ok in checks if not ok]
    for n, ok in checks:
        say("  %-5s %s" % ("ok" if ok else "НЕТ", n))
    if bad:
        fail("verify", "не прошло: " + ", ".join(bad), "см. соответствующий шаг")
    say("готово: база и схема на месте")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--work", default=r"D:\OracleFree", help="куда качать и распаковывать дистрибутив")
    p.add_argument("--install-dir", default=r"D:\Oracle26ai\product\26ai")
    p.add_argument("--port", type=int, default=1522)
    p.add_argument("--url", help="ссылка на zip, если автопоиск не справился")
    p.add_argument("--archive", help="архив .fza кассовой схемы от владельца")
    p.add_argument("--frontarchive", help="каталог RAD_Tokyo/Sources/FrontArchive")
    p.add_argument("--schema", default="FA_FRONT")
    p.add_argument("--wipe", action="store_true", help="очистить схему, если в ней уже что-то есть")
    for s in ("url", "download", "extract", "client", "install", "restore", "verify"):
        p.add_argument("--skip-" + s, action="store_true")
    a = p.parse_args()

    say("bootstrap Oracle Database Free: work=%s install=%s port=%d" % (a.work, a.install_dir, a.port))
    url = zip_path = targets = None
    if not a.skip_url:
        url = find_url(a.url)
    if not a.skip_download:
        zip_path = download(url, a.work)
    if not a.skip_extract:
        if not zip_path:
            zips = [os.path.join(a.work, n) for n in os.listdir(a.work) if n.lower().endswith(".zip")] if os.path.isdir(a.work) else []
            if not zips:
                fail("extract", "в %s нет zip" % a.work, "без --skip-download")
            zip_path = sorted(zips)[-1]
        extract(zip_path, a.work)
    if not a.skip_client:
        ensure_client()
    if not a.skip_install:
        install(a.work, a.install_dir, a.port)
    if not a.skip_restore:
        targets = restore(a.archive, a.frontarchive, a.work, a.port, a.schema, a.wipe)
    else:
        targets = os.path.join(a.work, "targets.ini")
    if not a.skip_verify:
        verify(a.frontarchive, targets, a.port)


if __name__ == "__main__":
    main()
