#!/usr/bin/env python3
"""
nvstat - NVIDIA GPU monitoring CLI with ASCII bar charts and gauges
Displays GPU temperature, memory, and utilization in real-time
"""

import subprocess
import time
import sys
import os
import re
import signal
import shutil
from datetime import datetime


# Minimum and preferred widths
MIN_WIDTH = 80
PREFERRED_WIDTH = 160


def get_terminal_size():
    """Get terminal size, with fallback"""
    try:
        size = shutil.get_terminal_size()
        return max(MIN_WIDTH, size.columns), size.lines
    except:
        return PREFERRED_WIDTH, 40


def get_gpu_stats():
    """Query nvidia-smi for GPU statistics"""
    try:
        # Query: GPU index, name, temp, memory used, memory total, utilization, power
        query = "index,name,temperature.gpu,memory.used,memory.total,utilization.gpu,utilization.memory,power.draw,power.limit"
        cmd = [
            "nvidia-smi",
            f"--query-gpu={query}",
            "--format=csv,noheader,nounits"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        if result.returncode != 0:
            return None
        
        gpus = []
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 9:
                try:
                    gpu = {
                        'index': int(parts[0]),
                        'name': parts[1],
                        'temp': float(parts[2]),
                        'mem_used': float(parts[3]),
                        'mem_total': float(parts[4]),
                        'util_gpu': float(parts[5]),
                        'util_mem': float(parts[6]),
                        'power_draw': float(parts[7]) if parts[7] not in ['[N/A]', 'N/A', ''] else 0,
                        'power_limit': float(parts[8]) if parts[8] not in ['[N/A]', 'N/A', ''] else 0,
                    }
                    gpus.append(gpu)
                except ValueError:
                    continue
        return gpus if gpus else None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def format_memory(mb):
    """Format memory size for display"""
    if mb < 1024:
        return f"{mb:.0f}MB"
    else:
        return f"{mb/1024:.2f}GB"


def clear_screen():
    """Clear terminal screen using ANSI escape"""
    print("\033[2J\033[H", end="")


def get_color(percentage, invert=False):
    """Get color code based on percentage threshold"""
    if invert:
        # For temperature: lower is better
        if percentage > 80:
            return "\033[91m"  # Red
        elif percentage > 60:
            return "\033[93m"  # Yellow
        else:
            return "\033[92m"  # Green
    else:
        # For utilization/memory: higher may be concerning
        if percentage > 90:
            return "\033[91m"  # Red
        elif percentage > 70:
            return "\033[93m"  # Yellow
        else:
            return "\033[92m"  # Green


def make_row(content, width, left="│", right="│"):
    """Create a row with proper padding to align right border"""
    # Calculate visible length (excluding ANSI codes)
    visible = re.sub(r'\033\[[0-9;]*m', '', content)
    padding = width - len(visible) - len(left) - len(right)
    if padding < 0:
        padding = 0
    return f"{left}{content}{' ' * padding}{right}"


def draw_section_header(title, width, bold, reset):
    """Draw a section header with proper width"""
    inner_width = width - 2
    title_part = f"─ {title} "
    remaining = inner_width - len(title_part)
    return f"{bold}┌{title_part}{'─' * remaining}┐{reset}"


def draw_section_footer(width, bold, reset):
    """Draw a section footer with proper width"""
    inner_width = width - 2
    return f"{bold}└{'─' * inner_width}┘{reset}"


def draw_bar_row(label, value, max_value, unit, width, label_width, bar_width, color_func=None, invert=False):
    """Draw a complete bar row with proper alignment"""
    reset = "\033[0m"
    
    if max_value == 0:
        percentage = 0
    else:
        percentage = min(100, (value / max_value) * 100)
    
    filled = int(bar_width * percentage / 100)
    bar = "█" * filled + "░" * (bar_width - filled)
    
    if color_func:
        color = color_func(percentage, invert)
    else:
        color = "\033[96m"  # Default cyan
    
    # Build the content
    value_str = f"{value:.1f}{unit}" if unit else f"{value:.1f}%"
    content = f" {label:<{label_width}} {color}│{bar}│{reset} {value_str:>10}"
    
    return make_row(content, width)


def draw_mem_bar_row(label, used, total, width, label_width, bar_width):
    """Draw a memory bar row with used/total display"""
    reset = "\033[0m"
    
    if total == 0:
        percentage = 0
    else:
        percentage = min(100, (used / total) * 100)
    
    filled = int(bar_width * percentage / 100)
    bar = "█" * filled + "░" * (bar_width - filled)
    
    color = get_color(percentage)
    mem_str = f"{format_memory(used)}/{format_memory(total)}"
    
    content = f" {label:<{label_width}} {color}│{bar}│{reset} {mem_str:>16}"
    
    return make_row(content, width)


def draw_power_bar_row(label, power_draw, power_limit, width, label_width, bar_width):
    """Draw a power bar row with watts display"""
    reset = "\033[0m"
    
    if power_limit == 0:
        percentage = 0
    else:
        percentage = min(100, (power_draw / power_limit) * 100)
    
    filled = int(bar_width * percentage / 100)
    bar = "█" * filled + "░" * (bar_width - filled)
    
    color = get_color(percentage)
    power_str = f"{power_draw:.0f}W/{power_limit:.0f}W"
    
    content = f" {label:<{label_width}} {color}│{bar}│{reset} {power_str:>16}"
    
    return make_row(content, width)


def draw_gauge_section(title, value, max_value, unit, width, gauge_width, color_func=None, invert=False, extra_info=""):
    """Draw a gauge with title and value"""
    reset = "\033[0m"
    bold = "\033[1m"
    
    if max_value == 0:
        percentage = 0
    else:
        percentage = min(100, (value / max_value) * 100)
    
    filled = int(gauge_width * percentage / 100)
    gauge_bar = "█" * filled + "░" * (gauge_width - filled)
    
    if color_func:
        color = color_func(percentage, invert)
    else:
        color = "\033[96m"
    
    top = "╔" + "═" * gauge_width + "╗"
    middle = "║" + gauge_bar + "║"
    bottom = "╚" + "═" * gauge_width + "╝"
    
    value_str = f"{value:.1f}{unit}" if unit else f"{percentage:.1f}%"
    if extra_info:
        value_str = f"{value_str}  {extra_info}"
    
    lines = [
        make_row(f"  {bold}{title}{reset}", width),
        make_row(f"    {top}", width),
        make_row(f"    {color}{middle}{reset}  {value_str}", width),
        make_row(f"    {bottom}", width),
    ]
    return lines


def draw_ui(gpus):
    """Draw the complete UI with dynamic width"""
    term_width, term_height = get_terminal_size()
    
    # Use available width, capped at preferred
    width = min(term_width, PREFERRED_WIDTH)
    
    clear_screen()
    
    reset = "\033[0m"
    bold = "\033[1m"
    dim = "\033[2m"
    
    # Calculate dynamic sizes based on width
    # Reserve space for: borders(2) + padding(2) + bar borders(2) + value display(16)
    fixed_space = 2 + 2 + 2 + 18
    
    # Label width for GPU name (GPU X: Full Name)
    label_width = min(50, (width - fixed_space) // 3)
    
    # Bar width uses remaining space
    bar_width = width - fixed_space - label_width - 2
    bar_width = max(20, bar_width)  # Minimum bar width
    
    # Gauge width
    gauge_width = min(50, (width - 20) // 2)
    
    # Header
    print(f"{bold}{'═' * width}{reset}")
    title = f"  NVSTAT - GPU Monitor  │  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  │  Terminal: {term_width}x{term_height}"
    print(f"{title}")
    print(f"{'═' * width}")
    
    if not gpus:
        print(f"\n⚠️  No GPUs detected or nvidia-smi not available")
        print(f"\n{'═' * width}")
        return
    
    # Calculate totals
    total_mem_used = sum(gpu['mem_used'] for gpu in gpus)
    total_mem_total = sum(gpu['mem_total'] for gpu in gpus)
    total_power_draw = sum(gpu['power_draw'] for gpu in gpus)
    total_power_limit = sum(gpu['power_limit'] for gpu in gpus)
    avg_util = sum(gpu['util_gpu'] for gpu in gpus) / len(gpus)
    avg_temp = sum(gpu['temp'] for gpu in gpus) / len(gpus)
    
    # ═══════════════════════════════════════════════════════════════════
    # TEMPERATURE CHART
    # ═══════════════════════════════════════════════════════════════════
    print()
    print(draw_section_header("TEMPERATURE", width, bold, reset))
    for gpu in gpus:
        label = f"GPU {gpu['index']}: {gpu['name']}"
        if len(label) > label_width:
            label = label[:label_width-2] + ".."
        print(draw_bar_row(label, gpu['temp'], 100, "°C", width, label_width, bar_width, get_color, invert=True))
    print(draw_section_footer(width, bold, reset))
    
    # ═══════════════════════════════════════════════════════════════════
    # GPU UTILIZATION CHART
    # ═══════════════════════════════════════════════════════════════════
    print()
    print(draw_section_header("GPU UTILIZATION", width, bold, reset))
    for gpu in gpus:
        label = f"GPU {gpu['index']}: {gpu['name']}"
        if len(label) > label_width:
            label = label[:label_width-2] + ".."
        print(draw_bar_row(label, gpu['util_gpu'], 100, "%", width, label_width, bar_width))
    print(draw_section_footer(width, bold, reset))
    
    # ═══════════════════════════════════════════════════════════════════
    # MEMORY USAGE CHART
    # ═══════════════════════════════════════════════════════════════════
    print()
    print(draw_section_header("MEMORY USAGE", width, bold, reset))
    for gpu in gpus:
        label = f"GPU {gpu['index']}: {gpu['name']}"
        if len(label) > label_width:
            label = label[:label_width-2] + ".."
        print(draw_mem_bar_row(label, gpu['mem_used'], gpu['mem_total'], width, label_width, bar_width))
    print(draw_section_footer(width, bold, reset))
    
    # ═══════════════════════════════════════════════════════════════════
    # POWER USAGE CHART
    # ═══════════════════════════════════════════════════════════════════
    print()
    print(draw_section_header("POWER USAGE", width, bold, reset))
    for gpu in gpus:
        label = f"GPU {gpu['index']}: {gpu['name']}"
        if len(label) > label_width:
            label = label[:label_width-2] + ".."
        power_max = gpu['power_limit'] if gpu['power_limit'] > 0 else 100
        print(draw_power_bar_row(label, gpu['power_draw'], power_max, width, label_width, bar_width))
    print(draw_section_footer(width, bold, reset))
    
    # ═══════════════════════════════════════════════════════════════════
    # TOTAL GAUGES
    # ═══════════════════════════════════════════════════════════════════
    print()
    print(draw_section_header("TOTALS", width, bold, reset))
    print(make_row("", width))
    
    # Total Memory Gauge
    mem_extra = f"({format_memory(total_mem_used)} / {format_memory(total_mem_total)})"
    for line in draw_gauge_section("Total VRAM", total_mem_used, total_mem_total, "", width, gauge_width, get_color, extra_info=mem_extra):
        print(line)
    print(make_row("", width))
    
    # Average Utilization Gauge
    for line in draw_gauge_section("Average GPU Utilization", avg_util, 100, "%", width, gauge_width):
        print(line)
    print(make_row("", width))
    
    # Total Power Gauge
    power_extra = f"({total_power_draw:.0f}W / {total_power_limit:.0f}W)"
    for line in draw_gauge_section("Total Power Draw", total_power_draw, total_power_limit, "W", width, gauge_width, get_color, extra_info=power_extra):
        print(line)
    print(make_row("", width))
    
    # Average Temperature Gauge
    for line in draw_gauge_section("Average Temperature", avg_temp, 100, "°C", width, gauge_width, get_color, invert=True):
        print(line)
    print(make_row("", width))
    
    print(draw_section_footer(width, bold, reset))
    
    # Footer
    print()
    print(f"{'═' * width}")
    print(f"{dim}Press Ctrl+C to exit  │  Refresh: 2s{reset}")
    print(f"{'═' * width}")


def main():
    """Main loop"""
    poll_interval = 2  # seconds
    
    def signal_handler(sig, frame):
        print("\n\nShutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        while True:
            gpus = get_gpu_stats()
            draw_ui(gpus)
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("\n\nExiting nvstat")
        sys.exit(0)


if __name__ == "__main__":
    main()
