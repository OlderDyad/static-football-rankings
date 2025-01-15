# GenerateDecades.ps1
# Part 1 - Start of file through Generator function:
# Generates decade pages for both teams and programs from templates

#region Configuration
Write-Host 'Generating decade pages and index...'

# Base URL configuration
$baseUrl = if ($env:GITHUB_ACTIONS -eq 'true') {
    '/static-football-rankings/docs/' # For GitHub Pages
} else {
    '/docs/'  # For local testing
}

function Generate-TeamBanner {
    param (
        [Parameter(Mandatory=$true)][object]$TopItem
    )

    if (!$TopItem) {
        return "<!-- No top item data available for banner -->"
    }

    # Get image paths with fallback
    $logoPath = if ($TopItem.LogoURL) { 
        "/static-football-rankings/images${$TopItem.LogoURL.TrimStart('/')}" 
    } else { 
        "/static-football-rankings/images/default-logo.png" 
    }
    
    $schoolLogoPath = if ($TopItem.School_Logo_URL) {
        "/static-football-rankings/images${$TopItem.School_Logo_URL.TrimStart('/')}"
    } else {
        "/static-football-rankings/images/default-logo.png"
    }

    # Get text values with fallbacks
    $backgroundColor = if ($TopItem.backgroundColor) { $TopItem.backgroundColor } else { '#FFFFFF' }
    $textColor = if ($TopItem.textColor) { $TopItem.textColor } else { '#000000' }
    $displayName = if ($TopItem.program) { $TopItem.program } elseif ($TopItem.team) { $TopItem.team } else { 'Unknown Team' }

    return @"
    <div class="team-header" style="background-color: $backgroundColor; color: $textColor;">
        <div class="container">
            <div class="row align-items-center">
                <div class="col-md-3 text-center">
                    <img src="$logoPath"
                         alt="$displayName Logo"
                         class="img-fluid team-logo"
                         onerror="this.src='/static-football-rankings/images/default-logo.png'; this.classList.add('default-logo');" />
                </div>
                <div class="col-md-6 text-center">
                    <h2>$displayName</h2>
                    $(if ($TopItem.mascot) { "<p class='mascot-name'>$($TopItem.mascot)</p>" })
                    <div class="team-stats">
                        <small>
                            $(if ($TopItem.seasons) { "Seasons: $($TopItem.seasons)" })
                            $(if ($TopItem.margin) { "| Margin: $([Math]::Round($TopItem.margin, 1))" })
                        </small>
                    </div>
                </div>
                <div class="col-md-3 text-center">
                    <img src="$schoolLogoPath"
                         alt="$displayName School Logo"
                         class="img-fluid school-logo"
                         onerror="this.src='/static-football-rankings/images/default-logo.png'; this.classList.add('default-logo');" />
                </div>
            </div>
        </div>
    </div>
"@
}

#Part 2 - Table Controls Script:

# Search & Pagination
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
            
            // Previous button
            html.push(`<li class="page-item ${this.currentPage === 1 ? 'disabled' : ''}">
                <button class="page-link" data-page="prev">&laquo;</button>
            </li>`);
            
            // Page numbers
            for (let i = 1; i <= totalPages; i++) {
                if (i === 1 || i === totalPages || (i >= this.currentPage - 2 && i <= this.currentPage + 2)) {
                    html.push(`<li class="page-item ${i === this.currentPage ? 'active' : ''}">
                        <button class="page-link" data-page="${i}">${i}</button>
                    </li>`);
                } else if (i === this.currentPage - 3 || i === this.currentPage + 3) {
                    html.push('<li class="page-item disabled"><span class="page-link">...</span></li>');
                }
            }
            
            // Next button
            html.push(`<li class="page-item ${this.currentPage === totalPages ? 'disabled' : ''}">
                <button class="page-link" data-page="next">&raquo;</button>
            </li>`);
            
            pagination.innerHTML = html.join('');
        }
    };

    // Initialize after DOM loads
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => TableControls.init());
    } else {
        TableControls.init();
    }
</script>
'@

# Part 3 - Comments Script:

# Comments script
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
      <p>Welcome, <strong>${user.name}</strong> (${user.email}).
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
'@

# Part 4 - Comments Logic Continued and Path Setup:

# Continue comment script
$commentCode = $commentCode + @'
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

/**********************************************************
 * INIT
 **********************************************************/
document.getElementById('submitComment')?.addEventListener('click', submitComment);

