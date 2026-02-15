###############################################################################
# GenerateAllPages.ps1
# Comprehensive static page generator for McKnight's American Football Rankings
###############################################################################

#region Configuration
Write-Host 'Initializing static page generation...' -ForegroundColor Green

# Base paths
$rootDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings"
$docsDir = Join-Path $rootDir "docs"
$dataDir = Join-Path $docsDir "data"
$templateBaseDir = Join-Path $docsDir "pages\public\templates"
$outputBaseDir = Join-Path $docsDir "pages\public"

# Debug path information
Write-Host "Checking paths:" -ForegroundColor Yellow
Write-Host "Root Directory: $rootDir"
Write-Host "Data Directory: $dataDir"
Write-Host "Template Directory: $templateBaseDir"
Write-Host "Output Directory: $outputBaseDir"

# Create necessary directories
$directories = @(
    (Join-Path $outputBaseDir "decades"),
    (Join-Path $outputBaseDir "states"),
    (Join-Path $outputBaseDir "all-time"),
    (Join-Path $outputBaseDir "latest-season"),
    (Join-Path $outputBaseDir "greatest")
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# Verify paths exist
if (-not (Test-Path $dataDir)) {
    Write-Error "Data directory not found: $dataDir"
    exit 1
}

if (-not (Test-Path $templateBaseDir)) {
    Write-Warning "Template directory not found, creating: $templateBaseDir"
    New-Item -ItemType Directory -Path $templateBaseDir -Force | Out-Null
}
#endregion Configuration

#region Template Verification
function Test-RequiredTemplates {
    $requiredTemplates = @(
        # Decade templates
        @{
            Path = Join-Path $templateBaseDir "decades\decade-teams-template.html"
            Description = "Decade Teams Template"
            Critical = $true
        },
        @{
            Path = Join-Path $templateBaseDir "decades\decade-programs-template.html"
            Description = "Decade Programs Template"
            Critical = $true
        },
        # State templates
        @{
            Path = Join-Path $templateBaseDir "states\state-teams-template.html"
            Description = "State Teams Template"
            Critical = $true
        },
        @{
            Path = Join-Path $templateBaseDir "states\state-programs-template.html"
            Description = "State Programs Template"
            Critical = $true
        },
        # All-time templates
        @{
            Path = Join-Path $templateBaseDir "all-time\all-time-teams-template.html"
            Description = "All-Time Teams Template"
            Critical = $false
        },
        @{
            Path = Join-Path $templateBaseDir "all-time\all-time-programs-template.html"
            Description = "All-Time Programs Template"
            Critical = $false
        },
        # Latest season template
        @{
            Path = Join-Path $templateBaseDir "latest-season\latest-season-template.html"
            Description = "Latest Season Template"
            Critical = $false
        },
        # Index templates
        @{
            Path = Join-Path $templateBaseDir "index\decades-index-template.html"
            Description = "Decades Index Template"
            Critical = $true
        },
        @{
            Path = Join-Path $templateBaseDir "index\states-index-template.html"
            Description = "States Index Template"
            Critical = $true
        },
        @{
            Path = Join-Path $templateBaseDir "index\all-time-index-template.html"
            Description = "All-Time Index Template"
            Critical = $false
        }
        @{
            Path = Join-Path $templateBaseDir "greatest\greatest-games.html"
            Description = "Greatest Games Template"
            Critical = $false
        }
        @{
            Path = Join-Path $templateBaseDir "greatest\greatest-rivalries.html"
            Description = "Greatest Rivalries Template"
            Critical = $false
        }
    )

    $missingTemplates = @()
    $missingCritical = $false

    Write-Host "Verifying required templates..." -ForegroundColor Yellow
    
    # First ensure template base directory exists
    if (-not (Test-Path $templateBaseDir)) {
        Write-Host "Creating template base directory: $templateBaseDir" -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $templateBaseDir -Force | Out-Null
    }

    # Ensure subdirectories exist
    @("decades", "states", "all-time", "latest-season", "index") | ForEach-Object {
        $subDir = Join-Path $templateBaseDir $_
        if (-not (Test-Path $subDir)) {
            Write-Host "Creating template subdirectory: $subDir" -ForegroundColor Yellow
            New-Item -ItemType Directory -Path $subDir -Force | Out-Null
        }
    }

    foreach ($template in $requiredTemplates) {
        if (-not (Test-Path $template.Path)) {
            $status = if ($template.Critical) { "CRITICAL" } else { "WARNING" }
            $color = if ($template.Critical) { "Red" } else { "Yellow" }
            Write-Host "[$status] Missing $($template.Description): $($template.Path)" -ForegroundColor $color
            
            $missingTemplates += $template
            if ($template.Critical) {
                $missingCritical = $true
            }
        } else {
            Write-Host "[OK] Found $($template.Description)" -ForegroundColor Green
        }
    }

    if ($missingCritical) {
        Write-Warning "Critical templates are missing. Please ensure all required templates are in place."
        return $false
    }

    if ($missingTemplates.Count -gt 0) {
        Write-Warning "Some non-critical templates are missing. Certain features may be limited."
        return $false
    }

    Write-Host "All required templates verified successfully." -ForegroundColor Green
    return $true
}

function Test-TemplateExists {
    param (
        [string]$TemplatePath,
        [string]$TemplateType,
        [bool]$Critical = $true
    )

    if (-not (Test-Path $TemplatePath)) {
        $message = "Template not found: $TemplateType ($TemplatePath)"
        if ($Critical) {
            Write-Error $message
            return $false
        } else {
            Write-Warning $message
            return $false
        }
    }
    return $true
}
#endregion Template Verification

#region Helper Functions
function Generate-TeamBanner {

    param (
        [Parameter(Mandatory=$true)][object]$TopItem,
        [string]$Type = "team" # "team" or "program"
    )

    if (!$TopItem) {
        return ""
    }

    # Handle Logo URLs from JSON
    $logoHtml = if ($TopItem.logoURL -and "$($TopItem.logoURL)".Trim()) {
        $logoPath = "/static-football-rankings/$($TopItem.logoURL.TrimStart('/'))"
        "<img src=`"$logoPath`" alt=`"Logo`" class=`"img-fluid team-logo`" onerror=`"this.style.display='none'`" />"
    } else {
        ""
    }

    $schoolLogoHtml = if ($TopItem.schoolLogoURL -and "$($TopItem.schoolLogoURL)".Trim()) {
        $schoolPath = "/static-football-rankings/$($TopItem.schoolLogoURL.TrimStart('/'))"
        "<img src=`"$schoolPath`" alt=`"School Logo`" class=`"img-fluid school-logo`" onerror=`"this.style.display='none'`" />"
    } else {
        ""
    }

    # Color handling
    $backgroundColor = if ($TopItem.backgroundColor -and "$($TopItem.backgroundColor)".Trim()) {
        $TopItem.backgroundColor
    } else {
        '#FFFFFF'
    }

    $textColor = if ($TopItem.textColor -and "$($TopItem.textColor)".Trim()) {
        $TopItem.textColor
    } else {
        '#000000'
    }

    # Display name logic
    $displayName = if ($Type -eq "team") {
        "$($TopItem.season) $($TopItem.team)"
    } else {
        $TopItem.program
    }

    $mascot = if ($TopItem.mascot) {
        "<p class='mascot-name'>$($TopItem.mascot)</p>"
    } else {
        ""
    }

@"
<div class="team-header" style="background-color: $backgroundColor; color: $textColor;">
    <div class="container">
        <div class="row align-items-center">
            <div class="col-md-3 text-center">
                $logoHtml
            </div>
            <div class="col-md-6 text-center">
                <h2>$displayName</h2>
                $mascot
                <div class="team-stats">
                    <small>
                        $(if ($Type -eq "program") { "Seasons: $($TopItem.seasons)" })
                    </small>
                </div>
            </div>
            <div class="col-md-3 text-center">
                $schoolLogoHtml
            </div>
        </div>
    </div>
</div>
"@
}

function Generate-TableRows {
    param (
        [Parameter(Mandatory=$true)][array]$Items,
        [Parameter(Mandatory=$true)][string]$Type  # "team" or "program"
    )

    $tableRows = $Items | ForEach-Object {
        if ($Type -eq "team") {
            @"
            <tr>
                <td>$($_.rank)</td>
                <td>$($_.team)</td>
                <td>$($_.season)</td>
                <td>$($_.combined)</td>
                <td>$($_.margin)</td>
                <td>$($_.win_loss)</td>
                <td>$($_.offense)</td>
                <td>$($_.defense)</td>
                <td>$($_.games_played)</td>
                <td>$($_.state)</td>
            </tr>
"@
        } else {
            @"
            <tr>
                <td>$($_.rank)</td>
                <td>$($_.program)</td>
                <td>$($_.seasons)</td>
                <td>$($_.combined)</td>
                <td>$($_.margin)</td>
                <td>$($_.win_loss)</td>
                <td>$($_.offense)</td>
                <td>$($_.defense)</td>
                <td>$($_.state)</td>
            </tr>
"@
        }
    }
    return $tableRows -join "`n"
}

function Generate-StandardizedJson {
    param (
        [string]$Type,
        [array]$Items,
        [object]$TopItem,
        [string]$Description,
        [string]$YearRange,
        [string]$OutputPath
    )

    Write-Host "Generating standardized JSON for $Type..." -ForegroundColor Yellow

    $standardizedData = @{
        topItem = $TopItem
        items = $Items
        metadata = @{
            timestamp = (Get-Date).ToString("o")
            type = $Type
            yearRange = $YearRange
            totalItems = $Items.Count
            description = $Description
        }
    }

    $jsonContent = $standardizedData | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText($OutputPath, $jsonContent, [System.Text.Encoding]::UTF8)
    Write-Host "Generated JSON file: $OutputPath" -ForegroundColor Green
}

function Generate-ComingSoonPage {
    param (
        [string]$OutputPath,
        [string]$Title,
        [string]$Message
    )

    $comingSoonHtml = @"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>$Title - McKnight's American Football</title>
    
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <link href="/static-football-rankings/css/styles.css" rel="stylesheet">
</head>
<body>
    <div class="header-banner">
        <img src="/static-football-rankings/images/football-field-top.jpg" alt="Football Field Header" class="w-100" />
    </div>

    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-8 text-center">
                <h1>$Title</h1>
                <div class="alert alert-info mt-4">
                    <h4 class="alert-heading">Coming Soon!</h4>
                    <p class="mb-0">$Message</p>
                </div>
                <a href="/static-football-rankings/index.html" class="btn btn-primary mt-3">Return to Home</a>
            </div>
        </div>
    </div>

    <footer class="mt-5 mb-3">
        <div class="text-center">
            <p>© 2025 McKnight's Football Rankings</p>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"@

    # Ensure directory exists before writing
    $outputDir = Split-Path $OutputPath -Parent
    if (-not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    }

    Set-Content -Path $OutputPath -Value $comingSoonHtml -Encoding UTF8
    Write-Host "Generated coming soon page: $OutputPath"
}

function Get-StateFullName {
    param([string]$StateCode)
    
    $stateNames = @{
        # US States
        "AL" = "Alabama"; "AK" = "Alaska"; "AZ" = "Arizona"; "AR" = "Arkansas"
        "CA" = "California"; "CO" = "Colorado"; "CT" = "Connecticut"; "DE" = "Delaware"
        "FL" = "Florida"; "GA" = "Georgia"; "HI" = "Hawaii"; "ID" = "Idaho"
        "IL" = "Illinois"; "IN" = "Indiana"; "IA" = "Iowa"; "KS" = "Kansas"
        "KY" = "Kentucky"; "LA" = "Louisiana"; "ME" = "Maine"; "MD" = "Maryland"
        "MA" = "Massachusetts"; "MI" = "Michigan"; "MN" = "Minnesota"; "MS" = "Mississippi"
        "MO" = "Missouri"; "MT" = "Montana"; "NE" = "Nebraska"; "NV" = "Nevada"
        "NH" = "New Hampshire"; "NJ" = "New Jersey"; "NM" = "New Mexico"; "NY" = "New York"
        "NC" = "North Carolina"; "ND" = "North Dakota"; "OH" = "Ohio"; "OK" = "Oklahoma"
        "OR" = "Oregon"; "PA" = "Pennsylvania"; "RI" = "Rhode Island"; "SC" = "South Carolina"
        "SD" = "South Dakota"; "TN" = "Tennessee"; "TX" = "Texas"; "UT" = "Utah"
        "VT" = "Vermont"; "VA" = "Virginia"; "WA" = "Washington"; "WV" = "West Virginia"
        "WI" = "Wisconsin"; "WY" = "Wyoming"
        # Canadian Provinces
        "AB" = "Alberta"; "BC" = "British Columbia"; "MB" = "Manitoba"; "NB" = "New Brunswick"
        "NS" = "Nova Scotia"; "QB" = "Quebec"; "SK" = "Saskatchewan"
    }
    
    return $stateNames[$StateCode]
}

function Process-StateIndexPage {
    Write-Host "Generating state index page..." -ForegroundColor Yellow
    
    $templatePath = Join-Path $templateBaseDir "index\states-index-template.html"
    $outputPath = Join-Path $outputBaseDir "states\index.html"
    
    if (Test-Path $templatePath) {
        try {
            # Simply copy the template to the output location
            Copy-Item -Path $templatePath -Destination $outputPath -Force
            Write-Host "Generated state index page: $outputPath" -ForegroundColor Green
        } catch {
            Write-Error "Error copying state index page: $_"
            throw
        }
    } else {
        Write-Error "State index template not found: $templatePath"
    }
}
#endregion Helper Functions

#region Template Scripts
# Table controls (search & pagination)
$tableControlsScript = @'
<script>
    const TableControls = {
        ROWS_PER_PAGE: 100,
        currentPage: 1,
        filteredRows: [],

        init() {
            const tableBody = document.querySelector('tbody');
            if (tableBody) {
                const rows = Array.from(tableBody.getElementsByTagName('tr'));
                this.filteredRows = rows;
                const totalRows = rows.length;
                
                const totalRowsElement = document.getElementById('totalRows');
                if (totalRowsElement) {
                    totalRowsElement.textContent = totalRows;
                }
                
                this.setupEventListeners();
                this.showPage(1);
            }
        },

        setupEventListeners() {
            const searchInput = document.getElementById('tableSearch');
            const pagination = document.getElementById('tablePagination');

            if (searchInput) {
                searchInput.value = '';
                const self = this;
                searchInput.addEventListener('input', function(e) {
                    self.filterTable(e.target.value.toLowerCase());
                });
            }

            if (pagination) {
                const self = this;
                pagination.addEventListener('click', function(e) {
                    const button = e.target.closest('button');
                    if (!button || button.parentElement.classList.contains('disabled')) return;
                    
                    const page = button.dataset.page;
                    if (page === 'prev') {
                        self.showPage(self.currentPage - 1);
                    } else if (page === 'next') {
                        self.showPage(self.currentPage + 1);
                    } else {
                        self.showPage(parseInt(page));
                    }
                });
            }
        },

        filterTable(searchTerm) {
            const tableBody = document.querySelector('tbody');
            if (!tableBody) return;

            const rows = Array.from(tableBody.getElementsByTagName('tr'));
            this.filteredRows = searchTerm.trim() === '' ? rows : rows.filter(row => {
                const text = Array.from(row.getElementsByTagName('td'))
                    .map(cell => cell.textContent || cell.innerText)
                    .join(' ')
                    .toLowerCase();
                return text.includes(searchTerm);
            });

            const totalRowsElement = document.getElementById('totalRows');
            if (totalRowsElement) {
                totalRowsElement.textContent = this.filteredRows.length;
            }

            this.currentPage = 1;
            this.showPage(1);
        },

        showPage(pageNum) {
            const tableBody = document.querySelector('tbody');
            if (!tableBody) return;

            this.currentPage = pageNum;
            const start = (pageNum - 1) * this.ROWS_PER_PAGE;
            const end = Math.min(start + this.ROWS_PER_PAGE, this.filteredRows.length);
            
            const allRows = Array.from(tableBody.getElementsByTagName('tr'));
            allRows.forEach(row => row.style.display = 'none');
            
            for (let i = start; i < end; i++) {
                if (this.filteredRows[i]) {
                    this.filteredRows[i].style.display = '';
                }
            }
            
            const startRowElement = document.getElementById('startRow');
            const endRowElement = document.getElementById('endRow');
            if (startRowElement) startRowElement.textContent = this.filteredRows.length === 0 ? 0 : start + 1;
            if (endRowElement) endRowElement.textContent = end;
            
            this.updatePaginationControls();
        },

        updatePaginationControls() {
            const pagination = document.getElementById('tablePagination');
            if (!pagination) return;
            
            const totalPages = Math.ceil(this.filteredRows.length / this.ROWS_PER_PAGE);
            let html = [];
            
            html.push(`<li class="page-item ${this.currentPage === 1 ? 'disabled' : ''}">
                <button class="page-link" data-page="prev">&laquo;</button>
            </li>`);
            
            for (let i = 1; i <= totalPages; i++) {
                if (i === 1 || i === totalPages || (i >= this.currentPage - 2 && i <= this.currentPage + 2)) {
                    html.push(`<li class="page-item ${i === this.currentPage ? 'active' : ''}">
                        <button class="page-link" data-page="${i}">${i}</button>
                    </li>`);
                } else if (i === this.currentPage - 3 || i === this.currentPage + 3) {
                    html.push('<li class="page-item disabled"><span class="page-link">...</span></li>');
                }
            }
            
            html.push(`<li class="page-item ${this.currentPage === totalPages ? 'disabled' : ''}">
                <button class="page-link" data-page="next">&raquo;</button>
            </li>`);
            
            pagination.innerHTML = html.join('');
        }
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => TableControls.init());
    } else {
        TableControls.init();
    }
