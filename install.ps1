# Link's Tool Box: installs (or upgrades) the newest Windows version from GitHub. In PowerShell:
#
#     irm https://raw.githubusercontent.com/losava/Links-Toolbox/main/install.ps1 | iex
#
# It downloads the newest release's Windows zip, unpacks it in a temporary folder, opens its installer window
# (click Install, or Upgrade), and removes the temporary folder once the installer is closed.
& {
    $ErrorActionPreference = 'Stop'
    $ProgressPreference = 'SilentlyContinue'      # (Windows PowerShell downloads far faster without the progress bar)
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    $url = 'https://github.com/losava/Links-Toolbox/releases/latest/download/Link.Toolbox.zip'
    $work = Join-Path $env:TEMP ('LinkToolbox-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
    New-Item -ItemType Directory -Force $work | Out-Null
    try {
        Write-Host "Downloading Link's Tool Box (about 85 MB)..."
        Invoke-WebRequest $url -OutFile "$work\Link Toolbox.zip" -UseBasicParsing
        Write-Host 'Unpacking...'
        Expand-Archive "$work\Link Toolbox.zip" $work -Force
        $py = "$work\Link Toolbox\python\pythonw.exe"
        $installer = "$work\Link Toolbox\app\install.py"
        if (-not (Test-Path $py) -or -not (Test-Path $installer)) { throw "The download does not look like Link's Tool Box." }
        Write-Host 'Opening the installer: click Install (or Upgrade).'
        Start-Process $py -ArgumentList "`"$installer`"" -Wait
        Write-Host 'Done.'
    } finally {
        Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
    }
}
