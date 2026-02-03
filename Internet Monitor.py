# ============================================================================
# INTERNET MONITOR - Speed and Quality Monitoring System
# ============================================================================
# Features:
# - Speed tests (download/upload) via speedtest-cli
# - Ping measurement and packet loss across multiple servers
# - History storage in CSV
# - Graphical visualization of results
# - Configuration via JSON (no code editing required)
# - Automatic tests with configurable interval
# ============================================================================

# Python standard libraries
import os              # File and directory manipulation
import csv             # CSV file reading/writing
import datetime        # Date and time manipulation
import subprocess      # External command execution (ping, speedtest)
import threading       # Asynchronous test execution (doesn't freeze UI)
import re              # Regex for extracting ping data
import json            # config.json manipulation
import sys             # Access to Python executable

# Tkinter GUI
import tkinter as tk
from tkinter import messagebox, ttk

# Data analysis and graphs
import pandas as pd                                      # DataFrame manipulation (CSV)
import matplotlib.pyplot as plt                          # Graph creation
import matplotlib.dates as mdates                        # Date formatting in graphs
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # matplotlib + tkinter integration

# Type hints for better documentation
from typing import Dict, Optional, Tuple

# ============================================================================
# CONFIGURATION MANAGER
# ============================================================================
# Responsibilities:
# - Load/save settings from config.json file
# - Create file with default values if it doesn't exist
# - Allow settings update without restart
# ============================================================================

class ConfigManager:
    """Manages application settings via JSON file"""
    
    # Default values - used on first run or if config.json is corrupted
    DEFAULT_CONFIG = {
        "download_target": 1000,         # Download target in Mbps (for visual indicator)
        "upload_target": 500,            # Upload target in Mbps
        "ping_target": 20,               # Ping target in ms (lower is better)
        "auto_test_interval": 30,        # Interval between automatic tests (minutes)
        "ping_targets": ["8.8.8.8", "1.1.1.1", "208.67.222.222"],  # Servers for packet loss test
        "ping_count": 4,                 # Number of packets per server
        "graph_last_n": 30               # How many tests to display in graph
    }
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize manager and load settings"""
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self) -> Dict:
        """Load settings from JSON or create with default values"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    config = self.DEFAULT_CONFIG.copy()
                    config.update(loaded_config)
                    return config
            except Exception as e:
                print(f"Error loading config: {e}. Using default.")
                return self.DEFAULT_CONFIG.copy()
        else:
            # Create default configuration file
            self.save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG.copy()
    
    def save_config(self, config: Dict = None) -> bool:
        """Save settings to JSON file"""
        try:
            config_to_save = config if config else self.config
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def update(self, key: str, value) -> bool:
        """Update a specific setting"""
        self.config[key] = value
        return self.save_config()
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.config.get(key, default)


# ============================================================================
# INTERNET TESTER
# ============================================================================
# Responsibilities:
# - Execute speedtest using speedtest-cli via subprocess
# - Measure packet loss across multiple DNS servers (redundancy)
# - Extract and parse results using regex
# - Return structured data (dictionaries)
# ============================================================================

