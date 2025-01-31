import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
import psutil
import pystray
from PIL import Image
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import winreg

class FilamentTracker:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Filament Tracker")
        
        # Set window size to 1/6 of screen
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        window_width = screen_width // 6
        window_height = screen_height // 6
        self.window.geometry(f"{window_width}x{window_height}")
        
        # Load saved filaments
        self.filaments = self.load_filaments()
        
        # Create GUI elements
        self.create_widgets()
        
        # Set up minimize to tray behavior
        self.window.protocol('WM_DELETE_WINDOW', self.minimize_to_tray)
        self.create_tray_icon()
        
    def create_tray_icon(self):
        # Create a simple image for the tray icon
        icon_image = Image.new('RGB', (64, 64), color='blue')
        self.icon = pystray.Icon(
            "filament_tracker",
            icon_image,
            "Filament Tracker",
            menu=pystray.Menu(
                pystray.MenuItem("Show", self.show_window),
                pystray.MenuItem("Exit", self.quit_app)
            )
        )
        threading.Thread(target=self.icon.run, daemon=True).start()
        
    def minimize_to_tray(self):
        self.window.withdraw()
        
    def show_window(self):
        self.window.deiconify()
        
    def quit_app(self):
        self.icon.stop()
        self.window.quit()
        
    def create_widgets(self):
        # Filament selection dropdown
        self.filament_var = tk.StringVar()
        self.filament_dropdown = ttk.Combobox(
            self.window, 
            textvariable=self.filament_var,
            values=self.get_filament_names()
        )
        self.filament_dropdown.grid(row=0, column=0, padx=5, pady=5)
        
        # New filament entry
        self.new_filament_entry = ttk.Entry(self.window)
        self.new_filament_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Add new filament button
        ttk.Button(
            self.window,
            text="Add New Filament",
            command=self.add_new_filament
        ).grid(row=0, column=2, padx=5, pady=5)
        
        # Usage entry
        self.usage_label = ttk.Label(self.window, text="Filament used (g):")
        self.usage_label.grid(row=1, column=0, padx=5, pady=5)
        
        self.usage_entry = ttk.Entry(self.window)
        self.usage_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Submit button
        ttk.Button(
            self.window,
            text="Submit Usage",
            command=self.submit_usage
        ).grid(row=1, column=2, padx=5, pady=5)
        
        # Display current amounts
        self.amount_text = tk.Text(self.window, height=5, width=40)
        self.amount_text.grid(row=2, column=0, columnspan=3, padx=5, pady=5)
        self.update_amounts_display()
        
    def load_filaments(self):
        try:
            with open('filaments.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
            
    def save_filaments(self):
        with open('filaments.json', 'w') as f:
            json.dump(self.filaments, f)
            
    def get_filament_names(self):
        return list(self.filaments.keys())
        
    def add_new_filament(self):
        name = self.new_filament_entry.get().strip()
        if name:
            if name not in self.filaments:
                self.filaments[name] = 1000  # Starting amount in grams
                self.save_filaments()
                self.update_filament_dropdown()
                self.update_amounts_display()
                self.new_filament_entry.delete(0, tk.END)
            else:
                messagebox.showwarning("Warning", "Filament already exists!")
                
    def update_filament_dropdown(self):
        self.filament_dropdown['values'] = self.get_filament_names()
        
    def submit_usage(self):
        filament = self.filament_var.get()
        try:
            usage = float(self.usage_entry.get())
            if filament in self.filaments:
                self.filaments[filament] -= usage
                if self.filaments[filament] <= 0:
                    del self.filaments[filament]
                self.save_filaments()
                self.update_filament_dropdown()
                self.update_amounts_display()
                self.usage_entry.delete(0, tk.END)
            else:
                messagebox.showwarning("Warning", "Please select a filament!")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number!")
            
    def update_amounts_display(self):
        self.amount_text.delete(1.0, tk.END)
        for name, amount in self.filaments.items():
            self.amount_text.insert(tk.END, f"{name}: {amount:.1f}g remaining\n")
            
    def run(self):
        self.window.mainloop()

def add_to_startup():
    # Add to Windows startup
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
        winreg.SetValueEx(key, "FilamentTracker", 0, winreg.REG_SZ, sys.executable + " " + os.path.abspath(__file__))
        winreg.CloseKey(key)
    except WindowsError:
        print("Unable to add to startup")

def is_bambu_studio_running():
    for proc in psutil.process_iter(['name']):
        try:
            # You might need to adjust this name based on the actual process name
            if "BambuStudio" in proc.info['name']:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def wait_for_bambu_studio():
    while not is_bambu_studio_running():
        time.sleep(1)
    return True

if __name__ == "__main__":
    # Add to startup programs
    add_to_startup()
    
    # Start a thread to wait for Bambu Studio
    if not is_bambu_studio_running():
        threading.Thread(target=wait_for_bambu_studio, daemon=True).start()
    
    # Start the tracker
    app = FilamentTracker()
    app.run()