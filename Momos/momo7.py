#!/usr/bin/env python3
"""
Momo - Helwan Linux Diagnostics (Ultimate Full Version)
Features: Streaming + Dynamic Disk Selection + Manual Scrolling
Author: Generated for Saeed Badrelden
"""

import curses
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import platform

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
    ("Smart Status", "smartctl -a /dev/sda", "smartctl"),
    ("Disk Speed", "hdparm -tT /dev/sda", "hdparm"),
    ("FIO Benchmark", "fio --name=randread --ioengine=libaio --iodepth=4 --rw=randread --bs=4k --direct=1 --size=512M --numjobs=4 --runtime=60 --time_based --group_reporting", "fio"),
    ("NVMe Smart", "nvme smart-log /dev/nvme0", "nvme"),
    ("NVMe Temperature", "nvme smart-log /dev/nvme0 | grep temperature", "nvme"),
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

LOG_DIR = Path.home() / ".momo" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
PACMAN_INSTALL = ["sudo", "pacman", "-S", "--noconfirm"]
DISK_TESTS = ["Smart Status", "Disk Speed", "NVMe Smart", "NVMe Temperature"]

# --------------------------- Utilities ---------------------------
def is_tool_installed(tool_name):
    if tool_name in ["cat", "free", "swapon", "df", "ping", "uptime", "uname", "top"]:
        return True
    return shutil.which(tool_name) is not None

def install_tool(tool_name):
    try:
        subprocess.run(PACMAN_INSTALL + [tool_name], check=True)
        return True
    except subprocess.CalledProcessError:
        return False

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
    result = subprocess.run("lsblk -d -o NAME,TYPE,SIZE -n", shell=True, capture_output=True, text=True)
    disks = [line.split()[0] for line in result.stdout.splitlines() if "disk" in line]
    if not disks:
        show_message(stdscr, "No disks found!")
        return None

    selected = 0
    while True:
        stdscr.clear()
        stdscr.addstr(1, 2, "Select a disk for this test (q=Cancel):")
        for idx, d in enumerate(disks):
            attr = curses.A_REVERSE if idx == selected else curses.A_NORMAL
            stdscr.addstr(3+idx, 4, d, attr)
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

# --------------------------- Curses TUI ---------------------------
class MomoTUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.curs_set(0)
        self.height, self.width = self.stdscr.getmaxyx()
        self.menu_items = [t[0] for t in TESTS] + ["Run All Tests", "View Logs Folder", "Exit"]
        self.selected = 0

    def draw(self):
        self.stdscr.erase()
        title = "Momo - Helwan Linux Diagnostics (Ultimate Full)"
        subtitle = "Arrows ↑↓ • Enter to run • s=Stop • q=Quit • Scroll Up/Down"
        self.stdscr.addstr(1, max(0, (self.width-len(title))//2), title, curses.A_BOLD)
        self.stdscr.addstr(2, max(0, (self.width-len(subtitle))//2), subtitle)
        for idx, item in enumerate(self.menu_items):
            y = 4 + idx
            attr = curses.A_REVERSE if idx == self.selected else curses.A_NORMAL
            self.stdscr.addstr(y, 4, f"{idx+1:2d}. {item}"[:self.width-8], attr)
        self.stdscr.addstr(self.height-2, 2, f"Logs: {LOG_DIR}", curses.A_DIM)
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
        elif item=="View Logs Folder":
            self.open_logs()
        elif item=="Exit":
            return
        else:
            self.run_test(idx)

    def run_test(self, idx):
        test_name, cmd, tool = TESTS[idx]
        if not is_tool_installed(tool):
            ans = prompt_yes_no(self.stdscr, f"Tool '{tool}' not found. Install via pacman?")
            if ans:
                ok = install_tool(tool)
                if not ok:
                    show_message(self.stdscr, f"Installation failed. Skipping {test_name}")
                    return
            else:
                show_message(self.stdscr, f"Skipping {test_name}")
                return

        # Disk selection
        if test_name in DISK_TESTS:
            disk = select_disk(self.stdscr)
            if disk is None:
                show_message(self.stdscr, f"Skipping {test_name} (no disk selected)")
                return
            if "smartctl" in cmd or "hdparm" in cmd:
                cmd = cmd.replace("/dev/sda", f"/dev/{disk}")
            elif "nvme" in cmd:
                cmd = cmd.replace("/dev/nvme0", f"/dev/{disk}")

        # Pad for manual scrolling
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
            pad.addstr(idx_line, 0, line[:self.width-4])
            idx_line += 1
            pad.refresh(offset, 0, 3, 2, self.height-4, self.width-2)
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
        show_message(self.stdscr, f"All tests completed.\nLogs saved in {LOG_DIR}")

    def open_logs(self):
        fm = shutil.which("xdg-open")
        if fm:
            subprocess.Popen([fm, str(LOG_DIR)])
        else:
            show_message(self.stdscr, f"Logs folder: {LOG_DIR}")

# --------------------------- UI Helpers ---------------------------
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

def show_message(stdscr, message):
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    for i, ln in enumerate(message.split('\n')):
        stdscr.addstr(2+i, 2, ln[:w-4])
    stdscr.addstr(h-2, 2, "Press any key to continue...", curses.A_DIM)
    stdscr.refresh()
    stdscr.getch()

# --------------------------- Entry Point ---------------------------
def main(stdscr):
    if platform.system() != "Linux":
        print("Momo runs only on Linux (Arch/Arch-based). Exiting.")
        return
    tui = MomoTUI(stdscr)
    tui.run()

if __name__=="__main__":
    curses.wrapper(main)
