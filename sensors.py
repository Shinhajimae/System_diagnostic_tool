"""Multiple selectable Windows tray temperature icons."""

import json
import os
import sys
import threading
import time

from PIL import Image, ImageDraw, ImageFont
import pystray

from hardware_temperatures import TemperatureMonitor


APP_NAME = "Sensors"
UPDATE_SECONDS = 2
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "Sensors"
CATEGORY_ORDER = {
    "CPU": 0,
    "GPU": 1,
    "Memory": 2,
    "Storage": 3,
    "Motherboard": 4,
    "Other": 5
}
DEFAULT_APPEARANCE = {
    "size": "Large",
    "color": "White",
    "show_label": False
}
TEXT_COLORS = {
    "White": "#ffffff",
    "Light Gray": "#d1d5db",
    "Green": "#4ade80",
    "Blue": "#60a5fa",
    "Orange": "#f59e0b",
    "Red": "#ef4444"
}


def set_window_icon(root):
    from pathlib import Path
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    try:
        root.iconbitmap(str(base / "terminal.ico"))
    except Exception:
        pass


def startup_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --startup'

    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    executable = pythonw if os.path.exists(pythonw) else sys.executable
    return f'"{executable}" "{os.path.abspath(__file__)}" --startup'


def is_startup_enabled():
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            RUN_KEY,
            0,
            winreg.KEY_READ
        ) as key:
            value, _ = winreg.QueryValueEx(key, RUN_NAME)
            return value == startup_command()

    except (FileNotFoundError, OSError):
        return False


def set_startup_enabled(enabled):
    import winreg

    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER,
        RUN_KEY,
        0,
        winreg.KEY_SET_VALUE
    ) as key:
        if not enabled:
            try:
                winreg.DeleteValue(key, RUN_NAME)
            except FileNotFoundError:
                pass
        else:
            winreg.SetValueEx(
                key,
                RUN_NAME,
                0,
                winreg.REG_SZ,
                startup_command()
            )

def toggle_startup(icon, item):
    set_startup_enabled(not is_startup_enabled())
    icon.update_menu()


def settings_path():
    """Keep user-selected preferences beside the portable executable."""
    from pathlib import Path
    folder = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    return str(folder / "sensors.settings.json")


def load_selected_sensors():
    try:
        with open(settings_path(), "r", encoding="utf-8") as file:
            return json.load(file).get("selected_sensors", [])
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def load_appearance():
    appearance = DEFAULT_APPEARANCE.copy()

    try:
        with open(settings_path(), "r", encoding="utf-8") as file:
            saved_appearance = json.load(file).get("appearance", {})

        for key in appearance:
            if key in saved_appearance:
                appearance[key] = saved_appearance[key]

    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass

    return appearance


def save_tray_settings(sensor_ids, appearance):
    with open(settings_path(), "w", encoding="utf-8") as file:
        json.dump(
            {
                "selected_sensors": sensor_ids,
                "appearance": appearance
            },
            file,
            indent=4
        )


def sort_readings(readings):
    return sorted(
        (reading for reading in readings if reading.category in {"CPU", "GPU", "Memory", "Storage", "Motherboard"}),
        key=lambda reading: (
            CATEGORY_ORDER.get(reading.category, 99),
            reading.hardware_name.lower(),
            reading.sensor_name.lower()
        )
    )


