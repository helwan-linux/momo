#!/usr/bin/env python3
"""
Momo - A Python TUI hub for system diagnostics (Arch/Arch-based)

Features:
- TUI (curses) menu to run common tests (RAM, CPU, Disk, Temp, GPU, Network, Battery)
- Detects whether required tools are installed (uses `shutil.which`)
- If a tool is missing, prompts user to install via pacman (asks before running)
- Runs commands and streams output to a window; logs saved under ~/.momo/logs/
- "Run all tests" option that runs tests sequentially and aggregates logs

Notes:
- Designed for Arch Linux / derivatives (uses pacman for installs). If you use a
  different package manager, tweak `install_with_pacman()`.
- Run with: `python3 momo_tui.py` or make executable and run `./momo_tui.py`
- Requires Python 3.8+ (uses standard library only)

Author: Generated for user (Helwan Linux project)
"""

import curses
import curses.panel
import shutil
import subprocess
import threading
import time
import os
from pathlib import Path
from datetime import datetime

# --------------------------- Configuration ---------------------------
# Map tests to the shell command to run and to the required binary
TESTS = [
    ("RAM: stress-ng (vm + cpu)", "stress-ng --vm 2 --vm-bytes 75% --cpu 2 --timeout 60s", "stress-ng"),
    ("RAM: memtester (example 1024M)", "memtester 1024M 1", "memtester"),
    ("RAM: memtest86+ (boot) (info)", "echo 'memtest86+ runs from boot; install memtest86+'", "memtest86+"),
    ("Disk: smartctl (short)", "smartctl -a /dev/sda", "smartctl"),
    ("Disk: fio (randrw sample)", "fio --name=randrw --iodepth=4 --rw=randrw --bs=4k --size=256M --numjobs=2 --runtime=30 --time_based", "fio"),
    ("Disk: dd read (dev)", "dd if=/dev/sda of=/dev/null bs=1M status=progress", "dd"),
    ("Temperature: lm-sensors (sensors)", "sensors", "sensors"),
    ("CPU: stress-ng cpu", "stress-ng --cpu 4 --timeout 30s", "stress-ng"),
    ("CPU: sysbench cpu", "sysbench --test=cpu --cpu-max-prime=20000 run", "sysbench"),
    ("GPU: glmark2", "glmark2", "glmark2"),
    ("GPU: nvtop (monitor)", "nvtop", "nvtop"),
    ("System: btop (monitor)", "btop", "btop"),
    ("IO: iotop (requires sudo)", "sudo iotop -o", "iotop"),
    ("Network: speedtest-cli", "speedtest", "speedtest"),
    ("Network: iperf3 server (run separately)", "iperf3 -s", "iperf3"),
    ("Power: powertop (recommend sudo)", "sudo powertop", "powertop"),
]

# Directory for logs
LOG_DIR = Path.home() / ".momo" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# pacman install command (used when prompting to install)
PACMAN_INSTALL = ["sudo", "pacman", "-S", "--noconfirm"]

# --------------------------- Utilities ---------------------------

def is_tool_installed(tool_name: str) -> bool:
    # special-case common shells/binaries
    if tool_name == "dd":
        # dd is coreutils; assume present
        return shutil.which("dd") is not None
    return shutil.which(tool_name) is not None


def install_with_pacman(tool_name: str) -> bool:
    """Try to install a package with pacman. Returns True if succeeded."""
    # Simple heuristic: package name ~= tool name; user can edit later
    cmd = PACMAN_INSTALL + [tool_name]
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def write_log(test_name: str, content: str) -> Path:
    fname = f"{timestamp()}-{sanitize_filename(test_name)}.log"
    path = LOG_DIR / fname
    path.write_text(content, encoding="utf-8", errors="ignore")
    return path


def sanitize_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in name).strip().replace(' ', '_')


# --------------------------- Curses UI ---------------------------

class MomoTUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.curs_set(0)
        self.height, self.width = self.stdscr.getmaxyx()
        self.menu_items = [t[0] for t in TESTS] + ["Run all tests", "View logs folder", "Exit"]
        self.selected = 0
        self.messages = []

    def draw(self):
        self.stdscr.erase()
        title = "Momo - Helwan Linux Diagnostics"
        subtitle = "Use arrows to move • Enter to run • q to quit"
        self.stdscr.addstr(1, center_x(self.width, title), title, curses.A_BOLD)
        self.stdscr.addstr(2, center_x(self.width, subtitle), subtitle)

        for idx, item in enumerate(self.menu_items):
            y = 4 + idx
            attr = curses.A_REVERSE if idx == self.selected else curses.A_NORMAL
            line = f" {idx+1:2d}. {item}"
            self.stdscr.addstr(y, 4, line[: self.width - 8], attr)

        footer = f"Logs: {LOG_DIR}"
        self.stdscr.addstr(self.height - 2, 2, footer[: self.width - 4], curses.A_DIM)
        self.stdscr.refresh()

    def run(self):
        while True:
            self.draw()
            c = self.stdscr.getch()
            if c in (curses.KEY_UP, ord('k')):
                self.selected = max(0, self.selected - 1)
            elif c in (curses.KEY_DOWN, ord('j')):
                self.selected = min(len(self.menu_items) - 1, self.selected + 1)
            elif c in (curses.KEY_ENTER, ord('\n'), ord('\r')):
                self.handle_selection(self.selected)
                if self.menu_items[self.selected] == "Exit":
                    break
            elif c in (ord('q'), 27):  # q or ESC
                break

    def handle_selection(self, idx: int):
        item = self.menu_items[idx]
        if item == "Run all tests":
            self.run_all_tests()
        elif item == "View logs folder":
            open_logs_folder()
        elif item == "Exit":
            return
        else:
            # Single test
            test_idx = idx
            self.run_test_by_index(test_idx)

    def run_test_by_index(self, test_idx: int):
        test_name, cmd, tool = TESTS[test_idx]
        run_command_flow(self.stdscr, test_name, cmd, tool)

    def run_all_tests(self):
        summary = []
        for i, (test_name, cmd, tool) in enumerate(TESTS):
            run_command_flow(self.stdscr, test_name, cmd, tool, allow_background=False)
            summary.append(test_name)
        show_message(self.stdscr, "All tests finished. Logs saved in: {}".format(LOG_DIR))


