Write-Host 'Creating test HTML file...'
$htmlContent = @'
<!DOCTYPE html>
<html>
<head><title>Test Page</title></head>
<body><h1>Test Content</h1></body>
</html>
'@

Set-Content -Path '.\test.html' -Value $htmlContent
Write-Host 'Done!'
