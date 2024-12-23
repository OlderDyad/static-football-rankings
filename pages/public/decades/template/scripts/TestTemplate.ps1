Write-Host 'Testing placeholder replacement...'

try {
    # Test data
    $testData = @{
        'DECADE_TITLE' = '1990s'
        'DECADE_ID' = '1990'
    }
    
    # Read template
    $template = Get-Content '.\decade-template.html' -Raw
    
    # Create test output
    $testOutput = $template
    foreach ($key in $testData.Keys) {
        $testOutput = $testOutput -replace "<!--$key-->", $testData[$key]
    }
    
    # Save test file
    Set-Content -Path '.\test-output.html' -Value $testOutput
    
    # Verify replacements
    Write-Host "
Verifying replacements:"
    
    # Check DECADE_TITLE was replaced everywhere
    $remainingTitles = ([regex]::Matches($testOutput, '<!--DECADE_TITLE-->')).Count
    if ($remainingTitles -eq 0) {
        Write-Host "   All DECADE_TITLE placeholders replaced"
    } else {
        throw "DECADE_TITLE replacement failed - $remainingTitles remaining"
    }
    
    # Check DECADE_ID was replaced
    $remainingIds = ([regex]::Matches($testOutput, '<!--DECADE_ID-->')).Count
    if ($remainingIds -eq 0) {
        Write-Host "   DECADE_ID placeholder replaced"
    } else {
        throw "DECADE_ID replacement failed - $remainingIds remaining"
    }
    
    # Verify the replacements are correct
    if ($testOutput.Contains("1990s Teams") -and 
        $testOutput.Contains('data-page-name="1990"')) {
        Write-Host "   Replacement values are correct"
    } else {
        throw "Replacement values not found in expected locations"
    }
    
    Write-Host "
Test output saved to test-output.html"
    Write-Host "Placeholder replacement test complete!"
    
} catch {
    Write-Error "Test failed: $_"
    exit 1
}
