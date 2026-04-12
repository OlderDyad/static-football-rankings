###############################################################################
# Inject-GA4.ps1
# One-time script to add Google Analytics 4 tracking to all HTML templates
# and patch the Generate-ComingSoonPage inline HTML in GenerateAllPages.ps1
#
# Run ONCE from the repo root, then commit the changes.
# Safe to re-run — skips files that already contain the GA4 snippet.
###############################################################################

$rootDir       = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings"
$templateDir   = Join-Path $rootDir "docs\pages\public\templates"
$generateScript = Join-Path $rootDir "scripts\GenerateAllPages.ps1"

# ── GA4 snippet (your Measurement ID is already filled in) ──────────────────
$ga4Snippet = @'
    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-GC17GSJ4S0"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());
      gtag('config', 'G-GC17GSJ4S0');
    </script>
'@

# ── Marker we use to detect already-patched files ───────────────────────────
$marker = 'G-GC17GSJ4S0'

$templatesPatched = 0
$templatesSkipped = 0
$templatesFailed  = 0

###############################################################################
# PART 1 — Inject into every .html template file
###############################################################################
Write-Host "`n=== Patching HTML template files ===" -ForegroundColor Cyan

$htmlFiles = Get-ChildItem -Path $templateDir -Filter "*.html" -Recurse

if ($htmlFiles.Count -eq 0) {
    Write-Warning "No .html files found under: $templateDir"
} else {
    foreach ($file in $htmlFiles) {
        try {
            $content = Get-Content $file.FullName -Raw -Encoding UTF8

            if ($content -match [regex]::Escape($marker)) {
                Write-Host "  [SKIP] Already has GA4: $($file.Name)" -ForegroundColor DarkGray
                $templatesSkipped++
                continue
            }

            if ($content -notmatch '</head>') {
                Write-Warning "  [WARN] No </head> tag found, skipping: $($file.Name)"
                $templatesFailed++
                continue
            }

            # Insert snippet immediately before </head>
            $patched = $content -replace '([ \t]*</head>)', "$ga4Snippet`$1"
            [System.IO.File]::WriteAllText($file.FullName, $patched, [System.Text.Encoding]::UTF8)
            Write-Host "  [OK]   Patched: $($file.FullName)" -ForegroundColor Green
            $templatesPatched++
        }
        catch {
            Write-Error "  [FAIL] $($file.Name): $_"
            $templatesFailed++
        }
    }
}

Write-Host "`nTemplate results: $templatesPatched patched, $templatesSkipped already done, $templatesFailed failed" -ForegroundColor Yellow

###############################################################################
# PART 2 — Patch Generate-ComingSoonPage in GenerateAllPages.ps1
#
# That function builds its own <head> block inline, so templates don't cover it.
# We find the closing </head> line inside the here-string and insert GA4 before it.
###############################################################################
Write-Host "`n=== Patching GenerateAllPages.ps1 (ComingSoonPage) ===" -ForegroundColor Cyan

if (-not (Test-Path $generateScript)) {
    Write-Warning "GenerateAllPages.ps1 not found at: $generateScript"
} else {
    try {
        $psContent = Get-Content $generateScript -Raw -Encoding UTF8

        if ($psContent -match [regex]::Escape($marker)) {
            Write-Host "  [SKIP] GenerateAllPages.ps1 already contains GA4 snippet." -ForegroundColor DarkGray
        } else {
            # The ComingSoonPage here-string contains a bare </head> line.
            # We target only that context by matching the Bootstrap link that precedes it
            # and the </head> that immediately follows — unique enough to be safe.
            $oldBlock = @'
    <link href="/static-football-rankings/css/styles.css" rel="stylesheet">
</head>
'@
            $newBlock = @'
    <link href="/static-football-rankings/css/styles.css" rel="stylesheet">
    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-GC17GSJ4S0"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());
      gtag('config', 'G-GC17GSJ4S0');
    </script>
</head>
'@
            if ($psContent -match [regex]::Escape($oldBlock)) {
                $psPatched = $psContent.Replace($oldBlock, $newBlock)
                [System.IO.File]::WriteAllText($generateScript, $psPatched, [System.Text.Encoding]::UTF8)
                Write-Host "  [OK]   Patched GenerateAllPages.ps1 ComingSoonPage block." -ForegroundColor Green
            } else {
                Write-Warning "  [WARN] Could not find the expected </head> pattern in GenerateAllPages.ps1."
                Write-Warning "         Add the GA4 snippet manually inside Generate-ComingSoonPage's here-string, before </head>."
            }
        }
    }
    catch {
        Write-Error "  [FAIL] GenerateAllPages.ps1: $_"
    }
}

###############################################################################
# Summary & next steps
###############################################################################
Write-Host @"

=== Done! Next steps ===
1. Run GenerateAllPages.ps1 (or run_update_cycle.ps1) to rebuild all output pages
2. Commit and push to GitHub
3. Visit https://analytics.google.com — within a few hours you should see
   active users appear in the Realtime report

To verify a page is tagged correctly, open any generated .html file and
search for 'G-GC17GSJ4S0'. It should appear in the <head> section.
"@ -ForegroundColor Green