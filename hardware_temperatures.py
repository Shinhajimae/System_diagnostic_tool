"""Temperature sensor access for the System Diagnostic Tool.

This separate module keeps the main beginner-friendly menu file readable.
It uses the HardwareMonitor Python package, which wraps Libre Hardware Monitor.
"""

from dataclasses import dataclass
import math


@dataclass
class TemperatureReading:
    sensor_id: str
    hardware_id: str
    category: str
    hardware_name: str
    sensor_name: str
    value: float


class LocalTemperatureMonitor:
    """Open the supported hardware sensors and read temperature values."""

    def __init__(self):
        self.errors = []
        try:
            from HardwareMonitor.Util import (
                HardwareTypeString,
                OpenComputer,
                SensorTypeString
            )
        except ImportError as error:
            raise RuntimeError(
                "HardwareMonitor is not installed. Run build_exe.bat again."
            ) from error

        self.computer = OpenComputer(
            all=True
        )
        self.hardware_type_names = HardwareTypeString
        self.sensor_type_names = SensorTypeString

    def _category(self, hardware_type):
        hardware_type = self.hardware_type_names.get(
            hardware_type,
            str(hardware_type)
        ).lower()

        if "cpu" in hardware_type:
            return "CPU"
        if "gpu" in hardware_type:
            return "GPU"
        if "storage" in hardware_type:
            return "Storage"
        if "motherboard" in hardware_type or "superio" in hardware_type:
            return "Motherboard"
        if "memory" in hardware_type:
            return "Memory"

        return "Other"

    def _collect_hardware(self, hardware, parent_category=None):
        readings = []
        category = parent_category or self._category(hardware.HardwareType)

        try:
            hardware.Update()
        except Exception as error:
            self.errors.append(f"{hardware.Name}: {error}")
            return readings

        for sensor in hardware.Sensors:
            sensor_type = self.sensor_type_names.get(
                sensor.SensorType,
                str(sensor.SensorType)
            ).lower()
            sensor_name = str(sensor.Name)
            sensor_name_lower = sensor_name.lower()

            if "temperature" not in sensor_type or sensor.Value is None:
                continue

            #Libre Hardware Monitor also exposes temperature limits as
            #temperature-type sensors. These are not live readings.
            excluded_names = (
                "warning",
                "critical",
                "threshold",
                "limit"
            )

            if any(name in sensor_name_lower for name in excluded_names):
                continue

            try:
                value = float(sensor.Value)
            except (TypeError, ValueError):
                continue

            #Zero and impossible values are normally unavailable sensors.
            if not math.isfinite(value) or value <= 0 or value > 150:
                continue

            hardware_id = str(hardware.Identifier)
            sensor_id = str(sensor.Identifier)

            readings.append(
                TemperatureReading(
                    sensor_id=sensor_id,
                    hardware_id=hardware_id,
                    category=category,
                    hardware_name=str(hardware.Name),
                    sensor_name=sensor_name,
                    value=value
                )
            )

        for sub_hardware in hardware.SubHardware:
            readings.extend(
                self._collect_hardware(sub_hardware, category)
            )

        return readings

    def read_temperatures(self):
        """Return every valid temperature currently exposed by the system."""
        self.errors = []
        readings = []

        for hardware in self.computer.Hardware:
            readings.extend(self._collect_hardware(hardware))

        return readings

    def default_sensor_ids(self, readings):
        """Choose useful defaults: CPU, GPU, motherboard, and each drive."""
        chosen = []

        for category in ("CPU", "GPU", "Memory", "Motherboard"):
            category_readings = [
                reading for reading in readings
                if reading.category == category
            ]

            preferred_names = {
                "CPU": ("package", "tctl", "tdie", "core max"),
                "GPU": ("core", "hot spot"),
                "Memory": ("temperature",),
                "Motherboard": ("motherboard", "system")
            }

            selected = None

            for preferred_name in preferred_names[category]:
                selected = next(
                    (
                        reading for reading in category_readings
                        if preferred_name in reading.sensor_name.lower()
                    ),
                    None
                )

                if selected:
                    break

            if not selected and category_readings:
                selected = category_readings[0]

            if selected:
                chosen.append(selected.sensor_id)

        #Select one temperature for every detected storage device.
        storage_hardware = set()

        for reading in readings:
            if (
                reading.category == "Storage"
                and reading.hardware_id not in storage_hardware
            ):
                chosen.append(reading.sensor_id)
                storage_hardware.add(reading.hardware_id)

        #Put motherboard after the storage devices in the tray.
        motherboard_ids = [
            sensor_id for sensor_id in chosen
            if any(
                reading.sensor_id == sensor_id
                and reading.category == "Motherboard"
                for reading in readings
            )
        ]
        chosen = [
            sensor_id for sensor_id in chosen
            if sensor_id not in motherboard_ids
        ]
        chosen.extend(motherboard_ids)

        return chosen

    def close(self):
        self.computer.Close()


class TemperatureMonitor(LocalTemperatureMonitor):
    """Front ends always read the broker; one background process owns hardware."""

    def __init__(self):
        pass

    def read_temperatures(self):
        from sensor_broker import read_snapshot
        return read_snapshot()

    def close(self):
        pass


def print_temperatures(category=None):
    """Print available temperatures for one menu section or the whole PC."""
    monitor = TemperatureMonitor()

    try:
        readings = monitor.read_temperatures()

        if category:
            readings = [
                reading for reading in readings
                if reading.category == category
            ]

        print("\nTemperatures")

        if not readings:
            print("Temperature Sensors: Unavailable")
            return

        for reading in readings:
            print(
                f"{reading.hardware_name} | "
                f"{reading.sensor_name}: "
                f"{reading.value:.1f} °C"
            )

    finally:
        monitor.close()
