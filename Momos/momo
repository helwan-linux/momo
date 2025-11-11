#!/usr/bin/env python3
"""
Momo - Helwan Linux Diagnostics (Full Pad + Streaming Version)
Author: Saeed Badrelden
"""

import curses
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import platform

# --------------------------- Configuration ---------------------------
TESTS = [
    ("RAM Usage", "free -h", "free"),
    ("RAM Details", "cat /proc/meminfo", "cat"),
    ("RAM Stress Test", "stress-ng --vm 2 --vm-bytes 75% --cpu 2 --timeout 30s", "stress-ng"),
    ("Memtester 512M", "memtester 512M 1", "memtester"),
    ("Memory Speed", "sysbench memory --memory-block-size=1M --memory-total-size=512M run", "sysbench"),
    ("Swap Usage", "swapon --show", "swapon"),
    ("CPU Info", "lscpu", "lscpu"),
    ("CPU Stress Test", "stress-ng --cpu 2 --timeout 20s", "stress-ng"),
    ("Smart Status", "smartctl -a /dev/sda", "smartctl"),
    ("Disk Speed", "hdparm -tT /dev/sda", "hdparm"),
    ("Disk Usage", "df -h", "df"),
    ("Sensors", "sensors", "sensors"),
    ("Ping Test", "ping -c 2 google.com", "ping"),
]

LOG_DIR = Path.home() / ".momo" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
DISK_TESTS = ["Smart Status", "Disk Speed"]

# --------------------------- Utilities ---------------------------
def is_tool_installed(tool_name):
    if tool_name in ["cat", "free", "swapon", "df", "ping"]:
        return True
    return shutil.which(tool_name) is not None

def write_log_stream(test_name, lines):
    fname = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{sanitize_filename(test_name)}.log"
    path = LOG_DIR / fname
    with open(path, "w", encoding="utf-8", errors="ignore") as f:
        for line in lines:
            f.write(line+"\n")
    return path

def sanitize_filename(name):
    return "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in name).strip().replace(' ', '_')

# --------------------------- Disk Selection ---------------------------
def select_disk(stdscr):
    try:
        # Use lsblk to find disks
        result = subprocess.run("lsblk -d -o NAME,TYPE,SIZE -n", shell=True, capture_output=True, text=True)
        disks = [line.split()[0] for line in result.stdout.splitlines() if "disk" in line]
    except Exception:
        disks = []

    if not disks:
        show_message(stdscr, "No disks found!")
        return None

    selected = 0
    while True:
        stdscr.clear()
        stdscr.addstr(1, 2, "Select a disk for this test (q=Cancel):")
        for idx, d in enumerate(disks):
            attr = curses.A_REVERSE if idx == selected else curses.A_NORMAL
            stdscr.addstr(3+idx, 4, d[:40], attr)
        stdscr.refresh()
        c = stdscr.getch()
        if c in (curses.KEY_UP, ord('k')):
            selected = max(0, selected-1)
        elif c in (curses.KEY_DOWN, ord('j')):
            selected = min(len(disks)-1, selected+1)
        elif c in (curses.KEY_ENTER, ord('\n'), ord('\r')):
            return disks[selected]
        elif c in (ord('q'), 27):
            return None

# --------------------------- Streaming Command ---------------------------
def run_command_stream(cmd, stop_flag):
    try:
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        while True:
            if stop_flag["stop"]:
                proc.terminate()
                break
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            if line:
                yield line.rstrip()
    except Exception as e:
        yield f"Error running command: {e}"

# --------------------------- UI Helpers ---------------------------
def show_message(stdscr, message):
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    for i, ln in enumerate(message.split('\n')):
        if i + 2 >= h - 1:
            break
        stdscr.addstr(2+i, 2, ln[:w-4])
    stdscr.addstr(h-2, 2, "Press any key to continue...", curses.A_DIM)
    stdscr.refresh()
    stdscr.getch()

def prompt_yes_no(stdscr, question):
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

