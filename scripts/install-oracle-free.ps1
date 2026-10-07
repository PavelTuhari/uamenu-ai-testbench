# Установка Oracle AI Database Free (26ai / 23ai) на Windows для стенда UAMenu.
#
# Запускать от имени администратора из любого места; дистрибутив заранее
# распакован в -InstallerDir (там setup.exe, "Oracle AI Database 26ai Free.msi",
# FREEInstall.rsp). Проверено на Windows 10 x64, Oracle AI Database Free
# 26ai 23.26.3.
#
# Почему не просто setup.exe - четыре грабли, на которых установка
# останавливается молча:
#  1. setup.exe сперва ставит пакет VC++; тот находит свою dll занятой,
#     помечает "нужна перезагрузка", и setup.exe выходит с кодом 0, ничего
#     не поставив. Поэтому запускаем сам MSI.
#  2. Установщик проверяет права всей цепочки каталогов назначения
#     ("Folder is not secure"). Создаём цепочку с выключенным
#     наследованием: доступ только SYSTEM и администраторам.
#  3. Он отказывается ставить при заданной TNS_ADMIN. Снимаем на время
#     установки и возвращаем в finally, что бы ни случилось.
#  4. Порт 1521 он считает занятым, если видит любые соединения с таким
#     номером, даже к удалённой базе. Поэтому 1522 по умолчанию.
#
# Пароль SYS/SYSTEM по умолчанию создаётся случайным и кладётся в хранилище
# учётных данных Windows (служба oraclefree:local, пользователь SYS) через
# python-модуль keyring. В выводе и журнале установки он не появляется:
# журнал после установки вычищается. Свой пароль - ключ -AskPassword.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File install-oracle-free.ps1 `
#       -InstallerDir D:\OracleFree -InstallDir D:\Oracle26ai\product\26ai -Port 1522
param(
  [Parameter(Mandatory = $true)][string]$InstallerDir,
  [string]$InstallDir = (Join-Path $env:SystemDrive 'Oracle26ai\product\26ai'),
  [int]$Port = 1522,
  [string]$VaultService = 'frontarchive:freelocal',   # так пароль SYS найдёт FrontArchive (sys_vault = freelocal)
  [switch]$AskPassword
)

$ErrorActionPreference = 'Stop'
$msi    = Get-ChildItem -Path $InstallerDir -Filter '*.msi' | Select-Object -First 1
$rsp    = Join-Path $InstallerDir 'install.rsp'
$log    = Join-Path $InstallerDir 'install.log'
$status = Join-Path $InstallerDir 'install-status.txt'
$python = (Get-Command python -ErrorAction SilentlyContinue).Source

function Say($text) {
  $line = "{0}  {1}" -f (Get-Date -Format 'HH:mm:ss'), $text
  Write-Output $line
  Add-Content -Path $status -Value $line -Encoding UTF8
}

Set-Content -Path $status -Value '' -Encoding UTF8
trap {
  Add-Content -Path $status -Encoding UTF8 -Value ("{0}  ОШИБКА: {1}" -f (Get-Date -Format 'HH:mm:ss'), $_.Exception.Message)
  exit 9
}