class InternetTester:
    """Responsible for executing speed and connection quality tests"""
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize tester with reference to config manager"""
        self.config = config_manager
    
    def measure_packet_loss(self) -> int:
        """
        Tests packet loss across multiple servers for greater reliability.
        
        Returns:
            int: Average loss percentage (0-100) or -1 on total failure
        """
        ping_targets = self.config.get('ping_targets', ["8.8.8.8", "1.1.1.1"])
        ping_count = self.config.get('ping_count', 4)
        
        results = []
        
        for target in ping_targets:
            try:
                param = '-n' if os.name == 'nt' else '-c'
                command = ['ping', param, str(ping_count), target]
                
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

                process = subprocess.Popen(
                    command, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    startupinfo=startupinfo, 
                    text=True
                )
                
                try:
                    output, _ = process.communicate(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    print(f"Timeout pinging {target}")
                    continue
                
                # Debug: shows COMPLETE ping output (useful for troubleshooting)
                print(f"\n=== Ping {target} ===")
                print(output)  # Complete output for analysis
                print("=" * 50)
                
                # Look for packet loss using multiple regex patterns
                # Windows PT-BR has different format than English, hence multiple patterns
                patterns = [
                    r'Perdidos\s*=\s*\d+\s*\((\d+)%',  # "Perdidos = 0 (0% de perda)" Windows PT-BR
                    r'(\d+)%\s*de perda',              # "0% de perda" generic Portuguese
                    r'(\d+)%\s*perdidos',              # "0% perdidos"
                    r'(\d+)%\s*loss',                  # "0% loss" (English)
                    r'\((\d+)%.*?lost\)',              # "(0% lost)" alternative format
                ]
                
                match = None
                for pattern in patterns:
                    match = re.search(pattern, output, re.IGNORECASE)
                    if match:
                        loss = int(match.group(1))
                        results.append(loss)
                        print(f"✅ Ping {target}: {loss}% loss (pattern: {pattern})")
                        break
                
                if not match:
                    print(f"⚠️ Could not extract packet loss from {target}")
            except Exception as e:
                print(f"Error pinging {target}: {e}")
                continue
        
        # Return average loss, or 0 if at least one succeeded
        if results:
            return int(sum(results) / len(results))
        
        # If all failed, try a simple ping to Google as fallback
        if not results:
            print("\n⚠️ Trying fallback: simple ping to 8.8.8.8...")
            try:
                param = '-n' if os.name == 'nt' else '-c'
                command = ['ping', param, '2', '8.8.8.8']
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                process = subprocess.Popen(command, stdout=subprocess.PIPE, 
                                           stderr=subprocess.PIPE, startupinfo=startupinfo, text=True)
                output, _ = process.communicate(timeout=5)
                
                print("=== Fallback Output ===")
                print(output)  # Complete output
                print("=" * 50)
                
                patterns = [
                    r'Perdidos\s*=\s*\d+\s*\((\d+)%',  # Windows PT-BR
                    r'(\d+)%\s*de perda',
                    r'(\d+)%\s*perdidos',
                    r'(\d+)%\s*loss',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, output, re.IGNORECASE)
                    if match:
                        print(f"✅ Fallback success: {match.group(1)}% loss")
                        return int(match.group(1))
                
                print("⚠️ No regex pattern found in fallback")
            except Exception as e:
                print(f"❌ Fallback failed: {e}")
        
        print(f"\n📊 Final results: {results}")
        return -1  # Only returns error (-1) if all servers failed
    
    def run_speedtest(self) -> Optional[Dict]:
        """
        Execute speed test using speedtest-cli.
        
        Process:
        1. Calls 'python -m speedtest --secure --json' via subprocess
        2. Waits up to 120 seconds (tests can take time)
        3. Parses returned JSON
        4. Converts bits/s to Mbps (division by 1,000,000)
        
        Returns:
            Dict with keys: download, upload, ping, isp, ip
            None on error
        """
        try:
            # Command: python -m speedtest --secure --json
            cmd = [sys.executable, '-m', 'speedtest', '--secure', '--json']
            
            # On Windows, hide CMD window
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                startupinfo=startupinfo, 
                text=True
            )
            
            # Wait for completion (timeout 120s)
            stdout, stderr = process.communicate(timeout=120)
            
            if process.returncode != 0:
                raise Exception(f"CLI Error: {stderr}")

            # Parse JSON returned by speedtest-cli
            result = json.loads(stdout)
            
            # Extract and convert data (bits -> Mbps)
            return {
                'download': result['download'] / 1_000_000,  # Convert bits/s to Mbps
                'upload': result['upload'] / 1_000_000,      # Convert bits/s to Mbps
                'ping': result['ping'],                       # Already in ms
                'isp': result['client'].get('isp', 'Unknown'),   # Internet provider
                'ip': result['client'].get('ip', 'Unknown')      # Client public IP
            }
        except Exception as e:
            raise Exception(f"Speedtest failed: {str(e)}")


# ============================================================================
# DATA MANAGER (CSV)
# ============================================================================
# Responsibilities:
# - Save tests to CSV file (append)
# - Read CSV and convert to pandas DataFrame
# - Calculate statistics (average, minimum, maximum)
# - Cache system for better performance
# - Automatic migration from old format (backward compatibility)
# ============================================================================

class DataManager:
    """Manages saving, reading and migration of CSV data"""
    
    # CSV file columns - order matters!
    COLUMNS = [
        "Date Time",             # Format: dd/mm/YYYY HH:MM:SS
        "Download (Mbps)",       # Download speed
        "Upload (Mbps)",         # Upload speed
        "Ping (ms)",             # HTTP latency to speedtest server
        "Packet Loss (%)",       # % of lost ICMP packets (0-100)
        "Provider",              # ISP name
        "Client IP"              # Public IP
    ]
    
    def __init__(self, csv_file: str):
        self.csv_file = csv_file
        self.cache = None            # DataFrame in memory (avoids reading CSV every time)
        self.cache_timestamp = 0     # File timestamp when cached
    
    def save_test(self, date_time: str, down: float, up: float, ping: float, 
                  packet_loss: int, isp: str, ip: str) -> Tuple[bool, str]:
        """
        Saves test result to CSV (append mode).
        
        Parameters:
            date_time: String in format "dd/mm/YYYY HH:MM:SS"
            down/up/ping: Numeric values (will be formatted with comma)
            packet_loss: Integer 0-100 (percentage)
            isp/ip: Strings with client information
        
        Returns:
            Tuple (success: bool, message: str)
        """
        new_file = not os.path.exists(self.csv_file)
        
        try:
            # Migration from old format if necessary
            if not new_file:
                self._check_migrate_format()

            with open(self.csv_file, mode='a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')
                if new_file:
                    writer.writerow(self.COLUMNS)
                
                writer.writerow([
                    date_time, 
                    f"{down:.2f}".replace('.', ','), 
                    f"{up:.2f}".replace('.', ','), 
                    f"{ping:.2f}".replace('.', ','),
                    f"{packet_loss}",
                    isp,
                    ip
                ])
            
            # Invalidate cache
            self.cache = None
            return True, "Success"
            
        except PermissionError:
            return False, "The file is open in another program. Close it and try again."
        except Exception as e:
            return False, f"Error saving: {str(e)}"
    
    def _check_migrate_format(self):
        """Check and migrate old CSV format if necessary"""
        try:
            with open(self.csv_file, 'r', encoding='utf-8-sig') as f:
                current_header = f.readline().strip().split(';')
            
            if len(current_header) < len(self.COLUMNS):
                old_df = pd.read_csv(self.csv_file, delimiter=';', decimal=',')
                for col in self.COLUMNS:
                    if col not in old_df.columns:
                        old_df[col] = "N/A"
                old_df.to_csv(self.csv_file, sep=';', decimal=',', 
                             index=False, encoding='utf-8-sig')
        except Exception as e:
            print(f"Migration error: {e}")
    
    def load_data(self, force_reload: bool = False) -> Optional[pd.DataFrame]:
        """Load data from CSV with cache system"""
        try:
            if not os.path.exists(self.csv_file):
                return None
            
            # Check if reload is needed
            file_mtime = os.path.getmtime(self.csv_file)
            if not force_reload and self.cache is not None and file_mtime == self.cache_timestamp:
                return self.cache
            
            # Load and process
            df = pd.read_csv(self.csv_file, delimiter=';', decimal=',')
            if not df.empty:
                df['Date Time'] = pd.to_datetime(
                    df['Date Time'], 
                    format='%d/%m/%Y %H:%M:%S', 
                    errors='coerce'
                )
                df = df.dropna(subset=['Date Time'])
                
                self.cache = df
                self.cache_timestamp = file_mtime
            
            return df
        except Exception as e:
            print(f"Error loading data: {e}")
            return None
    
    def get_statistics(self, last_n: int = 10) -> Optional[Dict]:
        """Calculate statistics from last N tests"""
        df = self.load_data()
        if df is None or df.empty:
            return None
        
        recent_df = df.tail(last_n)
        
        return {
            'total_tests': len(df),
            'down_mean': recent_df['Download (Mbps)'].mean(),
            'down_min': recent_df['Download (Mbps)'].min(),
            'down_max': recent_df['Download (Mbps)'].max(),
            'down_std': recent_df['Download (Mbps)'].std(),
            'up_mean': recent_df['Upload (Mbps)'].mean(),
            'up_min': recent_df['Upload (Mbps)'].min(),
            'up_max': recent_df['Upload (Mbps)'].max(),
            'ping_mean': recent_df['Ping (ms)'].mean(),
            'ping_min': recent_df['Ping (ms)'].min(),
            'ping_max': recent_df['Ping (ms)'].max(),
            'first_date': df.iloc[0]['Date Time'],
            'last_date': df.iloc[-1]['Date Time']
        }


# ============================================================================
# GRAPHICAL USER INTERFACE (GUI)
# ============================================================================
# Responsibilities:
# - Create and manage all Tkinter interface
# - Coordinate calls between ConfigManager, InternetTester and DataManager
# - Execute tests in separate thread (doesn't freeze UI)
# - Update cards, graphs and statistics
# - Manage automatic tests with timer
# ============================================================================

class InternetMonitorApp:
    """Internet monitor graphical interface - Coordination and UI"""
    
    def __init__(self, root):
        """Initialize application and components"""
        self.root = root
        self.root.title("Internet Monitor")
        self.root.geometry("900x750")
        self.root.configure(bg="#f0f0f0")

        # Initialize MVC pattern components
        self.script_folder = os.path.dirname(os.path.abspath(__file__))
        self.config = ConfigManager(os.path.join(self.script_folder, "config.json"))        # Model: Settings
        self.tester = InternetTester(self.config)                                            # Controller: Tests
        self.data_manager = DataManager(os.path.join(self.script_folder, 'internet_monitor.csv'))  # Model: Data
        
        # Application state control
        self.auto_test_active = False    # Flag for automatic tests
        self.auto_test_job = None        # Tkinter timer ID (for cancellation)
        self.testing = False             # Flag to prevent multiple simultaneous tests

        # Build interface and load initial data
        self.setup_ui()
        self.load_last_test()
        self.update_embedded_graph()

    def setup_ui(self):
        """Build entire graphical interface (Tkinter widgets)"""
        
        # Configure visual style of ttk components
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background="#f0f0f0")
        style.configure("TLabel", background="#f0f0f0", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#333")
        style.configure("Card.TFrame", background="white", relief="raised")
        
        # Main Container
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill="both", expand=True)

        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Label(header_frame, text="Monitoring Dashboard", style="Header.TLabel").pack(side="left")
        self.lbl_status = ttk.Label(header_frame, text="Ready", foreground="gray")
        self.lbl_status.pack(side="right", padx=10)

        # Client Info (ISP and IP)
        self.lbl_client_info = ttk.Label(main_frame, text="Provider: -- | IP: --", font=("Segoe UI", 9), foreground="#555")
        self.lbl_client_info.pack(fill="x", pady=(0, 5))
        
        # Summary statistics
        self.lbl_stats = ttk.Label(main_frame, text="Loading statistics...", font=("Segoe UI", 9), foreground="#888")
        self.lbl_stats.pack(fill="x", pady=(0, 10))

        # Status Cards - 4 column grid (Download, Upload, Ping, Loss)
        cards_frame = ttk.Frame(main_frame)
        cards_frame.pack(fill="x", pady=(0, 20))
        cards_frame.columnconfigure(0, weight=1)  # Download Card
        cards_frame.columnconfigure(1, weight=1)  # Upload Card
        cards_frame.columnconfigure(2, weight=1)  # Ping Card
        cards_frame.columnconfigure(3, weight=1)  # Packet Loss Card

        # Download Card (download speed)
        self.card_down = self.create_card(cards_frame, "Download", "⬇️", 0)
        # Upload Card (upload speed)
        self.card_up = self.create_card(cards_frame, "Upload", "⬆️", 1)
        # Ping Card (HTTP latency to speedtest server, NOT the same as ICMP ping)
        self.card_ping = self.create_card(cards_frame, "Ping (HTTP)", "📶", 2)
        # Packet Loss Card (% of lost ICMP packets measured separately)
        self.card_loss = self.create_card(cards_frame, "Pkt Loss", "❌", 3)

        # Progress Bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill="x", pady=(0, 10))

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(0, 10))
        
        self.btn_test = tk.Button(btn_frame, text="START TEST", command=self.start_test, 
                                  bg="#4CAF50", fg="white", font=("Segoe UI", 11, "bold"), 
                                  relief="flat", padx=20, pady=10, cursor="hand2")
        self.btn_test.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.btn_auto = tk.Button(btn_frame, text="🔄 Auto (OFF)", command=self.toggle_auto_test, 
                                  bg="#9E9E9E", fg="white", font=("Segoe UI", 10), 
                                  relief="flat", padx=15, cursor="hand2")
        self.btn_auto.pack(side="left", padx=(0, 5))
        
        self.btn_report = tk.Button(btn_frame, text="📊 Report", command=self.generate_report, 
                                    bg="#FF9800", fg="white", font=("Segoe UI", 10), 
                                    relief="flat", padx=15, cursor="hand2")
        self.btn_report.pack(side="left", padx=(0, 5))
        
        self.btn_config = tk.Button(btn_frame, text="⚙️ Config", command=self.open_settings, 
                                    bg="#9C27B0", fg="white", font=("Segoe UI", 10), 
                                    relief="flat", padx=15, cursor="hand2")
        self.btn_config.pack(side="left", padx=(0, 5))

        self.btn_folder = tk.Button(btn_frame, text="📂 Logs", command=self.open_folder, 
                                    bg="#2196F3", fg="white", font=("Segoe UI", 10), 
                                    relief="flat", padx=15, cursor="hand2")
        self.btn_folder.pack(side="right")

        # Graph Area
        self.graph_frame = ttk.Frame(main_frame)
        self.graph_frame.pack(fill="both", expand=True)
        
        # Placeholder for graph
        self.lbl_no_data = ttk.Label(self.graph_frame, text="No historical data available.", font=("Segoe UI", 12))
        self.lbl_no_data.pack(expand=True)

    def create_card(self, parent, title, icon, col):
        """
        Creates a visual card (white rectangle with title and value).
        
        Structure:
        - White frame with border
        - Upper label: emoji + title
        - Lower label: numeric value (--) in bold
        
        Returns: Value label (to update later)
        """
        frame = tk.Frame(parent, bg="white", bd=1, relief="solid")
        frame.grid(row=0, column=col, padx=5, sticky="ew")
        
        lbl_title = tk.Label(frame, text=f"{icon} {title}", bg="white", fg="#666", font=("Segoe UI", 10))
        lbl_title.pack(pady=(10, 0))
        lbl_value = tk.Label(frame, text="--", bg="white", fg="#333", font=("Segoe UI", 16, "bold"))
        lbl_value.pack(pady=(5, 10))
        
        # Return frame, title label and value label to allow coloring later
        frame.lbl_title = lbl_title
        frame.lbl_value = lbl_value
        return lbl_value

    def start_test(self):
        if self.testing:
            messagebox.showwarning("Warning", "A test is already in progress.")
            return
        
        self.testing = True
        self.btn_test.config(state="disabled", text="Testing...", bg="#a5d6a7")
        self.lbl_status.config(text="Starting tests...", foreground="blue")
        self.progress.start(10)
        threading.Thread(target=self.execute_test_thread, daemon=True).start()

    def measure_packet_loss(self):
        try:
            # Execute ping to Google DNS (8.8.8.8) with 4 packets
            param = '-n' if os.name == 'nt' else '-c'
            command = ['ping', param, '4', '8.8.8.8']
            
            # On Windows, we need to hide the CMD window
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                       startupinfo=startupinfo, text=True)
            output, _ = process.communicate()
            
            # Look for "x% loss" or "x% de perda"
            match = re.search(r'(\d+)% loss', output) or re.search(r'(\d+)% de perda', output)
            if match:
                return int(match.group(1))
            return 0
        except Exception:
            return -1  # Measurement error

    def execute_test_thread(self):
        """
        Execute tests in separate thread (doesn't freeze UI).
        
        Flow:
        1. Speedtest (can take 30-60s)
        2. Packet loss test (5-10s per server)
        3. Save to CSV
        4. Update UI using root.after() (thread-safe)
        
        Important: Never update UI directly from thread!
        Always use root.after(0, lambda: ...) to return to main thread.
        """
        try:
            # 1. Execute Speedtest (slow)
            self.root.after(0, lambda: self.lbl_status.config(text="Running Speedtest (may take a while)..."))
            speed_result = self.tester.run_speedtest()
            
            # 2. Measure packet loss (fast)
            self.root.after(0, lambda: self.lbl_status.config(text="Measuring Packet Loss..."))
            packet_loss = self.tester.measure_packet_loss()
            
            # Prepare data
            date_time = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            
            # Save to CSV
            success, msg = self.data_manager.save_test(
                date_time,
                speed_result['download'],
                speed_result['upload'],
                speed_result['ping'],
                packet_loss,
                speed_result['isp'],
                speed_result['ip']
            )
            
            # Finalize in main thread
            self.root.after(0, lambda: self.finish_test(
                success, msg, date_time,
                speed_result['download'],
                speed_result['upload'],
                speed_result['ping'],
                packet_loss,
                speed_result['isp'],
                speed_result['ip']
            ))

        except Exception as e:
            error_message = str(e)
            if "403" in error_message:
                error_message = "Error 403: Speedtest API failure. Try updating: 'pip install speedtest-cli --upgrade'"
            self.root.after(0, lambda: self.finish_test(False, error_message))

    def finish_test(self, success, msg, date_time=None, down=0, up=0, ping=0, packet_loss=0, isp="--", ip="--"):
        self.testing = False
        self.progress.stop()
        self.btn_test.config(state="normal", text="START TEST", bg="#4CAF50")

        if success:
            self.lbl_status.config(text=f"Last Test: {date_time}", foreground="green")
            self.lbl_client_info.config(text=f"Provider: {isp} | IP: {ip}")
            
            # Update cards with visual quality indicators
            target_down = self.config.get('download_target', 1000)
            target_up = self.config.get('upload_target', 500)
            target_ping = self.config.get('ping_target', 20)
            
            self.update_card_with_color(self.card_down, down, target_down, f"{down:.1f} Mbps", higher_better=True)
            self.update_card_with_color(self.card_up, up, target_up, f"{up:.1f} Mbps", higher_better=True)
            self.update_card_with_color(self.card_ping, ping, target_ping, f"{ping:.0f} ms", higher_better=False)
            
            loss_text = f"{packet_loss}%" if packet_loss >= 0 else "Error"
            loss_color = "red" if packet_loss > 0 else "#333"
            self.card_loss.config(text=loss_text, fg=loss_color)
            
            # Update graph and statistics
            self.update_embedded_graph()
            self.update_statistics()
        else:
            self.lbl_status.config(text="Test error", foreground="red")
            messagebox.showerror("Error", f"Failure: {msg}")

    def update_embedded_graph(self):
        """Update embedded graph using DataManager"""
        # Clear graph area
        for widget in self.graph_frame.winfo_children():
            widget.destroy()

        df = self.data_manager.load_data()
        if df is None or df.empty:
            ttk.Label(self.graph_frame, text="Run a test to see the history.", 
                      font=("Segoe UI", 12)).pack(expand=True)
            return

        try:
            # Get last N records (configurable)
            last_n = self.config.get('graph_last_n', 30)
            df_plot = df.tail(last_n).copy()

            # Create Matplotlib figure
            fig = plt.Figure(figsize=(6, 4), dpi=100)
            ax = fig.add_subplot(111)
            
            ax.plot(df_plot['Date Time'], df_plot['Download (Mbps)'], label='Download', color='#2196F3', marker='o', linewidth=2, markersize=4)
            ax.plot(df_plot['Date Time'], df_plot['Upload (Mbps)'], label='Upload', color='#FF9800', marker='x', linestyle='--', linewidth=1.5, markersize=5)

            # Target lines (configurable)
            target_down = self.config.get('download_target', 1000)
            target_up = self.config.get('upload_target', 500)
            ax.axhline(y=target_down, color='r', linestyle=':', alpha=0.5, label=f'Target Down ({target_down})')
            ax.axhline(y=target_up, color='orange', linestyle=':', alpha=0.3, label=f'Target Up ({target_up})')
            
            ax.set_title(f'Recent History (Last {len(df_plot)} tests)', fontsize=10)
            ax.set_ylabel('Speed (Mbps)', fontsize=9)
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3, frameon=False)
            
            # Date formatting
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
            fig.autofmt_xdate()
            
            # Layout adjustment
            fig.tight_layout()

            # Embed in Tkinter
            canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            
        except Exception as e:
            ttk.Label(self.graph_frame, text=f"Error loading graph: {e}").pack()

    def load_last_test(self):
        """Load and display data from last performed test using DataManager"""
        try:
            df = self.data_manager.load_data()
            if df is not None and not df.empty:
                last = df.iloc[-1]
                self.lbl_client_info.config(
                    text=f"Provider: {last.get('Provider', '--')} | IP: {last.get('Client IP', '--')}"
                )
                self.update_statistics()
        except Exception as e:
            print(f"Error loading last test: {e}")
    
    def update_card_with_color(self, card_label, value, target, text, higher_better=True):
        """
        Update card with colors based on performance (green/yellow/red).
        
        Logic:
        - Green: >= 80% of target
        - Yellow: >= 50% of target
        - Red: < 50% of target
        
        For ping (lower is better), inverts the calculation.
        """
        card_label.config(text=text)
        
        # Calculate relative performance (0.0 to 1.0+)
        if higher_better:  # Download/Upload - higher is better
            performance = (value / target) if target > 0 else 0
            bg_color = "#C8E6C9" if performance >= 0.8 else "#FFECB3" if performance >= 0.5 else "#FFCDD2"
        else:  # Ping - lower is better
            performance = (target / value) if value > 0 else 0
            bg_color = "#C8E6C9" if performance >= 0.8 else "#FFECB3" if performance >= 0.5 else "#FFCDD2"
        
        # Update card background color (frame + labels)
        parent_frame = card_label.master
        parent_frame.config(bg=bg_color)
        if hasattr(parent_frame, 'lbl_title'):
            parent_frame.lbl_title.config(bg=bg_color)
        card_label.config(bg=bg_color)
    
    def update_statistics(self):
        """Calculate and display statistics using DataManager"""
        try:
            stats = self.data_manager.get_statistics(last_n=10)
            if stats is None:
                self.lbl_stats.config(text="No data for statistics")
                return
            
            stats_text = (f"📈 Last 10 tests - Download: Avg {stats['down_mean']:.1f} | "
                          f"Min {stats['down_min']:.1f} | Max {stats['down_max']:.1f} Mbps | "
                          f"Avg Ping: {stats['ping_mean']:.0f}ms | Total: {stats['total_tests']}")
            self.lbl_stats.config(text=stats_text)
        except Exception as e:
            self.lbl_stats.config(text=f"Error calculating statistics: {e}")
    
    def toggle_auto_test(self):
        """
        Toggle automatic periodic tests on/off.
        
        When activated:
        - Schedules tests using root.after() (Tkinter timer)
        - Interval configurable in config.json (auto_test_interval)
        """
        self.auto_test_active = not self.auto_test_active
        interval = self.config.get('auto_test_interval', 30)  # Minutes
        
        if self.auto_test_active:
            self.btn_auto.config(text="🔄 Auto (ON)", bg="#4CAF50")
            self.lbl_status.config(text=f"Auto test active (every {interval}min)", foreground="blue")
            self.schedule_next_test()
        else:
            self.btn_auto.config(text="🔄 Auto (OFF)", bg="#9E9E9E")
            if self.auto_test_job:  # Cancel pending timer
                self.root.after_cancel(self.auto_test_job)
                self.auto_test_job = None
            self.lbl_status.config(text="Auto test disabled", foreground="gray")
    
    def schedule_next_test(self):
        """Schedule next automatic test using root.after()"""
        if self.auto_test_active:
            interval = self.config.get('auto_test_interval', 30)  # Minutes
            interval_ms = interval * 60 * 1000  # Convert to milliseconds
            # Save job ID to be able to cancel later
            self.auto_test_job = self.root.after(interval_ms, self.execute_auto_test)
    
    def execute_auto_test(self):
        """Timer callback - execute test if none in progress"""
        if not self.testing:
            self.start_test()
        self.schedule_next_test()  # Schedule next one
    
    def generate_report(self):
        """
        Generate statistical report in plain text.
        
        Content:
        - Analyzed period (first/last test)
        - Download/upload/ping statistics (average, min, max, standard deviation)
        - Percentage of tests below target
        - Comparative analysis with contracted target
        """
        try:
            # Get statistics from ALL tests (not just last 10)
            stats = self.data_manager.get_statistics(last_n=len(self.data_manager.load_data() or []))
            df = self.data_manager.load_data()
            
            if df is None or df.empty or stats is None:
                messagebox.showinfo("Report", "No data available to generate report.")
                return
            
            # Tests below target
            target_down = self.config.get('download_target', 1000)
            target_up = self.config.get('upload_target', 500)
            poor_tests = df[df['Download (Mbps)'] < target_down * 0.8]
            poor_pct = (len(poor_tests) / len(df)) * 100
            
            first_date = stats['first_date'].strftime('%d/%m/%Y %H:%M')
            last_date = stats['last_date'].strftime('%d/%m/%Y %H:%M')
            
            # Build report
            report = f"""═══════════════════════════════════════════════════
   INTERNET MONITORING REPORT
═══════════════════════════════════════════════════

Period: {first_date} to {last_date}
Total Tests: {stats['total_tests']}
Contracted Target: {target_down} Mbps Down / {target_up} Mbps Up

--- DOWNLOAD ---
Average: {stats['down_mean']:.2f} Mbps
Standard Deviation: {stats['down_std']:.2f} Mbps
Minimum: {stats['down_min']:.2f} Mbps
Maximum: {stats['down_max']:.2f} Mbps
Performance: {(stats['down_mean']/target_down)*100:.1f}% of target

--- UPLOAD ---
Average: {stats['up_mean']:.2f} Mbps
Minimum: {stats['up_min']:.2f} Mbps
Maximum: {stats['up_max']:.2f} Mbps
Performance: {(stats['up_mean']/target_up)*100:.1f}% of target

--- LATENCY (PING) ---
Average: {stats['ping_mean']:.2f} ms
Minimum: {stats['ping_min']:.2f} ms
Maximum: {stats['ping_max']:.2f} ms

--- QUALITY ---
Tests below 80% of target: {len(poor_tests)} ({poor_pct:.1f}%)

═══════════════════════════════════════════════════
"""
            
            # Save report to file
            report_name = os.path.join(self.script_folder, f"report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            with open(report_name, 'w', encoding='utf-8') as f:
                f.write(report)
            
            # Open the report
            messagebox.showinfo("Report Generated", f"Report saved to:\n{report_name}")
            subprocess.Popen(f'notepad "{report_name}"')
            
        except Exception as e:
            messagebox.showerror("Error", f"Error generating report: {e}")
    
    def open_settings(self):
        """
        Open dialog window to edit settings.
        
        Allows editing:
        - Download/upload/ping targets (for visual indicators)
        - Automatic test interval
        - Number of tests displayed in graph
        - Ping servers and packet count
        
        Saves directly to config.json when clicking "Save".
        """
        config_window = tk.Toplevel(self.root)
        config_window.title("Settings")
        config_window.geometry("450x400")
        config_window.configure(bg="#f0f0f0")
        config_window.transient(self.root)  # Modal window
        config_window.grab_set()             # Block interaction with main window
        
        # Main frame
        main_frame = ttk.Frame(config_window, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        ttk.Label(main_frame, text="⚙️ Monitor Settings", 
                  font=("Segoe UI", 14, "bold")).pack(pady=(0, 20))
        
        # Configuration entries (editable fields)
        configs = []  # List to store (key, var, type) for each field
        
        def create_field(label, key, field_type=float):
            """Helper: creates an entry field with label and value from config.json"""
            frame = ttk.Frame(main_frame)
            frame.pack(fill="x", pady=5)
            ttk.Label(frame, text=label, width=25).pack(side="left")
            var = tk.StringVar(value=str(self.config.get(key)))  # Load current value
            entry = ttk.Entry(frame, textvariable=var, width=15)
            entry.pack(side="left", padx=10)
            configs.append((key, var, field_type))  # Save for later processing
            return var
        
        # Configuration fields
        create_field("Download Target (Mbps):", "download_target", int)
        create_field("Upload Target (Mbps):", "upload_target", int)
        create_field("Ping Target (ms):", "ping_target", int)
        create_field("Auto-Test Interval (min):", "auto_test_interval", int)
        create_field("Graph: Last N tests:", "graph_last_n", int)
        create_field("Ping: Packet count:", "ping_count", int)
        
        # Ping servers area
        ttk.Label(main_frame, text="\nPing Servers (one per line):", 
                  font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 5))
        
        ping_text = tk.Text(main_frame, height=6, width=40)
        ping_text.pack(fill="x", pady=5)
        ping_targets = self.config.get('ping_targets', [])
        ping_text.insert("1.0", "\n".join(ping_targets))
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=20)
        
        def save():
            """Save button callback - validates and persists settings"""
            try:
                # Save numeric fields (convert string -> int/float)
                for key, var, field_type in configs:
                    value = field_type(var.get())
                    self.config.update(key, value)
                
                # Save ping server list (Text widget with multiple lines)
                ping_lines = ping_text.get("1.0", "end").strip().split("\n")
                ping_list = [line.strip() for line in ping_lines if line.strip()]  # Remove empty lines
                self.config.update('ping_targets', ping_list)
                
                messagebox.showinfo("Success", "Settings saved successfully!", parent=config_window)
                
                # Update graph if necessary
                self.update_embedded_graph()
                config_window.destroy()
            except ValueError:
                messagebox.showerror("Error", "Please enter valid numeric values.", parent=config_window)
        
        tk.Button(btn_frame, text="💾 Save", command=save, 
                  bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold"),
                  relief="flat", padx=20, pady=5, cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(btn_frame, text="❌ Cancel", command=config_window.destroy,
                  bg="#f44336", fg="white", font=("Segoe UI", 10),
                  relief="flat", padx=20, pady=5, cursor="hand2").pack(side="left", padx=5)
    
    def open_folder(self):
        """Open script directory in Windows Explorer (to access logs/config)"""
        subprocess.Popen(f'explorer "{self.script_folder}"')


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    # Initialize Tkinter
    root = tk.Tk()
    
    # Create application instance (initializes all UI and components)
    app = InternetMonitorApp(root)
    
    # Start Tkinter event loop (keeps running until window is closed)
    root.mainloop()