def choose_sensors(readings, selected_ids, appearance, monitor=None):
    """White settings dialog; Apply previews saved settings, Exit returns to tray."""
    import tkinter as tk
    from tkinter import ttk, messagebox

    readings = sort_readings(readings)
    result = {"saved": False, "sensor_ids": selected_ids, "appearance": appearance}
    root = tk.Tk()
    root.title("Sensors")
    set_window_icon(root)
    root.configure(background="white")
    scale = max(1.0, root.winfo_fpixels("1i") / 96.0)
    width = min(int(760 * scale), root.winfo_screenwidth() - 60)
    height = min(int(890 * scale), root.winfo_screenheight() - 90)
    root.geometry(f"{width}x{height}")
    root.minsize(min(width, 640), min(height, 600))
    ink, muted, border, blue = "#111827", "#596579", "#dde2eb", "#0067df"
    font = ("Segoe UI", 11)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("Sensors.TCombobox", font=font, padding=7, fieldbackground="white",
                    background="white", foreground=ink, bordercolor="#aab2c1", arrowsize=14)
    style.map("Sensors.TCombobox", fieldbackground=[("readonly", "white")],
              foreground=[("readonly", ink)], selectbackground=[("readonly", "white")],
              selectforeground=[("readonly", ink)])
    style.configure("Sensors.Vertical.TScrollbar", background="#c4cad3", troughcolor="white",
                    borderwidth=0, arrowsize=11, width=12)

    def frame(parent, **kwargs):
        return tk.Frame(parent, background="white", **kwargs)

    def label(parent, text, **kwargs):
        return tk.Label(parent, text=text, background="white", foreground=kwargs.pop("foreground", ink),
                        font=kwargs.pop("font", font), **kwargs)

    def line(parent):
        tk.Frame(parent, background=border, height=1).pack(fill="x")

    def button(parent, text, command, primary=False):
        outer = tk.Frame(parent, background=blue if primary else "#aab2c1", padx=1, pady=1)
        inner = tk.Button(outer, text=text, command=command, font=font,
                          background=blue if primary else "white",
                          foreground="white" if primary else ink,
                          activebackground="#0057bf" if primary else "#f3f6fb",
                          activeforeground="white" if primary else ink,
                          relief="flat", borderwidth=0, highlightthickness=0,
                          padx=18, pady=7, cursor="hand2", takefocus=True)
        inner.pack(fill="both", expand=True)
        return outer

    # Render the same blue checkbox and white tick independently of the OS theme.
    def checkbox(parent, text, variable, command=None):
        row = frame(parent)
        box = tk.Canvas(row, width=22, height=25, background="white", highlightthickness=0,
                        takefocus=True, cursor="hand2")
        box.pack(side="left", padx=(0, 12))
        caption = label(row, text, anchor="w", cursor="hand2")
        caption.pack(side="left", fill="x", expand=True)

        def draw(*_):
            box.delete("all")
            checked = bool(variable.get())
            box.create_rectangle(2, 3, 20, 21, fill=blue if checked else "white",
                                 outline=blue if checked else "#7d8798", width=1)
            if checked:
                box.create_line(6, 12, 10, 16, 17, 8, fill="white", width=2,
                                capstyle="round", joinstyle="round")
            if command:
                command()

        def toggle(_=None):
            variable.set(not variable.get())
            box.focus_set()
            return "break"

        box.bind("<Button-1>", toggle)
        caption.bind("<Button-1>", toggle)
        box.bind("<space>", toggle)
        box.bind("<FocusIn>", lambda _: box.configure(highlightthickness=1, highlightbackground=blue))
        box.bind("<FocusOut>", lambda _: box.configure(highlightthickness=0))
        variable.trace_add("write", draw)
        draw()
        return row

    header = frame(root)
    header.pack(fill="x", padx=26, pady=(20, 18))
    label(header, "Tray temperatures", font=("Segoe UI", 21, "bold")).pack(anchor="w")
    label(header, "Choose which temperatures appear beside the Windows clock.",
          foreground=muted).pack(anchor="w", pady=(5, 0))
    line(root)
    toolbar = frame(root)
    toolbar.pack(fill="x", padx=24, pady=10)
    variables = {}
    count = tk.StringVar(value="0 selected")

    def update_count():
        count.set(f"{sum(bool(v.get()) for v in variables.values())} selected")

    def select_all(checked):
        for variable in variables.values():
            variable.set(checked)

    button(toolbar, "Check all", lambda: select_all(True)).pack(side="left")
    button(toolbar, "Uncheck all", lambda: select_all(False)).pack(side="left", padx=(12, 0))
    tk.Label(toolbar, textvariable=count, bg="white", fg=ink, font=font).pack(side="right")
    line(root)

    # Pin controls to the bottom while only the sensor list scrolls.
    footer = frame(root)
    footer.pack(side="bottom", fill="x")
    line(footer)
    footer_inner = frame(footer)
    footer_inner.pack(fill="x", padx=24, pady=12)
    label(footer_inner, "Exit closes settings. Sensors stays in the tray.",
          font=("Segoe UI", 9), foreground=muted).pack(side="left")

    appearance_frame = frame(root)
    appearance_frame.pack(side="bottom", fill="x")
    line(appearance_frame)
    settings = frame(appearance_frame)
    settings.pack(fill="x", padx=26, pady=14)
    label(settings, "Tray appearance", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 12))
    controls = frame(settings)
    controls.pack(fill="x")
    controls.columnconfigure(1, weight=1)
    controls.columnconfigure(3, weight=1)
    size_variable = tk.StringVar(value=appearance.get("size", "Large"))
    color_variable = tk.StringVar(value=appearance.get("color", "White"))
    label_variable = tk.BooleanVar(value=appearance.get("show_label", False))
    label(controls, "Number size").grid(row=0, column=0, sticky="w", padx=(0, 12))
    ttk.Combobox(controls, textvariable=size_variable, values=("Small", "Medium", "Large"),
                 state="readonly", style="Sensors.TCombobox", width=14).grid(row=0, column=1, sticky="ew", padx=(0, 24))
    label(controls, "Text color").grid(row=0, column=2, sticky="w", padx=(0, 12))
    ttk.Combobox(controls, textvariable=color_variable, values=tuple(TEXT_COLORS),
                 state="readonly", style="Sensors.TCombobox", width=14).grid(row=0, column=3, sticky="ew")
    checkbox(settings, "Show component letter (C / G / M / S)", label_variable).pack(fill="x", pady=(14, 0))
    startup_variable = tk.BooleanVar(value=is_startup_enabled())
    checkbox(settings, "Start with Windows", startup_variable).pack(fill="x", pady=(8, 0))

    container = frame(root)
    container.pack(fill="both", expand=True)
    canvas = tk.Canvas(container, background="white", highlightthickness=0)
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview,
                              style="Sensors.Vertical.TScrollbar")
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    sensor_frame = frame(canvas)
    window = canvas.create_window((0, 0), window=sensor_frame, anchor="nw")
    sensor_frame.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window, width=event.width))
    canvas.configure(yscrollcommand=scrollbar.set)

    def wheel(event):
        # Do not steal the wheel from appearance dropdowns.
        widget = event.widget
        while widget:
            if widget is container:
                canvas.yview_scroll(-int(event.delta / 120) if abs(event.delta) >= 120 else (-1 if event.delta > 0 else 1), "units")
                return "break"
            widget = getattr(widget, "master", None)

    root.bind("<MouseWheel>", wheel)
    current_group = None
    for reading in readings:
        group = (reading.category, reading.hardware_id)
        if group != current_group:
            if current_group is not None:
                separator = frame(sensor_frame)
                separator.pack(fill="x", padx=26, pady=(12, 0))
                line(separator)
            current_group = group
            heading = frame(sensor_frame)
            heading.pack(fill="x", padx=26, pady=(12, 7))
            label(heading, reading.category, font=("Segoe UI", 13, "bold")).pack(side="left")
            if reading.category in ("CPU", "GPU"):
                label(heading, reading.hardware_name, font=("Segoe UI", 10),
                      foreground=muted).pack(side="left", padx=(20, 0))
        variable = tk.BooleanVar(value=reading.sensor_id in selected_ids)
        variables[reading.sensor_id] = variable
        name = reading.sensor_name
        if reading.category in ("Storage", "Memory", "Motherboard"):
            name = f"{reading.hardware_name} — {name}"
        row = frame(sensor_frame)
        row.pack(fill="x", padx=26, pady=3)
        label(row, f"{reading.value:.1f} °C", anchor="e", width=9).pack(side="right", padx=(12, 0))
        checkbox(row, name, variable, update_count).pack(side="left", fill="x", expand=True)
    update_count()
    preview = {"stop": None, "thread": None}

    def stop_preview():
        if preview["stop"]:
            preview["stop"].set()
            preview["thread"].join(timeout=8)
            preview["stop"] = None

    def apply():
        chosen = [key for key, variable in variables.items() if variable.get()]
        if not chosen:
            messagebox.showwarning(APP_NAME, "Choose at least one temperature sensor.", parent=root)
            return
        new_appearance = {"size": size_variable.get(), "color": color_variable.get(),
                          "show_label": label_variable.get()}
        try:
            if startup_variable.get() != is_startup_enabled():
                set_startup_enabled(startup_variable.get())
            save_tray_settings(chosen, new_appearance)
        except OSError as error:
            messagebox.showerror(APP_NAME, f"Could not save settings.\n\n{error}", parent=root)
            return
        result.update(saved=True, sensor_ids=chosen, appearance=new_appearance)
        if monitor is not None:
            stop_preview()
            preview["stop"] = threading.Event()
            preview["thread"] = threading.Thread(target=run_icons,
                args=(monitor, readings, chosen, new_appearance, preview["stop"], False), daemon=True)
            preview["thread"].start()

    def close():
        stop_preview()
        root.destroy()

    button(footer_inner, "Exit", close).pack(side="right")
    button(footer_inner, "Apply", apply, primary=True).pack(side="right", padx=(0, 12))
    root.protocol("WM_DELETE_WINDOW", close)
    root.bind("<Escape>", lambda _: close())
    root.mainloop()
    return result



