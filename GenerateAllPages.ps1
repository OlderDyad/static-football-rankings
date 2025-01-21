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
    (Join-Path $outputBaseDir "latest-season")
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

# Helper function to check individual templates
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
        return "<!-- No top item data available for banner -->"
    }

    # Handle Logo URLs from JSON
    $logoHtml = if ($TopItem.logoURL -and "$($TopItem.logoURL)".Trim()) {
        $logoPath = "/static-football-rankings/$($TopItem.logoURL.TrimStart('/'))"
        "<img src=`"$logoPath`" alt=`"Logo`" class=`"img-fluid team-logo`" onerror=`"this.style.display='none'`" />"
    } else {
        "<!-- No logo available -->"
    }

    $schoolLogoHtml = if ($TopItem.schoolLogoURL -and "$($TopItem.schoolLogoURL)".Trim()) {
        $schoolPath = "/static-football-rankings/$($TopItem.schoolLogoURL.TrimStart('/'))"
        "<img src=`"$schoolPath`" alt=`"School Logo`" class=`"img-fluid school-logo`" onerror=`"this.style.display='none'`" />"
    } else {
        "<!-- No school logo available -->"
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
            # Team rows - includes Season and Games columns
            @"
            <tr>
                <td>$($_.rank)</td>
                <td>$($_.team)</td>
                <td>$($_.season)</td>         # Single season
                <td>$($_.combined)</td>
                <td>$($_.margin)</td>
                <td>$($_.win_loss)</td>
                <td>$($_.offense)</td>
                <td>$($_.defense)</td>
                <td>$($_.games_played)</td>   # Games column
                <td>$($_.state)</td>
            </tr>
"@
        } else {
            # Program rows - includes Seasons column, no Games column
            @"
            <tr>
                <td>$($_.rank)</td>
                <td>$($_.program)</td>
                <td>$($_.seasons)</td>        # Multiple seasons
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
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Custom Stylesheet -->
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

    <!-- Bootstrap JS Bundle -->
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
$commentCode = @'
<script>
const VERCEL_API_BASE = "https://static-football-rankings.vercel.app/api";

/**********************************************************
 * AUTH / LOGIN LOGIC
 **********************************************************/
async function checkLoginStatus() {
    try {
        const res = await fetch(`${VERCEL_API_BASE}/auth/status`, {
            method: 'GET',
            credentials: 'include'
        });
        const data = await res.json();

        if (data.success && data.loggedIn) {
            document.getElementById('commentForm').style.display = 'block';
            document.getElementById('authorName').textContent = data.user.name || 'Anonymous';
            renderAuthUI(true, data.user);
        } else {
            document.getElementById('commentForm').style.display = 'none';
            document.getElementById('authorName').textContent = 'Anonymous';
            renderAuthUI(false);
        }
    } catch (error) {
        console.error('Login status error:', error);
        document.getElementById('commentForm').style.display = 'none';
        document.getElementById('authorName').textContent = 'Anonymous';
        renderAuthUI(false);
    }
}

function renderAuthUI(loggedIn, user = null) {
    const authContainer = document.getElementById('authContainer');
    if (!authContainer) return;

    if (loggedIn && user) {
        authContainer.innerHTML = `
            <p>Welcome, <strong>${user.name}</strong> (${user.email})
               <button id="logoutBtn" class="btn btn-outline-secondary btn-sm">Logout</button></p>
        `;
        document.getElementById('logoutBtn').addEventListener('click', doLogout);
    } else {
        authContainer.innerHTML = `
            <button id="loginBtn" class="btn btn-success">Sign in with Google</button>
        `;
        document.getElementById('loginBtn').addEventListener('click', doLogin);
    }
}

function doLogin() {
    window.location.href = `${VERCEL_API_BASE}/auth/google`;
}

function doLogout() {
    document.cookie = "auth_token=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Secure; SameSite=None;";
    document.cookie = "user_name=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Secure; SameSite=None;";
    document.cookie = "user_email=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Secure; SameSite=None;";
    window.location.reload();
}

/**********************************************************
 * COMMENTS LOGIC
 **********************************************************/
async function fetchComments() {
    const pageId = getPageId();
    try {
        const res = await fetch(`${VERCEL_API_BASE}/comments?pageId=${encodeURIComponent(pageId)}`, {
            method: 'GET',
            credentials: 'include'
        });
        const data = await res.json();
        if (data.success) {
            displayComments(data.comments);
        }
    } catch (err) {
        console.error('Error fetching comments:', err);
    }
}

function displayComments(comments) {
    const list = document.getElementById('commentsList');
    if (!list) return;
    if (!Array.isArray(comments) || comments.length === 0) {
        list.innerHTML = '<p class="text-muted">No comments yet</p>';
        return;
    }
    list.innerHTML = comments.map(c => `
        <div class="card mb-2">
            <div class="card-body">
                <p class="mb-1">${escapeHTML(c.text)}</p>
                <small class="text-muted">
                    by ${escapeHTML(c.author)} on ${new Date(c.timestamp).toLocaleString()}
                </small>
            </div>
        </div>
    `).join('');
}

async function submitComment() {
    const textEl = document.getElementById('commentText');
    const text = textEl.value.trim();
    if (!text) return alert('Please enter a comment');

    const pageId = getPageId();

    try {
        const res = await fetch(`${VERCEL_API_BASE}/comments`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, pageId })
        });
        const data = await res.json();
        if (data.success) {
            textEl.value = '';
            fetchComments();
        } else {
            alert('Error posting comment: ' + (data.error || 'Unknown'));
        }
    } catch (err) {
        console.error('Error posting comment:', err);
        alert('Failed to post comment');
    }
}

