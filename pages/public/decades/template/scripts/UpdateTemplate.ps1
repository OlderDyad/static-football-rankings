# UpdateTemplate.ps1
$templateContent = @'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><!--DECADE_TITLE--> High School Football Teams</title>
    <meta name="data-file" content="/static-football-rankings/data/decade-teams-<!--DECADE_ID-->.json">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="/static-football-rankings/css/styles.css" rel="stylesheet">
</head>
<body>
    <div class="header-banner">
        <img src="/static-football-rankings/docs/images/header/football-field-top.jpg" alt="Football Field Header" class="w-100" />
    </div>

    <div class="container mt-3">
        <nav aria-label="breadcrumb">
            <ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="/static-football-rankings/index.html">Home</a></li>
                <li class="breadcrumb-item"><a href="/static-football-rankings/pages/public/decades/index.html">Rankings by Decade</a></li>
                <li class="breadcrumb-item active"><!--DECADE_TITLE--> Teams</li>
            </ol>
        </nav>
    </div>

    <div class="loading-state"></div>
    <div class="team-header"></div>

    <div class="container mt-4">
        <h1 data-page-name="<!--DECADE_ID-->">Top High School Football Teams of the <!--DECADE_TITLE--></h1>
        
        <div class="table-responsive">
            <table class="table table-striped table-hover">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Team</th>
                        <th>State</th>
                        <th>Seasons</th>
                        <th>Combined</th>
                        <th>Margin</th>
                        <th>Win-Loss</th>
                        <th>Offense</th>
                        <th>Defense</th>
                        <th>Games</th>
                    </tr>
                </thead>
                <tbody id="programsTableBody">
                </tbody>
            </table>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script type="module" src="/static-football-rankings/docs/js/main.js"></script>
</body>
</html>
'@

Set-Content -Path '.\decade-template.html' -Value $templateContent -ErrorAction Stop
Write-Host 'Template updated successfully!'
exit 0