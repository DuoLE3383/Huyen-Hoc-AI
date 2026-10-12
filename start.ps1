param(
    [string]$Model = "qwen2.5:7b"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    throw "Python was not found. Install Python 3.10+ and add it to PATH."
}

$ollamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollamaCommand) {
    throw "Ollama was not found. Install it from https://ollama.com/download and retry."
}

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "Creating the Python virtual environment..."
    & $pythonCommand.Source -m venv (Join-Path $PSScriptRoot ".venv")
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the Python virtual environment."
    }
}

Write-Host "Installing/checking backend dependencies..."
& $venvPython -m pip install -r (Join-Path $PSScriptRoot "backend\requirements.txt")
if ($LASTEXITCODE -ne 0) {
    throw "Backend dependency installation failed."
}

$envFile = Join-Path $PSScriptRoot ".env.local"
if (-not $env:HUYEN_HOC_SECRET_KEY) {
    $storedSecret = $null
    if (Test-Path -LiteralPath $envFile) {
        foreach ($line in Get-Content -LiteralPath $envFile) {
            if ($line -match '^HUYEN_HOC_SECRET_KEY=(.*)$') {
                $storedSecret = $matches[1]
                break
            }
        }
    }

    if ($storedSecret) {
        if ($storedSecret.Length -lt 32) {
            throw ".env.local contains a HUYEN_HOC_SECRET_KEY shorter than 32 characters."
        }
        $env:HUYEN_HOC_SECRET_KEY = $storedSecret
    } else {
        $env:HUYEN_HOC_SECRET_KEY = (& $venvPython -c "import secrets; print(secrets.token_urlsafe(48))").Trim()
        if ($LASTEXITCODE -ne 0 -or $env:HUYEN_HOC_SECRET_KEY.Length -lt 32) {
            throw "Could not generate a valid local JWT secret."
        }
        Add-Content -LiteralPath $envFile -Value "HUYEN_HOC_SECRET_KEY=$env:HUYEN_HOC_SECRET_KEY" -Encoding UTF8
        Write-Host "Created a persistent local JWT secret in .env.local (git-ignored)."
    }
}

if (-not $env:TELEGRAM_BOT_TOKEN) {
    $telegramConfigFiles = @(
        $envFile,
        (Join-Path $PSScriptRoot "deploy\.env.prod")
    )
    foreach ($configFile in $telegramConfigFiles) {
        if (-not (Test-Path -LiteralPath $configFile)) {
            continue
        }

        foreach ($line in Get-Content -LiteralPath $configFile) {
            if ($line -match '^\s*TELEGRAM_BOT_TOKEN\s*=\s*(.*?)\s*$') {
                $token = $matches[1]
                if ($token.Length -ge 2 -and
                    (($token.StartsWith('"') -and $token.EndsWith('"')) -or
                     ($token.StartsWith("'") -and $token.EndsWith("'")))) {
                    $token = $token.Substring(1, $token.Length - 2)
                }
                if ($token -and $token -notmatch '^(CHANGE|PLACEHOLDER|REPLACE)') {
                    $env:TELEGRAM_BOT_TOKEN = $token
                    Write-Host "Loaded Telegram bot configuration from $configFile."
                    break
                }
            }
        }

        if ($env:TELEGRAM_BOT_TOKEN) {
            break
        }
    }
}

if (-not $env:OPENWEATHER_API_KEY) {
    $weatherConfigFiles = @(
        $envFile,
        (Join-Path $PSScriptRoot "deploy\.env.prod")
    )
    foreach ($configFile in $weatherConfigFiles) {
        if (-not (Test-Path -LiteralPath $configFile)) {
            continue
        }

        foreach ($line in Get-Content -LiteralPath $configFile) {
            if ($line -match '^\s*OPENWEATHER_API_KEY\s*=\s*(.*?)\s*$') {
                $key = $matches[1]
                if ($key.Length -ge 2 -and
                    (($key.StartsWith('"') -and $key.EndsWith('"')) -or
                     ($key.StartsWith("'") -and $key.EndsWith("'")))) {
                    $key = $key.Substring(1, $key.Length - 2)
                }
                if ($key -and $key -notmatch '^(CHANGE|PLACEHOLDER|REPLACE)') {
                    $env:OPENWEATHER_API_KEY = $key
                    break
                }
            }
        }

        if ($env:OPENWEATHER_API_KEY) {
            break
        }
    }
}

if (-not $env:OLLAMA_URL) {
    $env:OLLAMA_URL = "http://localhost:11434"
}
if ($env:OLLAMA_MODEL) {
    $Model = $env:OLLAMA_MODEL
} else {
    $env:OLLAMA_MODEL = $Model
}

$ollamaReady = $false
try {
    Invoke-RestMethod -Uri "$($env:OLLAMA_URL.TrimEnd('/'))/api/tags" -TimeoutSec 2 | Out-Null
    $ollamaReady = $true
} catch {
    Write-Host "Starting the Ollama server..."
    Start-Process -FilePath $ollamaCommand.Source -ArgumentList "serve" -WindowStyle Hidden
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Seconds 1
        try {
            Invoke-RestMethod -Uri "$($env:OLLAMA_URL.TrimEnd('/'))/api/tags" -TimeoutSec 2 | Out-Null
            $ollamaReady = $true
            break
        } catch {
        }
    }
}

if (-not $ollamaReady) {
    throw "Ollama did not become available at $($env:OLLAMA_URL). Start Ollama and retry."
}

$installedModels = & $ollamaCommand.Source list
if ($LASTEXITCODE -ne 0) {
    throw "Could not list Ollama models."
}
if (-not ($installedModels | Select-String -SimpleMatch $Model)) {
    Write-Host "Downloading Ollama model '$Model' (this may take a while)..."
    & $ollamaCommand.Source pull $Model
    if ($LASTEXITCODE -ne 0) {
        throw "Could not download Ollama model '$Model'."
    }
}

Write-Host "Starting Huyen Hoc AI at http://localhost:8000/"
Write-Host "Keep this window open. Press Ctrl+C to stop the app."
& $venvPython -m uvicorn main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
if ($LASTEXITCODE -ne 0) {
    throw "The backend exited with an error."
}
