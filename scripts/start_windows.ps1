param(
    [switch]$Build = $false
)

$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot
$ContainerName = "finally-app"
$ImageName = "finally:latest"

Write-Host "FinAlly Startup Script"
Write-Host "====================="
Write-Host ""

# Check if .env file exists
if (-not (Test-Path "$ProjectDir\.env")) {
    Write-Host "Error: .env file not found at $ProjectDir\.env"
    Write-Host "Please create .env from .env.example and add your API keys."
    exit 1
}

# Check if image needs to be built
$ImageExists = docker image inspect $ImageName 2>$null
if ($Build -or -not $ImageExists) {
    Write-Host "Building Docker image..."
    docker build -t $ImageName $ProjectDir
    Write-Host "Docker image built successfully."
    Write-Host ""
}

# Check if container is already running
$RunningContainer = docker ps --format "{{.Names}}" 2>$null | Select-String "^$ContainerName$"
if ($RunningContainer) {
    Write-Host "Container '$ContainerName' is already running."
    Write-Host ""
    Write-Host "FinAlly is running at http://localhost:8000"
    exit 0
}

# Check if container exists but is stopped
$ExistingContainer = docker ps -a --format "{{.Names}}" 2>$null | Select-String "^$ContainerName$"
if ($ExistingContainer) {
    Write-Host "Starting existing container..."
    docker start $ContainerName
} else {
    Write-Host "Starting new container..."
    docker run -d `
        --name $ContainerName `
        -p 8000:8000 `
        -v finally-data:/app/db `
        --env-file "$ProjectDir\.env" `
        -e PYTHONUNBUFFERED=1 `
        --restart unless-stopped `
        $ImageName
}

# Wait for container to be healthy
Write-Host "Waiting for FinAlly to be ready..."
$MaxRetries = 30
$Retries = 0

while ($Retries -lt $MaxRetries) {
    try {
        $Response = docker exec $ContainerName curl -s http://localhost:8000/api/health 2>$null
        if ($Response) {
            Write-Host ""
            Write-Host "FinAlly is running at http://localhost:8000"
            exit 0
        }
    } catch {
        # Ignore errors, keep retrying
    }
    Write-Host -NoNewline "."
    Start-Sleep -Seconds 1
    $Retries++
}

Write-Host ""
Write-Host "Warning: Health check timed out, but container may still be starting."
Write-Host "FinAlly should be available at http://localhost:8000"
Write-Host ""
Write-Host "To view logs: docker logs -f $ContainerName"
