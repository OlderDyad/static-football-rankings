# Fix-GenerateAllPages.ps1
# Removes the embedded replacement script and adds just the Giscus code

$filePath = ".\GenerateAllPages.ps1"

Write-Host "Reading GenerateAllPages.ps1..." -ForegroundColor Yellow
$content = Get-Content $filePath

# The problem: Lines 588-632 contain the replacement script itself
# We need to replace this entire section with just the Giscus commentCode definition

# Find where the problematic section starts (line 588: "# Comments functionality")
# Find where it ends (line 632: "#endregion Template Scripts")

$newContent = @()

# Add everything BEFORE line 588 (indices 0-587)
$newContent += $content[0..587]

# Add the correct Giscus code
$giscusBlock = @'
$commentCode = @"
<div class="container mt-5">
    <div class="comments-section">
        <h3 class="mb-4">Comments & Discussion</h3>
        <p class="text-muted small mb-3">
            Sign in with GitHub to comment. Comments are stored as 
            <a href="https://github.com/olderdyad/static-football-rankings/discussions" target="_blank">GitHub Discussions</a>.
        </p>
        <script src="https://giscus.app/client.js"
                data-repo="olderdyad/static-football-rankings"
                data-repo-id="R_kgDONn_yOg"
                data-category="General"
                data-category-id="DIC_kwDONn_yOs4C0hls"
                data-mapping="pathname"
                data-strict="0"
                data-reactions-enabled="1"
                data-emit-metadata="1"
                data-input-position="top"
                data-theme="preferred_color_scheme"
                data-lang="en"
                data-loading="lazy"
                crossorigin="anonymous"
                async>
        </script>
    </div>
</div>
"@

#endregion Template Scripts
'@

$newContent += $giscusBlock

# Add everything AFTER line 632 (indices 633 to end)
$newContent += $content[633..($content.Count - 1)]

# Save the fixed file
Write-Host "Writing fixed GenerateAllPages.ps1..." -ForegroundColor Yellow
$newContent | Set-Content $filePath -Encoding UTF8

Write-Host "`n✅ Fixed successfully!" -ForegroundColor Green
Write-Host "Removed embedded replacement script (lines 588-632)" -ForegroundColor Yellow
Write-Host "Added clean Giscus code" -ForegroundColor Green
Write-Host "`nNow run: .\GenerateAllPages.ps1" -ForegroundColor Cyan