def short_label(reading, category_numbers):
    if reading.category == "CPU":
        return "C"
    if reading.category == "GPU":
        return "G"
    if reading.category == "Motherboard":
        return "M"

    if reading.category == "Memory":
        return "R"

    category_numbers["Storage"] += 1
    return f"S{category_numbers['Storage']}"


def load_font(size, bold=False):
    filename = "arialbd.ttf" if bold else "arial.ttf"
    font_path = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", filename)

    try:
        return ImageFont.truetype(font_path, size)
    except OSError:
        return ImageFont.load_default()


def create_temperature_icon(label, reading=None, appearance=None):
    #Transparent, monochrome icon inspired by classic sensor utilities.
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    appearance = appearance or DEFAULT_APPEARANCE
    value = f"{round(reading.value):.0f}" if reading else "--"
    color = TEXT_COLORS.get(appearance.get("color"), "#ffffff")
    show_label = appearance.get("show_label", False)
    selected_size = appearance.get("size", "Large")

    if show_label:
        value_sizes = {"Small": 29, "Medium": 34, "Large": 39}
        label_font = load_font(15, bold=True)
        value_font = load_font(value_sizes.get(selected_size, 39), bold=True)
        label_box = draw.textbbox((0, 0), label, font=label_font)
        value_box = draw.textbbox((0, 0), value, font=value_font)

        draw.text(
            ((64 - (label_box[2] - label_box[0])) / 2, -2),
            label,
            font=label_font,
            fill=color,
            stroke_width=2,
            stroke_fill="black"
        )
        value_y = 20

    else:
        value_sizes = {"Small": 38, "Medium": 47, "Large": 55}
        value_font = load_font(value_sizes.get(selected_size, 55), bold=True)
        value_box = draw.textbbox((0, 0), value, font=value_font)
        value_y = (64 - (value_box[3] - value_box[1])) / 2 - value_box[1]

    draw.text(
        ((64 - (value_box[2] - value_box[0])) / 2, value_y),
        value,
        font=value_font,
        fill=color,
        stroke_width=2,
        stroke_fill="black"
    )

    return image


