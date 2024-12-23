Write-Host 'Generating decade pages and index...'

try {
    # Define decades
    $decades = @(
        @{ Name = 'pre1900'; StartYear = 1877; EndYear = 1899; DisplayName = 'Pre-1900s' };
        @{ Name = '1900s'; StartYear = 1900; EndYear = 1909; DisplayName = '1900s' };
        @{ Name = '1910s'; StartYear = 1910; EndYear = 1919; DisplayName = '1910s' };
        @{ Name = '1920s'; StartYear = 1920; EndYear = 1929; DisplayName = '1920s' };
        @{ Name = '1930s'; StartYear = 1930; EndYear = 1939; DisplayName = '1930s' };
        @{ Name = '1940s'; StartYear = 1940; EndYear = 1949; DisplayName = '1940s' };
        @{ Name = '1950s'; StartYear = 1950; EndYear = 1959; DisplayName = '1950s' };
        @{ Name = '1960s'; StartYear = 1960; EndYear = 1969; DisplayName = '1960s' };
        @{ Name = '1970s'; StartYear = 1970; EndYear = 1979; DisplayName = '1970s' };
        @{ Name = '1980s'; StartYear = 1980; EndYear = 1989; DisplayName = '1980s' };
        @{ Name = '1990s'; StartYear = 1990; EndYear = 1999; DisplayName = '1990s' };
        @{ Name = '2000s'; StartYear = 2000; EndYear = 2009; DisplayName = '2000s' };
        @{ Name = '2010s'; StartYear = 2010; EndYear = 2019; DisplayName = '2010s' };
        @{ Name = '2020s'; StartYear = 2020; EndYear = 2029; DisplayName = '2020s' }
    )

    # Define paths
    $scriptDir = $PSScriptRoot
    $outputDir = Split-Path -Parent $scriptDir
    $csvDir = "C:\Users\demck\OneDrive\Football_2024\csv"

    Write-Host "Script Directory: $scriptDir"
    Write-Host "Output Directory: $outputDir"
    Write-Host "CSV Directory: $csvDir"

    # Read templates
    $decadeTemplate = Get-Content ".\decade-template.html" -Raw
    $indexTemplate = Get-Content ".\index-template.html" -Raw
    
    # Generate decade pages
    foreach ($decade in $decades) {
        Write-Host "`nProcessing $($decade.DisplayName)..."
        
        $output = $decadeTemplate
        $output = $output -replace '\<!--DECADE_TITLE--\>', $decade.DisplayName
        $output = $output -replace '\<!--DECADE_ID--\>', $decade.Name
        
        # Add metadata
        $metadataTag = "<meta name=`"decade-info`" content=`"start-year:$($decade.StartYear),end-year:$($decade.EndYear)`">"
        $output = $output -replace "(?<=<head>.*?)\n", "`n    $metadataTag`n"
        
        # Save decade page
        $outputPath = Join-Path $outputDir "$($decade.Name).html"
        Set-Content -Path $outputPath -Value $output
        Write-Host "  Created $($decade.Name).html"
    }

    # Generate index
    Write-Host "`nGenerating index page..."
    
    $decadeCardsHtml = ""
    foreach ($decade in $decades) {
        $decadeCardsHtml += @"
        <div class="col-md-4 mb-4">
            <div class="card h-100">
                <div class="card-body">
                    <h5 class="card-title">$($decade.DisplayName)</h5>
                    <p class="card-text">Top teams from $($decade.StartYear) to $($decade.EndYear)</p>
                    <a href="$($decade.Name).html" class="btn btn-primary">View Rankings</a>
                </div>
            </div>
        </div>

"@
    }

    $indexContent = $indexTemplate -replace '\<!--DECADE_CARDS--\>', $decadeCardsHtml
    Set-Content -Path (Join-Path $outputDir "index.html") -Value $indexContent
    Write-Host "  Created index.html"

    Write-Host "`nAll files generated successfully!"

} catch {
    Write-Error "Generation failed: $_"
    exit 1
}
