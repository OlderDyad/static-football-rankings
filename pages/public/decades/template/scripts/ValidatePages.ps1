# ValidatePages.ps1
$decades = @(
    'pre1900', '1900s', '1910s', '1920s', '1930s', '1940s',
    '1950s', '1960s', '1970s', '1980s', '1990s', '2000s',
    '2010s', '2020s'
)

$requiredElements = @(
    @{Name = 'Meta charset'; Pattern = '<meta charset="UTF-8">' },
    @{Name = 'Bootstrap CSS'; Pattern = 'bootstrap@5.1.3/dist/css/bootstrap.min.css' },
    @{Name = 'Custom CSS'; Pattern = '<link href="css/styles.css"' },
    @{Name = 'Data file meta'; Pattern = 'content="data/decade-teams-' },
    @{Name = 'Main script'; Pattern = 'src="docs/js/main.js"' },
    @{Name = 'Loading state'; Pattern = '<div class="loading-state">' },
    @{Name = 'Base href'; Pattern = '<base href="/static-football-rankings/">' }
)

Write-Host "Validating pages..."
$errors = @()

# Check index page
$indexPath = "..\index.html"
if (Test-Path $indexPath) {
    Write-Host "Checking index page..."
    $content = Get-Content $indexPath -Raw
    foreach ($decade in $decades) {
        if (-not $content.Contains("$decade.html")) {
            $errors += "Index page missing link to $decade.html"
        }
    }
} else {
    $errors += "Index page not found"
}

# Check decade pages
foreach ($decade in $decades) {
    $pagePath = "..\$decade.html"
    if (-not (Test-Path $pagePath)) {
        $errors += "Page not found: $decade.html"
        continue
    }

    Write-Host "Checking $decade.html..."
    $content = Get-Content $pagePath -Raw
    
    foreach ($element in $requiredElements) {
        if (-not $content.Contains($element.Pattern)) {
            $errors += "$decade.html missing $($element.Name)"
        }
    }
}

if ($errors.Count -gt 0) {
    Write-Host "`nValidation errors found:"
    $errors | ForEach-Object { Write-Host "  - $_" }
    exit 1
} else {
    Write-Host "`nAll pages validated successfully!"
    exit 0
}