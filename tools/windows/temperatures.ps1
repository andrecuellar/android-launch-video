# Temperatures in one line: CPU (Core Temp, shared memory) and AMD GPU (LibreHardwareMonitor).
# Needs Core Temp running and the LibreHardwareMonitorLib.dll path (parameter -Lhm).
# From WSL: powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\...\temperatures.ps1' -Lhm 'C:\Tools\LibreHardwareMonitor\LibreHardwareMonitorLib.dll'
param([string]$Lhm = 'C:\Tools\LibreHardwareMonitor\LibreHardwareMonitorLib.dll')
$out = @()
try {
  $m = [System.IO.MemoryMappedFiles.MemoryMappedFile]::OpenExisting('CoreTempMappingObject', [System.IO.MemoryMappedFiles.MemoryMappedFileRights]::Read)
  $v = $m.CreateViewAccessor(0, 0, [System.IO.MemoryMappedFiles.MemoryMappedFileAccess]::Read)
  $n = $v.ReadUInt32(1536); $cpus = [math]::Max(1, $v.ReadUInt32(1540)); $tj = $v.ReadUInt32(1024)
  $f = $v.ReadByte(2684); $delta = $v.ReadByte(2685)
  $t = @(); for ($i = 0; $i -lt ($n * $cpus); $i++) { $x = $v.ReadSingle(1544 + 4 * $i); if ($delta -eq 1) { $x = $tj - $x }; if ($f -eq 1) { $x = ($x - 32) * 5 / 9 }; $t += $x }
  $l = @(); for ($i = 0; $i -lt $n; $i++) { $l += $v.ReadUInt32(4 * $i) }
  $out += ('CPU max {0:N0} C, avg {1:N1} C, load {2:N0} %' -f ($t | Measure-Object -Maximum).Maximum, ($t | Measure-Object -Average).Average, ($l | Measure-Object -Average).Average)
  $v.Dispose(); $m.Dispose()
} catch { $out += 'CPU no data (is Core Temp closed?)' }
try {
  Add-Type -Path $Lhm -ErrorAction Stop
  $pc = New-Object LibreHardwareMonitor.Hardware.Computer; $pc.IsGpuEnabled = $true; $pc.Open()
  foreach ($hw in $pc.Hardware) { $hw.Update() }
  $g = $pc.Hardware | Where-Object { $_.HardwareType -eq [LibreHardwareMonitor.Hardware.HardwareType]::GpuAmd } | Select-Object -First 1
  if ($g) {
    $temps = $g.Sensors | Where-Object { $_.SensorType -eq [LibreHardwareMonitor.Hardware.SensorType]::Temperature -and $_.Value -ne $null } | ForEach-Object { '{0} {1:N0} C' -f $_.Name, $_.Value }
    $fan = $g.Sensors | Where-Object { $_.SensorType -eq [LibreHardwareMonitor.Hardware.SensorType]::Fan } | Select-Object -First 1
    $txt = 'GPU ' + ($temps -join ', ')
    if ($fan) { $txt += (', fan {0:N0} RPM' -f $fan.Value) }
    $out += $txt
  } else { $out += 'GPU no data' }
  $pc.Close()
} catch { $out += 'GPU no data: ' + $_.Exception.Message }
'{0} | {1}' -f (Get-Date -Format 'HH:mm'), ($out -join ' | ')
