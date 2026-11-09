# Import the native framework source

This repository has been created under the Yuktara UI product name. The initial GitHub commit establishes the project identity and contribution rules. The native 2.8 source snapshot is not part of that commit yet.

## Import on Windows (PowerShell)

1. Download the **NovaUI Native 2.8 source ZIP** from the earlier project delivery in this conversation.
2. Clone this repository.
3. Extract the ZIP into a temporary directory.
4. Copy its contents into the repository root, excluding transient Python caches.
5. Commit and push.

```powershell
git clone https://github.com/sumankrsaurabh/Yuktara-UI.git
cd Yuktara-UI

$archive = "$HOME\Downloads\NovaUI-Native-2.8-source.zip"
$temp = Join-Path $env:TEMP "Yuktara-UI-Native-2.8"
Expand-Archive -Path $archive -DestinationPath $temp -Force

$sourceRoot = $temp
Get-ChildItem $sourceRoot -Recurse -File |
  Where-Object {
    $_.FullName -notmatch '[\\/](__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache)[\\/]' -and
    $_.Extension -notin @('.pyc', '.pyo')
  } |
  ForEach-Object {
    $relative = $_.FullName.Substring($sourceRoot.Length).TrimStart('\', '/')
    $destination = Join-Path (Get-Location) $relative
    New-Item -ItemType Directory -Force (Split-Path $destination) | Out-Null
    Copy-Item $_.FullName $destination -Force
  }

git add -A
git commit -m "Add Yuktara UI native framework 2.8"
git push origin main
```

If the ZIP extracts into a wrapper directory, set `$sourceRoot` to that directory's contents so that `novaui/`, `examples/`, `tests/` and `docs/` land at the repository root.

## Import on macOS / Linux

```bash
git clone https://github.com/sumankrsaurabh/Yuktara-UI.git
cd Yuktara-UI
unzip ~/Downloads/NovaUI-Native-2.8-source.zip -d /tmp/yuktara-ui-native-2.8
cp -a /tmp/yuktara-ui-native-2.8/. .
find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache \) -prune -exec rm -rf {} +
find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
git add -A
git commit -m "Add Yuktara UI native framework 2.8"
git push origin main
```

## Verify after import

```bash
python -m pytest -q tests/native
python -m compileall -q novaui
```

The Python import namespace remains `novaui` in this snapshot for compatibility. Do not rename it as part of the import; schedule that as a separate migration.
