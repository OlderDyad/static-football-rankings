# setup_project.ps1
$projectRoot = "C:\Users\demck\OneDrive\Football_2024\static-football-rankings"

# Function to log messages
function Write-Log {
    param($Message)
    Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'): $Message"
}

Write-Log "Starting project setup..."

# Create directory structure
$directories = @(
    "src",
    "src\data",
    "src\images",
    "src\images\header",
    "src\images\teams",
    "src\css",
    "src\js",
    "scripts",
    ".github\workflows"
)

foreach ($dir in $directories) {
    $path = Join-Path $projectRoot $dir
    if (-not (Test-Path $path)) {
        New-Item -Path $path -ItemType Directory -Force
        Write-Log "Created directory: $dir"
    } else {
        Write-Log "Directory already exists: $dir"
    }
}

# Create .gitignore
$gitignore = @"
# Dependencies
node_modules/

# Build output
dist/
build/

# Environment variables
.env
.env.local
.env.*.local

# IDE files
.vscode/
.idea/
*.suo
*.ntvs*
*.njsproj
*.sln
*.sw?

# Logs
logs
*.log
npm-debug.log*

# Runtime data
pids
*.pid
*.seed
*.pid.lock

# Mac files
.DS_Store

# Windows files
Thumbs.db
"@

$gitignorePath = Join-Path $projectRoot ".gitignore"
Set-Content -Path $gitignorePath -Value $gitignore
Write-Log "Created .gitignore file"

# Create README.md
$readme = @"
# McKnight's Football Rankings

Public repository for McKnight's Football Rankings static website. This project provides historical rankings and statistics for high school football programs.

## Features

- All-time program rankings (50+ seasons)
- Detailed program statistics
- Interactive search and filtering
- Public commenting system

## Development

### Prerequisites

- PowerShell
- Python (for local development server)
- Web browser

### Local Development

1. Clone the repository
2. Run a local server:
   ```bash
   python -m http.server 8000
   ```
3. Open http://localhost:8000 in your browser

## Deployment

The site is automatically deployed using GitHub Pages and Web Assembly.

## License

© 2024 McKnight's Football Rankings. All rights reserved.
"@

$readmePath = Join-Path $projectRoot "README.md"
Set-Content -Path $readmePath -Value $readme
Write-Log "Created README.md file"

# Copy existing files
Write-Log "Copying existing files..."

# Copy data files
$sourceData = Join-Path $projectRoot "data"
$destData = Join-Path $projectRoot "src\data"
if (Test-Path $sourceData) {
    Copy-Item -Path "$sourceData\*" -Destination $destData -Recurse -Force
    Write-Log "Copied data files"
} else {
    Write-Log "Warning: Source data directory not found"
}

# Copy CSS files
$sourceCss = Join-Path $projectRoot "css"
$destCss = Join-Path $projectRoot "src\css"
if (Test-Path $sourceCss) {
    Copy-Item -Path "$sourceCss\*" -Destination $destCss -Force
    Write-Log "Copied CSS files"
} else {
    Write-Log "Warning: Source CSS directory not found"
}

# Copy JS files
$sourceJs = Join-Path $projectRoot "js"
$destJs = Join-Path $projectRoot "src\js"
if (Test-Path $sourceJs) {
    Copy-Item -Path "$sourceJs\*" -Destination $destJs -Force
    Write-Log "Copied JavaScript files"
} else {
    Write-Log "Warning: Source JS directory not found"
}

# Copy HTML files
$sourceHtml = Join-Path $projectRoot "*.html"
$destHtml = Join-Path $projectRoot "src"
if (Test-Path $sourceHtml) {
    Copy-Item -Path $sourceHtml -Destination $destHtml -Force
    Write-Log "Copied HTML files"
} else {
    Write-Log "Warning: Source HTML files not found"
}

# Copy header image
$sourceImage = "C:\Users\demck\OneDrive\Football_2024\McKnightFootballRankings.WebV2\wwwroot\images\football-field-top.jpg"
$destImage = Join-Path $projectRoot "src\images\header\football-field-top.jpg"
if (Test-Path $sourceImage) {
    Copy-Item -Path $sourceImage -Destination $destImage -Force
    Write-Log "Copied header image"
} else {
    Write-Log "Warning: Header image not found at $sourceImage"
}

# Verify setup
Write-Log "`nVerifying setup..."
Write-Log "Checking directory structure..."
foreach ($dir in $directories) {
    $path = Join-Path $projectRoot $dir
    if (Test-Path $path) {
        Write-Log "✓ Directory exists: $dir"
    } else {
        Write-Log "✗ Missing directory: $dir"
    }
}

Write-Log "`nChecking key files..."
$keyFiles = @(
    ".gitignore",
    "README.md",
    "src\index.html",
    "src\css\styles.css",
    "src\js\main.js",
    "src\images\header\football-field-top.jpg"
)

foreach ($file in $keyFiles) {
    $path = Join-Path $projectRoot $file
    if (Test-Path $path) {
        Write-Log "✓ File exists: $file"
    } else {
        Write-Log "✗ Missing file: $file"
    }
}

Write-Log "`nSetup complete!"