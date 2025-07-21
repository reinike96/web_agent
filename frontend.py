import os
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import customtkinter as ctk
from new_orchestrator import NewOrchestrator
import threading
from itertools import cycle
import warnings
from system_tray import create_tray_icon
import hashlib
import sys
import shutil
import subprocess

warnings.filterwarnings("ignore", category=UserWarning)

class CTkTopFrame(ctk.CTkToplevel):
    def __init__(self, master, padx: int = 10, x_offset: int = None, y_offset: int = None):
        super().__init__()
        self.master = master
        self.master.minsize(200, 100)
        self.overrideredirect(True)
        self.transparent_color = self._apply_appearance_mode(self._fg_color)
        self.attributes("-transparentcolor", self.transparent_color)
        self.resizable(True, True)
        self.transient(self.master)
        self.config(background=self.transparent_color)
        self.x_offset = 20 if x_offset is None else x_offset
        self.y_offset = 60 if y_offset is None else y_offset
        ctk.deactivate_automatic_dpi_awareness()

        self.master.bind("<Configure>", lambda _: self.change_dimension())

    def change_dimension(self):
        width = self.master.winfo_width() - self.x_offset
        if width < 0:
            self.withdraw()
            return
        if self.master.state() == "iconic":
            self.withdraw()
            return
        height = self.master.winfo_height()
        x = self.master.winfo_x() + self.x_offset
        y = self.master.winfo_y() + self.y_offset
        if self.master.state() == "zoomed":
            y += 4
            x -= 7
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.deiconify()

    def show(self):
        self.change_dimension()
        self.deiconify()

base_dir = os.path.dirname(os.path.abspath(__file__))
assets_folder = os.path.join(base_dir, 'assets')

img1_path = os.path.join(assets_folder, "1.png")
logo_path = os.path.join(assets_folder, "logoFux.ico")
send_path = os.path.join(assets_folder, "send.png")
loading_path = os.path.join(assets_folder, "ezgif-7-588bfce70f.gif")
close_icon_path = os.path.join(assets_folder, "close.png")
book_path = os.path.join(assets_folder, "book-of-black-cover-closed.png")
pencil_icon_path = os.path.join(assets_folder, "pencil.png")
diskette_path = os.path.join(assets_folder, "diskette.png")

root = ctk.CTk()
root.title("Reinike AI")
root.iconbitmap(logo_path)
root.geometry("730x600")
root.resizable(False, False)

img1 = Image.open(img1_path)
tk_img1 = ImageTk.PhotoImage(img1)

l1 = ctk.CTkLabel(root, image=tk_img1, text="")
l1.place(x=0, y=0, relwidth=1, relheight=1)

top_window = CTkTopFrame(root)
top_window.withdraw()

root.after(0, top_window.show)
root.update_idletasks()

logo = ImageTk.PhotoImage(Image.open(logo_path).resize((70, 70), Image.LANCZOS))
logo_label = ctk.CTkLabel(top_window, image=logo, text="")
logo_label.place(relx=0.5, y=0, anchor='n')

label = ctk.CTkLabel(
    top_window,
    text="Enter your instruction:",
    corner_radius=6,
    font=("Century Gothic", 22)
)
label.place(relx=0.5, rely=0.28, anchor='center')

text_area = ctk.CTkTextbox(
    top_window,
    height=270,
    width=450,
    border_color="#515151",
    border_width=2,
    corner_radius=6
)
text_area.place(relx=0.5, rely=0.53, anchor='center')
text_area.configure(font=("Archivo", 18))

class LoadingGif:
    def __init__(self, parent):
        self.parent = parent
        self.loading_gif = Image.open(loading_path)
        self.frames = [ImageTk.PhotoImage(frame) for frame in self.get_frames(self.loading_gif)]
        self.frames_cycle = cycle(self.frames)
        self.image_label = tk.Label(self.parent, bg="#242424")

    @staticmethod
    def get_frames(image):
        try:
            i = 0
            while True:
                image.seek(i)
                yield image.copy()
                i += 1
        except EOFError:
            pass

    def start(self):
        self.image_label.place(relx=0.5, rely=0.08, anchor='center')
        self.update_label()

    def stop(self):
        self.image_label.place_forget()

    def update_label(self):
        try:
            frame = next(self.frames_cycle)
            self.image_label.config(image=frame)
            self.parent.after(50, self.update_label)
        except StopIteration:
            pass

PROMPTS_FILE = os.path.join(assets_folder, "prompts.txt")

def ensure_prompts_file():
    if not os.path.exists(PROMPTS_FILE):
        with open(PROMPTS_FILE, 'w', encoding="utf-8") as f:
            f.write("")