</script>
'@

# Comments functionality
# Comments functionality
$commentCode = @"
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

#endregion Template Scripts
#endregion Template Scripts

#region Processing Functions
function Process-Template {
    param (
        [Parameter(Mandatory=$true)][string]$TemplatePath,
        [Parameter(Mandatory=$true)][hashtable]$Replacements,
        [Parameter(Mandatory=$true)][object]$Data,
        [Parameter(Mandatory=$true)][string]$Type
    )

    Write-Host "`nProcessing template: $TemplatePath" -ForegroundColor Yellow
    
    try {
        $template = Get-Content $TemplatePath -Raw
        
        # Clean up any userStyle tags that might be present in the template
        $template = $template -replace '<userStyle>Normal</userStyle>', ''

        # Handle data file path if present
        if ($Replacements.ContainsKey('DataFilePath')) {
            $pattern = $Replacements.DataFilePath.Pattern
            $replacement = $Replacements.DataFilePath.Replacement
            Write-Host "  Updating data file path..." -ForegroundColor Yellow
            $template = $template -replace $pattern, $replacement
        }

        # Handle timestamp replacement
        $currentDate = Get-Date -Format "M/d/yyyy"
        $template = $template -replace '(<span id="lastUpdated">)[^<]*(</span>)', "`${1}$currentDate`${2}"

        # Handle all other replacements
        foreach ($key in $Replacements.Keys) {
            if ($key -ne 'DataFilePath' -and $Replacements[$key]) {
                Write-Host "  Replacing: $key" -ForegroundColor Yellow
                $template = $template -replace $key, $Replacements[$key]
            }
        }

        # Handle scripts (ensure they're clean of userStyle tags)
        $cleanTableControls = $tableControlsScript -replace '<userStyle>Normal</userStyle>', ''
        $cleanComments = $commentCode -replace '<userStyle>Normal</userStyle>', ''
        
        $template = $template -replace 'TABLE_CONTROLS_SCRIPT', $cleanTableControls
        $template = $template -replace 'COMMENTS_SCRIPT_PLACEHOLDER', $cleanComments

        # Handle table rows
        Write-Host "  Generating table rows..." -ForegroundColor Yellow
        $tableRows = Generate-TableRows -Items $Data.items -Type $Type
        Write-Host "  Generated $($Data.items.Count) rows"
        $template = $template -replace 'TABLE_ROWS', $tableRows

        return $template
    }
    catch {
        Write-Error "Error processing template: $_"
        throw
    }
}

