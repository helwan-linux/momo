# 🧠 Momo - Helwan Linux Diagnostics Tool (TUI Stable Version)

**Author:** Saeed Badrelden
**License:** GPL-3.0
**Platform:** Linux (Arch / Helwan Linux recommended)
**Version:** Stable (Curses TUI Edition)

---

## 🩺 Overview

**Momo** is a **powerful text-based diagnostic utility** designed for **Helwan Linux**, built on top of `curses` to provide an **interactive TUI (Terminal User Interface)** for system diagnostics and stress testing.
It offers a stable, safe, and user-friendly experience — far superior to the basic CLI version.

This version introduces:

* Interactive scrolling output
* Safe test termination (without breaking the UI)
* Automatic log saving
* Disk selection for SMART and performance tests
* Dynamic tool availability detection

---

## ⚙️ Features

* ✅ Interactive **TUI menu** built with `curses`
* ✅ Real-time **streaming output**
* ✅ **Scroll with ↑↓** during long test outputs
* ✅ **Stop tests anytime** (press `S` or `Q`)
* ✅ **Run all tests** automatically in sequence
* ✅ **Automatic log saving** under `~/.momo/logs/`
* ✅ Detection for missing tools with `[MISSING]` label
* ✅ Disk selection support for `/dev/sdX` and `/dev/nvmeX`

---

## 🧩 Test Categories

| Category              | Description                   | Required Tool |
| --------------------- | ----------------------------- | ------------- |
| RAM Usage             | Display memory summary        | `free`        |
| RAM Details           | Show `/proc/meminfo`          | `cat`         |
| RAM Stress Test (30s) | Simulate RAM load             | `stress-ng`   |
| Memtester 512M        | Test memory reliability       | `memtester`   |
| Memory Speed          | Benchmark memory speed        | `sysbench`    |
| Swap Usage            | Display swap partitions       | `swapon`      |
| CPU Info              | Show CPU architecture details | `lscpu`       |
| CPU Stress Test (20s) | Stress CPU cores              | `stress-ng`   |
| Smart Status          | Disk health via SMART         | `smartctl`    |
| Disk Speed            | Read/Write speed test         | `hdparm`      |
| Disk Usage            | Display mounted partitions    | `df`          |
| Sensors               | Read thermal and voltage data | `sensors`     |
| Ping Test             | Network connectivity          | `ping`        |

---

## 🖥️ Usage

### Run Momo

```bash
python3 momo.py
```

> 💡 Momo must be run **inside a Linux terminal (not GUI IDEs)**.
> If you see a curses error, try a larger terminal window or run from `tty`.

---

### Navigation

| Key            | Action                     |
| -------------- | -------------------------- |
| ↑ / ↓          | Move between tests         |
| **Enter**      | Run selected test          |
| **A**          | Run all tests sequentially |
| **S** or **Q** | Stop running test          |
| **Q**          | Quit the main menu         |

---

### Logs

Each test automatically generates a log file in:

```
~/.momo/logs/
```

File names include timestamps, e.g.:

```
Memory_Speed_2025-11-12_15-34-21.log
```

---

## 🧠 Design Philosophy

Momo’s design reflects the **Helwan Linux vision**:

> *“Diagnostics should be accessible, informative, and beautiful — even in the terminal.”*

Every feature is built with:

* Simplicity in mind
* Zero data loss
* Full control for the user
* Stability over speed

---

## 🧩 Dependencies

Before running Momo, make sure these tools are installed:

```bash
sudo pacman -S stress-ng memtester sysbench smartmontools hdparm lm_sensors
```

---

## 🐞 Error Handling

* If a required tool is missing → shown as `[MISSING]` in the menu.
* Graceful recovery from `curses` and `subprocess` errors.
* Tests that are stopped manually will display:

  ```
  --- Test Terminated by User ---
  ```

---

## 📁 Directory Structure

```
momo/
 ├── momo.py                # Main program
 ├── README.md              # You are here
 ├── ~/.momo/logs/          # Auto-generated logs
```

---

## 🚀 Future Plans

* Progress bar and elapsed time display
* View logs directly from TUI
* Multi-language (i18n) support
* Integration with Helwan Linux System Center

---

## 🪥 Credits

**Developed by:** Saeed Badrelden

**Project:** Helwan Linux

**Website:** [Helwan Linux Official Site](https://helwan-linux.github.io/helwanlinux/index.html)



> © 2025 Helwan Linux. Proudly made in Egypt 🇪🇬

---
