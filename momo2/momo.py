#!/usr/bin/env python3
"""
Momo - Helwan Linux Diagnostics Tool (TUI Stable Version with Curses)
Author: Saeed Badrelden (Based on original code)

NOTE: This version is robust and features interactive scrolling and safe test termination,
making it superior to the basic CLI version (momo10.py).
"""

import curses
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import platform
import sys
import time # Added for stable UI drawing

# --------------------------- Configuration ---------------------------
TESTS = [
    ("RAM Usage", "free -h", "free"),
    ("RAM Details", "cat /proc/meminfo", "cat"),
    ("RAM Stress Test (30s)", "stress-ng --vm 2 --vm-bytes 75% --cpu 2 --timeout 30s", "stress-ng"),
    ("Memtester 512M", "memtester 512M 1", "memtester"),
    ("Memory Speed", "sysbench memory --memory-block-size=1M --memory-total-size=512M run", "sysbench"),
    ("Swap Usage", "swapon --show", "swapon"),
    ("CPU Info", "lscpu", "lscpu"),
    ("CPU Stress Test (20s)", "stress-ng --cpu 2 --timeout 20s", "stress-ng"),
    ("Smart Status", "smartctl -a /dev/sda", "smartctl"),
    ("Disk Speed", "hdparm -tT /dev/sda", "hdparm"),
    ("Disk Usage", "df -h", "df"),
    ("Sensors", "sensors", "sensors"),
    ("Ping Test", "ping -c 2 google.com", "ping"),
]

LOG_DIR = Path.home() / ".momo" / "logs"
DISK_TESTS = ["Smart Status", "Disk Speed"]

# --------------------------- Helper Functions --------------------------

def check_tool_available(tool):
    return shutil.which(tool) is not None

def get_disks():
    if platform.system() != 'Linux':
        return []
    # Find all major disk devices (e.g., sda, sdb, nvme0n1)
    result = subprocess.run("lsblk -ndo NAME", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        # Filter out loop devices and temporary devices
        disks = [d.strip() for d in result.stdout.splitlines() if not d.strip().startswith('loop') and d.strip()]
        return disks
    return []

def select_disk(stdscr):
    disks = get_disks()
    if not disks:
        show_message(stdscr, "No disks found for testing.")
        return None

    stdscr.clear()
    stdscr.addstr(1, 2, "Select Disk to Test:", curses.A_BOLD)
    for i, disk in enumerate(disks):
        stdscr.addstr(3 + i, 2, f"{i+1}. /dev/{disk}")
    stdscr.addstr(len(disks) + 4, 2, "Enter number or 'c' to Cancel:")
    stdscr.refresh()

    while True:
        try:
            choice = stdscr.getch()
            if choice == ord('c'):
                return None
            
            choice = int(chr(choice)) - 1
            if 0 <= choice < len(disks):
                return disks[choice]
        except (ValueError, IndexError):
            continue
        except Exception:
            # Handle potential curses/getch errors
            continue

def run_command_stream(cmd, stop_flag=None):
    try:
        # Use shell=True for complex commands with pipes/redirection
        process = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
        )
        for line in process.stdout:
            # yield the line instantly
            yield line.rstrip()
            if stop_flag and stop_flag["stop"]:
                # Send SIGTERM to stop the subprocess safely
                process.terminate()
                process.wait()
                yield "\n--- Test Terminated by User ---"
                break
        
        # Ensure the process is fully closed
        if process.poll() is None:
            process.wait()
        
    except FileNotFoundError:
        yield f"ERROR: Command not found or tool not installed. Command: {cmd}"
    except Exception as e:
        yield f"ERROR: An exception occurred: {e}"

def write_log_stream(test_name, lines):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    sanitized_name = test_name.replace(" ", "_").replace("/", "_")
    log_file = LOG_DIR / f"{sanitized_name}_{timestamp}.log"
    try:
        with log_file.open("w", encoding="utf-8") as f:
            f.write(f"--- Momo Diagnostics Log: {test_name} ---\n")
            f.write(f"Date: {timestamp}\n")
            f.write("-" * 50 + "\n")
            for line in lines:
                f.write(line + "\n")
            f.write("-" * 50 + "\n")
        return log_file.name
    except Exception as e:
        return f"Failed to write log: {e}"

def show_message(stdscr, message):
    stdscr.clear()
    stdscr.border(0)
    lines = message.split('\n')
    for i, line in enumerate(lines):
        try:
            stdscr.addstr(2 + i, 2, line)
        except curses.error:
            pass # Ignore if message exceeds window size
    stdscr.addstr(len(lines) + 4, 2, "Press any key to continue...")
    stdscr.refresh()
    stdscr.getch()

# --------------------------- Main Application Class --------------------------

