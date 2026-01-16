# MCP Hot Reload Notifier - alerts when sentinel-campaign code is modified
$input_json = $input | ConvertFrom-Json

$file_path = $input_json.tool_input.file_path
if ($file_path -match 'sentinel-campaign.*\.py$') {
    # Quick notification beep
    [console]::beep(440, 100)
    [console]::beep(550, 100)

    Write-Host "⚡ MCP server code changed: $file_path" -ForegroundColor Cyan
    Write-Host "   Restart Claude Code to reload sentinel-campaign server" -ForegroundColor DarkCyan
}

exit 0
