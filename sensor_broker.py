"""Live temperatures shared through Windows memory; no snapshot files or history."""
from dataclasses import asdict
import ctypes
from ctypes import wintypes
import json
import math
import os
import struct
import threading
import time

SNAPSHOT_VERSION = 1
MAX_AGE_SECONDS = 20
CHANNEL_NAME = r'Local\DiagnosticSensors.LiveTemperatures.v2'
CAPACITY = 4 * 1024 * 1024
HEADER_SIZE = 16


class MemoryChannel:
    """A pagefile-backed named Windows mapping; clients only map it read-only.

    x64 aligned sequence stores are atomic. An odd sequence marks a write in
    progress; a reader accepts data only when matching even sequences surround
    its copy. The build supports x64 CPython only. No disk file is opened.
    """
    def __init__(self, writer=False, name=CHANNEL_NAME):
        if os.name != 'nt':
            raise OSError('Windows shared memory is required.')
        self.writer = writer
        self.name = name
        self.mapping = self.view = self.owner = None
        self.lock = threading.Lock()
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        k = self.kernel
        k.CreateFileMappingW.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                                        wintypes.DWORD, wintypes.DWORD, wintypes.LPCWSTR]
        k.CreateFileMappingW.restype = wintypes.HANDLE
        k.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
        k.OpenFileMappingW.restype = wintypes.HANDLE
        k.MapViewOfFile.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
                                   wintypes.DWORD, ctypes.c_size_t]
        k.MapViewOfFile.restype = ctypes.c_void_p
        k.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        k.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        k.CreateMutexW.restype = wintypes.HANDLE
        k.ReleaseMutex.argtypes = [wintypes.HANDLE]
        k.FlushProcessWriteBuffers.argtypes = []
        try:
            if writer:
                self.owner = k.CreateMutexW(None, True, name + '.Writer')
                if not self.owner:
                    raise ctypes.WinError(ctypes.get_last_error())
                if ctypes.get_last_error() == 183:
                    # Never release another writer's mutex; this handle did not acquire it.
                    k.CloseHandle(self.owner)
                    self.owner = None
                    raise RuntimeError('The Sensors background reader is already running.')
                self.mapping = k.CreateFileMappingW(ctypes.c_void_p(-1), None, 0x04, 0, CAPACITY, name)
                access = 0x0002 | 0x0004  # FILE_MAP_WRITE | FILE_MAP_READ
            else:
                self.mapping = k.OpenFileMappingW(0x0004, False, name)
                access = 0x0004  # FILE_MAP_READ; never create a mapping from the client
            if not self.mapping:
                raise ctypes.WinError(ctypes.get_last_error())
            self.view = k.MapViewOfFile(self.mapping, access, 0, 0, CAPACITY)
            if not self.view:
                raise ctypes.WinError(ctypes.get_last_error())
        except BaseException:
            self.close()
            raise

    def publish(self, payload):
        if not self.writer or not self.view:
            raise PermissionError('This temperature channel is read-only or closed.')
        if len(payload) > CAPACITY - HEADER_SIZE:
            raise ValueError('Temperature message is too large.')
        with self.lock:
            sequence = ctypes.c_uint64.from_address(self.view)
            value = (sequence.value + 1) | 1
            sequence.value = value
            self.kernel.FlushProcessWriteBuffers()
            ctypes.memmove(self.view + HEADER_SIZE, payload, len(payload))
            ctypes.memmove(self.view + 8, struct.pack('<II', len(payload), SNAPSHOT_VERSION), 8)
            self.kernel.FlushProcessWriteBuffers()
            sequence.value = value + 1

    def receive(self):
        if not self.view:
            raise RuntimeError('Temperature channel is closed.')
        for _ in range(30):
            before = ctypes.c_uint64.from_address(self.view).value
            if not before or before & 1:
                time.sleep(0.002)
                continue
            size, version = struct.unpack('<II', ctypes.string_at(self.view + 8, 8))
            if size > CAPACITY - HEADER_SIZE or version != SNAPSHOT_VERSION:
                raise RuntimeError('Invalid temperature message.')
            payload = ctypes.string_at(self.view + HEADER_SIZE, size)
            self.kernel.FlushProcessWriteBuffers()
            after = ctypes.c_uint64.from_address(self.view).value
            if before == after and not after & 1:
                return payload
        raise RuntimeError('The Sensors background reader is not ready.')

    def close(self):
        if self.view:
            self.kernel.UnmapViewOfFile(self.view)
            self.view = None
        if self.mapping:
            self.kernel.CloseHandle(self.mapping)
            self.mapping = None
        if self.owner:
            self.kernel.ReleaseMutex(self.owner)
            self.kernel.CloseHandle(self.owner)
            self.owner = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def is_administrator():
    return os.name == 'nt' and bool(ctypes.windll.shell32.IsUserAnAdmin())


