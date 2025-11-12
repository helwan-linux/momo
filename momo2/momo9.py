#!/usr/bin/env python3
"""
Momo CLI - Helwan Linux Diagnostics (No-Curses Version)
Author: Saeed Badrelden
"""

import subprocess
import shutil
from pathlib import Path
from datetime import datetime
import platform
import time

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
def sanitize_filename(name):
    return "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in name).strip().replace(' ', '_')

def is_tool_installed(tool_name):
    if tool_name in ["cat", "free", "swapon", "df", "ping"]:
        return True
    return shutil.which(tool_name) is not None

def write_log(test_name, content):
    fname = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{sanitize_filename(test_name)}.log"
    path = LOG_DIR / fname
    with open(path, "w", encoding="utf-8", errors="ignore") as f:
        f.write(content)
    return path

def select_disk():
    try:
        result = subprocess.run("lsblk -d -o NAME,TYPE,SIZE -n", shell=True, capture_output=True, text=True)
        disks = [line.split()[0] for line in result.stdout.splitlines() if "disk" in line]
    except Exception:
        disks = []

    if not disks:
        print("\nNo disks found!\n")
        return None

    print("\nAvailable disks:")
    for i, d in enumerate(disks, start=1):
        print(f" {i}. {d}")
    choice = input("Select disk number (or Enter to cancel): ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= len(disks)):
        print("Cancelled.\n")
        return None
    return disks[int(choice) - 1]

def run_command(cmd):
    try:
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        output_lines = []
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                print(line.rstrip())
                output_lines.append(line)
        return "".join(output_lines)
    except Exception as e:
        return f"Error running command: {e}"

# --------------------------- Main Logic ---------------------------
def run_test(idx):
    test_name, cmd, tool = TESTS[idx]
    print(f"\n--- Running: {test_name} ---")

    if not is_tool_installed(tool):
        choice = input(f"Tool '{tool}' not found. Skip this test? (y/n): ").lower()
        if choice != 'y':
            return

    if test_name in DISK_TESTS:
        disk = select_disk()
        if not disk:
            print(f"Skipping {test_name}.\n")
            return
        cmd = cmd.replace("/dev/sda", f"/dev/{disk}")

    output = run_command(cmd)
    log_path = write_log(test_name, output)
    print(f"\n✅ Finished: {test_name}")
    print(f"📁 Log saved to: {log_path}\n")
    time.sleep(1)

def run_all():
    for i in range(len(TESTS)):
        run_test(i)
    print("\n✅ All tests completed.")
    print(f"📁 Logs directory: {LOG_DIR}\n")

def main():
    if platform.system() != "Linux":
        print("Momo runs only on Linux. Exiting.")
        return

    while True:
        print("\nMomo - Helwan Linux Diagnostics")
        print("=" * 40)
        for i, t in enumerate(TESTS, start=1):
            print(f"{i:2d}. {t[0]}")
        print(f"{len(TESTS)+1:2d}. Run All Tests")
        print(f"{len(TESTS)+2:2d}. Exit")
        print("=" * 40)

        choice = input("Enter test number or 'all': ").strip().lower()

        if choice == 'all':
            run_all()
        elif choice.isdigit():
            idx = int(choice) - 1
            if idx == len(TESTS):
                run_all()
            elif idx == len(TESTS) + 1:
                print("Goodbye!")
                break
            elif 0 <= idx < len(TESTS):
                run_test(idx)
            else:
                print("Invalid choice.")
        else:
            print("Invalid input. Try again.")

if __name__ == "__main__":
    main()