function Process-DecadeData {
    param (
        [string]$DecadeName,
        [string]$StartYear,
        [string]$EndYear,
        [string]$DisplayName
    )

    Write-Host "`n========== Processing $DisplayName Programs ==========" -ForegroundColor Cyan

    # Define common replacements with CORRECTED paths
    $commonReplacements = @{
        'DECADE_DISPLAY_NAME' = $DisplayName
        'DECADE_NAME' = $DecadeName
        'DECADE_START' = $StartYear
        'DECADE_END' = $EndYear
    }

    # Process Programs
    $programJsonPath = Join-Path $dataDir "decades\programs\programs-$DecadeName.json"
    Write-Host "`nProcessing Programs" -ForegroundColor Yellow
    Write-Host "  JSON Path: $programJsonPath"
    
    if (Test-Path $programJsonPath) {
        try {
            $jsonContent = Get-Content $programJsonPath -Raw | ConvertFrom-Json
            
            # Add standardization step
            Generate-StandardizedJson -Type "decade-programs" `
                                   -Items $jsonContent.items `
                                   -TopItem $jsonContent.topItem `
                                   -Description "$DisplayName Programs" `
                                   -YearRange "$StartYear-$EndYear" `
                                   -OutputPath $programJsonPath

            $templatePath = Join-Path $templateBaseDir "decades\decade-programs-template.html"
            $outputPath = Join-Path $outputBaseDir "decades\$DecadeName-programs.html"

            if (Test-Path $templatePath) {
                # Create a template with the CORRECT data-file meta tag
                $template = Get-Content $templatePath -Raw
                
                # Fix meta tag for programs - CRITICAL FIX HERE
                $template = $template -replace '<meta name="data-file" content="[^"]*">', 
                                      "<meta name=`"data-file`" content=`"/static-football-rankings/data/decades/programs/programs-$DecadeName.json`">"
                
                # Process the rest of the template
                $processedTemplate = Process-Template -TemplatePath $templatePath `
                                                    -Replacements $commonReplacements `
                                                    -Data $jsonContent `
                                                    -Type "program"
                
                # Make sure the meta tag fix is preserved
                $processedTemplate = $processedTemplate -replace '<meta name="data-file" content="[^"]*">', 
                                                      "<meta name=`"data-file`" content=`"/static-football-rankings/data/decades/programs/programs-$DecadeName.json`">"
                
                Set-Content -Path $outputPath -Value $processedTemplate -Encoding UTF8
                Write-Host "`nGenerated: $DecadeName-programs.html" -ForegroundColor Green
            }
        }
        catch {
            Write-Error "Error processing $DecadeName programs: $_"
        }
    }

    
    # Process Teams
    $teamJsonPath = Join-Path $dataDir "decades\teams\teams-$DecadeName.json"
    Write-Host "`nProcessing Teams" -ForegroundColor Yellow
    Write-Host "  JSON Path: $teamJsonPath"
    
    if (Test-Path $teamJsonPath) {
        try {
            $jsonContent = Get-Content $teamJsonPath -Raw | ConvertFrom-Json
            
            # Add standardization step
            Generate-StandardizedJson -Type "decade-teams" `
                                   -Items $jsonContent.items `
                                   -TopItem $jsonContent.topItem `
                                   -Description "$DisplayName Teams" `
                                   -YearRange "$StartYear-$EndYear" `
                                   -OutputPath $teamJsonPath

            $templatePath = Join-Path $templateBaseDir "decades\decade-teams-template.html"
            $outputPath = Join-Path $outputBaseDir "decades\$DecadeName-teams.html"

            if (Test-Path $templatePath) {
                # Create a template with the CORRECT data-file meta tag
                $template = Get-Content $templatePath -Raw
                
                # Fix meta tag for teams - CRITICAL FIX HERE
                $template = $template -replace '<meta name="data-file" content="[^"]*">', 
                                      "<meta name=`"data-file`" content=`"/static-football-rankings/data/decades/teams/teams-$DecadeName.json`">"
                
                $processedTemplate = Process-Template -TemplatePath $templatePath `
                                                    -Replacements $commonReplacements `
                                                    -Data $jsonContent `
                                                    -Type "team"
                
                # Make sure the meta tag fix is preserved
                $processedTemplate = $processedTemplate -replace '<meta name="data-file" content="[^"]*">', 
                                                      "<meta name=`"data-file`" content=`"/static-football-rankings/data/decades/teams/teams-$DecadeName.json`">"
                
                Set-Content -Path $outputPath -Value $processedTemplate -Encoding UTF8
                Write-Host "`nGenerated: $DecadeName-teams.html" -ForegroundColor Green
            }
        }
        catch {
            Write-Error "Error processing $DecadeName teams: $_"
        }
    }
}

