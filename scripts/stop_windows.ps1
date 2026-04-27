$ErrorActionPreference = "Stop"

$ContainerName = "finally-app"

Write-Host "FinAlly Shutdown Script"
Write-Host "====================="
Write-Host ""

# Check if container exists and is running
$RunningContainer = docker ps --format "{{.Names}}" 2>$null | Select-String "^$ContainerName$"
if ($RunningContainer) {
    Write-Host "Stopping container '$ContainerName'..."
    docker stop $ContainerName
    docker rm $ContainerName
    Write-Host "Container stopped and removed."
    Write-Host ""
    Write-Host "Note: Data persists in the 'finally-data' Docker volume."
    Write-Host "To remove the volume and all data, run:"
    Write-Host "  docker volume rm finally-data"
} else {
    # Check if container exists but is stopped
    $ExistingContainer = docker ps -a --format "{{.Names}}" 2>$null | Select-String "^$ContainerName$"
    if ($ExistingContainer) {
        Write-Host "Container '$ContainerName' is not running."
        Write-Host "Removing stopped container..."
        docker rm $ContainerName
        Write-Host "Stopped container removed."
    } else {
        Write-Host "Container '$ContainerName' does not exist."
    }
}
