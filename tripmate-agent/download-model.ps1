$ErrorActionPreference = 'Stop'

$modelDirectory = Join-Path $PSScriptRoot 'models'
$modelPath = Join-Path $modelDirectory 'Qwen3-1.7B-Q8_0.gguf'
$modelUrl = 'https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/resolve/main/Qwen3-1.7B-Q8_0.gguf?download=true'

New-Item -ItemType Directory -Force -Path $modelDirectory | Out-Null
if (Test-Path $modelPath) {
    throw "Model already exists at $modelPath. Remove that specific file before downloading it again."
}

$ProgressPreference = 'SilentlyContinue'
Invoke-WebRequest -Uri $modelUrl -OutFile $modelPath
if ((Get-Item $modelPath).Length -lt 1GB) {
    throw "The downloaded model is unexpectedly small. Check the download and remove $modelPath before retrying."
}

Write-Output "Downloaded local model to $modelPath"
