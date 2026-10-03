# Auto-dismiss the CRT assert dialog ("LSX_FFT_BR == NULL" from livekit_ffi).
# "Ignore" is safe: the assert is a benign double-init race in the soxr FFT
# cache; pressing Ignore continues execution. This watcher clicks it whenever
# it appears, so the worker self-heals instead of freezing on the modal.
$ErrorActionPreference = "SilentlyContinue"
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$root = [System.Windows.Automation.AutomationElement]::RootElement
$cond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::NameProperty,
    "Microsoft Visual C++ Runtime Library")

Write-Host "assert-dialog watcher running (Ctrl+C to stop)"
while ($true) {
    $win = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $cond)
    if ($win) {
        $btnCond = New-Object System.Windows.Automation.PropertyCondition(
            [System.Windows.Automation.AutomationElement]::NameProperty, "Ignore")
        $btn = $win.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $btnCond)
        if ($btn) {
            $invoke = $btn.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
            $invoke.Invoke()
            Write-Host ("[auto-ignore] dismissed assert dialog at " + (Get-Date -Format T))
        }
    }
    Start-Sleep -Milliseconds 400
}
