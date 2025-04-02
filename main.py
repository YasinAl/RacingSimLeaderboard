import tkinter as tk
from tkinter import ttk, messagebox, PhotoImage, filedialog
import pandas as pd
import os
from acc_shm_reader import *
import time
import struct
import mmap

# Constants
GAMES = {"Assetto Corsa": "assetto_corsa.png", "Dirt Rally 2": "dirt_rally_2.png"}  # Ensure images are in .png format
CSV_FILE = "leaderboard.csv"
SHM_FILE = "Local\acpmf_phys"  # Shared memory file for Assetto Corsa
FETCH_INTERVAL = 1000  # Fetch data every 10 milliseconds

class LeaderboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Game Leaderboard")
        self.players = {}
        self.best_lap = "no lap completed"
        self.selected_game = None
        self.selected_player = None
        self.images = {}  # Store loaded images to prevent garbage collection

        # Start with game selection page
        self.show_game_selection()

    def show_game_selection(self):
        """Display game selection screen"""
        self.clear_window()
        ttk.Label(self.root, text="Select a Game:", font=("Arial", 16)).pack(pady=10)

        frame = ttk.Frame(self.root)
        frame.pack()

        for game, img_path in GAMES.items():
            img = PhotoImage(file=img_path)
            self.images[game] = img  # Store image reference

            btn = ttk.Button(frame, image=img, command=lambda g=game: self.select_game(g))
            btn.pack(side=tk.LEFT, padx=10)

    def select_game(self, game):
        """Handle game selection"""
        self.selected_game = game
        self.show_leaderboard_screen()

    def show_leaderboard_screen(self):
        """Display leaderboard management screen"""
        self.clear_window()

        ttk.Label(self.root, text=f"{self.selected_game} Leaderboard", font=("Arial", 16)).pack(pady=10)

        ttk.Button(self.root, text="Load Leaderboard", command=self.load_leaderboard).pack(pady=5)
        ttk.Button(self.root, text="New Leaderboard", command=self.new_leaderboard).pack()
        ttk.Button(self.root, text="Save Current Leaderboard", command=self.save_leaderboard).pack(pady=5)

        # Player management
        player_frame = ttk.Frame(self.root)
        player_frame.pack(pady=10)
        self.player_name_var = tk.StringVar()
        ttk.Entry(player_frame, textvariable=self.player_name_var, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(player_frame, text="Add Player", command=self.add_player).pack(side=tk.LEFT, padx=5)
        ttk.Button(player_frame, text="Clear Player Data", command=self.clear_player_data).pack(side=tk.LEFT, padx=5)

        self.lb_frame = ttk.Frame(self.root)
        self.lb_frame.pack(pady=10)

        self.tree = ttk.Treeview(self.lb_frame,
                                 columns=("Player", "Best Lap", "Total Time", "Current Lap", "Number of Laps"),
                                 show='headings')
        self.tree.heading("Player", text="Player")
        self.tree.heading("Best Lap", text="Best Lap")
        self.tree.heading("Total Time", text="Total Time")
        self.tree.heading("Current Lap", text="Current Lap")
        self.tree.heading("Number of Laps", text="Number of Laps")
        self.tree.pack()

        self.tree.bind("<ButtonRelease-1>", self.on_player_select)
        self.fetch_data_periodically()

    def save_leaderboard(self):
        """Save the current leaderboard to a user-specified CSV file"""
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if file_path:
            df = pd.DataFrame.from_dict(self.players, orient='index')
            df.index.name = "Player"
            df.to_csv(file_path)
            messagebox.showinfo("Success", "Leaderboard saved successfully!")

    def on_player_select(self, event):
        """Select a player by clicking on the table row"""
        selected_item = self.tree.selection()
        if selected_item:
            self.selected_player = self.tree.item(selected_item, 'values')[0]
            self.fetch_shared_memory()

    def load_leaderboard(self):
        """Load leaderboard from CSV"""
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if file_path:
            df = pd.read_csv(file_path)
            self.players = df.set_index("Player").T.to_dict()
            self.update_leaderboard()

    def new_leaderboard(self):
        """Start a new leaderboard"""
        self.players.clear()
        self.update_leaderboard()

    def add_player(self):
        """Add a player to the leaderboard"""
        name = self.player_name_var.get().strip()
        if name and name not in self.players:
            self.players[name] = {"Best Lap": 0, "Total Time": 0, "Current Lap": 0, "Number of Laps": 0}
            self.update_leaderboard()
        else:
            messagebox.showwarning("Warning", "Player already exists or name is empty.")

    def clear_player_data(self):
        """Clear data of the selected player"""
        if self.selected_player and self.selected_player in self.players:
            self.players[self.selected_player] = {"Best Lap": 0, "Total Time": 0, "Current Lap": 0, "Number of Laps": 0}
            self.update_leaderboard()
        else:
            messagebox.showwarning("Warning", "No player selected.")

    def fetch_shared_memory(self):
        """Fetch data from Assetto Corsa shared memory"""
        try:
            # with open(f"\\\.\pipe\{SHM_FILE}", "rb") as f:
            #     mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            #     data = mm.read(64)
            #     best_lap = struct.unpack("f", data[12:16])[0]
            #     total_time = struct.unpack("f", data[8:12])[0]
            #     current_lap = struct.unpack("i", data[16:20])[0]
            #     number_of_laps = struct.unpack("i", data[20:24])[0]
            info = read_graphics()
            print(info)
            best_lap_tmp = info["iLastTime"]
            if self.best_lap == "no_lap_completed":
                self.best_lap = info["lastTime"]
            if type(self.best_lap) == int and self.best_lap > best_lap_tmp:
                self.best_lap = info["lastTime"]
            total_time = "not set yet"
            current_lap = info["currentTime"]
            number_of_laps = info["numberOfLaps"]
            if self.selected_player:
                print("fetched ", time.time())
                self.players[self.selected_player]["Best Lap"] = self.best_lap
                self.players[self.selected_player]["Total Time"] = total_time
                self.players[self.selected_player]["Current Lap"] = current_lap
                self.players[self.selected_player]["Number of Laps"] = number_of_laps
                self.update_leaderboard()
        except Exception as e:
            print(f"Error reading shared memory: {e}")

    def update_leaderboard(self):
        """Update the leaderboard UI"""
        self.tree.delete(*self.tree.get_children())
        for player, data in self.players.items():
            self.tree.insert("", "end", values=(
            player, self.best_lap, data["Total Time"], data["Current Lap"], data["Number of Laps"]))

    def fetch_data_periodically(self):
        """Fetch shared memory data periodically"""
        self.fetch_shared_memory()
        self.root.after(FETCH_INTERVAL, self.fetch_data_periodically)

    def clear_window(self):
        """Clear all widgets from the current window"""
        for widget in self.root.winfo_children():
            widget.destroy()


# Run the app
root = tk.Tk()
app = LeaderboardApp(root)
root.mainloop()