def run_icons(monitor, readings, selected_ids, appearance, stop_event=None, settings_enabled=True):
    readings = sort_readings(readings)
    selected = [
        reading for reading in readings
        if reading.sensor_id in selected_ids
    ]

    stop_event = stop_event if stop_event is not None else threading.Event()
    settings_event = threading.Event()
    icons = []
    icon_sensors = {}
    category_numbers = {"Storage": 0}

    def stop_all(open_settings=False):
        if open_settings:
            settings_event.set()
        stop_event.set()

        for tray_icon in icons:
            tray_icon.stop()

    def settings_action(icon, item):
        stop_all(open_settings=True)

    def exit_action(icon, item):
        stop_all()

    for reading in selected:
        label = short_label(reading, category_numbers)
        title = (
            f"{reading.category} | {reading.hardware_name} | "
            f"{reading.sensor_name}: {reading.value:.1f} °C"
        )

        menu = pystray.Menu(
            pystray.MenuItem(
                "Sensor Settings...",
                settings_action,
                default=True,
                enabled=settings_enabled
            ),
            pystray.MenuItem(
                "Start with Windows",
                toggle_startup,
                checked=lambda item: is_startup_enabled()
            ),
            pystray.MenuItem("Exit All", exit_action, enabled=settings_enabled)
        )

        tray_icon = pystray.Icon(
            name=f"Sensors_{len(icons)}",
            icon=create_temperature_icon(label, reading, appearance),
            title=title,
            menu=menu
        )
        icon_sensors[tray_icon] = (reading.sensor_id, label)
        icons.append(tray_icon)

    def update_icons():
        while not stop_event.wait(UPDATE_SECONDS):
            try:
                latest = {
                    reading.sensor_id: reading
                    for reading in monitor.read_temperatures()
                }

                for tray_icon in icons:
                    sensor_id, label = icon_sensors[tray_icon]
                    reading = latest.get(sensor_id)
                    tray_icon.icon = create_temperature_icon(
                        label,
                        reading,
                        appearance
                    )

                    if reading:
                        tray_icon.title = (
                            f"{reading.category} | "
                            f"{reading.hardware_name} | "
                            f"{reading.sensor_name}: "
                            f"{reading.value:.1f} °C"
                        )[:127]
                    else:
                        tray_icon.title = "Temperature sensor unavailable"

            except Exception:
                for tray_icon in icons:
                    tray_icon.icon = create_temperature_icon(icon_sensors[tray_icon][1], None, appearance)
                    tray_icon.title = "Sensors: background reader unavailable"
                continue

    update_thread = threading.Thread(target=update_icons, daemon=True)
    update_thread.start()

    threads = []

    for tray_icon in icons:
        thread = threading.Thread(target=tray_icon.run, daemon=True)
        thread.start()
        threads.append(thread)

    stop_event.wait()
    stop_all()
    update_thread.join(timeout=3)
    for thread in threads:
        thread.join(timeout=2)

    return settings_event.is_set()


