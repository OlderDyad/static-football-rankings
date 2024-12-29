# Create-DecadePages.ps1
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

$templatePath = ".\decade-template.html"
$outputDir = "..\"

if (-not (Test-Path $templatePath)) {
    throw "Template not found at $templatePath"
}

$template = Get-Content $templatePath -Raw

foreach ($decade in $decades) {
    Write-Host "Processing $($decade.Title)..."
    $pageContent = $template

    # Replace placeholders
    $pageContent = $pageContent -replace '<!--DECADE_TITLE-->', $decade.Title
    $pageContent = $pageContent -replace '<!--DECADE_ID-->', $decade.Id
    $pageContent = $pageContent -replace '<!--DECADE_START-->', $decade.StartYear
    $pageContent = $pageContent -replace '<!--DECADE_END-->', $decade.EndYear

    # Create output file
    $outputPath = Join-Path $outputDir "$($decade.Id).html"
    Set-Content -Path $outputPath -Value $pageContent -Encoding UTF8
    
    Write-Host "Created $outputPath"
}
