Write-Host 'Creating decade template file...'

try {
    $templateContent = @'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><!--DECADE_TITLE--> High School Football Teams - McKnight's American Football</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="/static-football-rankings/css/styles.css" rel="stylesheet">
</head>
<body>
    <!-- Top Banner Image -->
    <div class="header-banner">
        <img src="/static-football-rankings/docs/images/football-field-top.jpg" 
             alt="Football Field Header" 
             class="w-100" />
    </div>

    <!-- Navigation Breadcrumb -->
    <div class="container mt-3">
        <nav aria-label="breadcrumb">
            <ol class="breadcrumb">
                <li class="breadcrumb-item">
                    <a href="/static-football-rankings/index.html">Home</a>
                </li>
                <li class="breadcrumb-item">
                    <a href="/static-football-rankings/pages/public/decades/index.html">Rankings by Decade</a>
                </li>
                <li class="breadcrumb-item active"><!--DECADE_TITLE--> Teams</li>
            </ol>
        </nav>
    </div>

    <!-- Team Header -->
    <div class="team-header" id="teamHeader"></div>

    <!-- Main Content -->
    <div class="container mt-4">
        <h1 data-page-name="<!--DECADE_ID-->">Top High School Football Teams of the <!--DECADE_TITLE--></h1>
        
        <div class="form-group mb-4">
            <input type="text" class="form-control" id="searchInput" placeholder="Search teams..." />
        </div>

        <div class="d-flex justify-content-end mb-3">
            <small class="text-muted">Updated: <span id="lastUpdated"></span></small>
        </div>

        <div class="table-responsive">
            <table class="table table-striped table-hover">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Program</th>
                        <th>Season</th>
                        <th>Combined</th>
                        <th>Margin</th>
                        <th>Win-Loss</th>
                        <th>Offense</th>
                        <th>Defense</th>
                        <th>Games</th>
                        <th>State</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody id="programsTableBody">
                </tbody>
            </table>
        </div>

        <nav aria-label="Page navigation" class="mt-4">
            <ul class="pagination justify-content-center" id="pagination"></ul>
        </nav>

        <!-- Comments Section -->
        <div class="comments-section mt-5">
            <h3>Comments</h3>
            <div id="authContainer" class="mb-3"></div>
            <div id="commentForm" class="mb-4" style="display: none">
                <div class="card">
                    <div class="card-body">
                        <textarea id="commentText" class="form-control mb-2" rows="3" placeholder="Share your thoughts..."></textarea>
                        <div class="d-flex justify-content-between align-items-center">
                            <button id="submitComment" class="btn btn-primary">Post Comment</button>
                            <small class="text-muted">Posting as <span id="authorName">Anonymous</span></small>
                        </div>
                    </div>
                </div>
            </div>
            <div id="commentsList"></div>
        </div>

        <footer class="mt-5 mb-3">
            <div class="text-center">
                <p> 2024 McKnight's Football Rankings</p>
            </div>
        </footer>
    </div>

    <!-- Scripts -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script type="module" src="/static-football-rankings/docs/js/main.js"></script>
</body>
</html>
'@

    # Create template file
    Set-Content -Path '.\decade-template.html' -Value $templateContent
    
    # Verify file was created
    if (Test-Path '.\decade-template.html') {
        Write-Host 'Template created successfully!'
        Write-Host 'Verifying content...'
        $fileContent = Get-Content '.\decade-template.html' -Raw
        if ($fileContent.Contains('<!--DECADE_TITLE-->')) {
            Write-Host 'Template placeholders verified.'
            exit 0
        } else {
            throw 'Template content verification failed!'
        }
    } else {
        throw 'Template file was not created!'
    }
} catch {
    Write-Error "Error creating template: $_"
    exit 1
}
