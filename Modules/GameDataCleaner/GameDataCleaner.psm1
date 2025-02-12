# Get functions from private and public folders
$Public = @( Get-ChildItem -Path $PSScriptRoot\Public\*.ps1 -ErrorAction SilentlyContinue )
Write-Host "Public functions found:" $Public.Count
Write-Host "Public function names:" $Public.BaseName

$Private = @( Get-ChildItem -Path $PSScriptRoot\Private\*.ps1 -ErrorAction SilentlyContinue )
Write-Host "Private functions found:" $Private.Count

# Dot source the files
foreach ($import in @($Public + $Private)) {
    try {
        Write-Host "Importing:" $import.FullName
        . $import.FullName
    }
    catch {
        Write-Error "Failed to import function $($import.FullName): $_"
    }
}

# Export public functions
Write-Host "Exporting functions:" $Public.BaseName
Export-ModuleMember -Function $Public.BaseName