function escapeHTML(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function getPageId() {
    const el = document.querySelector('[data-page-name]');
    return el ? el.getAttribute('data-page-name') : 'unknown';
}

// Initialize
document.getElementById('submitComment')?.addEventListener('click', submitComment);

(function initPage() {
    checkLoginStatus();
    fetchComments();
})();
</script>
'@
#endregion Template Scripts

#region Processing Functions
function Process-DecadeData {
    param (
        [string]$DecadeName,
        [string]$StartYear,
        [string]$EndYear,
        [string]$DisplayName
    )

    Write-Host "`n========== Processing $DisplayName Programs ==========" -ForegroundColor Cyan

    # Debug: Show input parameters
    Write-Host "Parameters:" -ForegroundColor Yellow
    Write-Host "  DecadeName: $DecadeName"
    Write-Host "  StartYear: $StartYear"
    Write-Host "  EndYear: $EndYear"
    Write-Host "  DisplayName: $DisplayName"

    # Process programs for this decade
    $programJsonPath = Join-Path $dataDir "decades\programs\decade-programs-$DecadeName.json"
    
    Write-Host "`nPaths:" -ForegroundColor Yellow
    Write-Host "  JSON Path: $programJsonPath"
    
    if (Test-Path $programJsonPath) {
        try {
            Write-Host "`nReading JSON data..." -ForegroundColor Yellow
            $jsonContent = Get-Content $programJsonPath -Raw
            Write-Host "  Raw JSON length: $($jsonContent.Length) characters"
            
            $programData = $null
            try {
                $programData = $jsonContent | ConvertFrom-Json
                Write-Host "  JSON successfully parsed" -ForegroundColor Green
            }
            catch {
                Write-Error "JSON parsing failed: $_"
                Write-Host "  First 500 characters of JSON:" -ForegroundColor Red
                Write-Host ($jsonContent.Substring(0, [Math]::Min(500, $jsonContent.Length)))
                return
            }

            # Debug: Check program data structure
            if ($programData.items) {
                Write-Host "`nProgram Data:" -ForegroundColor Yellow
                Write-Host "  Total Items: $($programData.items.Count)"
                Write-Host "`nFirst item details:" -ForegroundColor Yellow
                $firstItem = $programData.items[0]
                Write-Host "  Rank: $($firstItem.rank)"
                Write-Host "  Program: $($firstItem.program)"
                Write-Host "  State: $($firstItem.state)"
            } else {
                Write-Warning "No items found in program data"
            }

            $outputPath = Join-Path $outputBaseDir "decades\$DecadeName-programs.html"
            $templatePath = Join-Path $templateBaseDir "decades\decade-programs-template.html"
            
            if (Test-Path $templatePath) {
                Write-Host "`nProcessing template..." -ForegroundColor Yellow
                $template = Get-Content $templatePath -Raw

                # Replace placeholders
                $template = $template -replace 'DECADE_DISPLAY_NAME', $DisplayName
                $template = $template -replace 'DECADE_NAME', $DecadeName
                $template = $template -replace 'DECADE_START', $StartYear
                $template = $template -replace 'DECADE_END', $EndYear
                $template = $template -replace 'TABLE_CONTROLS_SCRIPT', $tableControlsScript
                $template = $template -replace 'COMMENTS_SCRIPT_PLACEHOLDER', $commentCode
                $template = $template -replace 'TIMESTAMP', (Get-Date -Format "M/d/yyyy")

                # Banner
                if ($programData.topItem) {
                    Write-Host "  Generating banner for top program: $($programData.topItem.program)" -ForegroundColor Yellow
                    $bannerHtml = Generate-TeamBanner -TopItem $programData.topItem -Type "program"
                    $template = $template -replace '<div id="teamHeaderContainer"></div>', $bannerHtml
                }

                # Table rows
                Write-Host "  Generating table rows..." -ForegroundColor Yellow
                $tableRows = Generate-TableRows -Items $programData.items -Type "program"
                Write-Host "  Generated $($programData.items.Count) table rows"
                $template = $template -replace 'TABLE_ROWS', $tableRows

                Set-Content -Path $outputPath -Value $template -Encoding UTF8
                Write-Host "`nGenerated: $DecadeName-programs.html" -ForegroundColor Green
            } else {
                Write-Error "Template not found: $templatePath"
            }
        } catch {
            Write-Error "Error processing $DecadeName programs: $_"
        }
    } else {
        Write-Error "JSON file not found: $programJsonPath"
    }
}

function Process-StateData {
    param (
        [string]$StateCode
    )

    Write-Host "Processing state: $StateCode"

    # Process teams for this state
    $teamJsonPath = Join-Path $dataDir "states\teams\state-teams-$StateCode.json"
    if (Test-Path $teamJsonPath) {
        try {
            $teamData = Get-Content $teamJsonPath -Raw | ConvertFrom-Json
            $outputPath = Join-Path $outputBaseDir "states\$StateCode-teams.html"

            $templatePath = Join-Path $templateBaseDir "states\state-teams-template.html"
            if (Test-Path $templatePath) {
                $template = Get-Content $templatePath -Raw

                $template = $template -replace 'STATE_CODE', $StateCode
                $template = $template -replace 'TABLE_CONTROLS_SCRIPT', $tableControlsScript
                $template = $template -replace 'COMMENTS_SCRIPT_PLACEHOLDER', $commentCode
                $template = $template -replace 'TIMESTAMP', (Get-Date -Format "M/d/yyyy")

                if ($teamData.topItem) {
                    $bannerHtml = Generate-TeamBanner -TopItem $teamData.topItem -Type "team"
                    $template = $template -replace '<div id="teamHeaderContainer"></div>', $bannerHtml
                }

                $tableRows = Generate-TableRows -Items $teamData.items -Type "team"
                $template = $template -replace 'TABLE_ROWS', $tableRows

                Set-Content -Path $outputPath -Value $template -Encoding UTF8
                Write-Host "Generated: $StateCode-teams.html"
            }
        } catch {
            Write-Error "Error processing $StateCode teams: $_"
        }
    }

    # Process programs for this state
    $programJsonPath = Join-Path $dataDir "states\programs\state-programs-$StateCode.json"
    if (Test-Path $programJsonPath) {
        try {
            $programData = Get-Content $programJsonPath -Raw | ConvertFrom-Json
            $outputPath = Join-Path $outputBaseDir "states\$StateCode-programs.html"

            $templatePath = Join-Path $templateBaseDir "states\state-programs-template.html"
            if (Test-Path $templatePath) {
                $template = Get-Content $templatePath -Raw

                $template = $template -replace 'STATE_CODE', $StateCode
                $template = $template -replace 'TABLE_CONTROLS_SCRIPT', $tableControlsScript
                $template = $template -replace 'COMMENTS_SCRIPT_PLACEHOLDER', $commentCode
                $template = $template -replace 'TIMESTAMP', (Get-Date -Format "M/d/yyyy")

                if ($programData.topItem) {
                    $bannerHtml = Generate-TeamBanner -TopItem $programData.topItem -Type "program"
                    $template = $template -replace '<div id="teamHeaderContainer"></div>', $bannerHtml
                }

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
                    "$Threshold+ Seasons All-Time Programs"
                }
                $template = $template -replace 'PAGE_TITLE', $pageTitle
                $template = $template -replace 'TABLE_CONTROLS_SCRIPT', $tableControlsScript
                $template = $template -replace 'COMMENTS_SCRIPT_PLACEHOLDER', $commentCode
                $template = $template -replace 'TIMESTAMP', (Get-Date -Format "M/d/yyyy")

                # Banner
                if ($jsonData.topItem) {
                    $headerHtml = Generate-TeamBanner -TopItem $jsonData.topItem -Type $Category
                    $template = $template -replace '<div id="teamHeaderContainer"></div>', $headerHtml
                }

                # Table rows
                $tableRows = Generate-TableRows -Items $jsonData.items -Type $Category
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
    Write-Host "Processing latest season data..."

    $jsonPath = Join-Path $dataDir "latest-season\latest-season-teams.json"
    if (Test-Path $jsonPath) {
        try {
            $jsonData = Get-Content $jsonPath -Raw | ConvertFrom-Json
            $outputPath = Join-Path $outputBaseDir "latest-season\index.html"

            $templatePath = Join-Path $templateBaseDir "latest-season\latest-season-template.html"
            if (Test-Path $templatePath) {
                $template = Get-Content $templatePath -Raw

                # Insert scripts
                $template = $template -replace 'TABLE_CONTROLS_SCRIPT', $tableControlsScript
                $template = $template -replace 'COMMENTS_SCRIPT_PLACEHOLDER', $commentCode
                $template = $template -replace 'TIMESTAMP', (Get-Date -Format "M/d/yyyy")

                if ($jsonData.topItem) {
                    $bannerHtml = Generate-TeamBanner -TopItem $jsonData.topItem -Type "team"
                    $template = $template -replace '<div id="teamHeaderContainer"></div>', $bannerHtml
                }

                $tableRows = Generate-TableRows -Items $jsonData.items -Type "team"
                $template = $template -replace 'TABLE_ROWS', $tableRows

                Set-Content -Path $outputPath -Value $template -Encoding UTF8
                Write-Host "Generated: latest-season/index.html"
            }
        } catch {
            Write-Error "Error processing latest season data: $_"
            Generate-ComingSoonPage -OutputPath (Join-Path $outputBaseDir "latest-season\index.html") `
                                  -Title "Latest Season Rankings" `
                                  -Message "Latest season rankings are being compiled. Please check back soon!"
        }
    } else {
        Write-Warning "Latest season JSON file not found: $jsonPath"
        Generate-ComingSoonPage -OutputPath (Join-Path $outputBaseDir "latest-season\index.html") `
                               -Title "Latest Season Rankings" `
                               -Message "Latest season rankings are being compiled. Please check back soon!"
    }
}

function Process-NationalChampions {
    Write-Host "Processing national champions data..." -ForegroundColor Yellow

    $jsonPath = Join-Path $dataDir "national-champions\national-champions.json"
    if (Test-Path $jsonPath) {
        try {
            Write-Host "Loading national champions data..."
            $championsData = Get-Content $jsonPath -Raw | ConvertFrom-Json
            $outputPath = Join-Path $outputBaseDir "national-champions.html"

            $templatePath = Join-Path $templateBaseDir "national-champions-template.html"
            if (Test-Path $templatePath) {
                $template = Get-Content $templatePath -Raw

                # Replace placeholders
                $template = $template -replace 'TABLE_CONTROLS_SCRIPT', $tableControlsScript
                $template = $template -replace 'COMMENTS_SCRIPT_PLACEHOLDER', $commentCode
                $template = $template -replace 'TIMESTAMP', (Get-Date -Format "M/d/yyyy")

                # Generate table rows
                $tableRows = $championsData | ForEach-Object {
                    @"
                    <tr>
                        <td>$($_.year)</td>
                        <td>$($_.team)</td>
                        <td>$($_.state)</td>
                        <td>$($_.source)</td>
                        <td>$($_.record)</td>
                        <td>$($_.rating)</td>
                    </tr>
"@
                }
                $template = $template -replace 'TABLE_ROWS', ($tableRows -join "`n")

                Set-Content -Path $outputPath -Value $template -Encoding UTF8
                Write-Host "Generated national-champions.html" -ForegroundColor Green
            } else {
                Write-Error "National champions template not found: $templatePath"
            }
        } catch {
            Write-Error "Error processing national champions data: $_"
            Generate-ComingSoonPage -OutputPath (Join-Path $outputBaseDir "national-champions.html") `
                                  -Title "Media National Champions" `
                                  -Message "National champions data is being compiled. Please check back soon!"
        }
    } else {
        Write-Warning "National champions data not found: $jsonPath"
        Generate-ComingSoonPage -OutputPath (Join-Path $outputBaseDir "national-champions.html") `
                               -Title "Media National Champions" `
                               -Message "National champions data is being compiled. Please check back soon!"
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
    $decades = @(
        @{ Name = "pre1900"; StartYear = 1877; EndYear = 1899; DisplayName = "Pre-1900s" }
        @{ Name = "1900s"; StartYear = 1900; EndYear = 1909; DisplayName = "1900s" }
        @{ Name = "1910s"; StartYear = 1910; EndYear = 1919; DisplayName = "1910s" }
        @{ Name = "1920s"; StartYear = 1920; EndYear = 1929; DisplayName = "1920s" }
        @{ Name = "1930s"; StartYear = 1930; EndYear = 1939; DisplayName = "1930s" }
        @{ Name = "1940s"; StartYear = 1940; EndYear = 1949; DisplayName = "1940s" }
        @{ Name = "1950s"; StartYear = 1950; EndYear = 1959; DisplayName = "1950s" }
        @{ Name = "1960s"; StartYear = 1960; EndYear = 1969; DisplayName = "1960s" }
        @{ Name = "1970s"; StartYear = 1970; EndYear = 1979; DisplayName = "1970s" }
        @{ Name = "1980s"; StartYear = 1980; EndYear = 1989; DisplayName = "1980s" }
        @{ Name = "1990s"; StartYear = 1990; EndYear = 1999; DisplayName = "1990s" }
        @{ Name = "2000s"; StartYear = 2000; EndYear = 2009; DisplayName = "2000s" }
        @{ Name = "2010s"; StartYear = 2010; EndYear = 2019; DisplayName = "2010s" }
        @{ Name = "2020s"; StartYear = 2020; EndYear = 2029; DisplayName = "2020s" }
    )

    foreach ($decade in $decades) {
        Process-DecadeData -DecadeName $decade.Name -StartYear $decade.StartYear -EndYear $decade.EndYear -DisplayName $decade.DisplayName
    }

    # Process States
    Write-Host "Processing state rankings..." -ForegroundColor Yellow
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
    Write-Host "Processing all-time rankings..." -ForegroundColor Yellow
    
    # Process all-time teams
    Write-Host "Processing all-time teams" -ForegroundColor Cyan
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
    Write-Host "Processing all-time programs" -ForegroundColor Cyan
    @("25", "50", "100") | ForEach-Object {
        Write-Host "Processing all-time programs ($_ seasons)" -ForegroundColor Yellow
        Process-AllTimeData -Category "programs" -Threshold $_
    }

    # Process Latest Season
    Write-Host "Processing latest season rankings..." -ForegroundColor Yellow
    Process-LatestSeasonData

    # Generate Index Pages
    Write-Host "Generating index pages..." -ForegroundColor Yellow

    # Decades index
    $decadeIndexPath = Join-Path $outputBaseDir "decades\index.html"
    $decadeIndexTemplatePath = Join-Path $templateBaseDir "index\decades-index-template.html"
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
    $allTimeIndexPath = Join-Path $outputBaseDir "all-time\index.html"
    $allTimeIndexTemplatePath = Join-Path $templateBaseDir "index\all-time-index-template.html"
    if (Test-Path $allTimeIndexTemplatePath) {
        $allTimeIndexTemplate = Get-Content $allTimeIndexTemplatePath -Raw
        Set-Content -Path $allTimeIndexPath -Value $allTimeIndexTemplate -Encoding UTF8
        Write-Host "Generated all-time rankings index page" -ForegroundColor Green
    }

    # States index
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
            $statesIndexContent = $statesIndexTemplate -replace 'STATE_CARDS', '<!-- No state data found -->'
        }
        Set-Content -Path $statesIndexPath -Value $statesIndexContent -Encoding UTF8
        Write-Host "Generated states index page" -ForegroundColor Green
    }

    Write-Host "Page generation completed successfully!" -ForegroundColor Green
} catch {
    Write-Error "Generation failed: $_"
    exit 1
} finally {
    Write-Host "Script execution completed." -ForegroundColor Green
}
#endregion Main Script Execution