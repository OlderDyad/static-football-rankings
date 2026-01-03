# generate-all-time-programs.ps1
# Generates JSON and HTML for all-time programs with Giscus comments

$logFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\imported_SQL_json\logs\all-time-programs.log"
$outputDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\data\all-time"

# Ensure directories exist and clear old files
New-Item -ItemType Directory -Force -Path (Split-Path $logFile) | Out-Null
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
Remove-Item "$outputDir\all-time-programs-*.json" -ErrorAction SilentlyContinue

# Start logging
Get-Date | Out-File $logFile
"Starting all-time programs generation" | Tee-Object -FilePath $logFile -Append

# Import common functions
. ".\common-functions.ps1"

# Path configuration (matches GenerateAllPages.ps1 pattern)
$docsDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs"
$templateBaseDir = Join-Path $docsDir "pages\public\templates"
$htmlOutputDir = Join-Path $docsDir "pages\public\all-time"

# Giscus Comments Configuration
$giscusScript = @"
<div class="container mt-5">
    <div class="comments-section">
        <h3 class="mb-4">Comments & Discussion</h3>
        <p class="text-muted small mb-3">
            Sign in with GitHub to comment. Comments are stored as 
            <a href="https://github.com/olderdyad/static-football-rankings/discussions" target="_blank">GitHub Discussions</a>.
        </p>
        <script src="https://giscus.app/client.js"
                data-repo="olderdyad/static-football-rankings"
                data-repo-id="R_kgDONn_yOg"
                data-category="General"
                data-category-id="DIC_kwDONn_yOs4C0hls"
                data-mapping="pathname"
                data-strict="0"
                data-reactions-enabled="1"
                data-emit-metadata="1"
                data-input-position="top"
                data-theme="preferred_color_scheme"
                data-lang="en"
                data-loading="lazy"
                crossorigin="anonymous"
                async>
        </script>
    </div>
</div>
"@

try {
    $connection = Connect-Database
    Write-Host "Database connection established"

    @(25, 50, 100) | ForEach-Object {
        $minSeasons = $_
        Write-Host "`nProcessing $minSeasons+ seasons programs..."
        
        $command = New-Object System.Data.SqlClient.SqlCommand("EXEC GetAllTimePrograms @MinSeasons", $connection)
        $command.Parameters.AddWithValue("@MinSeasons", $minSeasons)
        
        $adapter = New-Object System.Data.SqlClient.SqlDataAdapter($command)
        $programsDataset = New-Object System.Data.DataSet
        $adapter.Fill($programsDataset) | Out-Null

        if ($programsDataset.Tables[0].Rows.Count -gt 0) {
            $metadata = Get-TeamMetadata -connection $connection -TeamName $programsDataset.Tables[0].Rows[0].program -isProgram $true
            $jsonData = Format-ProgramData -programs $programsDataset.Tables[0] -metadata $metadata -description "All-time top programs ($minSeasons+ seasons)"
            
            $outputPath = Join-Path $outputDir "all-time-programs-$minSeasons.json"
            Write-Host "Writing to $outputPath"
            $jsonData | ConvertTo-Json -Depth 10 | Set-Content -Path $outputPath -Force
            
            if (Test-Path $outputPath) {
                $lastWriteTime = (Get-Item $outputPath).LastWriteTime
                Write-Host "File written: $outputPath (Last Modified: $lastWriteTime)"
            } else {
                Write-Host "File write failed: $outputPath" -ForegroundColor Red
            }
        }

        # Generate HTML files with Giscus comments
        $templatePath = Join-Path $templateBaseDir "all-time\all-time-programs-template.html"

        if (Test-Path $templatePath) {
            Write-Host "Using template: $templatePath"
            $template = Get-Content $templatePath -Raw
            $htmlFilename = "programs-$minSeasons-plus.html"
            
            # Replace all placeholders
            $template = $template -replace 'PROGRAM_THRESHOLD', $minSeasons
            $template = $template -replace 'TIMESTAMP', (Get-Date -Format "M/d/yyyy")
            $template = $template -replace 'COMMENTS_SCRIPT_PLACEHOLDER', $giscusScript
            
            # Note: TABLE_ROWS is intentionally left as-is since JavaScript populates the table
            # If you want to pre-populate, we'd need to add that logic here
            
            # Save HTML file
            $htmlPath = Join-Path $htmlOutputDir $htmlFilename
            Set-Content -Path $htmlPath -Value $template -Encoding UTF8
            Write-Host "Generated HTML: $htmlFilename with Giscus comments" -ForegroundColor Green
        } else {
            Write-Host "Template not found: $templatePath" -ForegroundColor Red
        }
    }
}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor Red
}
finally {
    if ($connection -and $connection.State -eq 'Open') {
        $connection.Close()
    }
}