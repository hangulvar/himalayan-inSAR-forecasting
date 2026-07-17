# monsoon_cycle.ps1 - the scheduled monsoon-watch cycle (ERRC "Eliminate", 2026-07-13).
#
# Replaces the manual 2-3-day runbook loop (docs/archive/Monsoon Watch Runbook (2026-07-11).md):
# for EACH registry site it runs live_alarm's fetch stage (mintpy image) then its alarm
# stage (insar image), refreshes the multi-AOI status board, and compares each site's
# alarm state against the previous run - raising a Windows toast ONLY when a human is
# needed (state change, any ALERT day, or a failed chain). Idempotent: safe to run any
# time; ERA5-Land's ~5-day lag just means quiet runs add nothing.
#
# Scheduled via Windows Task Scheduler as "InSAR Monsoon Watch Cycle" (every 2 days,
# 08:00, runs only when the user is logged on so toasts are visible). Disable with:
#   Unregister-ScheduledTask -TaskName 'InSAR Monsoon Watch Cycle' -Confirm:$false
# Season gate below self-silences Nov-Mar; re-check cadence each April.

$ErrorActionPreference = 'Continue'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$logDir = Join-Path $root 'logs'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory $logDir | Out-Null }
$log = Join-Path $logDir ("monsoon_cycle_" + (Get-Date -Format 'yyyy-MM-dd') + ".log")
$stateFile = Join-Path $logDir 'monsoon_state.json'

function Log($m) {
    ("{0}  {1}" -f (Get-Date -Format 's'), $m) | Out-File -FilePath $log -Append -Encoding utf8
}

function Toast($title, $msg) {
    # Best-effort Windows toast (WinRT; works from an interactive scheduled task).
    try {
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(
            [Windows.UI.Notifications.ToastTemplateType]::ToastText02)
        $texts = $xml.GetElementsByTagName('text')
        $texts.Item(0).AppendChild($xml.CreateTextNode($title)) | Out-Null
        $texts.Item(1).AppendChild($xml.CreateTextNode($msg)) | Out-Null
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Monsoon Watch').Show($toast)
    } catch { Log "toast failed: $_" }
}

$cycleStart = Get-Date
Log "=== monsoon cycle start ==="

# Housekeeping: prune cycle logs older than 60 days (keeps logs/ from growing unbounded).
try {
    Get-ChildItem $logDir -Filter 'monsoon_cycle_*.log' |
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-60) } |
        Remove-Item -Force -ErrorAction SilentlyContinue
} catch {}

# Season gate: the watch season is April-October (live_alarm's season starts 1 Apr;
# post-monsoon the sites go DORMANT). Off-season runs exit quietly.
$month = (Get-Date).Month
if ($month -lt 4 -or $month -gt 10) {
    Log "off-season (month $month) - nothing to do"
    exit 0
}

# Docker must already be RUNNING - this script never starts or stops it (user decision
# 2026-07-16: the user starts Docker themselves at logon; headless lifecycle management
# of Docker Desktop caused far more trouble than it saved - error log 2026-07-15/16).
# Grace window: a missed-schedule catch-up fires right at logon, so give the user up to
# 10 minutes to start Docker before skipping quietly until the next cycle.
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Log "Docker not running - waiting up to 10 min for the user to start it"
    Toast 'Monsoon Watch: waiting for Docker' 'Start Docker Desktop within 10 min and this cycle will run.'
    $tries = 0
    do { Start-Sleep 30; docker info *> $null; $tries++ } while ($LASTEXITCODE -ne 0 -and $tries -lt 20)
    if ($LASTEXITCODE -ne 0) {
        Log "Docker still not running - cycle SKIPPED (start Docker, then re-run this script or wait for the next cycle)"
        Toast 'Monsoon Watch: cycle skipped' 'Docker was not started. Run workflows/monsoon_cycle.ps1 manually after starting Docker.'
        exit 0
    }
    Log "Docker is up - continuing"
}

# The registry sites on monsoon watch. Calendar files follow live_alarm's suffix rule
# (Ramban grandfathered on _<year>, others _<slug>_<year>).
$year = (Get-Date).Year
$sites = @(
    @{ name = 'vaishnodevi'; cfg = 'config/vaishnodevi.yaml';
       cal = Join-Path $root ("data\rainfall\operational_alarm_calendar_vaishnodevi_$year.csv") },
    @{ name = 'ramban'; cfg = 'config/ramban.yaml';
       cal = Join-Path $root ("data\rainfall\operational_alarm_calendar_$year.csv") }
)

# Previous run's states, for change detection.
$prev = @{}
if (Test-Path $stateFile) {
    try {
        $obj = Get-Content $stateFile -Raw | ConvertFrom-Json
        foreach ($p in $obj.PSObject.Properties) { $prev[$p.Name] = $p.Value }
    } catch { Log "state file unreadable - treating as first run" }
}

$now = @{}
$attention = @()

foreach ($s in $sites) {
    $name = $s.name
    Log "--- $name : fetch (mintpy) ---"
    cmd /c "docker compose run --rm -e INSAR_CONFIG=$($s.cfg) mintpy python workflows/live_alarm.py 2>&1" |
        Out-File -FilePath $log -Append -Encoding utf8
    $fetchOk = ($LASTEXITCODE -eq 0)
    Log "--- $name : alarm (insar) ---"
    cmd /c "docker compose run --rm -e INSAR_CONFIG=$($s.cfg) insar python workflows/live_alarm.py 2>&1" |
        Out-File -FilePath $log -Append -Encoding utf8
    $alarmOk = ($LASTEXITCODE -eq 0)

    if (-not ($fetchOk -and $alarmOk)) {
        Log "$name : CHAIN FAILED (fetch=$fetchOk alarm=$alarmOk)"
        $attention += "$name cycle FAILED - see log"
        continue
    }

    # Current state = last row of the season alarm calendar.
    if (Test-Path $s.cal) {
        $last = Import-Csv $s.cal | Select-Object -Last 1
        $state = "{0} as-of {1} (E={2}, {3} live zones)" -f $last.alarm_level, $last.date,
                 $last.exceedance_E, $last.n_live_zones
        $now[$name] = @{ level = $last.alarm_level; as_of = $last.date }
        Log "$name : $state"
        if ($last.alarm_level -eq 'ALERT') {
            $attention += "$name is in ALERT ($state)"
        } elseif ($prev.ContainsKey($name) -and $prev[$name].level -ne $last.alarm_level) {
            $attention += ("$name changed {0} -> {1} ($state)" -f $prev[$name].level, $last.alarm_level)
        }
    } else {
        Log "$name : calendar CSV missing ($($s.cal))"
        $attention += "$name calendar missing - see log"
    }
}

# Refresh the multi-AOI status board (data/aoi_status.html).
cmd /c "docker compose run --rm insar python workflows/aoi_status.py 2>&1" |
    Out-File -FilePath $log -Append -Encoding utf8

$now | ConvertTo-Json | Out-File -FilePath $stateFile -Encoding utf8

if ($attention.Count -gt 0) {
    $msg = $attention -join ' | '
    Log "ATTENTION: $msg"
    Toast 'Monsoon Watch: attention needed' $msg
} else {
    Log "quiet cycle - no state change, no ALERT"
}

# Docker is left exactly as we found it: running. The user owns its lifecycle
# (stop it with `docker desktop stop` when done - never force-kill, error log
# 2026-07-15/16). The .wslconfig cap keeps the idle VM cost low regardless.
$elapsed = (Get-Date) - $cycleStart
Log ("=== monsoon cycle done (took {0:mm\:ss}) ===" -f $elapsed)
exit 0