function Process-StateData {
    param (
        [string]$StateCode
    )

    Write-Host "Processing state: $StateCode"

    # Process teams for this state
    $jsonPath = Join-Path $dataDir "states\teams\state-teams-$StateCode.json"
    if (Test-Path $jsonPath) {
        try {
            # Get the full state name
            $stateName = Get-StateFullName -StateCode $StateCode
            
            $teamData = Get-Content $jsonPath -Raw | ConvertFrom-Json
            $outputPath = Join-Path $outputBaseDir "states\$StateCode-teams.html"

            $templatePath = Join-Path $templateBaseDir "states\state-teams-template.html"
            if (Test-Path $templatePath) {
                $template = Get-Content $templatePath -Raw
                
                # Replace state code and name
                $template = $template -replace 'STATE_CODE', $StateCode
                $template = $template -replace 'STATE_NAME', $stateName                
                $template = $template -replace 'TABLE_CONTROLS_SCRIPT', $tableControlsScript
                $template = $template -replace 'COMMENTS_SCRIPT_PLACEHOLDER', $commentCode
                $template = $template -replace 'TIMESTAMP', (Get-Date -Format "M/d/yyyy")

                $tableRows = Generate-TableRows -Items $teamData.items -Type "team"
                $template = $template -replace 'TABLE_ROWS', $tableRows

                Set-Content -Path $outputPath -Value $template -Encoding UTF8
                Write-Host "Generated: $StateCode-teams.html"
            }
        } catch {
            Write-Error "Error processing $StateCode teams: $_"
        }
    }

    # Process programs
    $programJsonPath = Join-Path $dataDir "states\programs\state-programs-$StateCode.json"
    if (Test-Path $programJsonPath) {
        try {
            # Get the full state name
            $stateName = Get-StateFullName -StateCode $StateCode
            
            $programData = Get-Content $programJsonPath -Raw | ConvertFrom-Json
            $outputPath = Join-Path $outputBaseDir "states\$StateCode-programs.html"

            $templatePath = Join-Path $templateBaseDir "states\state-programs-template.html"
            if (Test-Path $templatePath) {
                $template = Get-Content $templatePath -Raw
                
                # Replace state code and name
                $template = $template -replace 'STATE_CODE', $StateCode
                $template = $template -replace 'STATE_NAME', $stateName                
                $template = $template -replace 'TABLE_CONTROLS_SCRIPT', $tableControlsScript
                $template = $template -replace 'COMMENTS_SCRIPT_PLACEHOLDER', $commentCode
                $template = $template -replace 'TIMESTAMP', (Get-Date -Format "M/d/yyyy")

                $tableRows = Generate-TableRows -Items $programData.items -Type "program"
                $template = $template -replace 'TABLE_ROWS', $tableRows

                Set-Content -Path $outputPath -Value $template -Encoding UTF8
                Write-Host "Generated: $StateCode-programs.html"
            }
        } catch {
            Write-Error "Error processing $StateCode programs: $_"
        }
    } else {
        # Generate coming soon page for missing program data
        Generate-ComingSoonPage -OutputPath (Join-Path $outputBaseDir "states\$StateCode-programs.html") `
                               -Title "$StateCode Programs" `
                               -Message "Program rankings for $StateCode are being compiled. Please check back soon!"
    }
}

