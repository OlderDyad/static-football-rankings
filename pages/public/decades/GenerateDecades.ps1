Write-Host 'Generating decade pages and index...'

try {
    # Define the complete list of decades with full metadata
    $decades = @(
        @{ Name = 'pre1900'; StartYear = 1877; EndYear = 1899; DisplayName = 'Pre-1900s' }
        @{ Name = '1900s'; StartYear = 1900; EndYear = 1909; DisplayName = '1900s' }
        @{ Name = '1910s'; StartYear = 1910; EndYear = 1919; DisplayName = '1910s' }
        @{ Name = '1920s'; StartYear = 1920; EndYear = 1929; DisplayName = '1920s' }
        @{ Name = '1930s'; StartYear = 1930; EndYear = 1939; DisplayName = '1930s' }
        @{ Name = '1940s'; StartYear = 1940; EndYear = 1949; DisplayName = '1940s' }
        @{ Name = '1950s'; StartYear = 1950; EndYear = 1959; DisplayName = '1950s' }
        @{ Name = '1960s'; StartYear = 1960; EndYear = 1969; DisplayName = '1960s' }
        @{ Name = '1970s'; StartYear = 1970; EndYear = 1979; DisplayName = '1970s' }
        @{ Name = '1980s'; StartYear = 1980; EndYear = 1989; DisplayName = '1980s' }
        @{ Name = '1990s'; StartYear = 1990; EndYear = 1999; DisplayName = '1990s' }
        @{ Name = '2000s'; StartYear = 2000; EndYear = 2009; DisplayName = '2000s' }
        @{ Name = '2010s'; StartYear = 2010; EndYear = 2019; DisplayName = '2010s' }
        @{ Name = '2020s'; StartYear = 2020; EndYear = 2029; DisplayName = '2020s' }
    )

    # Define paths
    $scriptDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\pages\public\decades"
    $templateDir = $scriptDir 
    $decadeTemplatePath = Join-Path $templateDir "decade-template.html"
    $indexTemplatePath = Join-Path $templateDir "index-template.html"
    $outputDir = $scriptDir
    $jsonBasePath = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\data"

    # Read templates and verify they exist
    if (-not (Test-Path $decadeTemplatePath)) {
        throw "Decade template file not found at $decadeTemplatePath"
    }
    if (-not (Test-Path $indexTemplatePath)) {
        throw "Index template file not found at $indexTemplatePath"
    }
    $decadeTemplate = Get-Content $decadeTemplatePath -Raw
    $indexTemplate = Get-Content $indexTemplatePath -Raw

    # Create output directory if it doesn't exist
    if (-not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
        Write-Host "Created output directory: $outputDir"
    }

    # First pass: Generate all decade pages
    foreach ($decade in $decades) {
        Write-Host "`nProcessing $($decade.DisplayName)..."

        $output = $decadeTemplate
        $output = $output -replace 'DECADE_DISPLAY_NAME', $decade.DisplayName
        $output = $output -replace 'DECADE_NAME', $decade.Name
        $output = $output -replace 'DECADE_START', $decade.StartYear
        $output = $output -replace 'DECADE_END', $decade.EndYear
        $output = $output -replace 'DECADE_ID', $decade.Name

        # Add metadata
        $metadataTag = "<meta name=`"decade-info`" content=`"start-year:$($decade.StartYear),end-year:$($decade.EndYear)`">"
        $output = $output -replace '(?<=<head>.*?)\n', "`n    $metadataTag`n"

        # Construct JSON file path
        $jsonFileName = "decade-teams-$($decade.Name).json"
        $jsonFilePath = Join-Path $jsonBasePath "decades/teams/$jsonFileName"

        # Load and process rankings data from JSON (only if the file exists)
        if (Test-Path $jsonFilePath) {
            Write-Host "Found JSON for $($decade.Name): $($jsonFilePath)" -ForegroundColor Green

            # Read and parse the JSON data
            $jsonData = Get-Content -Path $jsonFilePath -Raw | ConvertFrom-Json

            # Check if rankings are not null and the 'items' property exists
            if ($null -ne $jsonData -and $null -ne $jsonData.items -and $jsonData.items -is [System.Array]) {
                # Output the rankings for debugging
                Write-Host "Rankings for $($decade.DisplayName):" -ForegroundColor Yellow
                $jsonData.items | Format-Table

                # Create table rows HTML
                $tableRows = ""
                foreach ($rank in $jsonData.items | Select-Object -First 20) {
                    $tableRows += @"
                <tr>
                    <td>$($rank.rank)</td>
                    <td>$($rank.team)</td>
                    <td>$($rank.state)</td>
                    <td>$($rank.seasons)</td>
                    <td>$($rank.combined)</td>
                    <td>$($rank.margin)</td>
                    <td>$($rank.win_loss)</td>
                    <td>$($rank.offense)</td>
                    <td>$($rank.defense)</td>
                    <td>$($rank.games_played)</td>
                </tr>
"@
                }

                # Insert table rows into the template
                $output = $output -replace 'TABLE_ROWS', $tableRows
            } else {
                Write-Warning "Invalid or empty JSON data for $($decade.DisplayName): $jsonFilePath"
            }
        } else {
            Write-Warning "JSON file not found for $($decade.DisplayName): $jsonFilePath"
        }

        # Define the output path for the HTML file
        $outputPath = Join-Path $outputDir "$($decade.Name).html"

        # Save the HTML file for the current decade
        Set-Content -Path $outputPath -Value $output -Encoding UTF8

        # Verify that the HTML file was created successfully
        if (-not (Test-Path $outputPath)) {
            throw "Failed to create $($decade.DisplayName) page"
        }
    }

    # Second pass: Generate index
    Write-Host "`nGenerating index page..."

    # Build cards HTML in memory
    $decadeCardsHtml = $decades | ForEach-Object {
        @"
        <div class="col-md-4 mb-4">
            <div class="card h-100">
                <div class="card-body d-flex flex-column">
                    <h5 class="card-title">$($_.DisplayName)</h5>
                    <p class="card-text">Top teams from $($_.StartYear) to $($_.EndYear)</p>
                    <a href="$($_.Name).html" class="btn btn-primary mt-auto">View Rankings</a>
                </div>
            </div>
        </div>
"@
    }

    # Create and save index
    $indexPath = Join-Path $outputDir "index.html"
    $indexContent = $indexTemplate -replace 'DECADE_CARDS', ($decadeCardsHtml -join "`n")
    Set-Content -Path $indexPath -Value $indexContent -Encoding UTF8

    Write-Host "All files generated successfully in: $outputDir"

} catch {
    Write-Error "Generation failed: $_"
    exit 1
}