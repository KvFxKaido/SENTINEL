# Hinge Detector - plays alert sound when committing with "hinge" in message
$input_json = $input | ConvertFrom-Json

$command = $input_json.tool_input.command
if ($command -match 'git commit' -and $command -match 'hinge') {
    # Play exclamation sound 3 times for dramatic effect
    [System.Media.SystemSounds]::Exclamation.Play()
    Start-Sleep -Milliseconds 300
    [System.Media.SystemSounds]::Exclamation.Play()
    Start-Sleep -Milliseconds 300
    [System.Media.SystemSounds]::Exclamation.Play()

    Write-Host "🔶 HINGE MOMENT COMMITTED" -ForegroundColor Yellow
}

exit 0
