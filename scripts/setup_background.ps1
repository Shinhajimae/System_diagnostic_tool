param([string]$StartupUserSid,[switch]$PrepareBuild,[switch]$RebuildApproved)
$ErrorActionPreference='Stop'
function Stop-ExistingReader($Task){
 if(!$Task){return}
 Stop-ScheduledTask -TaskName $Task.TaskName
 $oldExe=$Task.Actions[0].Execute
 $deadline=(Get-Date).AddSeconds(10)
 do{
  $running=@(Get-CimInstance Win32_Process | Where-Object{$_.ExecutablePath -eq $oldExe -and ($oldExe -like '*\SensorsReader.exe' -or $_.CommandLine -match '(?i)(?:^|\s)--reader(?:\s|$)')})
  foreach($process in $running){[void](Invoke-CimMethod -InputObject $process -MethodName Terminate -Arguments @{Reason=[uint32]0} -ErrorAction SilentlyContinue)}
  if($running.Count){Start-Sleep -Milliseconds 250}
 }while($running.Count -and (Get-Date) -lt $deadline)
 if($running.Count){throw 'The existing reader could not be stopped automatically.'}
}
try{
 $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
 if(!([Security.Principal.WindowsPrincipal]$identity).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'Approve the background setup administrator request.'}
 if($StartupUserSid -ne $identity.User.Value){throw 'Run setup from your own administrator account; a different administrator account cannot configure your sign-in task.'}
 $source=Split-Path $PSScriptRoot -Parent
 $exe=Join-Path $source 'Sensors.exe'
 if(!$PrepareBuild){foreach($name in 'Diagnostic.exe','Sensors.exe'){
  if(!(Test-Path -LiteralPath (Join-Path $source $name) -PathType Leaf)){throw ('Missing '+$name+'. Run build_exe.bat first.')}
 }}
 $taskName='Diagnostic Sensors Reader'
 $old=Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
 $legacy=Join-Path ([Environment]::GetFolderPath('ProgramFiles')) 'Diagnostic'
 $allowed=@($exe,(Join-Path $legacy 'Sensors.exe'),(Join-Path $legacy 'SensorsReader.exe'))
 if($old){
  $recognised=$false
  if(@($old.Actions).Count -eq 1){
   $action=$old.Actions[0]
   $leaf=[IO.Path]::GetFileName($action.Execute)
   $readerAction=($leaf -ieq 'Sensors.exe' -and ([string]$action.Arguments).Trim() -eq '--reader') -or ($leaf -ieq 'SensorsReader.exe' -and [string]::IsNullOrWhiteSpace($action.Arguments))
   $owner=[string]$old.Principal.UserId
   if($owner -notmatch '^S-1-'){
    try{$owner=([Security.Principal.NTAccount]::new($owner)).Translate([Security.Principal.SecurityIdentifier]).Value}catch{$owner=''}
   }
   $recognised=$readerAction -and ($owner -eq $StartupUserSid -or ($owner -eq 'S-1-5-18' -and $action.Execute -in $allowed))
  }
  if(!$recognised){
   $target=(@($old.Actions | ForEach-Object{$_.Execute}) -join ', ')
   $problem=[InvalidOperationException]::new(('Task "'+$taskName+'" has an unexpected owner or action: '+$target+'. It was left unchanged because it could not be identified as this app reader.'))
   $problem.Data['SetupExitCode']=20
   throw $problem
  }
  if(!$RebuildApproved){
   do{$reply=Read-Host 'Sensors background task already exists. Rebuild it for this folder? [Y/N]'}while($reply -notmatch '^(?i)[yn]$')
   if($reply -match '^(?i)n$'){Write-Host 'Existing background task kept unchanged.';exit 21}
  }
  Write-Host 'Existing Sensors background task will be rebuilt for this folder.'
 }
 if($PrepareBuild){Stop-ExistingReader $old;Write-Host 'Background reader paused for rebuilding.';exit 0}
 $pawnKey='HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\PawnIO'
 if(!(Test-Path -LiteralPath $pawnKey)){
  do{$answer=Read-Host 'Protected temperatures require PawnIO. Install the driver through WinGet? [Y/N]'}while($answer -notmatch '^(?i)[yn]$')
  if($answer -match '^(?i)n$'){Write-Host 'Background setup cancelled. Nothing configured.';exit 1}
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'install_driver.ps1')
  if($LASTEXITCODE -ne 0){throw 'PawnIO setup did not complete.'}
 }
 Stop-ExistingReader $old
 # Clean up only the two known snapshot files from older versions; never recurse.
 $legacyData=Join-Path ([Environment]::GetFolderPath('CommonApplicationData')) 'Diagnostic'
 if(Test-Path -LiteralPath $legacyData){
  if((Get-Item -LiteralPath $legacyData -Force).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Refusing a redirected legacy data folder.'}
  foreach($name in 'temperatures.json','temperatures.tmp'){
   $file=Join-Path $legacyData $name
   if(Test-Path -LiteralPath $file){
    $item=Get-Item -LiteralPath $file -Force
    if($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Unexpected legacy snapshot path; left unchanged.'}
    Remove-Item -LiteralPath $file -Force
   }
  }
  if(!(Get-ChildItem -LiteralPath $legacyData -Force | Select-Object -First 1)){Remove-Item -LiteralPath $legacyData}
  Write-Host 'Removed obsolete temperature snapshot files from earlier versions.'
 }
 # Move saved preferences out of AppData into the portable folder.
 $legacySettingsFolder=Join-Path ([Environment]::GetFolderPath('ApplicationData')) 'AlexanderSystemDiagnosticTool'
 $legacySettings=Join-Path $legacySettingsFolder 'temperature_tray.json'
 if(Test-Path -LiteralPath $legacySettings){
  foreach($path in $legacySettingsFolder,$legacySettings){
   $item=Get-Item -LiteralPath $path -Force
   if($item.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Refusing a redirected legacy preferences path.'}
  }
  if((Get-Item -LiteralPath $legacySettings).PSIsContainer){throw 'Unexpected legacy preferences directory.'}
  $settings=Join-Path $source 'sensors.settings.json'
  if(!(Test-Path -LiteralPath $settings)){Copy-Item -LiteralPath $legacySettings -Destination $settings}
  Remove-Item -LiteralPath $legacySettings -Force
  if(!(Get-ChildItem -LiteralPath $legacySettingsFolder -Force | Select-Object -First 1)){Remove-Item -LiteralPath $legacySettingsFolder}
  Write-Host 'Preferences are now stored in sensors.settings.json beside the apps.'
 }
 # Run as the consenting user at sign-in, never SYSTEM against a portable executable.
 $action=New-ScheduledTaskAction -Execute $exe -Argument '--reader' -WorkingDirectory $source
 $trigger=New-ScheduledTaskTrigger -AtLogOn -User $StartupUserSid
 $principal=New-ScheduledTaskPrincipal -UserId $StartupUserSid -LogonType Interactive -RunLevel Highest
 $settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 20 -RestartInterval (New-TimeSpan -Minutes 1)
 Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Shares current temperatures in memory for the portable Diagnostic/Sensors apps.' -Force | Out-Null
 Start-ScheduledTask -TaskName $taskName
 Write-Host 'Background ready. Open the EXEs directly from your extracted folder.'
 Write-Host 'No apps copied and no shortcuts created. Keep this folder in place while the task is enabled.'
}catch{
 Write-Host ('Background setup failed: '+$_.Exception.Message) -ForegroundColor Red
 $code=1
 if($_.Exception.Data.Contains('SetupExitCode')){$code=[int]$_.Exception.Data['SetupExitCode']}
 [void](Read-Host 'Press Enter to close this setup error')
 exit $code
}
