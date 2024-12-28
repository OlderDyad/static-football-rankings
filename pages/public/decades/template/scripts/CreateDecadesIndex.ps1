# CreateDecadesIndex.ps1
$indexTemplate = @'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>High School Football Rankings by Decade</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="/static-football-rankings/css/styles.css" rel="stylesheet">
</head>
<body>
    <div class="header-banner">
        <img src="/static-football-rankings/images/football-field-top.jpg" alt="Football Field Header" class="w-100" />
    </div>

    <div class="container mt-3">
        <nav aria-label="breadcrumb">
            <ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="/static-football-rankings/index.html">Home</a></li>
                <li class="breadcrumb-item active">Rankings by Decade</li>
            </ol>
        </nav>

        <h1 class="mb-4">High School Football Rankings by Decade</h1>

        <div class="row">
            <!--DECADE_CARDS-->
        </div>

        <footer class="mt-5 mb-3">
            <div class="text-center">
                <p>© 2024 McKnight's Football Rankings</p>
            </div>
        </footer>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'@

$decades = @(
    @{ Id = 'pre1900'; Title = 'Pre-1900s'; StartYear = 1877; EndYear = 1899 }
    @{ Id = '1900s'; Title = '1900s'; StartYear = 1900; EndYear = 1909 }
    @{ Id = '1910s'; Title = '1910s'; StartYear = 1910; EndYear = 1919 }
    @{ Id = '1920s'; Title = '1920s'; StartYear = 1920; EndYear = 1929 }
    @{ Id = '1930s'; Title = '1930s'; StartYear = 1930; EndYear = 1939 }
    @{ Id = '1940s'; Title = '1940s'; StartYear = 1940; EndYear = 1949 }
    @{ Id = '1950s'; Title = '1950s'; StartYear = 1950; EndYear = 1959 }
    @{ Id = '1960s'; Title = '1960s'; StartYear = 1960; EndYear = 1969 }
    @{ Id = '1970s'; Title = '1970s'; StartYear = 1970; EndYear = 1979 }
    @{ Id = '1980s'; Title = '1980s'; StartYear = 1980; EndYear = 1989 }
    @{ Id = '1990s'; Title = '1990s'; StartYear = 1990; EndYear = 1999 }
    @{ Id = '2000s'; Title = '2000s'; StartYear = 2000; EndYear = 2009 }
    @{ Id = '2010s'; Title = '2010s'; StartYear = 2010; EndYear = 2019 }
    @{ Id = '2020s'; Title = '2020s'; StartYear = 2020; EndYear = 2029 }
)

$decadeCards = ""
foreach ($decade in $decades) {
    $decadeCards += @"

    <div class="col-md-4 mb-4">
        <div class="card h-100">
            <div class="card-body">
                <h5 class="card-title">$($decade.Title)</h5>
                <p class="card-text">Top teams from $($decade.StartYear) to $($decade.EndYear)</p>
                <a href="/static-football-rankings/pages/public/decades/$($decade.Id).html" class="btn btn-primary">View Rankings</a>
            </div>
        </div>
    </div>
"@
}

$indexContent = $indexTemplate -replace '<!--DECADE_CARDS-->', $decadeCards
$outputPath = "..\index.html"
Set-Content -Path $outputPath -Value $indexContent -Encoding UTF8
Write-Host "Created index page at $outputPath"