$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$pr = New-Object Security.Principal.WindowsPrincipal($id)
if (-not $pr.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { Say 'НЕТ ПРАВ: запустите от имени администратора'; exit 2 }
if (-not $msi) { Say "в $InstallerDir нет .msi - распакуйте дистрибутив"; exit 2 }
if (-not $python) { Say 'python не найден в PATH (нужен для хранилища паролей)'; exit 2 }
Say "установка $($msi.Name) в $InstallDir, порт $Port"

# -- пароль ---------------------------------------------------------------
if ($AskPassword) {
  $secure = Read-Host 'Пароль SYS/SYSTEM (не отображается)' -AsSecureString
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  $pw = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
} else {
  # Требования установщика: не короче 8, буквы обоих регистров и цифры
  $sets = @([char[]]'ABCDEFGHJKLMNPQRSTUVWXYZ', [char[]]'abcdefghijkmnpqrstuvwxyz', [char[]]'23456789')
  $all = $sets[0] + $sets[1] + $sets[2]
  $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
  function Pick($set) { $b = New-Object byte[] 4; $rng.GetBytes($b); $set[[BitConverter]::ToUInt32($b, 0) % $set.Length] }
  $chars = @((Pick $sets[0]), (Pick $sets[1]), (Pick $sets[2])); 1..21 | ForEach-Object { $chars += Pick $all }
  $pw = -join ($chars | Sort-Object { Get-Random })
  Say "пароль создан случайным, длина $($pw.Length)"
}
$helper = Join-Path $InstallerDir 'save_pw.py'
@"
import sys, keyring
pw = sys.stdin.readline().rstrip("\r\n")
keyring.set_password("$VaultService", "SYS", pw)
print("OK" if keyring.get_password("$VaultService", "SYS") == pw else "MISMATCH")
"@ | Set-Content -Path $helper -Encoding Ascii
$saved = (($pw | & $python $helper 2>&1) | Out-String).Trim()
Remove-Item $helper -Force -ErrorAction SilentlyContinue
if ($saved -ne 'OK') { Say "пароль не сохранился в хранилище: $saved"; exit 3 }
Say "пароль сохранён: $VaultService / SYS"

# -- файл ответов ---------------------------------------------------------
@("INSTALLDIR=$InstallDir\", "PASSWORD=$pw", "LISTENER_PORT=$Port", 'CHAR_SET=AL32UTF8',
  'DB_DOMAIN=', 'SOFTWARE_ONLY=FALSE', 'MODIFY_DIRECTORY_PERMISSIONS=TRUE') -join "`r`n" |
  Set-Content -Path $rsp -Encoding Ascii
Copy-Item $rsp (Join-Path $InstallerDir 'FREEInstall.rsp') -Force

# -- закрытая цепочка каталогов ------------------------------------------
$system = New-Object Security.Principal.SecurityIdentifier('S-1-5-18')
$admins = New-Object Security.Principal.SecurityIdentifier('S-1-5-32-544')
$chain = @(); $walk = $InstallDir
while ($walk -and ($walk -ne [IO.Path]::GetPathRoot($walk))) { $chain = @($walk) + $chain; $walk = Split-Path $walk -Parent }
foreach ($dir in $chain) {
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
  $acl = Get-Acl $dir
  $acl.SetAccessRuleProtection($true, $false)
  foreach ($rule in @($acl.Access)) { [void]$acl.RemoveAccessRule($rule) }
  foreach ($sid in @($system, $admins)) {
    $acl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($sid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')))
  }
  $acl.SetOwner($admins)
  Set-Acl -Path $dir -AclObject $acl
}
Say ("каталог базы закрыт: " + ($chain -join ', '))

# -- установка ------------------------------------------------------------
$savedTns = [Environment]::GetEnvironmentVariable('TNS_ADMIN', 'Machine')
$savedHome = [Environment]::GetEnvironmentVariable('ORACLE_HOME', 'Machine')
try {
  if ($savedTns)  { Say "TNS_ADMIN снимаем на время установки: $savedTns";  [Environment]::SetEnvironmentVariable('TNS_ADMIN', $null, 'Machine') }
  if ($savedHome) { Say "ORACLE_HOME снимаем на время установки: $savedHome"; [Environment]::SetEnvironmentVariable('ORACLE_HOME', $null, 'Machine') }
  if ((Get-Service msiserver).Status -ne 'Stopped') { Say 'внимание: служба установщика уже работает и могла запомнить TNS_ADMIN' }
  Say 'запускаю msiexec, это 10-25 минут'
  $sw = [Diagnostics.Stopwatch]::StartNew()
  $args = @('/i', "`"$($msi.FullName)`"", '/qn', '/L*v', "`"$log`"", "RSP_FILE=`"$rsp`"", 'REBOOT=ReallySuppress')
  $proc = Start-Process msiexec.exe -ArgumentList $args -Wait -PassThru
  Say ("msiexec завершился, код {0}, прошло {1:n1} мин" -f $proc.ExitCode, $sw.Elapsed.TotalMinutes)
}
finally {
  if ($savedTns)  { [Environment]::SetEnvironmentVariable('TNS_ADMIN', $savedTns, 'Machine');  Say "TNS_ADMIN возвращена" }
  if ($savedHome) { [Environment]::SetEnvironmentVariable('ORACLE_HOME', $savedHome, 'Machine'); Say "ORACLE_HOME возвращена" }
}

# -- журнал без пароля ----------------------------------------------------
if (Test-Path $log) {
  $text = Get-Content $log -Raw -Encoding Unicode
  if (-not $text) { $text = Get-Content $log -Raw }
  ($text -replace [regex]::Escape($pw), '***') | Set-Content ($log + '.clean') -Encoding UTF8
  Remove-Item $log -Force; Rename-Item ($log + '.clean') $log
  foreach ($line in (Select-String -Path $log -Pattern 'SEVERE|Return value 3|error status:' | Select-Object -First 6)) {
    Say ("журнал: " + ($line.Line -replace '\s+', ' ').Trim())
  }
}

# -- проверка -------------------------------------------------------------
foreach ($s in Get-Service -Name 'OracleService*', '*TNSListener*' -ErrorAction SilentlyContinue) { Say "служба $($s.Name): $($s.Status)" }
Say ("порт {0} слушается: {1}" -f $Port, [bool](netstat -ano | Select-String ":$Port\s" | Select-String 'LISTENING'))
$sqlplus = Get-ChildItem -Path $InstallDir -Filter sqlplus.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
if ($sqlplus) {
  $probe = "set heading off`r`nselect 'ALIVE ' || version from v`$instance;`r`nexit`r`n"
  $out = $probe | & $sqlplus.FullName -S "sys/$pw@//localhost:$Port/FREE as sysdba" 2>&1
  Say ("проверка подключения: " + ((($out -join ' ') -replace [regex]::Escape($pw), '***') -replace '\s+', ' ').Trim())
} else { Say 'sqlplus не найден - установка не дошла до конца, смотрите журнал' }

# -- следов не оставляем --------------------------------------------------
if (Test-Path $rsp) {
  $junk = New-Object byte[] ((Get-Item $rsp).Length)
  [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($junk)
  [IO.File]::WriteAllBytes($rsp, $junk); Remove-Item $rsp -Force
}
Set-Content -Path (Join-Path $InstallerDir 'FREEInstall.rsp') -Value 'PASSWORD=removed' -Encoding Ascii
Say 'файл ответов затёрт; готово'
