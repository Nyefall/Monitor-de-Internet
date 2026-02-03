# Internet Monitor

A desktop application built in Python that **monitors your internet connection quality in real-time**. It runs speed tests (download/upload), measures latency (ping), and detects packet loss, saving all history for later analysis.

## 🎯 What This Project Does

- **Tests actual speed** of your internet (download and upload in Mbps)
- **Measures latency** (ping) to test servers
- **Detects packet loss** by pinging multiple DNS servers (Google, Cloudflare, OpenDNS)
- **Saves history** of all tests in CSV for analysis
- **Generates graphs** showing quality evolution over time
- **Compares with your targets** and visually indicates if connection is good (green), fair (yellow), or poor (red)
- **Automates tests** at configurable intervals (e.g., every 30 minutes)
- **Generates reports** with complete statistical analysis

**Ideal for:** Documenting issues with your ISP, monitoring connection quality throughout the day, or simply tracking if you're getting what you're paying for.

## 🛠️ Technologies Used

| Technology | Version | Why It Was Chosen |
|------------|---------|-------------------|
| **Python** | 3.7+ | Versatile language, great for automation with mature data analysis libraries |
| **Tkinter** | Native | Python's native GUI, no extra dependencies, works on any OS |
| **speedtest-cli** | 2.1+ | Official Speedtest.net library, reliable and recognized results |
| **pandas** | 1.0+ | Industry standard for data manipulation, facilitates statistical calculations |
| **matplotlib** | 3.0+ | Robust graphing library, integrates well with Tkinter |

**Why these choices?**
- **Python + Tkinter:** Allows creating a portable executable without complex installations
- **speedtest-cli:** Uses the same infrastructure as speedtest.net, ensuring accuracy
- **pandas + matplotlib:** Classic combination for data analysis and visualization
- **MVC Architecture:** Code organized in separate classes for easy maintenance

## 🚀 Features

### Testing and Monitoring
- **Speed Test:** Measures Download, Upload, and Ping using `speedtest-cli`
- **Packet Loss:** Tests multiple servers (Google DNS, Cloudflare, OpenDNS) for greater reliability
- **Automatic Tests:** Runs tests periodically at configurable intervals
- **Visual Indicators:** Color-coded cards indicating quality (green/yellow/red)

### Analysis and Reports
- **Graphical Dashboard:** Interactive history visualization with target lines
- **Real-Time Statistics:** Averages, minimums, and maximums from recent tests
- **Detailed Reports:** Automatic generation of statistical analysis in text format
- **Persistent History:** All data saved in CSV with automatic migration

### Configuration
- **Settings Menu:** GUI to adjust all targets and parameters
- **config.json File:** External configuration without needing to edit code
- **Customizable:** Speed targets, test intervals, ping servers, etc.

## 📋 Prerequisites

- **Python 3.7 or higher** ([Download here](https://www.python.org/downloads/))
- **Internet connection** (for tests to work)
- **Windows, Linux, or macOS** (cross-platform)

## 🔧 Installation and Execution

### Step 1: Clone the repository
```bash
git clone https://github.com/Nyefall/Monitor-de-Internet.git
cd Monitor-de-Internet
```

### Step 2: Install dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Run the application
```bash
python "Internet Monitor.py"
```

> 💡 **Tip:** On first run, a `config.json` file will be automatically created with default values. You can customize it later.

### Alternative: Run without cloning
```bash
# Download the repository ZIP, extract it, and in the folder:
pip install speedtest-cli pandas matplotlib
python "Internet Monitor.py"
```

## 🎯 How to Use

### Main Interface
After running, you'll see a dashboard with 4 metric cards and action buttons:

```
┌─────────────────────────────────────────────────────┐
│  Monitoring Dashboard                               │
├──────────┬──────────┬──────────┬──────────┐        │
│ Download │  Upload  │   Ping   │  Loss    │        │
│ 450 Mbps │ 230 Mbps │  12 ms   │   0%     │        │
└──────────┴──────────┴──────────┴──────────┘        │
│                                                     │
│  [START TEST] [Auto] [Report] [Config] [Logs]      │
│                                                     │
│                                                     │
│  📈 History graph here                             │
└─────────────────────────────────────────────────────┘
```

### Available Buttons
| Button | Function |
|--------|----------|
| **START TEST** | Runs a single speed test |
| **🔄 Auto** | Toggles automatic periodic tests on/off |
| **📊 Report** | Generates statistical analysis in a .txt file |
| **⚙️ Config** | Opens menu to adjust targets and settings |
| **📂 Logs** | Opens folder with CSV and generated reports |

### Customizing
Click **⚙️ Config** to adjust:
- Download/Upload/Ping targets (for color indicators)
- Interval between automatic tests
- Ping servers for redundancy
- Number of tests displayed in the graph

## ⚙️ Available Settings

Edit via GUI (⚙️ Config) or directly in `config.json`:

```json
{
    "download_target": 1000,         // Download target in Mbps
    "upload_target": 500,            // Upload target in Mbps
    "ping_target": 20,               // Maximum acceptable latency (ms)
    "auto_test_interval": 30,        // Minutes between automatic tests
    "ping_targets": [                // Servers for packet loss test
        "8.8.8.8",                   // Google DNS
        "1.1.1.1",                   // Cloudflare DNS
        "208.67.222.222"             // OpenDNS
    ],
    "ping_count": 4,                 // Number of packets per server
    "graph_last_n": 30               // Tests displayed in graph
}
```

## 🏗️ Architecture (MVC)

The code follows a separation of concerns pattern with **complete inline documentation**:

- **`ConfigManager`:** Manages configuration via JSON
- **`InternetTester`:** Executes speed and ping tests (business logic)
- **`DataManager`:** Manages CSV with cache and automatic migration
- **`InternetMonitorApp`:** GUI and coordination (UI only)

**Code Quality:**
- ✅ 100% documented (docstrings + explanatory comments)
- ✅ Type hints on all public functions
- ✅ No unused imports
- ✅ ~1000 well-organized lines in 4 classes
- ✅ Thread-safe for responsive UI

## 📁 File Structure

```
Monitor-de-Internet/
├── Internet Monitor.py          # Main code (~1000 lines, 4 classes)
├── config.json                  # Settings (auto-generated)
├── internet_monitor.csv         # Historical data (generated after 1st test)
├── report_*.txt                 # Generated reports
├── requirements.txt             # Python dependencies
├── README.md                    # This file
├── IMPROVEMENTS.md              # Technical documentation of implemented improvements
├── .gitignore                   # Files ignored by Git
└── .gitattributes               # Git configuration
```

## 📚 Documentation

- **README.md:** Usage and installation guide
- **IMPROVEMENTS.md:** Technical details of refactoring and implemented improvements
- **Source code:** 100% documented with docstrings and explanatory comments

## 🐛 Troubleshooting

**Speedtest 403 Error:**
```bash
pip install speedtest-cli --upgrade
```

**Ping not working:**
- Check your firewall
- Test with different servers in the Config menu

**Corrupted CSV:**
- The system performs automatic migration
- If issues persist, delete the CSV and run a new test

## 🤝 Contributing

Contributions are welcome! Open issues or pull requests.

## 📄 License

MIT License

This project is licensed under the MIT License. See the LICENSE file for details.
