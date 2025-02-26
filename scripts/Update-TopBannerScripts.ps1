# Update-TopBannerScripts.ps1
$rootDir = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\docs\pages\public"
$templateDir = Join-Path $rootDir "templates"

# The standard script to add
$standardScript = @'
<!-- TopBanner initialization -->
<script type="module">
    import { TopBanner } from '/static-football-rankings/js/modules/topBanner.js';
    document.addEventListener('DOMContentLoaded', async () => {
        try {
            const banner = new TopBanner();
            await banner.initialize();
        } catch (error) {
            console.warn('Banner initialization failed:', error);
            document.body.style.display = 'block';
        }
    });
</script>
'@

# Get all HTML files that might need updating
$htmlFiles = Get-ChildItem -Path $rootDir -Filter "*.html" -Recurse | Where-Object {
    # Only process non-index files that contain teamHeaderContainer
    $content = Get-Content $_.FullName -Raw
    $content -match 'teamHeaderContainer' -and
    !($_.BaseName -eq "index") -and
    !($_.DirectoryName -match "\\index$")
}

foreach ($file in $htmlFiles) {
    Write-Host "Processing $($file.FullName)"
    $content = Get-Content $file.FullName -Raw
    
    # Check if the file has teamHeader.js or is missing TopBanner
    if ($content -match "teamHeader\.js" -or 
        !($content -match "import \{ TopBanner \} from '/static-football-rankings/js/modules/topBanner\.js'")) {
        
        # Back up the file
        $backupPath = "$($file.FullName).bak"
        Copy-Item -Path $file.FullName -Destination $backupPath -Force
        Write-Host "  Created backup: $backupPath"
        
        # Replace teamHeader script if present
        if ($content -match "teamHeader\.js") {
            Write-Host "  Replacing teamHeader.js import"
            $pattern = '<script type="module">[^<]*import[^<]*teamHeader\.js[^<]*</script>'
            $content = $content -replace $pattern, $standardScript
        }
        # Add TopBanner script if missing
        elseif (!($content -match "TopBanner")) {
            Write-Host "  Adding TopBanner initialization"
            $content = $content -replace '</body>', "$standardScript`n</body>"
        }
        
        # Write the updated content back
        Set-Content -Path $file.FullName -Value $content
        Write-Host "  Updated file" -ForegroundColor Green
    } else {
        Write-Host "  Already has correct TopBanner import" -ForegroundColor Gray
    }
}

Write-Host "Script execution completed!" -ForegroundColor Green