(function initPage() {
  checkLoginStatus();
  fetchComments();
})();
</script>
'@

#region Configuration and Setup
# Define paths
$rootDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings"
$docsDir = Join-Path $rootDir "docs"
$scriptDir = $PSScriptRoot
$templateDir = Join-Path $scriptDir "templates"
$outputDir = $scriptDir
$jsonBasePath = Join-Path $rootDir "data"

# Template paths
$teamTemplatePath = Join-Path $templateDir "decade-teams-template.html"
$programTemplatePath = Join-Path $templateDir "decade-programs-template.html"
$indexTemplatePath = Join-Path $templateDir "index-template.html"

# Define decades list
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
#endregion

# Part 5 - Beginning of Main Processing Section (with proper try/catch structure):

#region Main Processing
try {
    # Debug path information
    Write-Host "Root Directory: $rootDir"
    Write-Host "Docs Directory: $docsDir"
    Write-Host "Script Directory: $scriptDir"
    Write-Host "Template Directory: $templateDir"
    Write-Host "Output Directory: $outputDir"
    Write-Host "JSON Base Path: $jsonBasePath"

    # Verify templates exist
    if (-not (Test-Path $teamTemplatePath)) {
        throw "Team template file not found at $teamTemplatePath"
    }
    if (-not (Test-Path $programTemplatePath)) {
        throw "Program template file not found at $programTemplatePath"
    }
    if (-not (Test-Path $indexTemplatePath)) {
        throw "Index template file not found at $indexTemplatePath"
    }

    # Load templates
    $teamTemplate = Get-Content $teamTemplatePath -Raw
    $programTemplate = Get-Content $programTemplatePath -Raw
    $indexTemplate = Get-Content $indexTemplatePath -Raw

    # Process each decade
    foreach ($decade in $decades) {
        Write-Host "`nProcessing $($decade.DisplayName)..."

#      Part 6 - Teams Processing Section (inside the try block):

#region Team Processing
Write-Host "Processing Teams..."
$teamOutput = $teamTemplate
$teamOutput = $teamOutput -replace 'DECADE_DISPLAY_NAME', $decade.DisplayName
$teamOutput = $teamOutput -replace 'DECADE_NAME', $decade.Name
$teamOutput = $teamOutput -replace 'DECADE_START', $decade.StartYear
$teamOutput = $teamOutput -replace 'DECADE_END', $decade.EndYear
$teamOutput = $teamOutput -replace 'DECADE_ID', "$($decade.Name)-teams"
$teamOutput = $teamOutput -replace 'TABLE_CONTROLS_SCRIPT', $tableControlsScript

# Process team JSON
$teamJsonFileName = "decade-teams-$($decade.Name).json"
$teamJsonFilePath = Join-Path $jsonBasePath "decades\teams\$teamJsonFileName"

if (Test-Path $teamJsonFilePath) {
    Write-Host "Found team JSON for $($decade.Name): $teamJsonFilePath" -ForegroundColor Green
    $teamJsonData = Get-Content -Path $teamJsonFilePath -Raw | ConvertFrom-Json

    if ($null -ne $teamJsonData -and $null -ne $teamJsonData.items -and $teamJsonData.items -is [System.Array]) {
        # Process timestamp
        if ($null -ne $teamJsonData.metadata) {
            $timestamp = [DateTime]::Parse($teamJsonData.metadata.timestamp)
            $formattedTimestamp = $timestamp.ToString("M/d/yyyy")
            $teamOutput = $teamOutput -replace 'TIMESTAMP', $formattedTimestamp
        } else {
            $teamOutput = $teamOutput -replace 'TIMESTAMP', (Get-Date).ToString("M/d/yyyy")
        }

        # Process table rows
        $tableRows = ""
        foreach ($rank in $teamJsonData.items) {
            $tableRows += @"
<tr>
<td>$($rank.rank)</td>
<td>$($rank.team)</td>
<td>$($rank.state)</td>
<td>$($rank.season)</td>
<td>$($rank.combined)</td>
<td>$($rank.margin)</td>
<td>$($rank.win_loss)</td>
<td>$($rank.offense)</td>
<td>$($rank.defense)</td>
<td>$($rank.games_played)</td>
</tr>
"@
        }
        $teamOutput = $teamOutput -replace 'TABLE_ROWS', $tableRows

        # Generate and insert team banner
        if ($teamJsonData.topItem) {
            $bannerHtml = Generate-TeamBanner -TopItem $teamJsonData.topItem
            $teamOutput = $teamOutput -replace '<div id="teamHeaderContainer"></div>', $bannerHtml
        }
    } else {
        Write-Warning "Invalid or empty team JSON data for $($decade.DisplayName): $teamJsonFilePath"
    }
} else {
    Write-Warning "Team JSON file not found for $($decade.DisplayName): $teamJsonFilePath"
}

# Add comments script
$teamOutput = $teamOutput -replace 'COMMENTS_SCRIPT_PLACEHOLDER', $commentCode

# Save team file
$teamOutputPath = Join-Path $outputDir "$($decade.Name)-teams.html"
Set-Content -Path $teamOutputPath -Value $teamOutput -Encoding UTF8
#endregion

# Part 7 - Programs Processing Section (inside the try block):

#region Program Processing
Write-Host "Processing Programs..."
$programOutput = $programTemplate
$programOutput = $programOutput -replace 'DECADE_DISPLAY_NAME', $decade.DisplayName
$programOutput = $programOutput -replace 'DECADE_NAME', $decade.Name
$programOutput = $programOutput -replace 'DECADE_START', $decade.StartYear
$programOutput = $programOutput -replace 'DECADE_END', $decade.EndYear
$programOutput = $programOutput -replace 'DECADE_ID', "$($decade.Name)-programs"
$programOutput = $programOutput -replace 'TABLE_CONTROLS_SCRIPT', $tableControlsScript

# Process program JSON
$programJsonFileName = "decade-programs-$($decade.Name).json"
$programJsonFilePath = Join-Path $jsonBasePath "decades\programs\$programJsonFileName"

if (Test-Path $programJsonFilePath) {
    Write-Host "Found program JSON for $($decade.Name): $programJsonFilePath" -ForegroundColor Green
    $programJsonData = Get-Content -Path $programJsonFilePath -Raw | ConvertFrom-Json

    if ($null -ne $programJsonData -and $null -ne $programJsonData.items -and $programJsonData.items -is [System.Array]) {
        # Process timestamp
        if ($null -ne $programJsonData.metadata) {
            $timestamp = [DateTime]::Parse($programJsonData.metadata.timestamp)
            $formattedTimestamp = $timestamp.ToString("M/d/yyyy")
            $programOutput = $programOutput -replace 'TIMESTAMP', $formattedTimestamp
        } else {
            $programOutput = $programOutput -replace 'TIMESTAMP', (Get-Date).ToString("M/d/yyyy")
        }

        # Process table rows
        $tableRows = ""
        foreach ($rank in $programJsonData.items) {
            $tableRows += @"
<tr>
<td>$($rank.rank)</td>
<td>$($rank.program)</td>
<td>$($rank.state)</td>
<td>$($rank.seasons)</td>
<td>$($rank.combined)</td>
<td>$($rank.margin)</td>
<td>$($rank.win_loss)</td>
<td>$($rank.offense)</td>
<td>$($rank.defense)</td>
</tr>
"@
        }
        $programOutput = $programOutput -replace 'TABLE_ROWS', $tableRows

        # Generate and insert program banner
        if ($programJsonData.topItem) {
            $bannerHtml = Generate-TeamBanner -TopItem $programJsonData.topItem
            $programOutput = $programOutput -replace '<div id="teamHeaderContainer"></div>', $bannerHtml
        }
    } else {
        Write-Warning "Invalid or empty program JSON data for $($decade.DisplayName): $programJsonFilePath"
    }
} else {
    Write-Warning "Program JSON file not found for $($decade.DisplayName): $programJsonFilePath"
}

# Add comments script
$programOutput = $programOutput -replace 'COMMENTS_SCRIPT_PLACEHOLDER', $commentCode

# Save program file
$programOutputPath = Join-Path $outputDir "$($decade.Name)-programs.html"
Set-Content -Path $programOutputPath -Value $programOutput -Encoding UTF8
#endregion

# Part 8 - Index Generation and Final Section (completing the try/catch block):

} # End of foreach ($decade in $decades)

#region Index Generation
Write-Host "`nGenerating index page..."
$decadeCardsHtml = $decades | ForEach-Object {
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

$indexPath = Join-Path $outputDir "index.html"
$indexContent = $indexTemplate -replace 'DECADE_CARDS', ($decadeCardsHtml -join "`n")
Set-Content -Path $indexPath -Value $indexContent -Encoding UTF8

Write-Host "All files generated successfully in: $outputDir"

} catch {
Write-Error "Generation failed: $_"
exit 1
}
#endregion
