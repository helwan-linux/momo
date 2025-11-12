#!/usr/bin/env python3
"""
Momo - Helwan Linux Diagnostics (Streaming Version, No curses)
Author: Saeed Badrelden
"""

import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import platform
import sys

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
def select_disk():
    try:
        result = subprocess.run("lsblk -d -o NAME,TYPE,SIZE -n", shell=True, capture_output=True, text=True)
        disks = [line.split()[0] for line in result.stdout.splitlines() if "disk" in line]
    except Exception:
        disks = []

    if not disks:
        print("No disks found!")
        return None

    if len(disks) == 1:
        return disks[0]

    # Show disks and ask user to select
    print("Select a disk for this test:")
    for idx, d in enumerate(disks):
        print(f"{idx+1}. {d}")
    while True:
        choice = input("Enter number (or q to cancel): ").strip()
        if choice.lower() == "q":
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(disks):
            return disks[int(choice)-1]

# --------------------------- Streaming Command ---------------------------
def run_command_stream(cmd):
    try:
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            if line:
                yield line.rstrip()
    except Exception as e:
        yield f"Error running command: {e}"

# --------------------------- Simple CLI ---------------------------
def run_test(test_name, cmd, tool):
    if not is_tool_installed(tool):
        ans = input(f"Tool '{tool}' not found. Skip? [Y/n]: ").strip().lower()
        if ans == "n":
            return

    if test_name in DISK_TESTS:
        disk = select_disk()
        if disk is None:
            print(f"Skipping {test_name} (no disk selected)")
            return
        cmd = cmd.replace("/dev/sda", f"/dev/{disk}")

    lines = []
    print(f"\n=== Running: {test_name} ===\n")
    for line in run_command_stream(cmd):
        print(line)
        lines.append(line)
    logpath = write_log_stream(test_name, lines)
    print(f"\nFinished: {test_name}\nLog: {logpath}\n")

def run_all_tests():
    for test_name, cmd, tool in TESTS:
        run_test(test_name, cmd, tool)
    print(f"All tests completed. Logs: {LOG_DIR}")

# --------------------------- Entry Point ---------------------------
def main():
    if platform.system() != "Linux":
        print("Momo runs only on Linux. Exiting.")
        return

    print("Momo - Helwan Linux Diagnostics (No curses)")
    print("Select a test or run all:")
    for idx, (name, _, _) in enumerate(TESTS):
        print(f"{idx+1}. {name}")
    print(f"{len(TESTS)+1}. Run All Tests")
    print(f"{len(TESTS)+2}. Exit")

    while True:
        choice = input("\nEnter number: ").strip()
        if not choice.isdigit():
            continue
        choice = int(choice)
        if 1 <= choice <= len(TESTS):
            run_test(*TESTS[choice-1])
        elif choice == len(TESTS)+1:
            run_all_tests()
        elif choice == len(TESTS)+2:
            print("Exiting Momo.")
            break

if __name__ == "__main__":
    main()

