# Build every paper/slides deliverable: .docx -> .pdf (via installed Word) and the .pptx deck.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File paper/build.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File paper/build.ps1 -SkipPdf
#
# Word is used for the PDF so that the .docx and the .pdf are the same document rather than two
# independent renderings. With -SkipPdf (or no Word installed) the .docx and .pptx are still built
# and the script reports the PDF as not produced instead of failing silently.
param(
    [string]$Python = "",
    [string]$DataRoot = "",
    [switch]$SkipPdf
)

$ErrorActionPreference = "Stop"
$paperDir = $PSScriptRoot
$repo = Split-Path -Parent $paperDir
$out = Join-Path $paperDir "out"

if (-not $Python) {
    foreach ($candidate in @((Join-Path $repo ".venv/Scripts/python.exe"),
                             (Join-Path (Split-Path -Parent $repo) "legal-meaning-preservation-hi-en/.venv/Scripts/python.exe"))) {
        if (Test-Path $candidate) { $Python = $candidate; break }
    }
}
if (-not $Python) { $Python = "python" }
if (-not $DataRoot) {
    $sibling = Join-Path (Split-Path -Parent $repo) "legal-meaning-preservation-hi-en"
    if (Test-Path (Join-Path $repo "data/interim")) { $DataRoot = $repo }
    elseif (Test-Path $sibling) { $DataRoot = $sibling }
}
if ($DataRoot) { $env:LMP_DATA_ROOT = $DataRoot }
$env:PYTHONUTF8 = "1"

Write-Output "python:    $Python"
Write-Output "data root: $(if ($DataRoot) { $DataRoot } else { '(none - tables will be [TBD])' })"

# Human validation: scores from data/annotation/human/*.xlsx (writes status "pending" while they are empty)
& $Python (Join-Path (Split-Path -Parent $paperDir) "src/human_validation.py")
if (-not $?) { throw "human_validation.py failed" }
& $Python (Join-Path $paperDir "build_paper.py") --markdown
if (-not $?) { throw "build_paper.py failed" }
& $Python (Join-Path $paperDir "build_slides.py")
if (-not $?) { throw "build_slides.py failed" }
# Overleaf Beamer slides (paper/out/LMP_slides_overleaf.zip), converted from the PowerPoint deck just built
& $Python (Join-Path $paperDir "pptx_to_beamer.py")
if (-not $?) { throw "pptx_to_beamer.py failed" }
# Overleaf project (paper/out/LMP_paper_overleaf.zip): same content as the Word paper, compiled with XeLaTeX on Overleaf
& $Python (Join-Path $paperDir "build_latex.py")
if (-not $?) { throw "build_latex.py failed" }

$docx = Join-Path $out "LMP_paper_IEEE.docx"
$pdf = Join-Path $out "LMP_paper_IEEE.pdf"

if ($SkipPdf) {
    Write-Output "PDF:       skipped (-SkipPdf)"
    exit 0
}

# Word automation runs inside a job with a hard timeout: a first launch, an activation prompt or
# a modal dialog in an invisible Word instance otherwise blocks the whole build indefinitely.
$job = Start-Job -ArgumentList $docx, $pdf -ScriptBlock {
    param($docx, $pdf)
    $word = $null
    try {
        $word = New-Object -ComObject Word.Application
        $word.Visible = $false
        $word.DisplayAlerts = 0
        $document = $word.Documents.Open($docx, $false, $true)   # ConfirmConversions off, ReadOnly
        # 17 = wdExportFormatPDF, 0 = wdExportOptimizeForPrint
        $document.ExportAsFixedFormat($pdf, 17, $false, 0)
        $pages = $document.ComputeStatistics(2)                  # 2 = wdStatisticPages
        $document.Close($false)
        "PAGES:$pages"
    } catch {
        "ERROR:$($_.Exception.Message)"
    } finally {
        if ($word) {
            $word.Quit()
            [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($word)
        }
    }
}

$result = $null
if (Wait-Job $job -Timeout 300) { $result = (Receive-Job $job | Select-Object -Last 1) }
else { Stop-Job $job; $result = "ERROR:Word did not finish within 300s" }
Remove-Job $job -Force

if ($result -like "PAGES:*") {
    Write-Output "wrote $pdf ($($result.Substring(6)) pages)"
} else {
    Write-Output "PDF:       NOT produced - $result"
    Write-Output "           The .docx and .pptx are built. Open $docx and 'Save as PDF',"
    Write-Output "           or re-run this script on a machine with Word available."
    Get-Process WINWORD -ErrorAction SilentlyContinue |
        Where-Object { $_.StartTime -gt (Get-Date).AddMinutes(-10) } |
        Stop-Process -Force -ErrorAction SilentlyContinue
}