def show_error(message):
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.withdraw()
    set_window_icon(root)
    messagebox.showerror(APP_NAME, message)
    root.destroy()


def main():
    try:
        #Prevent several copies from creating duplicate tray icons.
        if os.name == "nt":
            import ctypes

            ctypes.windll.kernel32.CreateMutexW.restype = ctypes.c_void_p
            ctypes.windll.kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
            mutex = ctypes.windll.kernel32.CreateMutexW(
                None,
                False,
                "Local\\Diagnostic.Sensors.Tray"
            )

            if ctypes.windll.kernel32.GetLastError() == 183:
                ctypes.windll.kernel32.CloseHandle(mutex)
                show_error("Sensors is already running.")
                return

        monitor = TemperatureMonitor()
        startup = "--startup" in sys.argv
        for attempt in range(60 if startup else 1):
            try:
                readings = monitor.read_temperatures()
                if readings or not startup:
                    break
            except RuntimeError:
                if not startup or attempt == 59:
                    raise
            time.sleep(1)
        readings = sort_readings(readings)

        if not readings:
            show_error(
                "No temperature sensors were detected.\n\n"
                "The background reader may be starting, or this hardware exposes no supported temperatures. "
                "Run Install_Sensors_Background.bat if the reader has not been installed."
            )
            monitor.close()
            return

        selected_ids = load_selected_sensors()
        appearance = load_appearance()
        available_ids = {
            reading.sensor_id for reading in readings
        }
        valid_selected_ids = [
            sensor_id for sensor_id in selected_ids
            if sensor_id in available_ids
        ]
        saved_selection_changed = valid_selected_ids != selected_ids
        selected_ids = valid_selected_ids

        if startup:
            if not selected_ids:
                selected_ids = monitor.default_sensor_ids(readings)
                save_tray_settings(selected_ids, appearance)
        elif not selected_ids or saved_selection_changed:
            default_ids = monitor.default_sensor_ids(readings)

            for sensor_id in default_ids:
                if sensor_id not in selected_ids:
                    selected_ids.append(sensor_id)

            result = choose_sensors(readings, selected_ids, appearance, monitor)

            if result["saved"]:
                selected_ids = result["sensor_ids"]
                appearance = result["appearance"]

        while True:
            open_settings = run_icons(
                monitor,
                readings,
                selected_ids,
                appearance
            )

            if not open_settings:
                break

            readings = monitor.read_temperatures()
            result = choose_sensors(
                readings,
                selected_ids,
                appearance,
                monitor
            )

            if not result["saved"]:
                continue

            selected_ids = result["sensor_ids"]
            appearance = result["appearance"]

        monitor.close()

    except Exception as error:
        show_error(
            f"Sensors could not start.\n\n{error}\n\n"
            "Open the apps normally after installing the background reader once."
        )


if __name__ == "__main__":
    if "--reader" in sys.argv:
        from sensor_broker import run_background_reader
        run_background_reader()
        sys.exit(0)
    if "--self-test" in sys.argv:
        create_temperature_icon("C")
        sys.exit(0)
    main()