function Process-AllTimeData {
    param (
        [string]$Category,  # "teams" or "programs"
        [string]$Threshold = $null
    )

    Write-Host "Processing all-time $Category $(if ($Threshold) {"($Threshold+ seasons)"})"

    # Determine JSON path
    $jsonFileName = if ($Category -eq "teams") {
        "all-time-teams.json"
    } else {
        "all-time-programs-$Threshold.json"
    }
    $jsonPath = Join-Path $dataDir "all-time\$jsonFileName"
    Write-Host "Looking for JSON file: $jsonPath"

    if (Test-Path $jsonPath) {
        try {
            $jsonData = Get-Content $jsonPath -Raw | ConvertFrom-Json
            
            # Generate the standardized JSON file
            if ($Category -eq "teams") {
                Generate-StandardizedJson -Type "all-time-teams" `
                                       -Items $jsonData.items `
                                       -TopItem $jsonData.topItem `
                                       -Description "All-Time Greatest Teams" `
                                       -YearRange "all-time" `
                                       -OutputPath $jsonPath
            } else {
                Generate-StandardizedJson -Type "all-time-programs" `
                                       -Items $jsonData.items `
                                       -TopItem $jsonData.topItem `
                                       -Description "All-Time Programs $Threshold+ Seasons" `
                                       -YearRange "all-time" `
                                       -OutputPath $jsonPath
            }

            # Process template
            $templateName = if ($Category -eq "teams") {
                "all-time-teams-template.html"
            } else {
                "all-time-programs-template.html"
            }
            $templatePath = Join-Path $templateBaseDir "all-time\$templateName"

            if (Test-Path $templatePath) {
                Write-Host "Using template: $templateName"

                # Output name
                $outputFileName = if ($Category -eq "teams") {
                    "teams.html"
                } else {
                    "programs-$Threshold-plus.html"
                }
                $outputPath = Join-Path $outputBaseDir "all-time\$outputFileName"

                $template = Get-Content $templatePath -Raw

                $pageTitle = if ($Category -eq "teams") {
                    "All-Time Greatest Teams"
                } else {
                    "All-Time Programs $Threshold+ Seasons"
                }
                $template = $template -replace 'PAGE_TITLE', $pageTitle
                
                # Add this new section right after the page title replacement
                if ($Category -eq "programs") {
                    $template = $template -replace 'PROGRAM_THRESHOLD', $Threshold
                }
                
                $template = $template -replace 'TABLE_CONTROLS_SCRIPT', $tableControlsScript
                $template = $template -replace 'COMMENTS_SCRIPT_PLACEHOLDER', $commentCode
                $template = $template -replace 'TIMESTAMP', (Get-Date -Format "M/d/yyyy")

                # Table rows
                $tableRows = Generate-TableRows -Items $jsonData.items -Type $(if ($Category -eq "teams") { "team" } else { "program" })
                $template = $template -replace 'TABLE_ROWS', $tableRows

                Set-Content -Path $outputPath -Value $template -Encoding UTF8
                Write-Host "Generated: $outputFileName"
            } else {
                Write-Error "Template not found: $templatePath"
            }
        } catch {
            Write-Error "Error processing $jsonFileName : $_"
        }
    } else {
        Write-Warning "JSON file not found: $jsonPath"
    }
}

function Process-LatestSeasonData {
    Write-Host "Processing latest season data..." -ForegroundColor Yellow
    
    # Update the path to match the correct file name
    $jsonPath = Join-Path $dataDir "latest\latest-teams.json"
    Write-Host "Looking for file at: $jsonPath" -ForegroundColor Yellow
    
    if (Test-Path $jsonPath) {
        Write-Host "Found JSON file" -ForegroundColor Green
        try {
            $jsonContent = Get-Content $jsonPath -Raw
            Write-Host "JSON content length: $($jsonContent.Length)" -ForegroundColor Yellow
            $jsonData = $jsonContent | ConvertFrom-Json

            # Generate the standardized JSON file (like we do for other categories)
            Generate-StandardizedJson -Type "latest-teams" `
                                   -Items $jsonData.items `
                                   -TopItem $jsonData.topItem `
                                   -Description "Latest Season Rankings" `
                                   -YearRange "latest" `
                                   -OutputPath $jsonPath

            $templatePath = Join-Path $templateBaseDir "latest-season\latest-season-template.html"
            if (Test-Path $templatePath) {
                $template = Get-Content $templatePath -Raw
                
                # Define output path (this was missing in original)
                $outputPath = Join-Path $outputBaseDir "latest-season\index.html"

                # Insert scripts and update timestamp
                $template = $template -replace 'TABLE_CONTROLS_SCRIPT', $tableControlsScript
                $template = $template -replace 'COMMENTS_SCRIPT_PLACEHOLDER', $commentCode
                $template = $template -replace 'TIMESTAMP', (Get-Date -Format "M/d/yyyy")

                $tableRows = Generate-TableRows -Items $jsonData.items -Type "team"
                $template = $template -replace 'TABLE_ROWS', $tableRows

                # Write with UTF8 encoding to handle special characters
                [System.IO.File]::WriteAllText($outputPath, $template, [System.Text.Encoding]::UTF8)
                Write-Host "Generated: latest-season/index.html" -ForegroundColor Green
            } else {
                Write-Error "Template not found: $templatePath"
                Generate-ComingSoonPage -OutputPath (Join-Path $outputBaseDir "latest-season\index.html") `
                                      -Title "Latest Season Rankings" `
                                      -Message "Template file missing. Please check back soon!"
            }
        } catch {
            Write-Error "Error processing latest season data: $_"
            Generate-ComingSoonPage -OutputPath (Join-Path $outputBaseDir "latest-season\index.html") `
                                  -Title "Latest Season Rankings" `
                                  -Message "Error processing latest season data. Please check back soon!"
        }
    } else {
        Write-Warning "Latest season JSON file not found: $jsonPath"
        Generate-ComingSoonPage -OutputPath (Join-Path $outputBaseDir "latest-season\index.html") `
                               -Title "Latest Season Rankings" `
                               -Message "Latest season rankings are being compiled. Please check back soon!"
    }
}

function Process-MediaNationalChampions {
    Write-Host "Processing Media National Champions data..." -ForegroundColor Yellow
    $jsonPath = Join-Path $dataDir "media-national-champions\media-national-champions.json"
    Write-Host "Looking for data file: $jsonPath"
    
    if (Test-Path $jsonPath) {
        try {
            Write-Host "Loading Media National Champions data..." -ForegroundColor Yellow
            $championsData = Get-Content $jsonPath -Raw | ConvertFrom-Json
            $outputPath = Join-Path $outputBaseDir "media-national-champions.html"
            $templatePath = Join-Path $templateBaseDir "media-national-champions-template.html"
            
            if (Test-Path $templatePath) {
                $template = Get-Content $templatePath -Raw
                # Fix data-file meta tag
                $template = $template -replace '<meta name="data-file" content="[^"]*">', 
                    '<meta name="data-file" content="/static-football-rankings/data/media-national-champions/media-national-champions.json">'
                
                # Use no-pagination script for Media NC (show all 140 champions)
                $noPaginationScript = @'
<script>
    const TableControls = {
        filteredRows: [],
        init() {
            const tableBody = document.querySelector('tbody');
            if (tableBody) {
                const rows = Array.from(tableBody.getElementsByTagName('tr'));
                this.filteredRows = rows;
                this.setupEventListeners();
                this.showAllRows();
            }
        },
        setupEventListeners() {
            const searchInput = document.getElementById('tableSearch');
            if (searchInput) {
                searchInput.value = '';
                searchInput.addEventListener('input', (e) => this.filterTable(e.target.value.toLowerCase()));
            }
        },
        filterTable(searchTerm) {
            const tableBody = document.querySelector('tbody');
            if (!tableBody) return;
            const rows = Array.from(tableBody.getElementsByTagName('tr'));
            this.filteredRows = searchTerm.trim() === '' ? rows : rows.filter(row => {
                const text = Array.from(row.getElementsByTagName('td')).map(cell => cell.textContent).join(' ').toLowerCase();
                return text.includes(searchTerm);
            });
            this.showAllRows();
        },
        showAllRows() {
            const tableBody = document.querySelector('tbody');
            if (!tableBody) return;
            const allRows = Array.from(tableBody.getElementsByTagName('tr'));
            allRows.forEach(row => row.style.display = 'none');
            this.filteredRows.forEach(row => { row.style.display = ''; });
        }
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => TableControls.init());
    else TableControls.init();
</script>
'@
                
                # Replace placeholders
                $template = $template -replace 'TABLE_CONTROLS_SCRIPT', $noPaginationScript
                $template = $template -replace 'COMMENTS_SCRIPT_PLACEHOLDER', $commentCode
                $template = $template -creplace 'TIMESTAMP', (Get-Date -Format "M/d/yyyy")
                
                # Remove any userStyle tags
                $template = $template -replace '<userStyle>Normal</userStyle>', ''
                
                # Generate table rows - NEW COLUMN LAYOUT
                $tableRows = $championsData.items | ForEach-Object {
                    # Format combined rating
                    $combined = if ($null -ne $_.combined -and $_.combined -gt 0) { 
                        [math]::Round([double]$_.combined, 3) 
                    } else { 
                        "" 
                    }
                    
                    # Get record (already formatted as W-L-T)
                    $record = if ($_.record) { $_.record } else { "" }
                    
                    # Get coach name
                    $coach = if ($_.coach) { $_.coach } else { "" }
                    
                    # Get sources (use display field we created in Python)
                    $sources = if ($_.sources_display) { $_.sources_display } else { "N/A" }
                    
                    # Get notes
                    $notes = if ($_.notes) { $_.notes } else { "" }
                    
                    @"
    <tr>
        <td>$($_.year)</td>
        <td>$($_.team)</td>
        <td>$combined</td>
        <td>$record</td>
        <td>$coach</td>
        <td>$sources</td>
        <td>$notes</td>
        <td class="text-center">$($_.teamLinkHtml)</td>
    </tr>
"@
                }
                
                $template = $template -replace 'TABLE_ROWS', ($tableRows -join "`n")
                Set-Content -Path $outputPath -Value $template -Encoding UTF8
                Write-Host "Generated: media-national-champions.html" -ForegroundColor Green
            } else {
                Write-Error "Media National Champions template not found: $templatePath"
                Generate-ComingSoonPage -OutputPath $outputPath -Title "Media National Champions" -Message "Coming soon!"
            }
        } catch {
            Write-Error "Error processing Media National Champions data: $_"
            Generate-ComingSoonPage -OutputPath (Join-Path $outputBaseDir "media-national-champions.html") -Title "Media National Champions" -Message "Coming soon!"
        }
    } else {
        Write-Warning "Media National Champions data not found: $jsonPath"
        Generate-ComingSoonPage -OutputPath (Join-Path $outputBaseDir "media-national-champions.html") -Title "Media National Champions" -Message "Coming soon!"
    }
}

