$ErrorActionPreference='Stop'
try{
 $key='HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\PawnIO'
 if(Test-Path -LiteralPath $key){Write-Host 'PawnIO is already installed. Nothing to install.';exit 0}
 $winget=Get-Command winget.exe -ErrorAction Stop
 Write-Host 'PawnIO is missing. Installing the official package through WinGet...'
 & $winget.Source install --id namazso.PawnIO --exact --source winget --scope machine --silent --accept-source-agreements --accept-package-agreements --disable-interactivity
 if($LASTEXITCODE -notin 0,3010,1641){throw ('PawnIO installation failed: '+$LASTEXITCODE)}
 if(!(Test-Path -LiteralPath $key)){throw 'PawnIO installation was not detected. Restart if requested, then retry setup.'}
 Write-Host 'PawnIO installed. Restart Windows if requested by the installer.'
}catch{Write-Host $_.Exception.Message -ForegroundColor Red;exit 1}
