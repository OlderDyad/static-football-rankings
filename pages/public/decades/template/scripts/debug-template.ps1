Write-Host "Starting debug test..."
$testContent = @'
<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body><h1>Test Content</h1></body>
</html>
'@

Write-Host "Creating file..."
Set-Content -Path ".\decade-template.html" -Value $testContent
Write-Host "Done."
