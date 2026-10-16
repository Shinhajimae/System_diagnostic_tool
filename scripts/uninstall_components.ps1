param([switch]$Apply,[switch]$RemoveTask,[switch]$RemovePawnIO)
$ErrorActionPreference='Stop'

function Ask-Removal([string]$Question){
 while($true){
  $reply=Read-Host ($Question+' [Y/N]')
  if($reply.Trim() -match '^(?i)n(o)?$'){return $false}
  if($reply.Trim() -match '^(?i)y(es)?$'){return $true}
  Write-Host 'Enter Y to remove, or N to keep.'
 }
}

function Remove-BackgroundTask {
 $name='Diagnostic Sensors Reader'
 $task=Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
 if(!$task){Write-Host 'Sensors background task: not installed.';return}
 # Never stop/delete an unrelated task that happens to have the same name.
 $install=Join-Path ([Environment]::GetFolderPath('ProgramFiles')) 'Diagnostic'
 $allowed=@((Join-Path $install 'Sensors.exe'),(Join-Path $install 'SensorsReader.exe'))
 $portableRoot=Split-Path $PSScriptRoot -Parent
 $allowed+=Join-Path $portableRoot 'Sensors.exe'
 if(@($task.Actions).Count -ne 1 -or $task.Actions[0].Execute -notin $allowed){throw 'Task action does not match this tool; left unchanged.'}
 if($task.State -eq 'Running'){Stop-ScheduledTask -TaskName $name -ErrorAction Stop}
 Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction Stop
 if(Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue){throw 'Task removal could not be verified.'}
 Write-Host 'Sensors background task: removed. App files and tray startup preference kept.'
}

function Remove-PawnIO {
 $key='HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\PawnIO'
 if(!(Test-Path -LiteralPath $key)){Write-Host 'PawnIO: not installed.';return}
 $info=Get-ItemProperty -LiteralPath $key
 $location=[string]$info.InstallLocation
 if(!$location){$location=Join-Path ([Environment]::GetFolderPath('ProgramFiles')) 'PawnIO'}
 $uninstaller=Join-Path $location 'uninstall.exe'
 if(![IO.Path]::IsPathRooted($uninstaller) -or !(Test-Path -LiteralPath $uninstaller -PathType Leaf)){throw 'Official PawnIO uninstaller was not found. Use Windows Installed apps.'}
 Write-Host 'Opening the official PawnIO uninstaller. Complete or cancel it there.'
 $process=Start-Process -FilePath $uninstaller -ArgumentList '-uninstall' -Wait -PassThru
 if($process.ExitCode -notin 0,3010,1641){throw ('PawnIO uninstaller returned '+$process.ExitCode)}
 if(Test-Path -LiteralPath $key){Write-Host 'PawnIO remains installed; removal was cancelled or is incomplete.'}
 else{Write-Host 'PawnIO: removed. Restart Windows if requested.'}
}

function Remove-Python312 {
 $winget=Get-Command winget.exe -ErrorAction Stop
 Write-Host 'Uninstalling Python 3.12 only; other Python versions are left alone.'
 & $winget.Source uninstall --id Python.Python.3.12 --exact --source winget --accept-source-agreements --disable-interactivity | Out-Host
 if($LASTEXITCODE -notin 0,3010,1641){throw ('Python removal was not completed (WinGet code '+$LASTEXITCODE+'). It may already be absent.')}
 Write-Host 'Python 3.12 uninstaller finished. Other Python versions and project files were not removed.'
}

function Invoke-Uninstaller {
 if($Apply){
  if(!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'Administrator approval is required for task/driver removal.'}
  $failures=0
  if($RemoveTask){try{Remove-BackgroundTask}catch{Write-Host $_.Exception.Message -ForegroundColor Red;$failures++}}
  if($RemovePawnIO){try{Remove-PawnIO}catch{Write-Host $_.Exception.Message -ForegroundColor Red;$failures++}}
  return $failures
 }
 Write-Host 'Diagnostic / Sensors - optional component removal'
 Write-Host 'Type Y or N for each question, then press Enter to confirm.'
 Write-Host 'Removing the background task stops protected temperature delivery in this version.'
 $task=Ask-Removal 'Remove the Sensors background task?'
 $python=Ask-Removal 'Uninstall Python 3.12? Other programs may use it.'
 $pawn=Ask-Removal 'Uninstall PawnIO? Other monitoring programs may use it.'
 if(!$task -and !$python -and !$pawn){Write-Host 'Nothing selected. Nothing changed.';return 0}
 $failures=0
 # Run Python's uninstaller under the original account, not a different UAC admin account.
 if($python){try{Remove-Python312}catch{Write-Host $_.Exception.Message -ForegroundColor Red;$failures++}}
 if($task -or $pawn){
  $arguments='-NoProfile -ExecutionPolicy Bypass -File "'+$PSCommandPath+'" -Apply'
  if($task){$arguments+=' -RemoveTask'}
  if($pawn){$arguments+=' -RemovePawnIO'}
  try{
   $process=Start-Process powershell.exe -Verb RunAs -ArgumentList $arguments -Wait -PassThru
   if($process.ExitCode -ne 0){$failures++}
  }catch{Write-Host ('Administrator approval cancelled or removal failed: '+$_.Exception.Message);$failures++}
 }
 return $failures
}

try{exit (Invoke-Uninstaller)}catch{Write-Host $_.Exception.Message -ForegroundColor Red;exit 1}