def write_snapshot(readings, errors=(), channel=None):
    """Publish current readings in memory. The caller owns the writer handle."""
    if channel is None:
        raise ValueError('An in-memory writer channel is required.')
    data = {'version': SNAPSHOT_VERSION, 'timestamp': time.time(),
            'temperatures': [asdict(row) for row in readings], 'errors': list(errors)}
    channel.publish(json.dumps(data, allow_nan=False).encode('utf-8'))


def read_snapshot(channel=None, now=None):
    try:
        if channel is None:
            with MemoryChannel() as live:
                payload = live.receive()
        else:
            payload = channel.receive()
        data = json.loads(payload)
    except (OSError, ValueError) as error:
        raise RuntimeError('The Sensors background reader is not ready. Run Install_Sensors_Background.bat once, then open this app normally.') from error
    if not isinstance(data, dict):
        raise RuntimeError('Invalid sensor snapshot.')
    try:
        age = (time.time() if now is None else now) - float(data.get('timestamp', 0))
    except (ValueError, TypeError) as error:
        raise RuntimeError('Invalid sensor timestamp.') from error
    if data.get('version') != SNAPSHOT_VERSION or not -5 <= age <= MAX_AGE_SECONDS:
        raise RuntimeError('The Sensors background reader has stopped or its data is stale. Run Install_Sensors_Background.bat to repair it.')
    rows = data.get('temperatures')
    if not isinstance(rows, list):
        raise RuntimeError('Invalid sensor snapshot.')
    from hardware_temperatures import TemperatureReading
    readings = []
    for row in rows:
        try:
            value = float(row['value'])
            if not math.isfinite(value) or not -50 <= value <= 200:
                continue
            fields = ('sensor_id', 'hardware_id', 'category', 'hardware_name', 'sensor_name')
            if any(not isinstance(row.get(key), str) or len(row[key]) > 2048 for key in fields):
                continue
            readings.append(TemperatureReading(**{key: row[key] for key in fields}, value=value))
        except (KeyError, TypeError, ValueError):
            continue
    if not readings and data.get('errors'):
        raise RuntimeError('Sensors reader error: ' + str(data['errors'][0])[:500])
    return readings


def run_background_reader():
    if not is_administrator():
        raise RuntimeError('Only the background reader needs administrator access.')
    from hardware_temperatures import LocalTemperatureMonitor
    monitor = None
    with MemoryChannel(writer=True) as channel:
        _collect_forever(channel)


def _collect_forever(channel):
    from hardware_temperatures import LocalTemperatureMonitor
    monitor = None
    while True:
        try:
            if monitor is None:
                monitor = LocalTemperatureMonitor()
            write_snapshot(monitor.read_temperatures(), getattr(monitor, 'errors', ()), channel=channel)
        except Exception as error:
            try:
                write_snapshot([], [str(error)], channel=channel)
            except OSError:
                pass
            if monitor is not None:
                try:
                    monitor.close()
                except Exception:
                    pass
                monitor = None
            time.sleep(8)
        time.sleep(2)


if __name__ == '__main__':
    import sys
    if '--self-test' in sys.argv:
        import importlib.util
        sys.exit(0 if importlib.util.find_spec('HardwareMonitor') else 1)
    run_background_reader()
