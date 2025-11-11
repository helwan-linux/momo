#!/usr/bin/env python3
"""
Momo - Helwan Linux Diagnostics (Ultimate Streaming + Dynamic Disks + Scrolling)
Author: Generated for Saeed Badrelden
"""

import curses
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import platform
import time

# --------------------------- Configuration ---------------------------
TESTS = [
    # RAM
    ("RAM Usage", "free -h", "free"),
    ("RAM Details", "cat /proc/meminfo", "cat"),
    ("RAM Stress Test", "stress-ng --vm 2 --vm-bytes 75% --cpu 2 --timeout 60s", "stress-ng"),
    ("Memtester 1024M", "memtester 1024M 1", "memtester"),
    ("Memory Speed", "sysbench memory --memory-block-size=1M --memory-total-size=1G run", "sysbench"),
    ("Swap Usage", "swapon --show", "swapon"),

    # CPU
    ("CPU Info", "lscpu", "lscpu"),
    ("CPU Details", "cat /proc/cpuinfo", "cat"),
    ("CPU Stress Test", "stress-ng --cpu 4 --timeout 30s", "stress-ng"),
    ("Sysbench CPU", "sysbench cpu run", "sysbench"),

    # Disk
    ("Smart Status", "sudo smartctl -a /dev/DEVICE_PLACEHOLDER", "smartctl"),
    ("Disk Speed", "sudo hdparm -tT /dev/DEVICE_PLACEHOLDER", "hdparm"),
    ("FIO Benchmark", "fio --name=randread --ioengine=libaio --iodepth=4 --rw=randread --bs=4k --direct=1 --size=512M --numjobs=4 --runtime=60 --time_based --group_reporting", "fio"),
    ("NVMe Smart", "sudo nvme smart-log /dev/DEVICE_PLACEHOLDER", "nvme"),
    ("NVMe Temperature", "sudo nvme smart-log /dev/DEVICE_PLACEHOLDER | grep temperature", "nvme"),
    ("Disk Usage", "df -h", "df"),

    # Temperature / Fans
    ("Sensors", "sensors", "sensors"),
    ("Fan Speed", "sensors | grep -i fan", "sensors"),
    ("Live Temperature Monitor", "watch -n 1 sensors", "sensors"),

    # Networking
    ("Ping Test", "ping -c 4 google.com", "ping"),
    ("Speedtest Internet", "speedtest-cli", "speedtest"),
    ("iPerf3 LAN Server", "iperf3 -s", "iperf3"),
    ("iPerf3 LAN Client", "iperf3 -c 127.0.0.1", "iperf3"),

    # GPU
    ("NVIDIA Info", "nvidia-smi", "nvidia-smi"),
    ("AMD Info", "radeontop", "radeontop"),
    ("OpenGL Info", "glxinfo | grep OpenGL", "glxinfo"),
    ("GPU Benchmark", "glmark2", "glmark2"),

    # System
    ("Kernel & OS", "uname -a", "uname"),
    ("Uptime", "uptime", "uptime"),
    ("Top Processes", "top -b -n 1", "top"),
    ("Host Info", "hostnamectl", "hostnamectl"),
    ("Boot Analysis", "systemd-analyze", "systemd-analyze"),
    ("Boot Slow Services", "systemd-analyze blame", "systemd-analyze"),

    # Battery
    ("Battery Info", "upower -i /org/freedesktop/UPower/devices/battery_BAT0", "upower"),
    ("Battery Percentage", "acpi", "acpi")
]

# Tests that require dynamic disk selection
DISK_TESTS = ["Smart Status", "Disk Speed", "NVMe Smart", "NVMe Temperature"]

# Define log directory and installation command for Arch Linux
LOG_DIR = Path.home() / ".momo" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
PACMAN_INSTALL = ["sudo", "pacman", "-S", "--noconfirm"]

# --------------------------- Utilities ---------------------------
def is_tool_installed(tool_name):
    """Check if a system command/tool is available."""
    if tool_name in ["cat", "free", "swapon", "df", "ping", "uptime", "uname", "top"]:
        return True
    return shutil.which(tool_name) is not None

