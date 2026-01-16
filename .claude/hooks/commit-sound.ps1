# Commit Sound - plays confirmation sound on any commit
$input_json = $input | ConvertFrom-Json

$command = $input_json.tool_input.command
if ($command -match 'git commit') {
    [System.Media.SystemSounds]::Asterisk.Play()
}

exit 0
