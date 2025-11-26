# Windows Task Scheduler Setup for Daily Reports
# Run this script as Administrator to schedule daily report generation at 11:30 PM

# Configuration
$pythonExe = "python"  # Adjust if Python is in a different location
$scriptPath = "C:\Users\Surface Pro 7\Intradyne\scripts\generate_daily_report.py"
$workingDir = "C:\Users\Surface Pro 7\Intradyne"

# Task configuration
$taskName = "Intradyne_Daily_Paper_Trading_Report"
$taskDescription = "Generate daily paper trading report at 11:30 PM"
$triggerTime = "23:30"  # 11:30 PM

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "INTRADYNE - Daily Report Scheduler Setup" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

Write-Host "Checking existing task..." -ForegroundColor Yellow

# Remove existing task if it exists
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Found existing task. Removing..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

Write-Host "Creating scheduled task..." -ForegroundColor Yellow

# Create action
$action = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument $scriptPath `
    -WorkingDirectory $workingDir

# Create trigger (daily at 11:30 PM)
$trigger = New-ScheduledTaskTrigger -Daily -At $triggerTime

# Create settings
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

# Register the task
Register-ScheduledTask `
    -TaskName $taskName `
    -Description $taskDescription `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -User $env:USERNAME `
    -RunLevel Highest

Write-Host ""
Write-Host "SUCCESS! Scheduled task created:" -ForegroundColor Green
Write-Host "  Task Name: $taskName" -ForegroundColor White
Write-Host "  Schedule: Daily at $triggerTime (11:30 PM)" -ForegroundColor White
Write-Host "  Script: $scriptPath" -ForegroundColor White
Write-Host ""
Write-Host "The daily report will be automatically generated every day at 11:30 PM" -ForegroundColor Green
Write-Host ""
Write-Host "To view/manage the task:" -ForegroundColor Cyan
Write-Host "  1. Open Task Scheduler (taskschd.msc)" -ForegroundColor White
Write-Host "  2. Look for '$taskName'" -ForegroundColor White
Write-Host ""
Write-Host "To test the task now:" -ForegroundColor Cyan
Write-Host "  Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor Yellow
Write-Host ""
Write-Host "======================================================================"  -ForegroundColor Cyan
