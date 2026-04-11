"""
JARVIS Built-in Commands
Local commands that don't need AI processing.
"""

import datetime
import os
import platform
import shutil
import socket
import subprocess
import time

import psutil

from jarvis.config import USER_TITLE


def get_time() -> str:
    now = datetime.datetime.now()
    return f"The current time is {now.strftime('%I:%M %p')}, {USER_TITLE}."


def get_date() -> str:
    now = datetime.datetime.now()
    return f"Today is {now.strftime('%A, %B %d, %Y')}, {USER_TITLE}."


def get_system_status() -> str:
    """Full system diagnostics — very Jarvis."""
    cpu_percent = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory()
    disk = shutil.disk_usage("/")

    mem_used = memory.used / (1024 ** 3)
    mem_total = memory.total / (1024 ** 3)
    disk_used = disk.used / (1024 ** 3)
    disk_total = disk.total / (1024 ** 3)

    uptime_seconds = time.time() - psutil.boot_time()
    hours, remainder = divmod(int(uptime_seconds), 3600)
    minutes, _ = divmod(remainder, 60)

    lines = [
        f"System diagnostics complete, {USER_TITLE}.",
        f"  Host: {platform.node()} running {platform.system()} {platform.release()}",
        f"  CPU: {cpu_percent}% utilization across {psutil.cpu_count()} cores",
        f"  Memory: {mem_used:.1f} GB used of {mem_total:.1f} GB ({memory.percent}%)",
        f"  Disk: {disk_used:.1f} GB used of {disk_total:.1f} GB ({disk.used * 100 // disk.total}%)",
        f"  Uptime: {hours}h {minutes}m",
    ]
    return "\n".join(lines)


def get_ip_address() -> str:
    """Get local and public-facing IP."""
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return f"Local IP address is {local_ip}, {USER_TITLE}."
    except Exception:
        return f"I'm unable to determine the network address at the moment, {USER_TITLE}."


def get_battery_status() -> str:
    battery = psutil.sensors_battery()
    if battery is None:
        return f"No battery detected — this system appears to run on mains power, {USER_TITLE}."
    status = "charging" if battery.power_plugged else "discharging"
    return f"Battery is at {battery.percent}%, currently {status}, {USER_TITLE}."


def get_running_processes() -> str:
    """Top 5 processes by CPU usage."""
    procs = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent"]):
        try:
            procs.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    top = sorted(procs, key=lambda p: p.get("cpu_percent", 0) or 0, reverse=True)[:5]
    lines = [f"Top processes by CPU usage, {USER_TITLE}:"]
    for p in top:
        lines.append(f"  {p['name']} (PID {p['pid']}): {p.get('cpu_percent', 0):.1f}%")
    return "\n".join(lines)


# ─── Command Router ─────────────────────────────────────────────────

# Maps keyword patterns to handler functions
BUILTIN_COMMANDS = {
    ("what time", "current time", "tell me the time", "what's the time"): get_time,
    ("what date", "today's date", "what day", "what's the date"): get_date,
    ("system status", "system diagnostics", "run diagnostics", "system report", "system info"): get_system_status,
    ("ip address", "my ip", "network address"): get_ip_address,
    ("battery", "power status", "charge level"): get_battery_status,
    ("top processes", "running processes", "what's running"): get_running_processes,
}


def try_builtin(user_input: str) -> str | None:
    """
    Check if user input matches a built-in command.
    Returns the response string, or None if no match.
    """
    text = user_input.lower().strip()
    for keywords, handler in BUILTIN_COMMANDS.items():
        if any(kw in text for kw in keywords):
            return handler()
    return None
