# Diagnostic and Sensors

Copyright (c) 2026 Alexander Atanasov. Licensed under the MIT License; see LICENSE.

Two portable Windows applications:
- **Diagnostic**: hardware information, system overview and monitoring.
- **Sensors**: tray temperatures for supported CPU, GPU, RAM, motherboard and drives.

## Build and run

Extract the entire project folder and run **build_exe.bat**.
The batch calls `scripts/build_project.ps1`, which detects an installed standard
CPython 3.11-3.14 x64 (including Python 3.14). It installs Python 3.14 through
WinGet only if no compatible interpreter is found, creates a local versioned `.venv-*`, installs
the pinned dependencies and runs `build.py`. After a successful build, it
automatically launches temperature background setup and requests administrator approval.
Internet access is required for missing Python or dependencies.

The build creates **Diagnostic.exe** and **Sensors.exe** in this folder.
Open either EXE directly. There is no installer EXE, Program Files copy,
Start menu shortcut or nested application archive.
Build files stay in `.venv-*/` and `.build/`; Python is unnecessary for running
the resulting EXEs on another compatible Windows PC.

## Temperature background reader

Protected hardware readings require an elevated reader and PawnIO.
The build configures this automatically after creating both apps.
Use **Install_Sensors_Background.bat** to retry setup or configure it again later.
It asks before installing PawnIO through WinGet if missing, and registers
a task that runs this folder's `Sensors.exe --reader` at your sign-in.
It starts the reader immediately as well. No third executable is created.
Setup requires your own administrator account and approval.

The reader shares only the current temperatures through Windows shared memory.
It creates no temperature snapshot files or temperature history. Both apps read
the live memory channel without normal administrator prompts.
Readings depend on hardware and monitoring-library support; not every PC
exposes RAM, motherboard or drive temperature sensors.
Choose tray-app startup yourself from the Sensors menu.

## Sensors settings

The white settings window groups sensors by component and aligns temperature
values on the right. Check all / Uncheck all changes the selection and count.
Apply saves your choices and updates the tray icons while settings stays open.
Start with Windows is also available in this window; Apply saves that choice.
It controls the same sign-in setting as the tray menu.
Exit (or the window close button) closes settings; Sensors continues in the tray
with the last applied choices. Unapplied changes are discarded.
Use Exit All from a tray icon to quit Sensors completely.

Keep this folder in place while the task is enabled. Before moving it,
remove the background task and configure it again from the new location.
Before rebuilding, close both visible apps. The build automatically pauses its
existing background reader, then updates and restarts its task after building.
When the task exists, setup asks once whether to rebuild it for this folder:
Y plus Enter updates and restarts it; N plus Enter leaves it unchanged and
cancels a pending app rebuild to avoid replacing a running reader executable.
No manual task uninstall is needed.
Windows may request administrator approval for pausing and configuring the task.

## Remove optional components

Run **uninstall_exe.bat**. It asks separately about removing the background
task, Python 3.12 and PawnIO. Type **Y** or **N**, then press Enter for each.
Other programs may need Python or PawnIO. App files and tray startup
preferences are kept; disable tray startup before deleting the folder.
Earlier installed copies and shortcuts are not removed by this release.

## Project files

- `diagnostic.py`, `sensors.py`: application entry points.
- `hardware_temperatures.py`, `sensor_broker.py`: sensor access and snapshots.
- `build_exe.bat`, `build.py`: executable build entry points.
- `scripts/`: build, optional background/driver and removal helpers.
- `requirements*.txt`: runtime and build dependency specifications.
- `terminal.ico`, `terminal.png`, `terminal.svg`: shared app icon assets.
- `LICENSE`: project MIT license.
- `THIRD_PARTY_NOTICES.md`, `licenses/`: dependency notices and licenses.

## Files, startup and network activity

- Your selected sensors and appearance are saved only when you press Apply,
  or when first sign-in startup needs to choose default sensors, in
  `sensors.settings.json` beside the app. There are no new AppData preferences.
- Background setup registers one task, `Diagnostic Sensors Reader`, for your
  sign-in with highest privileges. It starts immediately and reads temperatures
  about every two seconds. It can restart after failure and runs on battery.
- Start with Windows adds/removes one per-user Run registry value named Sensors.
  This is your choice in settings or the tray menu; the build does not enable it.
- The build detects Python, installs Python 3.14 via WinGet only if none of the
  supported runtimes is present, and installs pinned packages into `.venv-*`.
  `.build/` contains build intermediates, caches, temporary files and build logs.
  pip, WinGet and their installers may also keep their usual caches or logs.
- PawnIO is a separate Windows driver installation. Setup asks before installing
  it if missing; existing installations are reused. It is not a portable file.
- One-file PyInstaller EXEs unpack bundled runtime files into a temporary `_MEI*`
  directory while running. This is normally cleaned on exit, but a crash may
  leave temporary files. Source execution can create `__pycache__/` files.
- Our application code has no telemetry, uploads, network listener or automatic
  app updater. Dependency downloads use pip/WinGet and access the internet;
  third-party installers can create their own normal installation artifacts.
- No app copies are made into Program Files and no shortcuts are created.
- Setup removes only legacy `temperatures.json`/`temperatures.tmp` files in
  `%ProgramData%/Diagnostic/` and removes that directory only if empty. It moves
  old AppData preferences into this folder if no portable preferences exist,
  then removes the obsolete preference file and its old directory if empty.
  Existing portable preferences take priority. Unrelated files are retained.
- Previous Program Files copies and Start menu shortcuts are not removed.
  The uninstaller leaves project files, local build environments, build logs,
  portable preferences and your tray startup choice in place. Its Python choice
  specifically targets Python 3.12; it does not remove your detected Python 3.14.

Generated executables and local build files are excluded by `.gitignore`.
Keep license and third-party notices with distributed releases.