def install_tool(tool_name):
    """Attempt to install a tool using Pacman."""
    try:
        # Some tools require specific package names (e.g., nvme-cli for nvme)
        package_map = {
            "nvme": "nvme-cli",
            "speedtest": "speedtest-cli",
            "hdparm": "hdparm",
            "smartctl": "smartmontools",
            "upower": "upower",
            "fio": "fio",
            "stress-ng": "stress-ng"
        }
        package_name = package_map.get(tool_name, tool_name)
        subprocess.run(PACMAN_INSTALL + [package_name], check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def write_log_stream(test_name, lines):
    """Write the collected output lines to a timestamped log file."""
    fname = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{sanitize_filename(test_name)}.log"
    path = LOG_DIR / fname
    with open(path, "w", encoding="utf-8", errors="ignore") as f:
        for line in lines:
            f.write(line+"\n")
    return path

def sanitize_filename(name):
    """Sanitize a string for use as a filename."""
    return "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in name).strip().replace(' ', '_')

# --------------------------- Disk Selection ---------------------------
def select_disk(stdscr):
    """
    Dynamically finds available disk devices (sda, nvme0n1, etc.)
    and prompts the user to select one for testing.
    """
    # Get all disk devices using lsblk
    result = subprocess.run("lsblk -d -o NAME,TYPE,SIZE -n", shell=True, capture_output=True, text=True)
    
    # Filter for devices that are of TYPE 'disk' (and not partitions, loops, etc.)
    disks = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1] == 'disk':
            disks.append(f"/dev/{parts[0]} ({parts[2]})") # e.g., "/dev/sda (256G)"

    if not disks:
        show_message(stdscr, "No storage disks found! Skipping disk test.")
        return None

    selected = 0
    while True:
        stdscr.clear()
        stdscr.addstr(1, 2, "Select a disk for this test (q=Cancel):", curses.A_BOLD)
        stdscr.addstr(2, 2, "Use arrows ↑↓ and Enter.")
        
        for idx, d in enumerate(disks):
            attr = curses.A_REVERSE if idx == selected else curses.A_NORMAL
            stdscr.addstr(4+idx, 4, d, attr)
        
        stdscr.refresh()
        c = stdscr.getch()
        
        if c in (curses.KEY_UP, ord('k')):
            selected = max(0, selected-1)
        elif c in (curses.KEY_DOWN, ord('j')):
            selected = min(len(disks)-1, selected+1)
        elif c in (curses.KEY_ENTER, ord('\n'), ord('\r')):
            # Extract just the device name (e.g., 'sda' from '/dev/sda (256G)')
            return disks[selected].split()[0].replace('/dev/', '') 
        elif c in (ord('q'), 27):
            return None

# --------------------------- Streaming Command ---------------------------
def run_command_stream(cmd):
    """Execute command and yield each line of output."""
    try:
        # Use Popen to run the command and capture output in real-time
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except FileNotFoundError:
        yield "Error: Command not found or shell failed to execute."
        return

    while True:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            # Process exited and no more output
            break
        if line:
            yield line.rstrip()
    
    # Check return code after reading all output
    if proc.returncode != 0 and proc.returncode is not None:
        yield f"\n*** Command finished with non-zero exit code: {proc.returncode} ***"

