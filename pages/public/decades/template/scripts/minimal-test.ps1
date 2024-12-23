Write-Host 'Creating test file...'
$content = 'Simple test content'
Set-Content -Path '.\test.txt' -Value $content
Write-Host 'Done!'
