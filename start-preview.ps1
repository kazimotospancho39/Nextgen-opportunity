$ErrorActionPreference = 'Stop'

$project = $PSScriptRoot
$python = 'C:\Users\kazim\OneDrive\Documents\Opportunity Hub Tanzania\.venv\Scripts\python.exe'
$previewDir = Join-Path $env:TEMP 'opportunity-hub-preview'
$cloudflared = Join-Path $previewDir 'cloudflared.exe'
$serverLog = Join-Path $previewDir 'server-out.log'
$serverError = Join-Path $previewDir 'server-error.log'
$tunnelOut = Join-Path $previewDir 'tunnel-out.log'
$tunnelError = Join-Path $previewDir 'tunnel-error.log'
$expectedHash = '76b2805253d0d6ffacb092a7acfbee99e7af6917835c0c5410e23f3ef5052da2'

if (-not (Test-Path -LiteralPath $python)) { throw "Python environment not found: $python" }
if (Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Port 5000 is already in use. Stop the other Opportunity Hub server, then run this preview launcher again.'
}
New-Item -ItemType Directory -Path $previewDir -Force | Out-Null

if (-not (Test-Path -LiteralPath $cloudflared)) {
    $downloadUrl = 'https://github.com/cloudflare/cloudflared/releases/download/2026.10.3/cloudflared-windows-amd64.exe'
    Write-Host 'Downloading Cloudflare Tunnel for this temporary preview...'
    & curl.exe --location --fail --silent --show-error --output $cloudflared $downloadUrl
    if ($LASTEXITCODE -ne 0) { throw 'Cloudflare Tunnel download failed.' }
}
$actualHash = (Get-FileHash -LiteralPath $cloudflared -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualHash -ne $expectedHash) {
    Remove-Item -LiteralPath $cloudflared -Force
    throw 'Cloudflare Tunnel checksum did not match the official release. The downloaded file was removed.'
}

$randomBytes = New-Object byte[] 24
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($randomBytes)
$previewAdminPassword = [Convert]::ToBase64String($randomBytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
$secretBytes = New-Object byte[] 48
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($secretBytes)
$previewSecret = [Convert]::ToBase64String($secretBytes)
$server = $null
$tunnel = $null
try {
    $env:ADMIN_PASSWORD = $previewAdminPassword
    $env:FLASK_SECRET_KEY = $previewSecret
    $env:DEMO_PAYMENTS = 'true'
    $server = Start-Process -FilePath $python -ArgumentList 'app.py' -WorkingDirectory $project -PassThru -WindowStyle Hidden -RedirectStandardOutput $serverLog -RedirectStandardError $serverError
    Remove-Item Env:ADMIN_PASSWORD, Env:FLASK_SECRET_KEY, Env:DEMO_PAYMENTS

    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        if ($server.HasExited) { throw "Opportunity Hub stopped while starting. See $serverError" }
        try {
            $response = Invoke-WebRequest -Uri 'http://127.0.0.1:5000/health' -TimeoutSec 2 -UseBasicParsing
            if ($response.StatusCode -eq 200) { $ready = $true; break }
        } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $ready) { throw "Opportunity Hub did not become ready on port 5000. See $serverError" }

    $response = Invoke-WebRequest -Uri 'http://127.0.0.1:5000/health' -TimeoutSec 5 -UseBasicParsing
    if ($response.StatusCode -ne 200) { throw 'The service on port 5000 is not responding as Opportunity Hub.' }

    Remove-Item -LiteralPath $tunnelOut, $tunnelError -Force -ErrorAction SilentlyContinue
    $tunnel = Start-Process -FilePath $cloudflared -ArgumentList @('tunnel', '--url', 'http://127.0.0.1:5000') -PassThru -WindowStyle Hidden -RedirectStandardOutput $tunnelOut -RedirectStandardError $tunnelError
    $previewUrl = $null
    for ($i = 0; $i -lt 45 -and -not $previewUrl; $i++) {
        if ($tunnel.HasExited) { throw "Cloudflare Tunnel stopped unexpectedly. See $tunnelError" }
        $logText = (Get-Content -LiteralPath $tunnelOut -Raw -ErrorAction SilentlyContinue) + (Get-Content -LiteralPath $tunnelError -Raw -ErrorAction SilentlyContinue)
        if ($logText) {
            if ($logText -match 'https://[a-z0-9-]+\.trycloudflare\.com') { $previewUrl = $Matches[0]; break }
        }
        Start-Sleep -Seconds 1
    }
    if (-not $previewUrl) { throw "No preview URL appeared. Check $tunnelError and your internet connection." }

    Write-Host ''
    Write-Host "Client preview link: $previewUrl" -ForegroundColor Green
    Write-Host 'This temporary link works only while this PowerShell window stays open.'
    Write-Host 'Payments are in demo mode. Share the link with your client; the admin password below is for you only.'
    Write-Host "Temporary admin password: $previewAdminPassword" -ForegroundColor Yellow
    Set-Clipboard -Value $previewUrl
    Write-Host 'The preview link has been copied to your clipboard.'
    Write-Host 'Press Ctrl+C to stop the preview.'
    while (-not $tunnel.HasExited -and -not $server.HasExited) { Start-Sleep -Seconds 1 }
} finally {
    Remove-Item Env:ADMIN_PASSWORD, Env:FLASK_SECRET_KEY, Env:DEMO_PAYMENTS -ErrorAction SilentlyContinue
    if ($tunnel -and -not $tunnel.HasExited) { Stop-Process -Id $tunnel.Id -Force -ErrorAction SilentlyContinue }
    if ($server -and -not $server.HasExited) { Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue }
}