# --------------------------- Helpers for running commands ---------------------------


def run_command_flow(stdscr, test_name: str, cmd: str, tool: str, allow_background=True):
    """Check tool, prompt install if needed, then run command and show output in a scrollable window."""
    # Ensure command is available
    installed = is_tool_installed(tool)
    if not installed:
        prompt = f"Tool '{tool}' not found. Try to install with pacman? (y/n)"
        ans = prompt_yes_no(stdscr, prompt)
        if ans:
            ok = install_with_pacman(tool)
            if not ok:
                show_message(stdscr, f"Installation of {tool} failed or aborted.")
                return
        else:
            show_message(stdscr, f"Skipping test: {test_name}")
            return

    # Run command and display output
    show_message(stdscr, f"Running: {test_name}\nCommand: {cmd}\n(Press 's' to stop)" )
    output, rc = run_command_stream(stdscr, cmd)
    logpath = write_log(test_name, output)
    show_message(stdscr, f"Finished: {test_name}\nReturn code: {rc}\nLog: {logpath}")


def run_command_stream(stdscr, cmd: str, timeout: int = None):
    """Run a shell command, stream output to a curses window. Return (output_text, returncode)."""
    # Open a pad for output
    h, w = stdscr.getmaxyx()
    padh = max(1000, h * 3)
    pad = curses.newpad(padh, w - 4)
    pad_pos = 0

    # Start subprocess
    # Use shell=True to allow complex commands (fio sample, dd progress etc.)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)

    output_lines = []
    stdscr.nodelay(True)
    last_line_time = time.time()
    stopped = False
    try:
        while True:
            # Read line if available
            line = p.stdout.readline()
            if line == '' and p.poll() is not None:
                break
            if line:
                output_lines.append(line)
                # add to pad
                try:
                    pad.addstr(len(output_lines)-1, 0, line[:w-6])
                except Exception:
                    # ignore encoding/width issues
                    pass
                # Refresh visible area of pad
                start = max(0, len(output_lines) - (h - 6))
                pad.refresh(start, 0, 4, 2, h - 4, w - 3)
                last_line_time = time.time()

            # handle keypresses
            try:
                c = stdscr.getch()
                if c == ord('q'):
                    # quit viewing and kill process
                    p.terminate()
                    stopped = True
                    break
                elif c == ord('s'):
                    p.terminate()
                    stopped = True
                    break
                elif c == curses.KEY_UP:
                    pad_pos = max(0, pad_pos - 1)
                elif c == curses.KEY_DOWN:
                    pad_pos = pad_pos + 1
            except curses.error:
                # no input
                pass

            # small sleep to avoid busy loop
            time.sleep(0.01)
            # timeout guard
            if timeout and (time.time() - last_line_time) > timeout:
                p.terminate()
                stopped = True
                break

    finally:
        stdscr.nodelay(False)
        # drain remaining
        try:
            remaining = p.communicate(timeout=1)[0]
            if remaining:
                output_lines.append(remaining)
        except Exception:
            pass

    rc = p.poll()
    return ("".join(output_lines), rc)


# --------------------------- UI small helpers ---------------------------


def center_x(width, text):
    return max(0, (width - len(text)) // 2)


def show_message(stdscr, message: str, pause: bool = True):
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    lines = message.split('\n')
    for i, ln in enumerate(lines):
        stdscr.addstr(2 + i, 2, ln[: w - 4])
    stdscr.addstr(h - 2, 2, "Press any key to continue...", curses.A_DIM)
    stdscr.refresh()
    stdscr.getch()


def prompt_yes_no(stdscr, question: str) -> bool:
    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        stdscr.addstr(2, 2, question[: w - 4])
        stdscr.addstr(4, 4, "y = yes • n = no • q = cancel")
        stdscr.refresh()
        c = stdscr.getch()
        if c in (ord('y'), ord('Y')):
            return True
        if c in (ord('n'), ord('N'), ord('q'), 27):
            return False


def open_logs_folder():
    # Try to open file manager if available, otherwise print path
    try:
        fm = shutil.which('xdg-open') or shutil.which('gio') or shutil.which('xdg')
        if fm:
            subprocess.Popen([fm, str(LOG_DIR)])
        else:
            print(f"Logs at: {LOG_DIR}")
    except Exception as e:
        print(f"Unable to open logs folder: {e}")


# --------------------------- Entry point ---------------------------

def main(stdscr):
    tui = MomoTUI(stdscr)
    tui.run()


if __name__ == '__main__':
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print('\nExiting Momo')