function Process-McKnightNationalChampions {
    Write-Host "Processing McKnight National Champions data..." -ForegroundColor Yellow
    $jsonPath = Join-Path $dataDir "mcknight-national-champions\mcknight-national-champions.json"
    Write-Host "Looking for data file: $jsonPath"
    
    if (Test-Path $jsonPath) {
        try {
            Write-Host "Loading McKnight National Champions data..." -ForegroundColor Yellow
            $championsData = Get-Content $jsonPath -Raw | ConvertFrom-Json
            $outputPath = Join-Path $outputBaseDir "mcknight-national-champions.html"
            $templatePath = Join-Path $templateBaseDir "mcknight-national-champions-template.html"
            
            if (Test-Path $templatePath) {
                $template = Get-Content $templatePath -Raw
                # Fix data-file meta tag
                $template = $template -replace '<meta name="data-file" content="[^"]*">', 
                    '<meta name="data-file" content="/static-football-rankings/data/mcknight-national-champions/mcknight-national-champions.json">'
                # Replace placeholders
                $template = $template -replace 'TABLE_CONTROLS_SCRIPT', $tableControlsScript
                $template = $template -replace 'COMMENTS_SCRIPT_PLACEHOLDER', $commentCode
                $template = $template -creplace 'TIMESTAMP', (Get-Date -Format "M/d/yyyy")
                
                # Remove any userStyle tags
                $template = $template -replace '<userStyle>Normal</userStyle>', ''
                
                # Generate table rows
                $tableRows = $championsData.items | ForEach-Object {
                    $combined = if ($null -ne $_.combined) { [math]::Round([double]$_.combined, 3) } else { "" }
                    $margin = if ($null -ne $_.margin) { [math]::Round([double]$_.margin, 3) } else { "" }
                    $winLoss = if ($null -ne $_.win_loss) { [math]::Round([double]$_.win_loss, 3) } else { "" }
                    $offense = if ($null -ne $_.offense) { [math]::Round([double]$_.offense, 3) } else { "" }
                    $defense = if ($null -ne $_.defense) { [math]::Round([double]$_.defense, 3) } else { "" }
                    
                    @"
    <tr>
        <td>$($_.year)</td>
        <td>$($_.team)</td>
        <td>$combined</td>
        <td>$margin</td>
        <td>$winLoss</td>
        <td>$offense</td>
        <td>$defense</td>
        <td>$($_.games_played)</td>
        <td class="text-center">$($_.teamLinkHtml)</td>
    </tr>
"@
                }
                
                $template = $template -replace 'TABLE_ROWS', ($tableRows -join "`n")
                Set-Content -Path $outputPath -Value $template -Encoding UTF8
                Write-Host "Generated: mcknight-national-champions.html" -ForegroundColor Green
            } else {
                Write-Error "McKnight National Champions template not found: $templatePath"
                Generate-ComingSoonPage -OutputPath $outputPath -Title "McKnight National Champions" -Message "Coming soon!"
            }
        } catch {
            Write-Error "Error processing McKnight National Champions data: $_"
            Generate-ComingSoonPage -OutputPath (Join-Path $outputBaseDir "mcknight-national-champions.html") -Title "McKnight National Champions" -Message "Coming soon!"
        }
    } else {
        Write-Warning "McKnight National Champions data not found: $jsonPath"
        Generate-ComingSoonPage -OutputPath (Join-Path $outputBaseDir "mcknight-national-champions.html") -Title "McKnight National Champions" -Message "Coming soon!"
    }
}

