# Проверка машины стенда UAMenu: что есть, чего нет. Ничего не меняет.
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\check-prereqs.ps1
param(
  [string]$StudioBin = 'C:\Program Files (x86)\Embarcadero\Studio\19.0\bin',
  [int]$OraclePort = 1522
)

$rows = @()
function Row($need, $what, $ok, $note) {
  $script:rows += [pscustomobject]@{ 'Нужно' = $need; 'Что' = $what; 'Есть' = $(if ($ok) { 'да' } else { 'НЕТ' }); 'Подробность' = $note }
}

# RAD Studio и сборка
$dcc = Join-Path $StudioBin 'bcc32.exe'
Row 'сборка' 'RAD Studio 19 (bcc32)' (Test-Path $dcc) $dcc
$rsvars = Join-Path $StudioBin 'rsvars.bat'
Row 'сборка' 'rsvars.bat' (Test-Path $rsvars) $rsvars
$msb = Get-Command msbuild -ErrorAction SilentlyContinue
# msbuild появляется в PATH после rsvars.bat - его отсутствие само по себе не беда
Row 'сборка, не обяз.' 'msbuild в PATH' ($null -ne $msb) $(if ($msb) { $msb.Source } else { 'после call rsvars.bat появится' })

# Oracle Instant Client
$ic = $env:ORACLE_CLIENT_DIR
if (-not $ic) { $ic = (Get-ChildItem 'C:\oracle' -Directory -Filter 'instantclient*' -ErrorAction SilentlyContinue | Select-Object -First 1).FullName }
Row 'база' 'Oracle Instant Client 19' ($ic -and (Test-Path (Join-Path $ic 'oci.dll'))) $(if ($ic) { $ic } else { 'C:\oracle\instantclient_19_xx либо ORACLE_CLIENT_DIR' })
$tns = $env:TNS_ADMIN
Row 'база' 'TNS_ADMIN и tnsnames.ora' ($tns -and (Test-Path (Join-Path $tns 'tnsnames.ora'))) $(if ($tns) { $tns } else { 'переменная не задана' })

# Python
$py = Get-Command python -ErrorAction SilentlyContinue
Row 'инструменты' 'Python 3.12' ($null -ne $py) $(if ($py) { (& python --version 2>&1) } else { 'python.org' })
if ($py) {
  foreach ($m in 'oracledb', 'keyring', 'flask', 'cryptography') {
    & python -c "import $m" 2>$null
    Row 'инструменты' "модуль $m" ($LASTEXITCODE -eq 0) "pip install $m"
  }
}

# Oracle Free
$svc = Get-Service -Name 'OracleServiceFREE' -ErrorAction SilentlyContinue
Row 'база' 'служба OracleServiceFREE' ($svc -and $svc.Status -eq 'Running') $(if ($svc) { "$($svc.Status)" } else { 'не установлена (шаг 1.3) - можно жить с базой владельца' })
$lsn = Get-Service -Name '*TNSListener*' -ErrorAction SilentlyContinue | Select-Object -First 1
Row 'база' 'слушатель Oracle' ($lsn -and $lsn.Status -eq 'Running') $(if ($lsn) { "$($lsn.Name) $($lsn.Status)" } else { '—' })
$listening = netstat -ano | Select-String ":$OraclePort\s" | Select-String 'LISTENING'
Row 'база' "порт $OraclePort слушается" ([bool]$listening) $(if ($listening) { 'да' } else { 'нет' })

# Git и GitHub CLI
$git = Get-Command git -ErrorAction SilentlyContinue
Row 'исходники' 'git' ($null -ne $git) $(if ($git) { (& git --version) } else { 'git-scm.com' })
$gh = Get-Command gh -ErrorAction SilentlyContinue
Row 'исходники' 'gh (не обязательно)' ($null -ne $gh) $(if ($gh) { 'есть' } else { 'cli.github.com' })

# Edge для снимков
$edge = @('C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', 'C:\Program Files\Microsoft\Edge\Application\msedge.exe') | Where-Object { Test-Path $_ } | Select-Object -First 1
Row 'снимки' 'Microsoft Edge (безголовые снимки дашбордов)' ([bool]$edge) $(if ($edge) { $edge } else { 'не обязательно' })

# Пользователь: касса и секреты должны работать под одним
$id = [Security.Principal.WindowsIdentity]::GetCurrent()
Row 'пользователь' 'текущий пользователь Windows' $true "$($id.Name) - под ним же запускать кассу и переносить секреты"

$rows | Format-Table -AutoSize -Wrap
$missing = @($rows | Where-Object { $_.'Есть' -eq 'НЕТ' -and $_.'Нужно' -in @('сборка', 'инструменты') }).Count
if ($missing) { Write-Output "Не хватает обязательного: $missing. Сборка и инструменты без этого не заработают." }
else { Write-Output 'Обязательное на месте.' }