# --------------------------- Momo TUI ---------------------------
class MomoTUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.curs_set(0)
        self.height, self.width = self.stdscr.getmaxyx()
        self.menu_items = [t[0] for t in TESTS] + ["Run All Tests", "Exit"]
        self.selected = 0
        self.pad_offset = 0
        self.pad_height = max(len(self.menu_items)+10, 100)
        self.menu_pad = curses.newpad(self.pad_height, self.width)

    def draw(self):
        self.stdscr.erase()
        title = "Momo - Helwan Linux Diagnostics"
        subtitle = "↑↓ Arrows • Enter=Run • s=Stop • q=Quit"
        self.stdscr.addstr(1, max(0, (self.width-len(title))//2), title, curses.A_BOLD)
        self.stdscr.addstr(2, max(0, (self.width-len(subtitle))//2), subtitle)
        
        # Update Pad with the menu
        self.menu_pad.erase()
        for idx, item in enumerate(self.menu_items):
            attr = curses.A_REVERSE if idx == self.selected else curses.A_NORMAL
            try:
                self.menu_pad.addstr(idx, 2, f"{idx+1:2d}. {item}"[:self.width-4], attr)
            except curses.error:
                pass
        
        # Display part of Pad
        visible_height = self.height - 5
        if self.selected < self.pad_offset:
            self.pad_offset = self.selected
        elif self.selected >= self.pad_offset + visible_height:
            self.pad_offset = self.selected - visible_height +1
        self.menu_pad.refresh(self.pad_offset, 0, 4, 0, self.height-2, self.width-1)
        self.stdscr.addstr(self.height-1, 2, f"Logs: {LOG_DIR}", curses.A_DIM)
        self.stdscr.refresh()

    def run(self):
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
        item = self.menu_items[idx]
        if item=="Run All Tests":
            self.run_all()
        elif item=="Exit":
            return
        else:
            self.run_test(idx)

    def run_test(self, idx):
        test_name, cmd, tool = TESTS[idx]
        if not is_tool_installed(tool):
            ans = prompt_yes_no(self.stdscr, f"Tool '{tool}' not found. Skip?")
            if not ans:
                return

        if test_name in DISK_TESTS:
            disk = select_disk(self.stdscr)
            if disk is None:
                show_message(self.stdscr, f"Skipping {test_name} (no disk selected)")
                return
            cmd = cmd.replace("/dev/sda", f"/dev/{disk}")

        stop_flag = {"stop": False}
        lines = []
        pad_height = 5000
        pad = curses.newpad(pad_height, self.width-2)
        offset = 0
        idx_line = 0

        for line in run_command_stream(cmd, stop_flag):
            if idx_line >= pad_height:
                break
            lines.append(line)
            try:
                pad.addstr(idx_line, 0, line[:self.width-4])
            except curses.error:
                pass
            idx_line += 1
            # Refresh pad to show current output
            # (offset, 0) - top-left corner of the pad to display
            # (3, 2, self.height-4, self.width-2) - screen area where pad is shown
            pad.refresh(offset, 0, 3, 2, self.height-4, self.width-2)
            
            # Check for input to scroll or stop
            c = self.stdscr.getch()
            if c == curses.KEY_UP:
                offset = max(0, offset-1)
            elif c == curses.KEY_DOWN:
                offset += 1
            elif c in (ord('s'), ord('q')):
                stop_flag["stop"] = True
                break

        logpath = write_log_stream(test_name, lines)
        show_message(self.stdscr, f"Finished: {test_name}\nLog: {logpath}")

    def run_all(self):
        for i in range(len(TESTS)):
            self.run_test(i)
        show_message(self.stdscr, f"All tests completed.\nLogs: {LOG_DIR}")

# --------------------------- Entry Point ---------------------------
def main(stdscr):
    if platform.system() != "Linux":
        print("Momo runs only on Linux. Exiting.")
        return
    tui = MomoTUI(stdscr)
    tui.run()

if __name__=="__main__":
    curses.wrapper(main)
