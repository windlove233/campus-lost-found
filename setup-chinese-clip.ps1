param([switch]$ModelOnly)

$ErrorActionPreference = 'Stop'
$project = $PSScriptRoot

if (-not $ModelOnly) {
    $venv = Join-Path $project '.venv'
    $python = Join-Path $venv 'Scripts/python.exe'
    $env:TMP = (New-Item -ItemType Directory -Force -Path (Join-Path $venv 'tmp')).FullName
    $env:TEMP = $env:TMP

    if (-not (Test-Path -LiteralPath $python)) {
        python -m venv --without-pip $venv
        if ($LASTEXITCODE) { throw 'Could not create the Python virtual environment.' }
    }
    if (-not (Test-Path -LiteralPath (Join-Path $venv 'Scripts/pip.exe'))) {
        & $python -m ensurepip --upgrade --default-pip
        if ($LASTEXITCODE) { throw 'Could not install pip in the virtual environment.' }
    }

    & $python -m pip --disable-pip-version-check --no-cache-dir --timeout 60 install `
        torch==2.11.0 torchvision==0.26.0 --index-url https://download.pytorch.org/whl/cu128
    if ($LASTEXITCODE) { throw 'Could not install CUDA-enabled PyTorch.' }

    & $python -m pip --disable-pip-version-check --no-cache-dir --timeout 60 install `
        transformers==4.57.6 --index-url https://pypi.org/simple
    if ($LASTEXITCODE) { throw 'Could not install Transformers.' }

    & $python -m pip check
    if ($LASTEXITCODE) { throw 'The installed Python dependencies are inconsistent.' }
}

$model = (New-Item -ItemType Directory -Force -Path (Join-Path $project 'models/chinese-clip-vit-base-patch16')).FullName
$source = 'https://www.modelscope.cn/models/AI-ModelScope/chinese-clip-vit-base-patch16/resolve/master'
$weightHash = '7b7b583c210c867410bc6bdb8a55fe14eec62999e0a9ea31ff222dc501f9cfbe'

foreach ($name in 'config.json', 'preprocessor_config.json', 'vocab.txt', 'pytorch_model.bin') {
    $destination = Join-Path $model $name
    $hasWeights = $name -eq 'pytorch_model.bin'
    if (Test-Path -LiteralPath $destination -PathType Leaf) {
        if (-not $hasWeights -or (Get-FileHash -LiteralPath $destination).Hash -eq $weightHash) {
            continue
        }
    }

    $partial = "$destination.part"
    $completeWeightDownload = $hasWeights -and (Test-Path -LiteralPath $partial -PathType Leaf) `
        -and (Get-Item -LiteralPath $partial).Length -eq 753177983
    if (-not $completeWeightDownload) {
        Write-Host "Downloading $name"
        curl.exe --fail --location --retry 3 --connect-timeout 20 --continue-at - `
            --output $partial "$source/$name"
        if ($LASTEXITCODE) { throw "Could not download $name." }
    }
    if ($hasWeights -and (Get-FileHash -LiteralPath $partial).Hash -ne $weightHash) {
        Remove-Item -LiteralPath $partial
        throw 'The downloaded model weights failed the SHA-256 check. Run setup again to retry.'
    }
    Move-Item -LiteralPath $partial -Destination $destination -Force
}

Write-Host "Chinese-CLIP files are ready in $model"
