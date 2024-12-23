Write-Host 'Verifying template structure...'

try {
    # Check if file exists and get content
    if (-not (Test-Path '.\decade-template.html')) {
        throw 'Template file not found!'
    }
    
    $content = Get-Content '.\decade-template.html' -Raw
    
    # Required elements to check
    $requiredElements = @(
        @{Name = 'Page title placeholder'; Pattern = '<!--DECADE_TITLE--> High School Football Teams'},
        @{Name = 'Decade ID placeholder'; Pattern = 'data-page-name="<!--DECADE_ID-->"'},
        @{Name = 'Bootstrap CSS'; Pattern = 'bootstrap@5.1.3/dist/css/bootstrap.min.css'},
        @{Name = 'Custom styles'; Pattern = '/static-football-rankings/css/styles.css'},
        @{Name = 'Search input'; Pattern = '<input type="text" class="form-control" id="searchInput"'},
        @{Name = 'Table structure'; Pattern = '<table class="table table-striped table-hover">'},
        @{Name = 'Comments section'; Pattern = '<div class="comments-section'},
        @{Name = 'Main JavaScript'; Pattern = '/static-football-rankings/docs/js/main.js'}
    )
    
    Write-Host "
Checking required elements:"
    foreach ($element in $requiredElements) {
        $found = $content -match [regex]::Escape($element.Pattern)
        Write-Host ("  {0}: {1}" -f $element.Name, $(if ($found) {' Found'} else {' MISSING'}))
    }
    
    # Count placeholder occurrences
    $decadeTitleCount = ([regex]::Matches($content, '<!--DECADE_TITLE-->')).Count
    Write-Host "
Placeholder occurrences:"
    Write-Host "  DECADE_TITLE: $decadeTitleCount (should be multiple)"
    Write-Host "  DECADE_ID: $(([regex]::Matches($content, '<!--DECADE_ID-->')).Count) (should be 1)"
    
    Write-Host "
Template verification complete!"
    
} catch {
    Write-Error "Verification failed: $_"
    exit 1
}