def parse_prompt_line(line):
    if "|||" in line:
        title, prompt = line.split("|||", 1)
        return title.strip(), prompt.strip()
    return None, line.strip()

def format_prompt_line(title, prompt):
    return f"{title}|||{prompt}" if title and title.strip() else prompt

def load_prompts():
    ensure_prompts_file()
    with open(PROMPTS_FILE, 'r', encoding="utf-8") as f:
        return [parse_prompt_line(line) for line in f if line.strip()]

def save_all_prompts(prompts_list):
    ensure_prompts_file()
    with open(PROMPTS_FILE, 'w', encoding="utf-8") as f:
        for t, p in prompts_list:
            f.write(format_prompt_line(t, p) + "\n")

def save_prompt(new_prompt):
    prompts = load_prompts()
    prompts.append((None, new_prompt.strip()))
    save_all_prompts(prompts)

def delete_prompt_line(title_to_remove, prompt_to_remove):
    prompts = load_prompts()
    updated = [(t, p) for t, p in prompts if not (t == title_to_remove and p == prompt_to_remove)]
    save_all_prompts(updated)

def rename_prompt_line(old_title, old_prompt, new_title):
    prompts = load_prompts()
    updated = [(new_title.strip() if t == old_title and p == old_prompt else t, p) for t, p in prompts]
    save_all_prompts(updated)

def open_prompts_dropdown(event=None):
    # This function needs to be defined to handle the book icon click
    pass 

loading_gif = None

def set_message(message, reset=True):
    def _update_label():
        global loading_gif
        label.configure(text=message)
        if reset and loading_gif:
            loading_gif.stop()
            root.after(4000, lambda: label.configure(text="Enter your instruction:"))
    root.after(0, _update_label)

cancel_event = threading.Event()
button_send = None # Will be defined later
button_close = None # Will be defined later
button = None # Will be defined later

def cancel_task():
    global button
    cancel_event.set()
    if loading_gif:
        loading_gif.stop()
    if button:
        button.configure(text="Send", image=button_send, command=start_task_thread)
    set_message("Process canceled!")

def start_task_thread():
    global button
    cancel_event.clear()
    if button:
        button.configure(text="Cancel", image=button_close, command=cancel_task)
    thread = threading.Thread(target=run_agent_task)
    thread.daemon = True
    thread.start()

def run_agent_task():
    global loading_gif, button
    if loading_gif:
        loading_gif.start()
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        set_message("GROQ_API_KEY not found in .env file.", reset=True)
        if button:
             button.configure(text="Send", image=button_send, command=start_task_thread)
        return

    set_message("Starting Web Agent...", reset=False)
    goal = text_area.get("1.0", "end-1c").strip()

    if not goal:
        set_message("Please enter a goal for the agent.", reset=True)
        if button:
            button.configure(text="Send", image=button_send, command=start_task_thread)
        return

    try:
        agent = NewOrchestrator(goal=goal, message_callback=lambda msg: set_message(msg, reset=False))
        agent.run()
        set_message("Agent has finished its task.", reset=True)
    except Exception as e:
        print(f"An error occurred: {e}")
        set_message(f"Error: {e}", reset=True)
    finally:
        if loading_gif:
            loading_gif.stop()
        if button:
            button.configure(text="Send", image=button_send, command=start_task_thread)

def main():
    global loading_gif, button, button_send, button_close
    
    # --- Main UI Setup ---
    button_frame = ctk.CTkFrame(top_window, fg_color="transparent")
    button_frame.place(relx=0.5, rely=0.85, anchor='center')

    button_send = ImageTk.PhotoImage(Image.open(send_path).resize((25, 25), Image.LANCZOS))
    button_close = ImageTk.PhotoImage(Image.open(close_icon_path).resize((25, 25), Image.LANCZOS))
    book_icon = ImageTk.PhotoImage(Image.open(book_path).resize((25, 25), Image.LANCZOS))

    prompts_icon_label = ctk.CTkLabel(top_window, image=book_icon, text="")
    prompts_icon_label.place(relx=0.78, rely=0.28, anchor='center')
    prompts_icon_label.bind("<Button-1>", open_prompts_dropdown)

    button = ctk.CTkButton(
        button_frame,
        text="Send",
        width=150,
        height=50,
        corner_radius=6,
        image=button_send,
        compound='left',
        font=("Archivo", 18),
        hover_color='#d98e0f',
        fg_color="#D76E0B",
        command=start_task_thread
    )
    button.pack(expand=True)

    loading_gif = LoadingGif(top_window)
    loading_gif.stop()

    def on_exit():
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_exit)
    root.mainloop()

# The main.py will call this
# if __name__ == "__main__":
#     main()