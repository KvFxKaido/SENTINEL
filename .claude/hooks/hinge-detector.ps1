# Hinge Detector - plays MGS alert sound when committing with "hinge" in message
$input_json = $input | ConvertFrom-Json

# Only trigger on git commit commands
$command = $input_json.tool_input.command
if ($command -match 'git commit' -and $command -match 'hinge') {
    # MGS Alert sound - ascending tones
    [console]::beep(600, 150)
    Start-Sleep -Milliseconds 50
    [console]::beep(800, 150)
    Start-Sleep -Milliseconds 50
    [console]::beep(1000, 200)

    Write-Host "🔶 HINGE MOMENT COMMITTED" -ForegroundColor Yellow
}

exit 0
