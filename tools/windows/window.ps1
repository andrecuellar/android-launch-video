# Emulator windows: list them (title, window and client area in screen coordinates), move the main
# one to X,Y without resizing, place it with a size, and put it on top or back to normal.
#   window.ps1 list | window.ps1 move -X 0 -Y 0 | window.ps1 place -X 0 -Y 0 -W 1200 -H 2600 | window.ps1 top | window.ps1 normal
param([Parameter(Mandatory=$true)][string]$Action, [int]$X = 0, [int]$Y = 0, [int]$W = 0, [int]$H = 0)
Add-Type -TypeDefinition @"
using System; using System.Text; using System.Collections.Generic; using System.Runtime.InteropServices;
public class Win {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
  public delegate bool EnumProc(IntPtr h, IntPtr p);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f, IntPtr p);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref POINT p);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint flags);
  public static List<IntPtr> OfProcess(uint pid) {
    var l = new List<IntPtr>();
    EnumWindows((h, p) => { uint q; GetWindowThreadProcessId(h, out q); if (q == pid && IsWindowVisible(h)) l.Add(h); return true; }, IntPtr.Zero);
    return l;
  }
}
"@
$proc = Get-Process qemu-system-x86_64 -ErrorAction Stop | Select-Object -First 1
$windows = [Win]::OfProcess([uint32]$proc.Id)
function Title($h) { $sb = New-Object System.Text.StringBuilder 256; [void][Win]::GetWindowText($h, $sb, 256); $sb.ToString() }
$main = $windows | Where-Object { (Title $_) -like 'Android Emulator*' } | Select-Object -First 1
switch ($Action) {
  'list' {
    foreach ($h in $windows) {
      $r = New-Object Win+RECT; [void][Win]::GetWindowRect($h, [ref]$r)
      $c = New-Object Win+RECT; [void][Win]::GetClientRect($h, [ref]$c)
      $o = New-Object Win+POINT; [void][Win]::ClientToScreen($h, [ref]$o)
      "'{0}' window=({1},{2})-({3},{4}) client_origin=({5},{6}) client={7}x{8}" -f (Title $h), $r.L, $r.T, $r.R, $r.B, $o.X, $o.Y, $c.R, $c.B
    }
  }
  'move'   { [Win]::SetWindowPos($main, [IntPtr]::Zero, $X, $Y, 0, 0, 0x0001 -bor 0x0004) }
  'place'  { [Win]::SetWindowPos($main, [IntPtr]::Zero, $X, $Y, $W, $H, 0x0004) }
  'top'    { [Win]::SetWindowPos($main, [IntPtr](-1), 0, 0, 0, 0, 0x0001 -bor 0x0002) }
  'normal' { [Win]::SetWindowPos($main, [IntPtr](-2), 0, 0, 0, 0, 0x0001 -bor 0x0002) }
}
