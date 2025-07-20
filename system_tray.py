import threading
from PIL import Image
import pystray

# Variable global para guardar el tray icon
tray_icon = None

def create_tray_icon(root, exit_callback):
    global tray_icon
    # Load an image for the tray icon from assets or use a placeholder
    try:
        from os.path import dirname, join, abspath
        icon_path = join(dirname(abspath(__file__)), '..', 'assets', 'logoFux.ico')
        image = Image.open(icon_path)
    except Exception:
        image = Image.new('RGB', (64, 64), color='black')
    
    def on_show(icon, item):
        root.deiconify()
        icon.stop()

    def on_exit(icon, item):
        icon.stop()
        exit_callback()

    menu = pystray.Menu(
        pystray.MenuItem("Show", on_show),
        pystray.MenuItem("Exit", on_exit)
    )
    
    tray_icon = pystray.Icon("reinike", image, "Reinike AI", menu)
    # Enable double click to show the window (may work on Windows)
    tray_icon._on_double_click = on_show
    threading.Thread(target=tray_icon.run, daemon=True).start()
    return tray_icon

def stop_tray_icon():
    global tray_icon
    if tray_icon:
        tray_icon.stop()
        tray_icon = None
