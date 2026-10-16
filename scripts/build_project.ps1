$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $project

function Invoke-PythonProbe([string]$Executable,[string]$Prefix=''){
 # Native stderr from an absent launcher runtime is a failed probe, not a build error.
 $process=$null
 try{
  $code="import sys,struct,json,sysconfig; print(json.dumps({'executable':sys.executable,'major':sys.version_info.major,'minor':sys.version_info.minor,'bits':struct.calcsize('P')*8,'implementation':sys.implementation.name,'free_threaded':bool(sysconfig.get_config_var('Py_GIL_DISABLED'))}))"
  $info=[Diagnostics.ProcessStartInfo]::new()
  $info.FileName=$Executable
  $info.Arguments=($Prefix+' -c "'+$code+'"').Trim()
  $info.UseShellExecute=$false;$info.CreateNoWindow=$true
  $info.RedirectStandardOutput=$true;$info.RedirectStandardError=$true
  $process=[Diagnostics.Process]::new();$process.StartInfo=$info
  [void]$process.Start()
  $stdout=$process.StandardOutput.ReadToEndAsync()
  $stderr=$process.StandardError.ReadToEndAsync()
  if(!$process.WaitForExit(10000)){$process.Kill();return $null}
  if($process.ExitCode -ne 0){return $null}
  $result=$stdout.Result.Trim() | ConvertFrom-Json
  if($result.implementation -eq 'cpython' -and $result.major -eq 3 -and $result.minor -ge 11 -and $result.minor -le 14 -and $result.bits -eq 64 -and !$result.free_threaded -and (Test-Path -LiteralPath $result.executable -PathType Leaf)){return $result}
 }catch{return $null}finally{if($process){$process.Dispose()}}
 return $null
}

function Find-Python {
 foreach($name in 'python.exe','python3.exe','py.exe'){
  $command=Get-Command $name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
  if(!$command){continue}
  # Do not launch the Microsoft Store's legacy python execution alias.
  if($name -ne 'py.exe' -and $command.Source -match '\\Microsoft\\WindowsApps\\python(?:3)?\.exe$'){continue}
  $prefix=if($name -eq 'py.exe'){'-3'}else{''}
  $found=Invoke-PythonProbe $command.Source $prefix
  if($found){return $found}
 }
 # PEP 514 registrations also find installations absent from PATH.
 foreach($hive in 'HKCU:','HKLM:'){
  $root=$hive+'\Software\Python'
  foreach($company in @(Get-ChildItem -LiteralPath $root -ErrorAction SilentlyContinue)){
   foreach($tag in @(Get-ChildItem -LiteralPath $company.PSPath -ErrorAction SilentlyContinue | Sort-Object PSChildName -Descending)){
    $key=Join-Path $tag.PSPath 'InstallPath'
    if(!(Test-Path -LiteralPath $key)){continue}
    $value=Get-Item -LiteralPath $key
    $exe=$value.GetValue('ExecutablePath')
    if(!$exe -and $value.GetValue('')){$exe=Join-Path $value.GetValue('') 'python.exe'}
    if($exe){$found=Invoke-PythonProbe $exe;if($found){return $found}}
   }
  }
 }
 # A launcher's default may be unsupported while another compatible version exists.
 $launcher=Get-Command py.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
 if($launcher){foreach($version in '3.14','3.13','3.12','3.11'){
  $found=Invoke-PythonProbe $launcher.Source ('-'+$version)
  if($found){return $found}
 }}
 return $null
}

function Invoke-ReaderSetup([switch]$PrepareBuild,[switch]$RebuildApproved){
 $setup=Join-Path $PSScriptRoot 'setup_background.ps1'
 $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
 $arguments='-NoProfile -ExecutionPolicy Bypass -File "'+$setup+'" -StartupUserSid '+$sid
 if($PrepareBuild){$arguments+=' -PrepareBuild'}
 if($RebuildApproved){$arguments+=' -RebuildApproved'}
 try{$process=Start-Process powershell.exe -Verb RunAs -ArgumentList $arguments -Wait -PassThru}
 catch{throw 'Administrator approval for background configuration was cancelled or failed.'}
 if($process.ExitCode -eq 21){return $false}
 if($process.ExitCode -eq 20){throw 'An existing task could not be identified as this app reader. It was left unchanged; the administrator window shows its owner/action error.'}
 if($process.ExitCode -ne 0){throw 'Background configuration failed. Its exact error was shown in the administrator window. Retry with Install_Sensors_Background.bat after resolving that error.'}
 return $true
}

try{
 $runtime=Find-Python
 if(!$runtime){
  Write-Host 'No compatible Python found (standard CPython 3.11-3.14 x64). Installing Python 3.14...'
  $winget=Get-Command winget.exe -ErrorAction Stop
  & $winget.Source install --id Python.Python.3.14 --exact --source winget --scope user --architecture x64 --accept-source-agreements --accept-package-agreements --disable-interactivity
  if($LASTEXITCODE -notin 0,3010,1641){throw 'Python installation did not complete. Install standard Python 3.14 x64, then retry.'}
  $runtime=Find-Python
  if(!$runtime){throw 'Python could not be located after installation. Reopen the build and retry.'}
 }
 $python=[string]$runtime.executable
 Write-Host ('Using Python '+$runtime.major+'.'+$runtime.minor+' x64: '+$python)
 # Keep environments for different Python versions separate; never delete a user's environment.
 $environment=Join-Path $project ('.venv-'+$runtime.major+'.'+$runtime.minor)
 & $python -m venv $environment
 if($LASTEXITCODE -ne 0){throw 'Could not create the local build environment.'}
 $builder=Join-Path $environment 'Scripts\python.exe'
 & $builder -m pip install -r (Join-Path $project 'requirements-lock.txt')
 if($LASTEXITCODE -ne 0){throw 'Dependency installation failed. See the pip error above.'}
 $existing=Get-ScheduledTask -TaskName 'Diagnostic Sensors Reader' -ErrorAction SilentlyContinue
 $readerRebuildApproved=$false
 if($existing){
  Write-Host 'Pausing the existing temperature reader before rebuilding...'
  if(!(Invoke-ReaderSetup -PrepareBuild)){Write-Host 'Build cancelled. Existing task unchanged.';exit 0}
  $readerRebuildApproved=$true
 }
 & $builder (Join-Path $project 'build.py')
 if($LASTEXITCODE -ne 0){throw 'Build failed. See .build logs.'}
 Write-Host 'Both apps built. Configuring the temperature background reader...'
 if(!(Invoke-ReaderSetup -RebuildApproved:$readerRebuildApproved)){Write-Host 'Apps built. Existing background task kept unchanged.';exit 0}
 Write-Host 'Ready: Diagnostic.exe, Sensors.exe and the temperature background reader.'
}catch{Write-Host ('Build/setup failed: '+$_.Exception.Message) -ForegroundColor Red;Read-Host 'Press Enter to close';exit 1}
