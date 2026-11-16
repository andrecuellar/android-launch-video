# Orientation and mode of the primary monitor, with ChangeDisplaySettingsEx (not saved to the registry).
#   display.ps1 status     -> shows the current mode (and saves it the first time to original.json)
#   display.ps1 portrait   -> rotates to portrait (90 degrees), same refresh rate
#   display.ps1 restore    -> goes back exactly to the mode in original.json
#   add -Test to validate a change without applying it.
# From WSL: powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\...\display.ps1' status
param([Parameter(Mandatory=$true)][ValidateSet('status','portrait','restore')][string]$Action, [switch]$Test)
$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class Display {
  [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
  public struct DEVMODE {
    [MarshalAs(UnmanagedType.ByValTStr, SizeConst=32)] public string dmDeviceName;
    public short dmSpecVersion; public short dmDriverVersion; public short dmSize; public short dmDriverExtra;
    public int dmFields; public int dmPositionX; public int dmPositionY;
    public int dmDisplayOrientation; public int dmDisplayFixedOutput;
    public short dmColor; public short dmDuplex; public short dmYResolution; public short dmTTOption; public short dmCollate;
    [MarshalAs(UnmanagedType.ByValTStr, SizeConst=32)] public string dmFormName;
    public short dmLogPixels; public int dmBitsPerPel; public int dmPelsWidth; public int dmPelsHeight;
    public int dmDisplayFlags; public int dmDisplayFrequency;
    public int dmICMMethod; public int dmICMIntent; public int dmMediaType; public int dmDitherType;
    public int dmReserved1; public int dmReserved2; public int dmPanningWidth; public int dmPanningHeight;
  }
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern bool EnumDisplaySettings(string dev, int mode, ref DEVMODE dm);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int ChangeDisplaySettingsEx(string dev, ref DEVMODE dm, IntPtr hwnd, int flags, IntPtr param);
  public static DEVMODE Current() { var dm = new DEVMODE(); dm.dmSize = (short)Marshal.SizeOf(typeof(DEVMODE)); EnumDisplaySettings("\\\\.\\DISPLAY1", -1, ref dm); return dm; }
}
"@
$path = Join-Path $PSScriptRoot 'original.json'
function Show($dm) {
  $dpi = (Get-ItemProperty 'HKCU:\Control Panel\Desktop\WindowMetrics' -Name AppliedDPI -ErrorAction SilentlyContinue).AppliedDPI
  "size={6} width={0} height={1} hz={2} orientation={3} bits={4} dpi={5}" -f $dm.dmPelsWidth, $dm.dmPelsHeight, $dm.dmDisplayFrequency, $dm.dmDisplayOrientation, $dm.dmBitsPerPel, $dpi, $dm.dmSize
}
$dm = [Display]::Current()
$extra = $dm.dmDriverExtra
$dm.dmDriverExtra = 0
switch ($Action) {
  'status' {
    if (-not (Test-Path $path)) {
      @{ width=$dm.dmPelsWidth; height=$dm.dmPelsHeight; hz=$dm.dmDisplayFrequency; orientation=$dm.dmDisplayOrientation } | ConvertTo-Json | Set-Content $path
      "saved original.json"
    }
    Show $dm
  }
  'portrait' {
    if (-not (Test-Path $path)) { throw "Run 'status' first to save the original mode." }
    $o = Get-Content $path | ConvertFrom-Json
    $dm.dmPelsWidth = $o.height; $dm.dmPelsHeight = $o.width; $dm.dmDisplayFrequency = $o.hz
    $dm.dmDisplayOrientation = 1
    $dm.dmFields = 0x80 -bor 0x80000 -bor 0x100000 -bor 0x400000
    $r = [Display]::ChangeDisplaySettingsEx('\\.\DISPLAY1', [ref]$dm, [IntPtr]::Zero, $(if ($Test) {2} else {0}), [IntPtr]::Zero)
    "result=$r"; Show ([Display]::Current())
  }
  'restore' {
    $o = Get-Content $path | ConvertFrom-Json
    $dm.dmPelsWidth = $o.width; $dm.dmPelsHeight = $o.height; $dm.dmDisplayFrequency = $o.hz
    $dm.dmDisplayOrientation = $o.orientation
    $dm.dmFields = 0x80 -bor 0x80000 -bor 0x100000 -bor 0x400000
    $r = [Display]::ChangeDisplaySettingsEx('\\.\DISPLAY1', [ref]$dm, [IntPtr]::Zero, $(if ($Test) {2} else {0}), [IntPtr]::Zero)
    "result=$r"; Show ([Display]::Current())
  }
}
