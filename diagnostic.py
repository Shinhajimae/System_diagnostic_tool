import os
import sys

if "--self-test" in sys.argv:
    from hardware_temperatures import TemperatureMonitor
    print("Diagnostic build OK")
    sys.exit(0)
if os.name == "nt":
    import ctypes
    ctypes.windll.kernel32.SetConsoleTitleW("Diagnostic")


while True:

    #System Diagnostic Tool
    #Creator Alexander Atanasov / 2026
    #Edition 1.2.1
    
    #This tool is designed to provide a comprehensive overview of the system's hardware and software configuration.
    #It collects information about the CPU, GPU, memory, motherboard, storage devices, network interfaces,
    #and operating system details.
    #The tool can be used for troubleshooting, performance monitoring, and system audits.
    #//
    
    
    
    
    
    choices = {
        "1": "CPU Information",
        "2": "GPU Information",
        "3": "Memory Information",
        "4": "Motherboard Information",
        "5": "Storage Information",
        "6": "Network Information",
        "7": "Operating System Information",
        "8": "Complete System Overview",
        "9": "Real-Time Monitoring",
        "0": "Exit"
    }
    
    for key, value in choices.items():

        print(f"{key}. {value}")
    
    number = input("\nPlease select an option (0-9): ")
    #//
    
        
    
    
    #CPU Information
    if number == "1":
    
        import platform
        import psutil
        import subprocess
        #|
        cpu_info = platform.processor()
        print(f"CPU Information: {cpu_info}")
    
        cpu_name = subprocess.run(
            ["powershell", "-Command",
             "(Get-CimInstance Win32_Processor).Name"],
            capture_output=True,
            text=True
        )
        print(f"CPU Name: {cpu_name.stdout.strip()}")
    
        cpu_architecture = platform.architecture()
        print(f"CPU Architecture: {cpu_architecture[0]}")
    
        physical_cores = psutil.cpu_count(logical=False)
        logical_cores = psutil.cpu_count(logical=True)
    
        print(f"Physical Cores: {physical_cores}")
        print(f"Logical Cores: {logical_cores}")
    
        cpu_frequency = psutil.cpu_freq()
    
        if cpu_frequency:
            print(f"CPU Frequency: {cpu_frequency.current:.2f} MHz")
        else:
            print("CPU Frequency: Unavailable")
    
        cpu_percentage = psutil.cpu_percent(interval=1)
        print(f"CPU Usage: {cpu_percentage}%")

        try:
            from hardware_temperatures import print_temperatures
            print_temperatures("CPU")

        except Exception as error:
            print("\nTemperatures")
            print(f"CPU Temperature: Unavailable ({error})")
        #//
    
    
    
    
    #GPU Information
    elif number == "2":
    
        import subprocess
        #|
        gpu_info = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_VideoController | "
             "Select-Object -ExpandProperty Name"],
            capture_output=True,
            text=True
        )
        print(f"GPU Information: {gpu_info.stdout.strip()}")
    
        gpu_memory_usage = subprocess.run(
            ["powershell", "-Command",
             "(Get-Counter '\\GPU Local Adapter Memory(*)\\Local Usage').CounterSamples | "
             "Sort-Object CookedValue -Descending | "
             "Select-Object -First 1 -ExpandProperty CookedValue"],
            capture_output=True,
            text=True
        )
    
        try:
            gpu_memory_mb = float(gpu_memory_usage.stdout.strip()) / (1024 ** 2)
            print(f"GPU Memory Usage: {gpu_memory_mb:.2f} MB")
    
        except ValueError:
            print("GPU Memory Usage: Unavailable")
    
        gpu_percentage = subprocess.run(
            ["powershell", "-Command",
             "$gpu = (Get-Counter '\\GPU Engine(*)\\Utilization Percentage').CounterSamples; "
             "($gpu | Measure-Object CookedValue -Maximum).Maximum"],
            capture_output=True,
            text=True
        )
    
        try:
            print(f"GPU Usage: {float(gpu_percentage.stdout.strip()):.2f}%")
    
        except ValueError:
            print("GPU Usage: Unavailable")
    
        gpu_driver_version = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_VideoController | "
             "Select-Object -ExpandProperty DriverVersion"],
            capture_output=True,
            text=True
        )
        print(f"GPU Driver Version: {gpu_driver_version.stdout.strip()}")

        try:
            from hardware_temperatures import print_temperatures
            print_temperatures("GPU")

        except Exception as error:
            print("\nTemperatures")
            print(f"GPU Temperature: Unavailable ({error})")
        #//
    
    
    
    
    #Memory Information
    elif number == "3":
    
        import psutil
        import subprocess
        #|
        memory_manufacturer = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_PhysicalMemory | "
             "Select-Object -First 1 -ExpandProperty Manufacturer"],
            capture_output=True,
            text=True
        )
    
        manufacturer = memory_manufacturer.stdout.strip()
    
        if not manufacturer:
            manufacturer = "Unknown"
    
        print(f"Memory Manufacturer: {manufacturer}")
    
        memory_modules = subprocess.run(
            ["powershell", "-Command",
             "(Get-CimInstance Win32_PhysicalMemory).Count"],
            capture_output=True,
            text=True
        )
        print(f"Memory Modules: {memory_modules.stdout.strip()}")
    
        memory_total = subprocess.run(
            ["powershell", "-Command",
             "(Get-CimInstance Win32_PhysicalMemory | "
             "Measure-Object -Property Capacity -Sum).Sum"],
            capture_output=True,
            text=True
        )
    
        try:
            memory_total_gb = int(memory_total.stdout.strip()) / (1024 ** 3)
            print(f"Total Memory: {memory_total_gb:.2f} GB")
    
        except ValueError:
            print("Total Memory: Unavailable")
    
        #ConfiguredClockSpeed shows the configured RAM speed,
        #including an enabled XMP/EXPO profile when reported by the system.
        memory_speed = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_PhysicalMemory | "
             "Select-Object -First 1 -ExpandProperty ConfiguredClockSpeed"],
            capture_output=True,
            text=True
        )
        print(f"Memory Speed: {memory_speed.stdout.strip()} MHz")
    
        memory = psutil.virtual_memory()
    
        print(f"Memory Used: {memory.used / (1024 ** 3):.2f} GB")
        print(f"Memory Available: {memory.available / (1024 ** 3):.2f} GB")
        print(f"Memory Usage: {memory.percent}%")

        try:
            from hardware_temperatures import print_temperatures
            print_temperatures("Memory")

        except Exception as error:
            print("\nTemperatures")
            print(f"Memory Temperature: Unavailable ({error})")
        #//
    
    
    
    
    
    #Motherboard Information
    elif number == "4":
    
        import subprocess
        #|
        motherboard_manufacturer = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_BaseBoard | "
             "Select-Object -ExpandProperty Manufacturer"],
            capture_output=True,
            text=True
        )
        print(f"Motherboard Manufacturer: {motherboard_manufacturer.stdout.strip()}")
    
        motherboard_model = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_BaseBoard | "
             "Select-Object -ExpandProperty Product"],
            capture_output=True,
            text=True
        )
        print(f"Motherboard Model: {motherboard_model.stdout.strip()}")
    
        motherboard_serial_number = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_BaseBoard | "
             "Select-Object -ExpandProperty SerialNumber"],
            capture_output=True,
            text=True
        )
        print(f"Motherboard Serial Number: {motherboard_serial_number.stdout.strip()}")
    
        motherboard_version = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_BaseBoard | "
             "Select-Object -ExpandProperty Version"],
            capture_output=True,
            text=True
        )
    
        version = motherboard_version.stdout.strip()
    
        if not version or version.lower() == "default string":
            version = "Unknown"
    
        print(f"Motherboard Version: {version}")
    
        bios_version = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_BIOS | "
             "Select-Object -ExpandProperty SMBIOSBIOSVersion"],
            capture_output=True,
            text=True
        )
        print(f"BIOS Version: {bios_version.stdout.strip()}")
    
        bios_manufacturer = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_BIOS | "
             "Select-Object -ExpandProperty Manufacturer"],
            capture_output=True,
            text=True
        )
        print(f"BIOS Manufacturer: {bios_manufacturer.stdout.strip()}")

        try:
            from hardware_temperatures import print_temperatures
            print_temperatures("Motherboard")

        except Exception as error:
            print("\nTemperatures")
            print(f"Motherboard Temperature: Unavailable ({error})")
         #//
    
    
    
    
    #Storage Information
    elif number == "5":
    
        import subprocess
        import json
        #|
        storage_devices = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_DiskDrive | "
             "Select-Object Manufacturer, Model, SerialNumber, Size, InterfaceType, MediaType, Status | "
             "ConvertTo-Json"],
            capture_output=True,
            text=True
        )
    
        try:
            devices = json.loads(storage_devices.stdout)
    
        except json.JSONDecodeError:
            devices = []
            print("Storage device information is unavailable.")
    
        #Convert single device to a list if only one storage device exists
        if isinstance(devices, dict):
            devices = [devices]
    
        for number, device in enumerate(devices, start=1):
    
            print(f"\nStorage Device {number}")
            print(f"Manufacturer: {device['Manufacturer']}")
            print(f"Model: {device['Model']}")
            print(f"Serial Number: {device['SerialNumber']}")
            if device["Size"]:
                print(f"Size: {int(device['Size']) / (1024 ** 3):.2f} GB")
            else:
                print("Size: Unknown")
            print(f"Interface Type: {device['InterfaceType']}")
            print(f"Media Type: {device['MediaType']}")
            print(f"Status: {device['Status']}")
    
        logical_drives = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_LogicalDisk | "
             "Where-Object { $_.DriveType -eq 3 } | "
             "Select-Object DeviceID, Size, FreeSpace | "
             "ConvertTo-Json"],
            capture_output=True,
            text=True
        )
    
        try:
            drives = json.loads(logical_drives.stdout)
    
        except json.JSONDecodeError:
            drives = []
            print("Logical drive information is unavailable.")
    
        #Convert single drive to a list if only one logical drive exists
        if isinstance(drives, dict):
            drives = [drives]
    
        print("\nLogical Drives")
    
        for drive in drives:
    
            total_bytes = int(drive["Size"])
            available_bytes = int(drive["FreeSpace"])
            used_bytes = total_bytes - available_bytes
            usage = (used_bytes / total_bytes) * 100
    
            print(f"\nDrive {drive['DeviceID']}")
            print(f"Total Space: {total_bytes / (1024 ** 3):.2f} GB")
            print(f"Used Space: {used_bytes / (1024 ** 3):.2f} GB")
            print(f"Available Space: {available_bytes / (1024 ** 3):.2f} GB")
            print(f"Usage: {usage:.1f}%")

        try:
            from hardware_temperatures import print_temperatures
            print_temperatures("Storage")

        except Exception as error:
            print("\nTemperatures")
            print(f"Storage Temperature: Unavailable ({error})")
        #//
    
    
    
    
    #Network Information
    elif number == "6":
    
        import subprocess
        import json
        #|
        network_interfaces = subprocess.run(
            ["powershell", "-Command",
             "Get-NetAdapter | "
             "Where-Object { $_.Status -eq 'Up' } | "
             "Select-Object Name, Status, MacAddress, LinkSpeed | "
             "ConvertTo-Json"],
            capture_output=True,
            text=True
        )
    
        try:
            interfaces = json.loads(network_interfaces.stdout)
    
        except json.JSONDecodeError:
            interfaces = []
            print("Network interface information is unavailable.")
    
        #Convert single interface to a list if only one interface exists
        if isinstance(interfaces, dict):
            interfaces = [interfaces]
    
        for interface in interfaces:
    
            interface_name = interface["Name"]
    
            #Apostrophes must be escaped before using the name in PowerShell.
            powershell_interface_name = interface_name.replace("'", "''")
    
            print(f"\nNetwork Interface: {interface_name}")
            print(f"Status: {interface['Status']}")
            print(f"MAC Address: {interface['MacAddress']}")
            print(f"Link Speed: {interface['LinkSpeed']}")
    
            #IPv4 Address
            network_ipv4 = subprocess.run(
                ["powershell", "-Command",
                 f"Get-NetIPAddress -InterfaceAlias '{powershell_interface_name}' "
                 "-AddressFamily IPv4 | "
                 "Where-Object { $_.IPAddress -notlike '169.254.*' } | "
                 "Select-Object -First 1 -ExpandProperty IPAddress"],
                capture_output=True,
                text=True
            )
    
            ipv4 = network_ipv4.stdout.strip()
    
            if not ipv4:
                ipv4 = "Unknown"
    
            print(f"IPv4 Address: {ipv4}")
    
            #Default Gateway
            network_gateway = subprocess.run(
                ["powershell", "-Command",
                 f"(Get-NetIPConfiguration -InterfaceAlias '{powershell_interface_name}')."
                 "IPv4DefaultGateway.NextHop"],
                capture_output=True,
                text=True
            )
    
            gateway = network_gateway.stdout.strip()
    
            if not gateway:
                gateway = "Unknown"
    
            print(f"Default Gateway: {gateway}")
    
            #DNS Servers
            network_dns = subprocess.run(
                ["powershell", "-Command",
                 f"(Get-DnsClientServerAddress -InterfaceAlias '{powershell_interface_name}' "
                 "-AddressFamily IPv4).ServerAddresses -join ', '"],
                capture_output=True,
                text=True
            )
    
            dns = network_dns.stdout.strip()
    
            if not dns:
                dns = "Unknown"
    
            print(f"DNS Servers: {dns}")
    
            #Network Statistics
            network_statistics = subprocess.run(
                ["powershell", "-Command",
                 f"Get-NetAdapterStatistics -Name '{powershell_interface_name}' | "
                 "Select-Object ReceivedBytes, SentBytes | "
                 "ConvertTo-Json"],
                capture_output=True,
                text=True
            )
    
            try:
                statistics = json.loads(network_statistics.stdout)
    
                received_bytes = int(statistics["ReceivedBytes"])
                sent_bytes = int(statistics["SentBytes"])
    
                print(f"Data Received: {received_bytes / (1024 ** 3):.2f} GB")
                print(f"Data Sent: {sent_bytes / (1024 ** 3):.2f} GB")
    
            except (json.JSONDecodeError, TypeError, ValueError):
                print("Network Statistics: Unavailable")
        #//
    
    
    
    
    #Operating System Information
    elif number == "7":
    
        import subprocess
        import json
        #|
    
        operating_system = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_OperatingSystem | "
             "Select-Object Caption, Version, BuildNumber, OSArchitecture, "
             "SerialNumber, BuildType, InstallDate, Locale | "
             "ConvertTo-Json"],
            capture_output=True,
            text=True
        )
    
        try:
            os_info = json.loads(operating_system.stdout)
    
        except json.JSONDecodeError:
            print("Operating system information is unavailable.")
            exit()
    
        print("\nOperating System Information")
    
        print(f"Operating System: {os_info['Caption']}")
        print(f"Version: {os_info['Version']}")
        print(f"Build Number: {os_info['BuildNumber']}")
        print(f"Architecture: {os_info['OSArchitecture']}")
        print(f"Serial Number: {os_info['SerialNumber']}")
        print(f"Build Type: {os_info['BuildType']}")
        print(f"Install Date: {os_info['InstallDate']}")
        print(f"Locale: {os_info['Locale']}")
    
        operating_system_boot_time = subprocess.run(
            ["powershell", "-Command",
             "(Get-CimInstance Win32_OperatingSystem).LastBootUpTime"],
            capture_output=True,
            text=True
        )
    
        print(f"Last Boot Up Time: {operating_system_boot_time.stdout.strip()}")
    
        operating_system_uptime = subprocess.run(
            ["powershell", "-Command",
             "$uptime = (Get-Date) - "
             "(Get-CimInstance Win32_OperatingSystem).LastBootUpTime; "
             "\"$($uptime.Days) days, "
             "$($uptime.Hours) hours, "
             "$($uptime.Minutes) minutes\""],
            capture_output=True,
            text=True
        )
    
        print(f"Uptime: {operating_system_uptime.stdout.strip()}")
        #//
    
    
    
    #Complete System Overview
    elif number == "8":
    
        import subprocess
        import json
        import psutil
        #|
    
        print("\nComplete System Overview")
    
        #Computer Name
        computer_name = subprocess.run(
            ["powershell", "-Command",
             "$env:COMPUTERNAME"],
            capture_output=True,
            text=True
        )
    
        print(f"Computer Name: {computer_name.stdout.strip()}")
    
        #Operating System
        operating_system = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_OperatingSystem | "
             "Select-Object Caption, BuildNumber, OSArchitecture | "
             "ConvertTo-Json"],
            capture_output=True,
            text=True
        )
    
        try:
            os_info = json.loads(operating_system.stdout)
    
        except json.JSONDecodeError:
            print("Operating system information is unavailable.")
            exit()
    
        print(f"Operating System: {os_info['Caption']}")
        print(f"Windows Build: {os_info['BuildNumber']}")
        print(f"System Architecture: {os_info['OSArchitecture']}")
    
        print("\nCPU")
    
        #CPU Name
        cpu_name = subprocess.run(
            ["powershell", "-Command",
             "(Get-CimInstance Win32_Processor).Name"],
            capture_output=True,
            text=True
        )
    
        print(f"CPU: {cpu_name.stdout.strip()}")
    
        physical_cores = psutil.cpu_count(logical=False)
        logical_cores = psutil.cpu_count(logical=True)
    
        print(f"Physical Cores: {physical_cores}")
        print(f"Logical Cores: {logical_cores}")
    
        cpu_frequency = psutil.cpu_freq()
    
        if cpu_frequency:
            print(f"Current CPU Frequency: {cpu_frequency.current:.2f} MHz")
    
        print("\nGPU")
    
        #GPU Name
        gpu_name = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_VideoController | "
             "Select-Object -ExpandProperty Name"],
            capture_output=True,
            text=True
        )
    
        print(f"GPU: {gpu_name.stdout.strip()}")
    
        print("\nMemory")
    
        #RAM Information
        memory_info = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_PhysicalMemory | "
             "Select-Object Manufacturer, Capacity, ConfiguredClockSpeed | "
             "ConvertTo-Json"],
            capture_output=True,
            text=True
        )
    
        try:
            memory_modules = json.loads(memory_info.stdout)
    
        except json.JSONDecodeError:
            memory_modules = []
            print("RAM information is unavailable.")
    
        if isinstance(memory_modules, dict):
            memory_modules = [memory_modules]
    
        total_memory = 0
    
        for module in memory_modules:
            total_memory += int(module["Capacity"])
    
        print(f"RAM: {total_memory / (1024 ** 3):.2f} GB")
    
        if memory_modules:
            print(f"RAM Manufacturer: {memory_modules[0]['Manufacturer']}")
            print(f"RAM Speed: {memory_modules[0]['ConfiguredClockSpeed']} MHz")
            print(f"RAM Modules: {len(memory_modules)}")
    
        print("\nMotherboard")
    
        #Motherboard
        motherboard = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_BaseBoard | "
             "Select-Object Manufacturer, Product | "
             "ConvertTo-Json"],
            capture_output=True,
            text=True
        )
    
        try:
            motherboard_info = json.loads(motherboard.stdout)
    
            print(f"Manufacturer: {motherboard_info['Manufacturer']}")
            print(f"Model: {motherboard_info['Product']}")
    
        except json.JSONDecodeError:
            print("Motherboard information is unavailable.")
    
        #BIOS
        bios_version = subprocess.run(
            ["powershell", "-Command",
             "(Get-CimInstance Win32_BIOS).SMBIOSBIOSVersion"],
            capture_output=True,
            text=True
        )
    
        print(f"BIOS Version: {bios_version.stdout.strip()}")
    
        print("\nStorage")
    
        #Storage Devices
        storage_devices = subprocess.run(
            ["powershell", "-Command",
             "Get-CimInstance Win32_DiskDrive | "
             "Select-Object Model, Size, MediaType | "
             "ConvertTo-Json"],
            capture_output=True,
            text=True
        )
    
        try:
            devices = json.loads(storage_devices.stdout)
    
        except json.JSONDecodeError:
            devices = []
            print("Storage device information is unavailable.")
    
        if isinstance(devices, dict):
            devices = [devices]
    
        for device_number, device in enumerate(devices, start=1):
    
            size_gb = int(device["Size"]) / (1024 ** 3)
    
            print(
                f"Storage {device_number}: "
                f"{device['Model']} - "
                f"{size_gb:.2f} GB"
            )

        try:
            from hardware_temperatures import print_temperatures
            print_temperatures()

        except Exception as error:
            print("\nTemperatures")
            print(f"Hardware Temperatures: Unavailable ({error})")

        print("\nSystem Runtime")
    
        #Boot Time
        boot_time = subprocess.run(
            ["powershell", "-Command",
             "(Get-CimInstance Win32_OperatingSystem).LastBootUpTime"],
            capture_output=True,
            text=True
        )
    
        print(f"Last Boot Up Time: {boot_time.stdout.strip()}")
    
        #Uptime
        uptime = subprocess.run(
            ["powershell", "-Command",
             "$uptime = (Get-Date) - "
             "(Get-CimInstance Win32_OperatingSystem).LastBootUpTime; "
             "\"$($uptime.Days) days, "
             "$($uptime.Hours) hours, "
             "$($uptime.Minutes) minutes\""],
            capture_output=True,
            text=True
        )
    
        print(f"System Uptime: {uptime.stdout.strip()}")
        #//
    
    
    
    
    #Realtime Monitoring
    elif number == "9":
    
        import psutil
        import subprocess
        import time
        import os
        import re
        #|
        #Temperature Sensors
        try:
            from hardware_temperatures import TemperatureMonitor

            temperature_monitor = TemperatureMonitor()
            temperature_error = None

        except Exception as error:
            temperature_monitor = None
            temperature_error = str(error)

        #Initial Network Statistics
        previous_network = psutil.net_io_counters()
        previous_received = previous_network.bytes_recv
        previous_sent = previous_network.bytes_sent
    
        #Initial Disk Statistics
        previous_disk = psutil.disk_io_counters()
        if previous_disk:
            previous_disk_read = previous_disk.read_bytes
            previous_disk_write = previous_disk.write_bytes
        else:
            previous_disk_read = 0
            previous_disk_write = 0
    
        try:
    
            while True:
    
                #CPU
                cpu_usage = psutil.cpu_percent(interval=1)
                cpu_frequency = psutil.cpu_freq()
    
                per_core_usage = psutil.cpu_percent(
                    interval=None,
                    percpu=True
                )
    
                #Memory
                memory = psutil.virtual_memory()
    
                #Storage - All Fixed Drives
                drives = []
    
                for partition in psutil.disk_partitions():
    
                    if "fixed" in partition.opts:
    
                        try:
    
                            drive_usage = psutil.disk_usage(
                                partition.mountpoint
                            )
    
                            drives.append(
                                (
                                    partition.device,
                                    drive_usage.percent,
                                    drive_usage.used,
                                    drive_usage.free,
                                    drive_usage.total
                                )
                            )
    
                        except PermissionError:
                            pass
    
                #Disk Read / Write Speed
                current_disk = psutil.disk_io_counters()
    
                if current_disk:
                    disk_read_speed = (
                        current_disk.read_bytes
                        - previous_disk_read
                    ) / (1024 ** 2)
    
                    disk_write_speed = (
                        current_disk.write_bytes
                        - previous_disk_write
                    ) / (1024 ** 2)
    
                    previous_disk_read = current_disk.read_bytes
                    previous_disk_write = current_disk.write_bytes
    
                else:
                    disk_read_speed = 0.0
                    disk_write_speed = 0.0
    
                #Network
                current_network = psutil.net_io_counters()
    
                download_speed = (
                    current_network.bytes_recv
                    - previous_received
                ) / (1024 ** 2)
    
                upload_speed = (
                    current_network.bytes_sent
                    - previous_sent
                ) / (1024 ** 2)
    
                previous_received = current_network.bytes_recv
                previous_sent = current_network.bytes_sent
    
                #Internet Latency
                internet_ping = subprocess.run(
                    [
                        "ping",
                        "-n", "1",
                        "-w", "1000",
                        "1.1.1.1"
                    ],
                    capture_output=True,
                    text=True
                )
    
                latency_match = re.search(
                    r"(?:time|zeit)[=<]\s*(\d+)ms",
                    internet_ping.stdout,
                    re.IGNORECASE
                )
    
                if latency_match:
                    latency = f"{latency_match.group(1)} ms"
                else:
                    latency = "Unavailable"
    
                #GPU Usage
                gpu_usage = subprocess.run(
                    [
                        "powershell",
                        "-Command",
                        "$gpu = (Get-Counter "
                        "'\\GPU Engine(*)\\Utilization Percentage')."
                        "CounterSamples; "
                        "($gpu | Measure-Object "
                        "CookedValue -Maximum).Maximum"
                    ],
                    capture_output=True,
                    text=True
                )
    
                try:
                    gpu_percentage = float(
                        gpu_usage.stdout.strip()
                    )
    
                except ValueError:
                    gpu_percentage = 0.0
    
                #GPU Memory
                gpu_memory = subprocess.run(
                    [
                        "powershell",
                        "-Command",
                        "(Get-Counter "
                        "'\\GPU Local Adapter Memory(*)\\Local Usage')."
                        "CounterSamples | "
                        "Sort-Object CookedValue -Descending | "
                        "Select-Object -First 1 "
                        "-ExpandProperty CookedValue"
                    ],
                    capture_output=True,
                    text=True
                )
    
                try:
                    gpu_memory_mb = (
                        float(gpu_memory.stdout.strip())
                        / (1024 ** 2)
                    )
    
                except ValueError:
                    gpu_memory_mb = 0.0
    
                #Running Processes
                process_count = len(psutil.pids())
    
                #Top 5 Processes by Memory Usage
                processes = []
    
                for process in psutil.process_iter(
                    ["pid", "name", "memory_info"]
                ):
    
                    try:
                        process_memory = (
                            process.info["memory_info"].rss
                            / (1024 ** 2)
                        )
    
                        processes.append(
                            (
                                process.info["pid"],
                                process.info["name"],
                                process_memory
                            )
                        )
    
                    except (
                        psutil.NoSuchProcess,
                        psutil.AccessDenied,
                        AttributeError
                    ):
                        pass
    
                top_processes = sorted(
                    processes,
                    key=lambda process: process[2],
                    reverse=True
                )[:5]

                #Hardware Temperatures
                if temperature_monitor:

                    try:
                        temperatures = temperature_monitor.read_temperatures()
                        temperature_error = None

                    except Exception as error:
                        temperatures = []
                        temperature_error = str(error)

                else:
                    temperatures = []

                temperatures_by_category = {
                    "CPU": [],
                    "GPU": [],
                    "Memory": [],
                    "Storage": [],
                    "Motherboard": []
                }

                for temperature in temperatures:
                    if temperature.category in temperatures_by_category:
                        temperatures_by_category[temperature.category].append(
                            temperature
                        )

                def print_category_temperatures(category):
                    category_temperatures = temperatures_by_category[category]

                    if category_temperatures:
                        for temperature in category_temperatures:
                            print(
                                f"Temperature | "
                                f"{temperature.hardware_name} | "
                                f"{temperature.sensor_name}: "
                                f"{temperature.value:.1f} °C"
                            )
                    else:
                        print("Temperature Sensors: Unavailable")
    
                #System Uptime
                uptime_seconds = int(
                    time.time() - psutil.boot_time()
                )
    
                uptime_days = uptime_seconds // 86400
                uptime_hours = (uptime_seconds % 86400) // 3600
                uptime_minutes = (uptime_seconds % 3600) // 60
    
                #Clear Terminal
                os.system("cls")
    
                print("Real-Time System Monitoring")
                print(
                    f"Updated: "
                    f"{time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
    
                #CPU
                print("\nCPU")
    
                print(f"CPU Usage: {cpu_usage}%")
    
                if cpu_frequency:
    
                    print(
                        f"CPU Frequency: "
                        f"{cpu_frequency.current:.2f} MHz"
                    )
    
                core_information = []
    
                for core_number, core_usage in enumerate(
                    per_core_usage,
                    start=1
                ):
    
                    core_information.append(
                        f"Core {core_number}: {core_usage}%"
                    )
    
                print(" | ".join(core_information))

                print_category_temperatures("CPU")
    
                #GPU
                print("\nGPU")
    
                print(
                    f"GPU Usage: "
                    f"{gpu_percentage:.2f}%"
                )
    
                print(
                    f"GPU Memory Usage: "
                    f"{gpu_memory_mb:.2f} MB"
                )

                print_category_temperatures("GPU")
    
                #Memory
                print("\nMemory")
    
                print(
                    f"Memory Usage: "
                    f"{memory.percent}%"
                )
    
                print(
                    f"Memory Used: "
                    f"{memory.used / (1024 ** 3):.2f} GB"
                )
    
                print(
                    f"Memory Available: "
                    f"{memory.available / (1024 ** 3):.2f} GB"
                )

                print_category_temperatures("Memory")
    
                #Storage
                print("\nStorage")
    
                for drive, usage, used, free, total in drives:
    
                    print(
                        f"{drive} "
                        f"{usage}% Used | "
                        f"{used / (1024 ** 3):.2f} GB Used | "
                        f"{free / (1024 ** 3):.2f} GB Free | "
                        f"{total / (1024 ** 3):.2f} GB Total"
                    )
    
                print(
                    f"Disk Read: "
                    f"{disk_read_speed:.2f} MB/s"
                )
    
                print(
                    f"Disk Write: "
                    f"{disk_write_speed:.2f} MB/s"
                )

                print_category_temperatures("Storage")

                #Motherboard
                print("\nMotherboard")

                print_category_temperatures("Motherboard")

                if temperature_error:
                    print(f"Sensor Error: {temperature_error}")
    
                #Network
                print("\nNetwork")
    
                print(
                    f"Download Speed: "
                    f"{download_speed:.2f} MB/s"
                )
    
                print(
                    f"Upload Speed: "
                    f"{upload_speed:.2f} MB/s"
                )
    
                print(
                    f"Internet Latency: "
                    f"{latency}"
                )
    
                #Processes
                print("\nProcesses")
    
                print(
                    f"Running Processes: "
                    f"{process_count}"
                )
    
                print("Top 5 Processes by Memory:")
    
                for process_id, process_name, process_memory in top_processes:
    
                    print(
                        f"{process_name} "
                        f"(PID {process_id}): "
                        f"{process_memory:.2f} MB"
                    )
    
                #Runtime
                print("\nRuntime")
    
                print(
                    f"System Uptime: "
                    f"{uptime_days} days, "
                    f"{uptime_hours} hours, "
                    f"{uptime_minutes} minutes"
                )
    
                print("\nPress Ctrl+C to return.")
    
        except KeyboardInterrupt:

            print("\nReturning to the main menu.")

            if temperature_monitor:
                temperature_monitor.close()
        #//
    elif number == "0":
    
        print("Exiting the program.")
        break
    
    
    elif number not in choices:
    
        print("Invalid selection. Please choose a number between 0 and 9.")
    
    
    #Return to the menu after the selected option is finished.
    input("\nPress Enter to return to the menu...")
    os.system("cls")
