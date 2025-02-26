# Simple-CheckHtml.ps1
# A simpler script to check HTML pages for image loading in tables

$rootDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs"
$samplePage = Join-Path $rootDir "pages\public\decades\2000s-programs.html"

Write-Host "Checking HTML for table image loading issues..." -ForegroundColor Cyan

# Check a sample page
if (Test-Path $samplePage) {
    $content = Get-Content -Path $samplePage -Raw
    Write-Host "Found sample page: 2000s-programs.html" -ForegroundColor Green
    
    # Look for script tags
    $scriptTags = [regex]::Matches($content, '<script\s+src="([^"]+)"')
    Write-Host "Found $($scriptTags.Count) script tags:" -ForegroundColor Yellow
    
    foreach ($tag in $scriptTags) {
        $src = $tag.Groups[1].Value
        Write-Host "  $src" -ForegroundColor Green
        
        # Check if it's a main.js or similar
        if ($src -match '(main|table|app)\.js') {
            $scriptPath = Join-Path $rootDir $src.TrimStart('/')
            if (Test-Path $scriptPath) {
                Write-Host "Found potential table script: $scriptPath" -ForegroundColor Cyan
                
                # Extract and save for examination
                $scriptContent = Get-Content -Path $scriptPath -Raw
                $scriptContent | Out-File -FilePath "extracted-script.js"
                Write-Host "Saved script content to extracted-script.js" -ForegroundColor Green
                
                # Look for image loading in the script
                if ($scriptContent -match '<img') {
                    Write-Host "Script contains img tags - may be loading images in tables!" -ForegroundColor Red
                }
            }
        }
    }
    
    # Look for inline scripts
    $inlineScripts = [regex]::Matches($content, '<script>(.*?)</script>', [System.Text.RegularExpressions.RegexOptions]::Singleline)
    Write-Host "Found $($inlineScripts.Count) inline scripts" -ForegroundColor Yellow
    
    if ($inlineScripts.Count -gt 0) {
        $inlineScript = $inlineScripts[0].Groups[1].Value
        $inlineScript | Out-File -FilePath "inline-script.js"
        Write-Host "Saved first inline script to inline-script.js" -ForegroundColor Green
        
        # Look for table-related code
        if ($inlineScript -match 'teamsTableBody') {
            Write-Host "Inline script references table body!" -ForegroundColor Cyan
            
            # Look for image loading
            if ($inlineScript -match '<img') {
                Write-Host "Inline script contains img tags - may be loading images in tables!" -ForegroundColor Red
            }
        }
    }
    
    # Extract table HTML to see its structure
    $tableHtml = [regex]::Match($content, '<table.*?</table>', [System.Text.RegularExpressions.RegexOptions]::Singleline)
    if ($tableHtml.Success) {
        $tableHtml.Value | Out-File -FilePath "table-structure.html"
        Write-Host "Saved table structure to table-structure.html" -ForegroundColor Green
        
        # Look for image tags in the table
        if ($tableHtml.Value -match '<img') {
            Write-Host "Table HTML contains img tags!" -ForegroundColor Red
        }
    }
    
    # Look for the actual table generation pattern
    if ($content -match 'TABLE_ROWS') {
        Write-Host "Found TABLE_ROWS placeholder - checking template content" -ForegroundColor Cyan
        
        # Extract some context around it
        $contextMatch = [regex]::Match($content, '.{0,100}TABLE_ROWS.{0,100}')
        if ($contextMatch.Success) {
            Write-Host "Table rows context: $($contextMatch.Value)" -ForegroundColor Yellow
        }
    }
    
    # Now look at the page template
    $templatePath = Join-Path $rootDir "pages\public\templates\decades\decade-programs-template.html"
    if (Test-Path $templatePath) {
        Write-Host "`nChecking template: decade-programs-template.html" -ForegroundColor Cyan
        $templateContent = Get-Content -Path $templatePath -Raw
        
        # Look for table rows pattern
        if ($templateContent -match 'TABLE_ROWS') {
            Write-Host "Found TABLE_ROWS placeholder in template" -ForegroundColor Green
            
            # Try to find how rows are generated
            $functionMatches = [regex]::Matches($templateContent, 'function\s+([a-zA-Z0-9_]+)\s*\(')
            Write-Host "Found functions in template: $($functionMatches.Count)" -ForegroundColor Yellow
            foreach ($match in $functionMatches) {
                $functionName = $match.Groups[1].Value
                Write-Host "  Function: $functionName" -ForegroundColor Green
                
                # Look for context around this function
                $functionContext = [regex]::Match($templateContent, "function\s+$functionName.*?\{.*?\}", [System.Text.RegularExpressions.RegexOptions]::Singleline)
                if ($functionContext.Success) {
                    $functionContext.Value | Out-File -FilePath "function-$functionName.js"
                    Write-Host "  Saved function code to function-$functionName.js" -ForegroundColor Green
                    
                    # Check if it's generating table rows
                    if ($functionContext.Value -match 'tr>|<td') {
                        Write-Host "  Function appears to generate table rows" -ForegroundColor Cyan
                        
                        # Check for image tags
                        if ($functionContext.Value -match '<img') {
                            Write-Host "  ⚠️ Function includes img tags in table generation!" -ForegroundColor Red
                        }
                    }
                }
            }
        }
        
        # Look for direct HTML table rows
        $rowPatterns = [regex]::Matches($templateContent, '<tr.*?</tr>', [System.Text.RegularExpressions.RegexOptions]::Singleline)
        Write-Host "Found $($rowPatterns.Count) table row patterns in template" -ForegroundColor Yellow
        
        if ($rowPatterns.Count -gt 0) {
            $sampleRow = $rowPatterns[0].Value
            $sampleRow | Out-File -FilePath "sample-row.html"
            Write-Host "Saved sample row to sample-row.html" -ForegroundColor Green
            
            # Check if rows include images
            if ($sampleRow -match '<img') {
                Write-Host "⚠️ Table rows in template include img tags!" -ForegroundColor Red
                
                # Extract the image pattern
                $imagePattern = [regex]::Match($sampleRow, '<img[^>]*>')
                if ($imagePattern.Success) {
                    Write-Host "Image pattern: $($imagePattern.Value)" -ForegroundColor Red
                }
            }
        }
    }
} else {
    Write-Host "Sample page not found: $samplePage" -ForegroundColor Red
}

Write-Host "`nHTML check complete! Check the output files for details." -ForegroundColor Cyan