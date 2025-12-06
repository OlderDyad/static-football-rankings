# =============================================================================
# CHECK VERCEL/NEXT.JS SETUP
# =============================================================================
# Run this script to check if you're affected by the React vulnerability
# =============================================================================

$repoRoot = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings"

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "CHECKING VERCEL/NEXT.JS SETUP" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

# Check for package.json
$packageJson = Join-Path $repoRoot "package.json"
if (Test-Path $packageJson) {
    Write-Host "`n[FOUND] package.json" -ForegroundColor Yellow
    $content = Get-Content $packageJson -Raw | ConvertFrom-Json
    
    # Check for Next.js
    if ($content.dependencies.next -or $content.devDependencies.next) {
        $nextVersion = if ($content.dependencies.next) { $content.dependencies.next } else { $content.devDependencies.next }
        Write-Host "  Next.js version: $nextVersion" -ForegroundColor Red
        Write-Host "  *** YOU MAY BE AFFECTED BY CVE-2025-55182 ***" -ForegroundColor Red
        Write-Host "  Safe versions: 15.0.5, 15.1.9, 15.2.6, 15.3.6, 15.4.8, 15.5.7, 16.0.7" -ForegroundColor Yellow
    } else {
        Write-Host "  No Next.js dependency found" -ForegroundColor Green
    }
    
    # Check for React
    if ($content.dependencies.react -or $content.devDependencies.react) {
        $reactVersion = if ($content.dependencies.react) { $content.dependencies.react } else { $content.devDependencies.react }
        Write-Host "  React version: $reactVersion" -ForegroundColor Yellow
        if ($reactVersion -match "^19\.") {
            Write-Host "  React 19 detected - check if using Server Components" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "`n[NOT FOUND] No package.json in repo root" -ForegroundColor Green
    Write-Host "  Your main site appears to be static HTML (not Next.js)" -ForegroundColor Green
}

# Check for Vercel configuration
$vercelJson = Join-Path $repoRoot "vercel.json"
if (Test-Path $vercelJson) {
    Write-Host "`n[FOUND] vercel.json" -ForegroundColor Yellow
    Get-Content $vercelJson
} else {
    Write-Host "`n[NOT FOUND] No vercel.json" -ForegroundColor Gray
}

# Check for API folder (serverless functions)
$apiFolder = Join-Path $repoRoot "api"
if (Test-Path $apiFolder) {
    Write-Host "`n[FOUND] api/ folder (Vercel Serverless Functions)" -ForegroundColor Yellow
    Get-ChildItem $apiFolder -Recurse -Name | ForEach-Object { Write-Host "  $_" }
} else {
    Write-Host "`n[NOT FOUND] No api/ folder" -ForegroundColor Gray
}

# Check for pages folder (Next.js)
$pagesFolder = Join-Path $repoRoot "pages"
if (Test-Path $pagesFolder) {
    Write-Host "`n[FOUND] pages/ folder (Next.js Pages Router)" -ForegroundColor Yellow
} else {
    Write-Host "`n[NOT FOUND] No pages/ folder" -ForegroundColor Gray
}

# Check for app folder (Next.js App Router with Server Components)
$appFolder = Join-Path $repoRoot "app"
if (Test-Path $appFolder) {
    Write-Host "`n[FOUND] app/ folder (Next.js App Router - USES SERVER COMPONENTS)" -ForegroundColor Red
    Write-Host "  *** This is where the vulnerability exists! ***" -ForegroundColor Red
} else {
    Write-Host "`n[NOT FOUND] No app/ folder" -ForegroundColor Green
}

Write-Host "`n" + "=" * 60 -ForegroundColor Cyan
Write-Host "SUMMARY" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

# Summary
$hasNextJs = (Test-Path $packageJson) -and ((Get-Content $packageJson -Raw) -match '"next"')
$hasAppRouter = Test-Path $appFolder

if ($hasNextJs -and $hasAppRouter) {
    Write-Host "STATUS: POTENTIALLY VULNERABLE" -ForegroundColor Red
    Write-Host "Action: Update Next.js immediately" -ForegroundColor Red
    Write-Host "Run: npm install next@15.5.7" -ForegroundColor Yellow
} elseif ($hasNextJs) {
    Write-Host "STATUS: CHECK MANUALLY" -ForegroundColor Yellow
    Write-Host "You have Next.js but no app/ folder detected" -ForegroundColor Yellow
    Write-Host "Check your Vercel dashboard for framework details" -ForegroundColor Yellow
} else {
    Write-Host "STATUS: LIKELY NOT AFFECTED" -ForegroundColor Green
    Write-Host "Your project appears to be static HTML, not Next.js" -ForegroundColor Green
    Write-Host "The comments API may use simple serverless functions" -ForegroundColor Green
}

Write-Host "`nNext Steps:" -ForegroundColor Cyan
Write-Host "1. Check https://vercel.com/dashboard for your project settings" -ForegroundColor White
Write-Host "2. Look at 'Framework Preset' in Settings -> General" -ForegroundColor White
Write-Host "3. If using Next.js, update to a safe version" -ForegroundColor White