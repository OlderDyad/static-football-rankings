# Add-TableColorTheming.ps1
# Adds dynamic table coloring script to GenerateAllPages.ps1

$targetFile = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings\scripts\GenerateAllPages.ps1"

# 1. Define the JavaScript Payload
# We escape the $ signs so PowerShell doesn't try to interpret them as variables
$jsPayload = @'
$tableColorScript = @"
<script>
(function(){
    function hexToRgba(hex, opacity) {
        hex = hex.replace('#', '');
        // Handle 3-digit hex (e.g. #FFF)
        if(hex.length === 3) {
            hex = hex[0]+hex[0] + hex[1]+hex[1] + hex[2]+hex[2];
        }
        const r = parseInt(hex.substring(0, 2), 16);
        const g = parseInt(hex.substring(2, 4), 16);
        const b = parseInt(hex.substring(4, 6), 16);
        return 'rgba(' + r + ',' + g + ',' + b + ',' + opacity + ')';
    }
    
    function applyColors(bg, text) {
        if (!bg) return;
        const style = document.createElement('style');
        style.textContent = 
            'thead th, thead tr, .sticky-top.bg-white {' +
            '  background-color: ' + bg + ' !important;' +
            '  color: ' + text + ' !important;' +
            '}' +
            '.table-striped > tbody > tr:nth-of-type(odd) > * {' +
            '  --bs-table-accent-bg: ' + hexToRgba(bg, 0.08) + ' !important;' +
            '}' +
            '.table-striped > tbody > tr:nth-of-type(even) > * {' +
            '  --bs-table-accent-bg: #ffffff !important;' +
            '}' +
            '.table-hover > tbody > tr:hover > * {' +
            '  --bs-table-accent-bg: ' + hexToRgba(bg, 0.18) + ' !important;' +
            '}' +
            '.btn-primary {' +
            '  background-color: ' + bg + ' !important;' +
            '  border-color: ' + bg + ' !important;' +
            '}' +
            '.btn-outline-primary {' +
            '  color: ' + bg + ' !important;' +
            '  border-color: ' + bg + ' !important;' +
            '}' +
            '.btn-outline-primary:hover {' +
            '  background-color: ' + bg + ' !important;' +
            '  color: ' + text + ' !important;' +
            '}';
        document.head.appendChild(style);
    }
    
    async function init() {
        try {
            const meta = document.querySelector('meta[name="data-file"]');
            if (!meta) return;
            // Add cache buster to ensure we get fresh color data
            const resp = await fetch(meta.getAttribute('content') + '?t=' + new Date().getTime());
            if (!resp.ok) return;
            const data = await resp.json();
            if (data.topItem && data.topItem.backgroundColor) {
                applyColors(data.topItem.backgroundColor, data.topItem.textColor || '#FFFFFF');
            }
        } catch (e) {
            console.warn('Table color init:', e);
        }
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
</script>
"@
'@

Write-Host "Reading GenerateAllPages.ps1..." -ForegroundColor Cyan
$content = Get-Content $targetFile -Raw

# 2. Inject the Variable Definition
# We look for the Comments script definition and insert our Table Script before it
if ($content -notmatch "tableColorScript =") {
    Write-Host "Injecting Table Color Script Definition..." -ForegroundColor Yellow
    $content = $content -replace '(\$commentCode = @)', "$jsPayload`n`n`$1"
} else {
    Write-Host "Script definition already exists. Skipping injection." -ForegroundColor Gray
}

# 3. Inject the HTML Replacement Logic
# We look for the TIMESTAMP replacement line and add our body tag replacement after it
# We do this for both -replace and -creplace versions to be safe
$injectionCode = '
                $template = $template -replace ''</body>'', "$tableColorScript`n</body>"'

if ($content -notmatch "replace '</body>', `"`$tableColorScript") {
    Write-Host "Injecting HTML Insertion Logic..." -ForegroundColor Yellow
    # Fix for Teams Loop
    $content = $content -replace "(template -creplace 'TIMESTAMP', \(Get-Date -Format `"M/d/yyyy`"\))", "`$1$injectionCode"
} else {
    Write-Host "HTML insertion logic already exists. Skipping." -ForegroundColor Gray
}

# 4. Save Changes
Set-Content -Path $targetFile -Value $content -Encoding UTF8
Write-Host "GenerateAllPages.ps1 has been updated!" -ForegroundColor Green
Write-Host "Now run: .\GenerateAllPages.ps1" -ForegroundColor Green