# --------------------------- Curses TUI ---------------------------
class MomoTUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.curs_set(0) # Hide cursor
        # Enable non-blocking input for immediate key presses
        self.stdscr.nodelay(False) 
        self.height, self.width = self.stdscr.getmaxyx()
        self.menu_items = [t[0] for t in TESTS] + ["Run All Tests", "View Logs Folder", "Exit"]
        self.selected = 0

    def draw(self):
        """Draws the main menu."""
        self.stdscr.erase()
        title = "Momo - Helwan Linux Diagnostics (Ultimate Streaming)"
        subtitle = "Arrows ↑↓ • Enter to run • q=Quit"
        
        self.stdscr.addstr(1, max(0, (self.width-len(title))//2), title, curses.A_BOLD)
        self.stdscr.addstr(2, max(0, (self.width-len(subtitle))//2), subtitle)
        
        for idx, item in enumerate(self.menu_items):
            y = 4 + idx
            attr = curses.A_REVERSE if idx == self.selected else curses.A_NORMAL
            self.stdscr.addstr(y, 4, f"{idx+1:2d}. {item}"[:self.width-8], attr)
        
        self.stdscr.addstr(self.height-2, 2, f"Logs: {LOG_DIR}", curses.A_DIM)
        self.stdscr.refresh()

    def run(self):
        """Main TUI loop."""
        while True:
            self.draw()
            c = self.stdscr.getch()
            
            if c in (curses.KEY_UP, ord('k')):
                self.selected = max(0, self.selected-1)
            elif c in (curses.KEY_DOWN, ord('j')):
                self.selected = min(len(self.menu_items)-1, self.selected+1)
            elif c in (curses.KEY_ENTER, ord('\n'), ord('\r')):
                self.handle_selection(self.selected)
                if self.menu_items[self.selected]=="Exit":
                    break
            elif c in (ord('q'), 27):
                break

    def handle_selection(self, idx):
        """Routes selection to the appropriate handler."""
        item = self.menu_items[idx]
        if item=="Run All Tests":
            self.run_all()
        elif item=="View Logs Folder":
            self.open_logs()
        elif item=="Exit":
            return
        else:
            self.run_test(idx)

    def run_test(self, idx):
        """
        Runs a specific test with streaming output and manual scrolling support.
        This function is the core of the TUI logic.
        """
        test_name, cmd, tool = TESTS[idx]
        
        # 1. Tool Installation Check
        if not is_tool_installed(tool):
            ans = prompt_yes_no(self.stdscr, f"Tool '{tool}' not found. Install via pacman?")
            if ans:
                ok = install_tool(tool)
                if not ok:
                    show_message(self.stdscr, f"Installation failed. Skipping {test_name}")
                    return
            else:
                show_message(self.stdscr, f"Skipping {test_name} (tool not installed)")
                return

        # 2. Dynamic Disk Handling (Substitution)
        final_cmd = cmd
        if test_name in DISK_TESTS:
            disk = select_disk(self.stdscr)
            if disk is None:
                show_message(self.stdscr, f"Skipping {test_name} (no disk selected or canceled)")
                return
            
            # The placeholder is now unique, making substitution safer.
            final_cmd = cmd.replace("DEVICE_PLACEHOLDER", disk)


        # 3. Streaming and Scrolling Setup
        
        # Area for output (relative coordinates from stdscr)
        PAD_START_Y = 4
        PAD_HEIGHT = self.height - PAD_START_Y - 2 # Reserve space for header and footer
        
        # Initialize pad and state variables
        pad = curses.newpad(1000, self.width) # Start with 1000 lines
        pad_lines = 0
        scroll_offset = 0 # Vertical scroll position within the pad
        lines_buffer = [] # Buffer to store all lines for logging
        
        self.stdscr.clear()
        self.stdscr.addstr(1, 2, f"Running: {test_name}", curses.A_BOLD)
        self.stdscr.addstr(2, 2, f"Command: {final_cmd[:self.width-12]}", curses.A_DIM)
        self.stdscr.addstr(self.height - 2, 2, "s=Stop | ↑↓=Scroll | q=Quit Test", curses.A_REVERSE)
        self.stdscr.refresh()
        
        # Enable non-blocking input for real-time key check
        self.stdscr.nodelay(True)
        
        # 4. Main Streaming Loop
        proc_gen = run_command_stream(final_cmd)
        is_running = True
        
        while is_running or pad_lines > 0:
            if is_running:
                try:
                    line = next(proc_gen)
                    lines_buffer.append(line)
                    
                    # Write line to pad
                    pad.addstr(pad_lines, 0, line[:self.width-2])
                    pad_lines += 1
                    
                    # Ensure the pad is large enough (resize if needed)
                    if pad_lines >= pad.getmaxyx()[0] - 1:
                        # Resize pad: double the size, keep existing content
                        pad.resize(pad.getmaxyx()[0] + 500, self.width)

                    # Auto-scroll: if the user hasn't manually scrolled up, keep the latest line visible
                    if scroll_offset == pad_lines - PAD_HEIGHT - 1 or pad_lines < PAD_HEIGHT:
                        scroll_offset = max(0, pad_lines - PAD_HEIGHT)
                        
                except StopIteration:
                    is_running = False
                except Exception as e:
                    is_running = False
                    lines_buffer.append(f"Internal Error: {e}")
                    pad.addstr(pad_lines, 0, f"Internal Error: {e}")
                    pad_lines += 1

            # 5. Handle Input (Scroll and Stop)
            c = self.stdscr.getch()
            if c != curses.ERR:
                if c in (ord('s'), ord('q')):
                    # Use a shell signal to stop the process gracefully (SIGINT/SIGTERM)
                    # Note: Popen is inside run_command_stream, so we can't directly terminate it here.
                    # We rely on the generator finishing. For now, we only break the TUI loop.
                    is_running = False 
                    show_message(self.stdscr, f"Test stopped by user.")
                    break # Exit the while loop
                
                elif c in (curses.KEY_UP, ord('k')):
                    scroll_offset = max(0, scroll_offset - 1)
                
                elif c in (curses.KEY_DOWN, ord('j')):
                    # Prevent scrolling past the last line of output
                    max_scroll = max(0, pad_lines - PAD_HEIGHT - 1)
                    scroll_offset = min(scroll_offset + 1, max_scroll)
            
            # 6. Refresh Display
            # pad.refresh(pad_row_start, pad_col_start, screen_row_start, screen_col_start, screen_row_end, screen_col_end)
            pad.refresh(scroll_offset, 0, PAD_START_Y, 2, PAD_START_Y + PAD_HEIGHT, self.width - 2)
            
            if not is_running:
                # If the process is finished, we wait for user input to exit this view
                self.stdscr.addstr(self.height - 2, 2, "Test FINISHED. Press ENTER/any key to continue.", curses.A_REVERSE)
                self.stdscr.refresh()
                if c in (curses.KEY_ENTER, ord('\n'), ord('\r')):
                    break
                time.sleep(0.05) # Throttle loop slightly if running in finished state
            elif is_running:
                time.sleep(0.01) # Small throttle to avoid 100% CPU usage during active streaming
            
        # 7. Cleanup and Logging
        self.stdscr.nodelay(False) # Restore blocking input
        logpath = write_log_stream(test_name, lines_buffer)
        
        # Provide final success message
        show_message(self.stdscr, f"Finished: {test_name}\nLog saved: {logpath}")

    def run_all(self):
        """Runs all tests sequentially."""
        show_message(self.stdscr, "Starting 'Run All Tests'. Please note that tests requiring user selection (like Disk tests) will be skipped in this mode for simplicity.")
        
        for i in range(len(TESTS)):
            test_name = TESTS[i][0]
            # Skip interactive disk tests in 'Run All' mode
            if test_name in DISK_TESTS or test_name == "FIO Benchmark":
                continue 
            
            self.run_test(i)
        
        show_message(self.stdscr, f"All non-interactive tests completed.\nLogs saved in {LOG_DIR}")

    def open_logs(self):
        """Attempts to open the logs folder in the desktop file manager."""
        fm = shutil.which("xdg-open")
        if fm:
            subprocess.Popen([fm, str(LOG_DIR)])
        else:
            show_message(self.stdscr, f"Logs folder location:\n{LOG_DIR}")

# --------------------------- UI Helpers ---------------------------
def prompt_yes_no(stdscr, question):
    """Simple curses prompt for Yes/No questions."""
    while True:
        stdscr.clear()
        stdscr.addstr(2, 2, question)
        stdscr.addstr(4, 4, "y=Yes  n=No  q=Cancel")
        stdscr.refresh()
        c = stdscr.getch()
        if c in (ord('y'), ord('Y')):
            return True
        if c in (ord('n'), ord('N'), ord('q'), 27):
            return False

def show_message(stdscr, message):
    """Displays a non-interactive message until any key is pressed."""
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    for i, ln in enumerate(message.split('\n')):
        stdscr.addstr(2+i, 2, ln[:w-4])
    stdscr.addstr(h-2, 2, "Press any key to continue...", curses.A_DIM)
    stdscr.refresh()
    stdscr.getch()

# --------------------------- Entry Point ---------------------------
def main(stdscr):
    """Entry point for the Curses application."""
    if platform.system() != "Linux":
        # Cannot run commands on non-Linux OS
        print("Momo runs only on Linux (Arch/Arch-based). Exiting.")
        return
    tui = MomoTUI(stdscr)
    tui.run()

if __name__=="__main__":
    try:
        curses.wrapper(main)
    except curses.error as e:
        print(f"Curses Error: {e}")
        print("Ensure your terminal supports the necessary capabilities (e.g., check TERM environment variable).")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
