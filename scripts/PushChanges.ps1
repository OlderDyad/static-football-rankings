<#
.SYNOPSIS
    Automates staging, committing, and pushing changes to GitHub.

.DESCRIPTION
    This script stages all changes in the current Git repository, commits them with a provided message,
    and pushes the commits to the specified remote branch on GitHub.

.PARAMETER CommitMessage
    The commit message describing the changes. If not provided, the script will prompt for one.

.PARAMETER Remote
    The name of the remote repository (default is 'origin').

.PARAMETER Branch
    The name of the branch to push to (default is the current branch).

.EXAMPLE
    .\PushChanges.ps1 -CommitMessage "Fixed search functionality bug"

.EXAMPLE
    .\PushChanges.ps1

.NOTES
    Ensure you have Git installed and configured on your system.
    Navigate to your project directory before running this script.
#>

param (
    [Parameter(Mandatory=$false)]
    [string]$CommitMessage = "Automated commit",

    [Parameter(Mandatory=$false)]
    [string]$Remote = "origin",

    [Parameter(Mandatory=$false)]
    [string]$Branch
)

# Function to check if Git is installed
function Check-Git {
    try {
        git --version | Out-Null
    } catch {
        Write-Error "Git is not installed or not added to PATH. Please install Git and try again."
        exit 1
    }
}

# Function to get the current Git branch
function Get-CurrentBranch {
    try {
        $currentBranch = git rev-parse --abbrev-ref HEAD
        return $currentBranch.Trim()
    } catch {
        Write-Error "Unable to determine the current Git branch."
        exit 1
    }
}

# Function to stage all changes
function Stage-AllChanges {
    Write-Host "Staging all changes..."
    git add .
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to stage changes."
        exit 1
    }
}

# Function to commit changes
function Commit-Changes($message) {
    Write-Host "Committing changes with message: '$message'"
    git commit -m $message
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to commit changes. Ensure there are changes to commit."
        exit 1
    }
}

# Function to push changes
function Push-Changes($remote, $branch) {
    Write-Host "Pushing changes to '$remote/$branch'..."
    git push $remote $branch
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to push changes to '$remote/$branch'."
        exit 1
    }
}

# Function to validate Git repository
function Validate-GitRepository {
    try {
        git rev-parse --is-inside-work-tree | Out-Null
    } catch {
        Write-Error "The current directory is not a Git repository."
        exit 1
    }
}

# Main Execution Flow
Check-Git
Validate-GitRepository

# Determine the branch if not provided
if ([string]::IsNullOrWhiteSpace($Branch)) {
    $Branch = Get-CurrentBranch
    Write-Host "Detected current branch: '$Branch'"
} else {
    Write-Host "Using specified branch: '$Branch'"
}

# Prompt for commit message if it's still empty
if ([string]::IsNullOrWhiteSpace($CommitMessage)) {
    $CommitMessage = Read-Host "Enter commit message"
    if ([string]::IsNullOrWhiteSpace($CommitMessage)) {
        Write-Error "Commit message cannot be empty."
        exit 1
    }
}

Stage-AllChanges
Commit-Changes $CommitMessage
Push-Changes $Remote $Branch

Write-Host "✅ All changes have been successfully pushed to '$Remote/$Branch'."
