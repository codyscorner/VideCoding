import tkinter as tk
from tkinter import ttk, messagebox
import time
from datetime import datetime
import os
import sys

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame

# PyInstaller-compatible base path
def _base_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

class StopwatchTimerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Stopwatch & Timer v1.0.0")
        self.root.geometry("450x650")
        self.root.minsize(400, 600)
        
        # Color Theme (Aqua)
        self.colors = {
            "bg": "#E0FFFF",          # Light Cyan / Aqua background
            "fg": "#004B4B",          # Dark Cyan text
            "accent1": "#00FFFF",     # Cyan / Aqua
            "accent2": "#008B8B",     # Dark Cyan
            "button_bg": "#00CED1",   # Dark Turquoise
            "button_fg": "#FFFFFF",
            "button_active": "#20B2AA" # Light Sea Green
        }
        
        self.root.configure(bg=self.colors["bg"])
        
        # Initialize Audio
        try:
            pygame.mixer.init()
            self.sound_loaded = True
        except Exception as e:
            print(f"Failed to initialize pygame mixer: {e}")
            self.sound_loaded = False
            
        self.chime_file = os.path.join(_base_path(), "TimerChime.mp3")

        # Configure Styling
        style = ttk.Style()
        style.theme_use('clam')
        
        # Notebook (Tabs) style
        style.configure('TNotebook', background=self.colors["bg"])
        style.configure('TNotebook.Tab', background=self.colors["accent1"], foreground=self.colors["fg"], padding=[15, 5], font=('Helvetica', 11, 'bold'))
        style.map('TNotebook.Tab', background=[('selected', self.colors["bg"])], foreground=[('selected', self.colors["accent2"])])
        
        # Frames style
        style.configure('Aqua.TFrame', background=self.colors["bg"])
        
        # Notebook setup
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.stopwatch_frame = ttk.Frame(self.notebook, style='Aqua.TFrame')
        self.timer_frame = ttk.Frame(self.notebook, style='Aqua.TFrame')
        
        self.notebook.add(self.stopwatch_frame, text="Stopwatch")
        self.notebook.add(self.timer_frame, text="Timer")
        
        self._init_stopwatch_ui()
        self._init_timer_ui()

    def _create_button(self, parent, text, command, width=10):
        btn = tk.Button(
            parent, 
            text=text, 
            command=command, 
            bg=self.colors["button_bg"], 
            fg=self.colors["button_fg"],
            activebackground=self.colors["button_active"],
            activeforeground=self.colors["button_fg"],
            font=('Helvetica', 12, 'bold'),
            borderwidth=0,
            cursor="hand2",
            width=width,
            pady=8
        )
        return btn

    # ================= STOPWATCH LOGIC =================
    def _init_stopwatch_ui(self):
        # State variables
        self.sw_running = False
        self.sw_start_time = 0
        self.sw_elapsed = 0
        self.sw_laps = []
        self.MAX_LAPS = 50
        
        # Display
        self.sw_display = tk.Label(self.stopwatch_frame, text="00:00:00.00", font=('Helvetica', 40, 'bold'), bg=self.colors["bg"], fg=self.colors["accent2"])
        self.sw_display.pack(pady=30)
        
        # Buttons Frame
        btn_frame = tk.Frame(self.stopwatch_frame, bg=self.colors["bg"])
        btn_frame.pack(pady=10)
        
        self.sw_btn_start = self._create_button(btn_frame, "Start", self.sw_start)
        self.sw_btn_start.grid(row=0, column=0, padx=5)
        
        self.sw_btn_stop = self._create_button(btn_frame, "Stop", self.sw_stop)
        self.sw_btn_stop.grid(row=0, column=1, padx=5)
        self.sw_btn_stop.config(state=tk.DISABLED)
        
        self.sw_btn_lap = self._create_button(btn_frame, "Lap", self.sw_lap)
        self.sw_btn_lap.grid(row=1, column=0, padx=5, pady=10)
        self.sw_btn_lap.config(state=tk.DISABLED)
        
        self.sw_btn_reset = self._create_button(btn_frame, "Reset", self.sw_reset)
        self.sw_btn_reset.grid(row=1, column=1, padx=5, pady=10)
        
        # Status Box (Laps)
        status_label = tk.Label(self.stopwatch_frame, text="Laps & Status", font=('Helvetica', 12, 'bold'), bg=self.colors["bg"], fg=self.colors["fg"])
        status_label.pack(anchor='w', padx=20, pady=(10, 0))
        
        self.sw_status_box = tk.Text(self.stopwatch_frame, height=15, width=40, font=('Consolas', 11), bg="#FFFFFF", fg=self.colors["fg"], state=tk.DISABLED, relief=tk.FLAT)
        self.sw_status_box.pack(padx=20, pady=5, fill=tk.BOTH, expand=True)
        
        # Scrollbar for status box
        scrollbar = ttk.Scrollbar(self.sw_status_box, command=self.sw_status_box.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.sw_status_box.config(yscrollcommand=scrollbar.set)
        
        self._log_sw_status("Stopwatch initialized. Ready.")

    def format_time(self, t):
        mins, secs = divmod(t, 60)
        hours, mins = divmod(mins, 60)
        millisecs = int((t % 1) * 100)
        return f"{int(hours):02d}:{int(mins):02d}:{int(secs):02d}.{millisecs:02d}"

    def _log_sw_status(self, message):
        self.sw_status_box.config(state=tk.NORMAL)
        self.sw_status_box.insert(tk.END, message + "\n")
        self.sw_status_box.see(tk.END)
        self.sw_status_box.config(state=tk.DISABLED)

    def sw_start(self):
        if not self.sw_running:
            self.sw_start_time = time.time() - self.sw_elapsed
            self.sw_running = True
            self._update_stopwatch()
            
            self.sw_btn_start.config(state=tk.DISABLED)
            self.sw_btn_stop.config(state=tk.NORMAL)
            if len(self.sw_laps) < self.MAX_LAPS:
                self.sw_btn_lap.config(state=tk.NORMAL)
                
            if self.sw_elapsed == 0:
                start_str = datetime.now().strftime("%I:%M:%S %p")
                self._log_sw_status(f"Session Started: {start_str}")
                self._log_sw_status("-" * 35)

    def _update_stopwatch(self):
        if self.sw_running:
            self.sw_elapsed = time.time() - self.sw_start_time
            self.sw_display.config(text=self.format_time(self.sw_elapsed))
            self.root.after(50, self._update_stopwatch)

    def sw_stop(self):
        if self.sw_running:
            self.sw_running = False
            self.sw_btn_start.config(state=tk.NORMAL)
            self.sw_btn_stop.config(state=tk.DISABLED)
            self.sw_btn_lap.config(state=tk.DISABLED)

    def sw_lap(self):
        if self.sw_running and len(self.sw_laps) < self.MAX_LAPS:
            lap_time = self.sw_elapsed
            self.sw_laps.append(lap_time)
            
            # Calculate lap split (difference from previous lap)
            if len(self.sw_laps) == 1:
                split_time = lap_time
            else:
                split_time = lap_time - self.sw_laps[-2]
                
            lap_num = len(self.sw_laps)
            self._log_sw_status(f"Lap {lap_num:02d}: {self.format_time(lap_time)}  (Split: {self.format_time(split_time)})")
            
            if lap_num >= self.MAX_LAPS:
                self.sw_btn_lap.config(state=tk.DISABLED)
                self._log_sw_status("Maximum 50 laps reached.")

    def sw_reset(self):
        self.sw_running = False
        self.sw_elapsed = 0
        self.sw_laps = []
        self.sw_display.config(text="00:00:00.00")
        
        self.sw_btn_start.config(state=tk.NORMAL)
        self.sw_btn_stop.config(state=tk.DISABLED)
        self.sw_btn_lap.config(state=tk.DISABLED)
        
        self.sw_status_box.config(state=tk.NORMAL)
        self.sw_status_box.delete('1.0', tk.END)
        self.sw_status_box.config(state=tk.DISABLED)
        self._log_sw_status("Stopwatch reset. Ready.")

    # ================= TIMER LOGIC =================
    def _init_timer_ui(self):
        self.tmr_running = False
        self.tmr_paused = False
        self.tmr_remaining = 0
        self.tmr_end_time = 0
        self.is_ringing = False
        self.channel = None
        
        # Display
        self.tmr_display = tk.Label(self.timer_frame, text="00:00:00", font=('Helvetica', 40, 'bold'), bg=self.colors["bg"], fg=self.colors["accent2"])
        self.tmr_display.pack(pady=(30, 10))
        
        # Input Frame
        input_frame = tk.Frame(self.timer_frame, bg=self.colors["bg"])
        input_frame.pack(pady=10)
        
        tk.Label(input_frame, text="HH", bg=self.colors["bg"], fg=self.colors["fg"], font=('Helvetica', 10, 'bold')).grid(row=0, column=0)
        tk.Label(input_frame, text="MM", bg=self.colors["bg"], fg=self.colors["fg"], font=('Helvetica', 10, 'bold')).grid(row=0, column=1)
        tk.Label(input_frame, text="SS", bg=self.colors["bg"], fg=self.colors["fg"], font=('Helvetica', 10, 'bold')).grid(row=0, column=2)
        
        # Spinboxes for time entry
        spinbox_font = ('Helvetica', 14)
        self.tmr_hh = ttk.Spinbox(input_frame, from_=0, to=99, width=3, font=spinbox_font, justify=tk.CENTER)
        self.tmr_hh.grid(row=1, column=0, padx=5)
        self.tmr_hh.set(0)
        
        self.tmr_mm = ttk.Spinbox(input_frame, from_=0, to=59, width=3, font=spinbox_font, justify=tk.CENTER)
        self.tmr_mm.grid(row=1, column=1, padx=5)
        self.tmr_mm.set(0)
        
        self.tmr_ss = ttk.Spinbox(input_frame, from_=0, to=59, width=3, font=spinbox_font, justify=tk.CENTER)
        self.tmr_ss.grid(row=1, column=2, padx=5)
        self.tmr_ss.set(0)
        
        # Buttons Frame
        btn_frame = tk.Frame(self.timer_frame, bg=self.colors["bg"])
        btn_frame.pack(pady=20)
        
        self.tmr_btn_start = self._create_button(btn_frame, "Start", self.tmr_start)
        self.tmr_btn_start.grid(row=0, column=0, padx=5)
        
        self.tmr_btn_pause = self._create_button(btn_frame, "Pause", self.tmr_pause)
        self.tmr_btn_pause.grid(row=0, column=1, padx=5)
        self.tmr_btn_pause.config(state=tk.DISABLED)
        
        self.tmr_btn_reset = self._create_button(btn_frame, "Reset", self.tmr_reset)
        self.tmr_btn_reset.grid(row=1, column=0, columnspan=2, padx=5, pady=10, sticky="ew")

    def _get_input_seconds(self):
        try:
            h = int(self.tmr_hh.get() or 0)
            m = int(self.tmr_mm.get() or 0)
            s = int(self.tmr_ss.get() or 0)
            return h * 3600 + m * 60 + s
        except ValueError:
            return 0

    def format_timer(self, seconds):
        if seconds < 0:
            seconds = 0
        mins, secs = divmod(seconds, 60)
        hours, mins = divmod(mins, 60)
        return f"{int(hours):02d}:{int(mins):02d}:{int(secs):02d}"

    def tmr_start(self):
        if self.is_ringing:
            self.stop_ringing()
            return

        if not self.tmr_running:
            if not self.tmr_paused:
                self.tmr_remaining = self._get_input_seconds()
            
            if self.tmr_remaining <= 0:
                messagebox.showwarning("Invalid Time", "Please enter a time greater than zero.")
                return
                
            self.tmr_running = True
            self.tmr_paused = False
            self.tmr_end_time = time.time() + self.tmr_remaining
            
            # Disable inputs
            self.tmr_hh.config(state="disabled")
            self.tmr_mm.config(state="disabled")
            self.tmr_ss.config(state="disabled")
            
            self.tmr_btn_start.config(state=tk.DISABLED)
            self.tmr_btn_pause.config(state=tk.NORMAL)
            
            self._update_timer()

    def _update_timer(self):
        if self.tmr_running:
            self.tmr_remaining = self.tmr_end_time - time.time()
            if self.tmr_remaining <= 0:
                self.tmr_remaining = 0
                self.tmr_display.config(text="00:00:00")
                self.play_chime()
                self._reset_timer_state()
            else:
                self.tmr_display.config(text=self.format_timer(self.tmr_remaining))
                self.root.after(100, self._update_timer)

    def tmr_pause(self):
        if self.tmr_running:
            self.tmr_running = False
            self.tmr_paused = True
            self.tmr_btn_start.config(state=tk.NORMAL)
            self.tmr_btn_pause.config(state=tk.DISABLED)

    def tmr_reset(self):
        if self.is_ringing:
            self.stop_ringing()
            
        self._reset_timer_state()
        self.tmr_display.config(text="00:00:00")
        
    def _reset_timer_state(self):
        self.tmr_running = False
        self.tmr_paused = False
        self.tmr_remaining = 0
        
        self.tmr_hh.config(state="normal")
        self.tmr_mm.config(state="normal")
        self.tmr_ss.config(state="normal")
        
        self.tmr_btn_start.config(state=tk.NORMAL)
        self.tmr_btn_pause.config(state=tk.DISABLED)

    def play_chime(self):
        if self.sound_loaded and os.path.exists(self.chime_file):
            try:
                sound = pygame.mixer.Sound(self.chime_file)
                self.channel = sound.play(loops=-1) # Loop until stopped
                self.is_ringing = True
                self.tmr_btn_start.config(text="STOP ALARM", state=tk.NORMAL, bg="red", fg="white")
                self.tmr_display.config(fg="red")
            except Exception as e:
                print(f"Error playing sound: {e}")
                self.fallback_alert()
        else:
            self.fallback_alert()
            
    def stop_ringing(self):
        if self.channel:
            self.channel.stop()
        self.is_ringing = False
        self.tmr_btn_start.config(text="Start", bg=self.colors["button_bg"], fg=self.colors["button_fg"])
        self.tmr_display.config(fg=self.colors["accent2"])
        
    def fallback_alert(self):
        self.root.bell()
        messagebox.showinfo("Time's Up!", "The timer has finished!")

if __name__ == "__main__":
    from pathlib import Path
    root = tk.Tk()
    _icon = Path(_base_path()) / "app_icon.ico"
    if _icon.exists():
        try:
            root.iconbitmap(str(_icon))
        except Exception:
            pass
    app = StopwatchTimerApp(root)
    root.mainloop()
