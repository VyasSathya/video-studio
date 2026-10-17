# Run the agent-brain README tour for real in a throwaway clone and save each command with its exact output.
#   powershell -ExecutionPolicy Bypass -File projects\agent-brain-terminal\capture.ps1 [-Repo C:\Dev\agent-brain] [-Python python]
# Output goes through ConvertFrom-Json | select (shown in the command itself), so no absolute paths reach the video.
param([string]$Repo = 'C:\Dev\agent-brain', [string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$t = Join-Path $env:TEMP ('agent-brain-tour-' + [guid]::NewGuid().ToString('n').Substring(0, 8))
git clone -q $Repo $t
$steps = @(
    @{ label = 'Route a folder';                         cmd = 'brain route --cwd examples/todo-api/src | ConvertFrom-Json | select project, role' },
    @{ label = 'Save a handoff';                         cmd = 'brain handoff --file examples/handoff.example.json | ConvertFrom-Json | select id' },
    @{ label = 'What is current';                        cmd = 'brain current --project todo-api | ConvertFrom-Json | % tasks | select task, evidence_changed' },
    @{ label = 'Save it again without saying what it replaces'; cmd = 'brain handoff --file examples/handoff.example.json'; highlight = @(, @('agent-brain error:', 'red')) },
    @{ label = 'Change the file the handoff cites';      cmd = 'Add-Content examples/todo-api/NOTES.md "Staging deploy started."' },
    @{ label = 'What is current now';                    cmd = 'brain current --project todo-api | ConvertFrom-Json | % tasks | select task, evidence_changed'; highlight = @(, @('True$', 'amber')) }
)
$out = @()
$i = 0
foreach ($s in $steps) {
    $i++
    $f = Join-Path $t ("_step$i.ps1")
    $body = "Set-Location '$t'`nfunction brain { `$a = (`$args | % { if (`$_ -match ' ') { '`"' + `$_ + '`"' } else { `$_ } }) -join ' '; cmd /c `"$Python -m agent_brain --brain examples/tiny-brain `$a 2>&1`" }`n" + $s.cmd + ' | Out-String -Width 110'
    [IO.File]::WriteAllText($f, $body)
    $text = powershell -NoProfile -ExecutionPolicy Bypass -File $f
    $rec = [ordered]@{ label = $s.label; cmd = $s.cmd; out = (($text -join "`n").Trim("`n").TrimEnd()) }
    if ($s.highlight) { $rec.highlight = $s.highlight }
    $out += [pscustomobject]$rec
}
Remove-Item -Recurse -Force $t
[IO.File]::WriteAllText((Join-Path $here 'session.json'), ($out | ConvertTo-Json -Depth 5))
Write-Host "captured $($out.Count) steps -> $here\session.json"