class MomoApp:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.curs_set(0) # Hide cursor
        self.height, self.width = stdscr.getmaxyx()
        self.current_selection = 0
        
        # Color initialization (for better visibility)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE) # Highlight color

    def draw_menu(self):
        self.stdscr.clear()
        self.stdscr.border(0)
        self.stdscr.addstr(1, 2, "Momo - Helwan Linux Diagnostics", curses.A_BOLD)
        self.stdscr.addstr(self.height - 2, 2, "Use ↑↓ to navigate, Enter to select, 'A' for All, 'Q' to quit.", curses.A_DIM)

        # Draw the actual menu items
        menu_items = [name for name, _, _ in TESTS]
        menu_items.append("Run All Tests (Full Diagnosis)")
        menu_items.append("Exit Momo")

        for i, item in enumerate(menu_items):
            x = 4
            y = 3 + i
            style = curses.A_NORMAL
            
            # Check for tool availability and dim if missing
            if i < len(TESTS) and not check_tool_available(TESTS[i][2]):
                item_display = f"[MISSING] {item}"
                style |= curses.A_DIM
            else:
                item_display = item
                
            # Highlight the current selection
            if i == self.current_selection:
                style |= curses.color_pair(1)

            try:
                self.stdscr.addstr(y, x, item_display, style)
            except curses.error:
                pass # Ignore if screen is too small

        self.stdscr.refresh()
        
    def run_menu(self):
        while True:
            self.draw_menu()
            
            # Use nodelay for the main menu loop to ensure quick response
            self.stdscr.nodelay(False)
            c = self.stdscr.getch()

            if c == curses.KEY_UP:
                self.current_selection = max(0, self.current_selection - 1)
            elif c == curses.KEY_DOWN:
                self.current_selection = min(len(TESTS) + 1, self.current_selection + 1)
            elif c in (curses.KEY_ENTER, 10, 13):
                # Execute selected action
                if self.current_selection < len(TESTS):
                    self.run_test(self.current_selection)
                elif self.current_selection == len(TESTS):
                    self.run_all()
                elif self.current_selection == len(TESTS) + 1:
                    break
            elif c in (ord('a'), ord('A')):
                self.run_all()
            elif c in (ord('q'), ord('Q')):
                break
            
            # Mandatory sleep for stable UI refresh, reducing flicker
            time.sleep(0.01) 


    def run_test(self, index):
        test_name, cmd, tool = TESTS[index]
        
        if not check_tool_available(tool):
            show_message(self.stdscr, f"Error: Required tool '{tool}' is not installed or not in PATH.\nInstall it via your package manager (e.g., 'sudo pacman -S {tool}').")
            return

        # Handle Disk Tests
        if test_name in DISK_TESTS:
            disk = select_disk(self.stdscr)
            if disk is None:
                return # User cancelled
            cmd = cmd.replace("/dev/sda", f"/dev/{disk}")

        # Display area setup
        self.stdscr.clear()
        self.stdscr.border(0)
        self.stdscr.addstr(1, 2, f"Running Test: {test_name} (Press 'Q' or 'S' to STOP)", curses.A_BOLD)
        self.stdscr.addstr(self.height - 2, 2, "Use ↑↓ to scroll. Log will be saved automatically.", curses.A_DIM)
        self.stdscr.refresh()

        stop_flag = {"stop": False}
        lines = []
        pad_height = 5000 # Max lines buffer
        
        # Create a new pad for the streaming output
        pad = curses.newpad(pad_height, self.width-4)
        offset = 0
        idx_line = 0
        
        # Set nodelay=True inside the run loop for non-blocking input check
        self.stdscr.nodelay(True) 

        for line in run_command_stream(cmd, stop_flag):
            if idx_line >= pad_height:
                # Stop if pad buffer is full
                lines.append("--- PAD BUFFER FULL. Output truncated. ---")
                break 
                
            lines.append(line)
            try:
                # Add line to the pad
                pad.addstr(idx_line, 0, line[:self.width-6])
            except curses.error:
                pass 
                
            idx_line += 1
            
            # Auto-scroll down if not manually scrolling
            if idx_line > (self.height - 6) and offset < idx_line - (self.height - 6):
                 offset = idx_line - (self.height - 6)
            
            # Refresh pad to show current output
            # (offset, 0) - top-left corner of the pad to display
            # (3, 2, self.height-4, self.width-2) - screen area where pad is shown
            pad.refresh(offset, 0, 3, 2, self.height-4, self.width-2)
            
            # Check for input to scroll or stop (non-blocking)
            c = self.stdscr.getch()
            if c == curses.KEY_UP:
                offset = max(0, offset-1)
            elif c == curses.KEY_DOWN:
                offset += 1
            elif c in (ord('s'), ord('q')):
                stop_flag["stop"] = True
                # Break here to allow run_command_stream to handle termination
                break 
                
            # Sleep slightly to prevent CPU overload during streaming
            time.sleep(0.005) 

        # Return to blocking input after test completion
        self.stdscr.nodelay(False)
        
        # Final refresh for the last bit of output
        pad.refresh(offset, 0, 3, 2, self.height-4, self.width-2)
        
        logpath = write_log_stream(test_name, lines)
        show_message(self.stdscr, f"Finished: {test_name}\nLog: {logpath}")

    def run_all(self):
        for i in range(len(TESTS)):
            # This loop calls run_test and waits for each one to finish
            self.run_test(i)
        show_message(self.stdscr, f"All tests completed.\nLogs saved in: {LOG_DIR}")

# --------------------------- Entry Point ---------------------------\
def main(stdscr):
    if platform.system() != "Linux":
        show_message(stdscr, "Momo runs only on Linux. Exiting.")
        return

    try:
        app = MomoApp(stdscr)
        app.run_menu()
    except Exception as e:
        # Emergency exit/error handling
        stdscr.clear()
        stdscr.addstr(1, 1, "FATAL ERROR OCCURRED:")
        stdscr.addstr(2, 1, str(e))
        stdscr.addstr(4, 1, "Press any key to exit.")
        stdscr.refresh()
        stdscr.getch()

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except curses.error as e:
        print(f"A curses error occurred. Try running the program in a standard terminal. Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
