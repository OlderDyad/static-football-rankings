# Create RunAll.ps1
$runAllContent = @'
Write-Host "Starting template update and page generation process..."

# Step 1: Update template
Write-Host "Step 1: Updating template..."
.\scripts\UpdateTemplate.ps1

# Step 2: Generate decade pages
Write-Host "`nStep 2: Creating decade pages..."
.\Create-DecadePages.ps1

# Step 3: Create index
Write-Host "`nStep 3: Creating index page..."
.\scripts\CreateDecadesIndex.ps1

# Step 4: Validate
Write-Host "`nStep 4: Validating all pages..."
.\scripts\ValidatePages.ps1

Write-Host "`nProcess complete!"
'@

Set-Content -Path ".\RunAll.ps1" -Value $runAllContent