function Process-GreatestGames {
    Write-Host "Processing Greatest Games page..." -ForegroundColor Yellow

    $templatePath = Join-Path $templateBaseDir "greatest\greatest-games.html"
    $outputDir    = Join-Path $outputBaseDir   "greatest"
    $outputPath   = Join-Path $outputDir        "greatest-games.html"

    # Ensure output directory exists
    if (-not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
        Write-Host "  Created output directory: $outputDir" -ForegroundColor Cyan
    }

    if (Test-Path $templatePath) {
        try {
            $template = Get-Content $templatePath -Raw -Encoding UTF8

            # Inject comments script (same pattern as all other pages)
            $template = $template -replace 'COMMENTS_SCRIPT_PLACEHOLDER', $commentCode

            # Remove any stray userStyle tags (housekeeping, same as other functions)
            $template = $template -replace '<userStyle>Normal</userStyle>', ''

            Set-Content -Path $outputPath -Value $template -Encoding UTF8
            Write-Host "  Generated: greatest-games.html" -ForegroundColor Green
        } catch {
            Write-Error "Error processing Greatest Games template: $_"
            Generate-ComingSoonPage `
                -OutputPath $outputPath `
                -Title "Greatest Games" `
                -Message "The Greatest Games rankings are coming soon. Please check back later."
        }
    } else {
        Write-Warning "Greatest Games template not found: $templatePath"
        Generate-ComingSoonPage `
            -OutputPath $outputPath `
            -Title "Greatest Games" `
            -Message "The Greatest Games rankings are coming soon. Please check back later."
    }
}

function Process-GreatestGames {
    Write-Host "Processing Greatest Games page..." -ForegroundColor Yellow

    $templatePath = Join-Path $templateBaseDir "greatest\greatest-games.html"
    $outputDir    = Join-Path $outputBaseDir   "greatest"
    $outputPath   = Join-Path $outputDir        "greatest-games.html"

    # Ensure output directory exists
    if (-not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
        Write-Host "  Created output directory: $outputDir" -ForegroundColor Cyan
    }

    if (Test-Path $templatePath) {
        try {
            $template = Get-Content $templatePath -Raw

            # Inject comments script (same pattern as all other pages)
            $template = $template -replace 'COMMENTS_SCRIPT_PLACEHOLDER', $commentCode

            # Remove any stray userStyle tags (housekeeping, same as other functions)
            $template = $template -replace '<userStyle>Normal</userStyle>', ''

            Set-Content -Path $outputPath -Value $template -Encoding UTF8
            Write-Host "  Generated: greatest-games.html" -ForegroundColor Green
        } catch {
            Write-Error "Error processing Greatest Games template: $_"
            Generate-ComingSoonPage `
                -OutputPath $outputPath `
                -Title "Greatest Games" `
                -Message "The Greatest Games rankings are coming soon. Please check back later."
        }
    } else {
        Write-Warning "Greatest Games template not found: $templatePath"
        Generate-ComingSoonPage `
            -OutputPath $outputPath `
            -Title "Greatest Games" `
            -Message "The Greatest Games rankings are coming soon. Please check back later."
    }
}

function Process-GreatestRivalries {
    Write-Host "Processing Greatest Rivalries page..." -ForegroundColor Yellow

    $templatePath = Join-Path $templateBaseDir "greatest\greatest-rivalries.html"
    $outputDir    = Join-Path $outputBaseDir   "greatest"
    $outputPath   = Join-Path $outputDir        "greatest-rivalries.html"

    if (-not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
        Write-Host "  Created output directory: $outputDir" -ForegroundColor Cyan
    }

    if (Test-Path $templatePath) {
        try {
            $template = Get-Content $templatePath -Raw -Encoding UTF8
            $template = $template -replace 'COMMENTS_SCRIPT_PLACEHOLDER', $commentCode
            $template = $template -replace '<userStyle>Normal</userStyle>', ''
            Set-Content -Path $outputPath -Value $template -Encoding UTF8
            Write-Host "  Generated: greatest-rivalries.html" -ForegroundColor Green
        } catch {
            Write-Error "Error processing Greatest Rivalries template: $_"
            Generate-ComingSoonPage `
                -OutputPath $outputPath `
                -Title "Greatest Rivalries" `
                -Message "The Greatest Rivalries rankings are coming soon. Please check back later."
        }
    } else {
        Write-Warning "Greatest Rivalries template not found: $templatePath"
        Generate-ComingSoonPage `
            -OutputPath $outputPath `
            -Title "Greatest Rivalries" `
            -Message "The Greatest Rivalries rankings are coming soon. Please check back later."
    }
}

#endregion Processing Functions

#region Main Script Execution
try {
    Write-Host "Starting page generation..." -ForegroundColor Green
    
    # Initial template verification - do this first
    Write-Host "Performing initial template verification..." -ForegroundColor Yellow
    if (-not (Test-RequiredTemplates)) {
        Write-Warning "Some templates are missing. Limited functionality will be available."
        Write-Host "Press any key to continue or Ctrl+C to abort..." -ForegroundColor Yellow
        $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
    }

    Write-Host "Verifying data directory structure..." -ForegroundColor Yellow
    
    # Debug: Check if we can access the data directory
    Get-ChildItem $dataDir -Directory | ForEach-Object {
        Write-Host "Found directory: $($_.FullName)" -ForegroundColor Cyan
    }

    # Process Decades
    Write-Host "`nProcessing decades..." -ForegroundColor Green
    $decades = @(
        [ordered]@{ Name = "pre1900"; StartYear = 1877; EndYear = 1899; DisplayName = "Pre-1900s" },
        [ordered]@{ Name = "1900s"; StartYear = 1900; EndYear = 1909; DisplayName = "1900s" },
        [ordered]@{ Name = "1910s"; StartYear = 1910; EndYear = 1919; DisplayName = "1910s" },
        [ordered]@{ Name = "1920s"; StartYear = 1920; EndYear = 1929; DisplayName = "1920s" },
        [ordered]@{ Name = "1930s"; StartYear = 1930; EndYear = 1939; DisplayName = "1930s" },
        [ordered]@{ Name = "1940s"; StartYear = 1940; EndYear = 1949; DisplayName = "1940s" },
        [ordered]@{ Name = "1950s"; StartYear = 1950; EndYear = 1959; DisplayName = "1950s" },
        [ordered]@{ Name = "1960s"; StartYear = 1960; EndYear = 1969; DisplayName = "1960s" },
        [ordered]@{ Name = "1970s"; StartYear = 1970; EndYear = 1979; DisplayName = "1970s" },
        [ordered]@{ Name = "1980s"; StartYear = 1980; EndYear = 1989; DisplayName = "1980s" },
        [ordered]@{ Name = "1990s"; StartYear = 1990; EndYear = 1999; DisplayName = "1990s" },
        [ordered]@{ Name = "2000s"; StartYear = 2000; EndYear = 2009; DisplayName = "2000s" },
        [ordered]@{ Name = "2010s"; StartYear = 2010; EndYear = 2019; DisplayName = "2010s" },
        [ordered]@{ Name = "2020s"; StartYear = 2020; EndYear = 2029; DisplayName = "2020s" }
    )

    foreach ($decade in $decades) {
        Process-DecadeData -DecadeName $decade.Name -StartYear $decade.StartYear -EndYear $decade.EndYear -DisplayName $decade.DisplayName
    }

    # Define regions and states
$stateRegions = @{
    "Northeast" = @{
        Name = "Northeast"
        States = @("CT", "DC", "DE", "ME", "MA", "NH", "RI", "VT", "NJ", "NY", "PA")
        Color = "region-northeast"
        Title = "Northeast States"
    }
    "South" = @{
        Name = "South"
        States = @("AL", "AR", "FL", "GA", "KY", "LA", "MD", "MS", "NC", "SC", "TN", "VA", "WV")
        Color = "region-south"
        Title = "Southern States"
    }
    "Midwest" = @{
        Name = "Midwest"
        States = @("IL", "IN", "IA", "KS", "MI", "MN", "MO", "NE", "ND", "OH", "SD", "WI")
        Color = "region-midwest"
        Title = "Midwestern States"
    }
    "West" = @{
        Name = "West"
        States = @("AK", "AZ", "CA", "CO", "HI", "ID", "MT", "NV", "NM", "OR", "UT", "WA", "WY")
        Color = "region-west"
        Title = "Western States"
    }
    "Canada" = @{
        Name = "Canada"
        States = @("AB", "BC", "SK", "MB", "NS", "QB", "NB")
        Color = "region-canada"
        Title = "Canadian Provinces"
    }
}


    # Process States
    Write-Host "`nProcessing state rankings..." -ForegroundColor Green
    $stateTeamsDir = Join-Path $dataDir "states\teams"
    if (Test-Path $stateTeamsDir) {
        $stateFiles = Get-ChildItem $stateTeamsDir -Filter "state-teams-*.json"
        $stateCodes = $stateFiles | ForEach-Object {
            $_.BaseName -replace 'state-teams-', ''
        } | Sort-Object -Unique

        foreach ($stateCode in $stateCodes) {
            Process-StateData -StateCode $stateCode
        }
    } else {
        Write-Warning "No state-teams directory found. Skipping state-based generation."
    }

    # Process All-Time Rankings
    Write-Host "`nProcessing all-time rankings..." -ForegroundColor Green
    
    # Process all-time teams
    Write-Host "Processing all-time teams..." -ForegroundColor Cyan
    $allTimeTeamsPath = Join-Path $dataDir "all-time\all-time-teams.json"
    if (Test-Path $allTimeTeamsPath) {
        Process-AllTimeData -Category "teams"
    } else {
        Write-Warning "All-time teams data not yet available"
        Generate-ComingSoonPage -OutputPath (Join-Path $outputBaseDir "all-time\teams.html") `
                               -Title "All-Time Greatest Teams" `
                               -Message "All-time team rankings are coming soon! Please check back later."
    }
    
    # Process all-time programs
    Write-Host "Processing all-time programs..." -ForegroundColor Cyan
    @("25", "50", "100") | ForEach-Object {
        Write-Host "Processing all-time programs ($_ seasons)..." -ForegroundColor Yellow
        Process-AllTimeData -Category "programs" -Threshold $_
    }

    # Process Latest Season
    Write-Host "`nProcessing latest season rankings..." -ForegroundColor Green
    Process-LatestSeasonData

    # Process National Champions
    Write-Host "`nProcessing National Champions..." -ForegroundColor Green
    Process-MediaNationalChampions
    Process-McKnightNationalChampions

    # Process Greatest Games
    Write-Host "`nProcessing Greatest Games..." -ForegroundColor Green
    Process-GreatestGames

    # Process Greatest Rivalries
    Write-Host "`nProcessing Greatest Rivalries..." -ForegroundColor Green
    Process-GreatestRivalries

    # Generate Index Pages
    Write-Host "`nGenerating index pages..." -ForegroundColor Green

    # Decades index
    Write-Host "Generating decades index..." -ForegroundColor Yellow
    $decadeIndexPath = Join-Path $outputBaseDir "decades\index.html"
    Write-Host "Output path: $decadeIndexPath" -ForegroundColor Cyan
    $decadeIndexTemplatePath = Join-Path $templateBaseDir "index\decades-index-template.html"
    Write-Host "Template path: $decadeIndexTemplatePath" -ForegroundColor Cyan

    if (Test-Path $decadeIndexTemplatePath) {
        $decadeIndexTemplate = Get-Content $decadeIndexTemplatePath -Raw
        $decadeCards = $decades | ForEach-Object {
            @"
<div class="col-md-6 mb-4">
    <div class="card h-100">
        <div class="card-body d-flex flex-column">
            <h5 class="card-title">$($_.DisplayName)</h5>
            <p class="card-text">Top teams and programs from $($_.StartYear) to $($_.EndYear)</p>
            <div class="mt-auto">
                <a href="$($_.Name)-teams.html" class="btn btn-primary me-2">Season Rankings</a>
                <a href="$($_.Name)-programs.html" class="btn btn-outline-primary">Program Rankings</a>
            </div>
        </div>
    </div>
</div>
"@
        }
        $decadeIndexContent = $decadeIndexTemplate -replace 'DECADE_CARDS', ($decadeCards -join "`n")
        Set-Content -Path $decadeIndexPath -Value $decadeIndexContent -Encoding UTF8
        Write-Host "Generated decades index page" -ForegroundColor Green
    }



    # All-time index
    Write-Host "Generating all-time index..." -ForegroundColor Yellow
    $allTimeIndexPath = Join-Path $outputBaseDir "all-time\index.html"
    $allTimeIndexTemplatePath = Join-Path $templateBaseDir "index\all-time-index-template.html"
    if (Test-Path $allTimeIndexTemplatePath) {
        $allTimeIndexTemplate = Get-Content $allTimeIndexTemplatePath -Raw
        Set-Content -Path $allTimeIndexPath -Value $allTimeIndexTemplate -Encoding UTF8
        Write-Host "Generated all-time rankings index page" -ForegroundColor Green
    }

    # States index
    Write-Host "Generating states index..." -ForegroundColor Yellow
    $statesIndexPath = Join-Path $outputBaseDir "states\index.html"
    $statesIndexTemplatePath = Join-Path $templateBaseDir "index\states-index-template.html"
    if (Test-Path $statesIndexTemplatePath) {
        $statesIndexTemplate = Get-Content $statesIndexTemplatePath -Raw
        if ($stateCodes) {
            $stateCards = $stateCodes | ForEach-Object {
                @"
<div class="col-md-4 mb-4">
    <div class="card h-100">
        <div class="card-body d-flex flex-column">
            <h5 class="card-title">$_</h5>
            <div class="mt-auto">
                <a href="$_-teams.html" class="btn btn-primary me-2">Teams</a>
                <a href="$_-programs.html" class="btn btn-outline-primary">Programs</a>
            </div>
        </div>
    </div>
</div>
"@
            }
            $statesIndexContent = $statesIndexTemplate -replace 'STATE_CARDS', ($stateCards -join "`n")
        } else {
            $statesIndexContent = $statesIndexTemplate -replace 'STATE_CARDS', ''
        }
        Set-Content -Path $statesIndexPath -Value $statesIndexContent -Encoding UTF8
        Write-Host "Generated states index page" -ForegroundColor Green
    }

    Write-Host "`nPage generation completed successfully!" -ForegroundColor Green
} catch {
    Write-Error "Generation failed: $_"
    exit 1
} finally {
    Write-Host "Script execution completed." -ForegroundColor Green
}
#endregion Main Script Execution