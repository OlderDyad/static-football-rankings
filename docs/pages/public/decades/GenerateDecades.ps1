# GenerateDecades.ps1
# Generates decade pages from a template, inserts table rows from JSON,
# and finally injects an inline comments/auth snippet into each .html file using a placeholder.

Write-Host 'Generating decade pages and index...'

# Determine the base URL based on environment
$baseUrl = if ($env:GITHUB_ACTIONS -eq 'true') {
    '/static-football-rankings/docs/' # For GitHub Pages
} else {
    '/docs/'  # For local testing
}

# Inline comment/auth snippet using single-quoted Here-String to prevent variable expansion
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

try {
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

     # Define paths - using absolute paths for clarity
     $rootDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings"
     $docsDir = Join-Path $rootDir "docs"
     $scriptDir = $PSScriptRoot  # Current directory
     $templateDir = $scriptDir   # Templates in same directory as script
     $outputDir = $scriptDir     # Output to same directory
     # Update this line to point to the correct data directory
     $jsonBasePath = Join-Path $rootDir "data"  # Changed from "docs/data" to "data"
 
     # Debug path information
     Write-Host "Root Directory: $rootDir"
     Write-Host "Docs Directory: $docsDir"
     Write-Host "Script Directory: $scriptDir"
     Write-Host "Template Directory: $templateDir"
     Write-Host "Output Directory: $outputDir"
     Write-Host "JSON Base Path: $jsonBasePath"

     
    # Define template paths
    $decadeTemplatePath = Join-Path $templateDir "decade-template.html"
    $indexTemplatePath = Join-Path $templateDir "index-template.html"

    # Check templates exist (using decadeTemplatePath consistently)
    if (-not (Test-Path $decadeTemplatePath)) {
        throw "Decade template file not found at $decadeTemplatePath"
    }
    if (-not (Test-Path $indexTemplatePath)) {
        throw "Index template file not found at $indexTemplatePath"
    }

    # Read templates (using decadeTemplatePath consistently)
    $decadeTemplate = Get-Content $decadeTemplatePath -Raw
    $indexTemplate = Get-Content $indexTemplatePath -Raw

    # Ensure output directory exists
    if (-not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
        Write-Host "Created output directory: $outputDir"
    }

    # Process each decade
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
        $output = $output -replace '(?<=<head>.*?)\n', "`n        $metadataTag`n"

        # Add base tag
        $baseTag = "<base href=`"$baseUrl`">"
        $output = $output -replace '(?<=<head>.*?)\n', "`n        $baseTag`n"

       # Process JSON data
$jsonFileName = "decade-teams-$($decade.Name).json"
$jsonFilePath = Join-Path $jsonBasePath "decades\teams\$jsonFileName"

if (Test-Path $jsonFilePath) {
    Write-Host "Found JSON for $($decade.Name): $jsonFilePath" -ForegroundColor Green
    $jsonData = Get-Content -Path $jsonFilePath -Raw | ConvertFrom-Json

    if ($null -ne $jsonData -and $null -ne $jsonData.items -and $jsonData.items -is [System.Array]) {
        Write-Host "Rankings for $($decade.DisplayName):" -ForegroundColor Yellow
        $jsonData.items | Format-Table

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
        $output = $output -replace 'TABLE_ROWS', $tableRows
    } else {
        Write-Warning "Invalid or empty JSON data for $($decade.DisplayName): $jsonFilePath"
    }
} else {
    Write-Warning "JSON file not found for $($decade.DisplayName): $jsonFilePath"
}

        # Add comments script
        $output = $output -replace '<!--COMMENTS_SCRIPT_PLACEHOLDER-->', $commentCode

        # Save the file
        $outputPath = Join-Path $outputDir "$($decade.Name).html"
        Set-Content -Path $outputPath -Value $output -Encoding UTF8

        if (-not (Test-Path $outputPath)) {
            throw "Failed to create $($decade.DisplayName) page"
        }
    }

    # Create index page
    Write-Host "`nGenerating index page..."
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

    $indexPath = Join-Path $outputDir "index.html"
    $indexContent = $indexTemplate -replace 'DECADE_CARDS', ($decadeCardsHtml -join "`n")
    Set-Content -Path $indexPath -Value $indexContent -Encoding UTF8

    Write-Host "All files generated successfully in: $outputDir"

} catch {
    Write-Error "Generation failed: $_"
    exit 1
}







