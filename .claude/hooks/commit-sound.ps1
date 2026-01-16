# Commit Sound - plays a tactical "mission complete" sound on any commit
$input_json = $input | ConvertFrom-Json

$command = $input_json.tool_input.command
if ($command -match 'git commit') {
    # Mission complete - descending confirmation tone
    [console]::beep(800, 100)
    [console]::beep(600, 150)
}

exit 0
