#!/usr/bin/env python3
"""
Memory Monitor for z21-Terminal Backend

Monitors Python process memory usage and YOLO model VRAM/RAM consumption.
Logs periodic snapshots to CSV for analysis.

Usage:
    python backend_memory_monitor.py [--interval SECONDS] [--output FILE]

Requirements:
    pip install psutil
"""

import psutil
import csv
import time
import argparse
from datetime import datetime
from pathlib import Path


def get_process_memory(pid=None):
    """Get memory info for a process by PID (or current process)."""
    if pid:
        try:
            proc = psutil.Process(pid)
        except psutil.NoSuchProcess:
            return None
    else:
        proc = psutil.Process()

    mem_info = proc.memory_info()

    return {
        "timestamp": datetime.now().isoformat(),
        "pid": proc.pid,
        "rss_mb": mem_info.rss / 1024 / 1024,  # Resident Set Size (physical RAM)
        "vms_mb": mem_info.vms / 1024 / 1024,  # Virtual Memory Size
        "percent": proc.memory_percent(),       # % of total RAM
        "num_threads": proc.num_threads(),
        "num_fds": proc.num_fds() if hasattr(proc, 'num_fds') else 0,
    }


def find_yolo_processes():
    """Find all Python processes that might be running YOLO tracking."""
    yolo_procs = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and any('yolo' in str(c).lower() or 'tracking' in str(c).lower() for c in cmdline):
                yolo_procs.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return yolo_procs


def monitor_main_process(interval=5, output_file=None, duration_minutes=None):
    """
    Monitor the z21-Terminal backend process.

    Args:
        interval: Seconds between measurements
        output_file: CSV file to write results
        duration_minutes: Stop after N minutes (None = infinite)
    """
    if output_file is None:
        output_file = Path(__file__).parent / "results" / f"backend_memory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    else:
        output_file = Path(output_file)

    output_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"🔍 Monitoring backend memory usage...")
    print(f"📊 Output: {output_file}")
    print(f"⏱️  Interval: {interval}s")
    if duration_minutes:
        print(f"⏰ Duration: {duration_minutes} minutes")
    print(f"Press Ctrl+C to stop\n")

    # CSV header
    fieldnames = ["timestamp", "rss_mb", "vms_mb", "percent", "num_threads", "cpu_percent"]

    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        start_time = time.time()
        try:
            while True:
                # Check duration
                if duration_minutes and (time.time() - start_time) > duration_minutes * 60:
                    print(f"\n✅ Duration reached ({duration_minutes}m). Stopping.")
                    break

                # Get memory info
                proc = psutil.Process()
                mem_info = proc.memory_info()
                cpu_percent = proc.cpu_percent(interval=0.1)

                row = {
                    "timestamp": datetime.now().isoformat(),
                    "rss_mb": f"{mem_info.rss / 1024 / 1024:.2f}",
                    "vms_mb": f"{mem_info.vms / 1024 / 1024:.2f}",
                    "percent": f"{proc.memory_percent():.2f}",
                    "num_threads": proc.num_threads(),
                    "cpu_percent": f"{cpu_percent:.2f}",
                }

                writer.writerow(row)
                csvfile.flush()

                # Pretty print
                print(f"[{row['timestamp']}] RAM: {row['rss_mb']} MB | VRAM: {row['vms_mb']} MB | CPU: {row['cpu_percent']}%")

                time.sleep(interval)

        except KeyboardInterrupt:
            print(f"\n\n✅ Monitoring stopped. Results saved to: {output_file}")

            # Print summary
            print_summary(output_file)


def print_summary(csv_file):
    """Print summary statistics from CSV file."""
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            if not rows:
                return

            rss_values = [float(r['rss_mb']) for r in rows]
            cpu_values = [float(r['cpu_percent']) for r in rows]

            print("\n📊 SUMMARY STATISTICS")
            print("=" * 50)
            print(f"Total samples: {len(rows)}")
            print(f"RAM Usage:")
            print(f"  Min:     {min(rss_values):.2f} MB")
            print(f"  Max:     {max(rss_values):.2f} MB")
            print(f"  Average: {sum(rss_values) / len(rss_values):.2f} MB")
            print(f"CPU Usage:")
            print(f"  Min:     {min(cpu_values):.2f}%")
            print(f"  Max:     {max(cpu_values):.2f}%")
            print(f"  Average: {sum(cpu_values) / len(cpu_values):.2f}%")

    except Exception as e:
        print(f"⚠️  Could not generate summary: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Monitor z21-Terminal backend memory usage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Monitor every 5 seconds indefinitely
  python backend_memory_monitor.py

  # Monitor every 2 seconds for 10 minutes
  python backend_memory_monitor.py --interval 2 --duration 10

  # Custom output file
  python backend_memory_monitor.py --output my_test.csv
        """
    )

    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=5,
        help="Seconds between measurements (default: 5)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output CSV file (default: test/memory/results/backend_memory_TIMESTAMP.csv)"
    )
    parser.add_argument(
        "--duration", "-d",
        type=int,
        default=None,
        help="Stop after N minutes (default: run indefinitely)"
    )

    args = parser.parse_args()

    monitor_main_process(
        interval=args.interval,
        output_file=args.output,
        duration_minutes=args.duration
    )


if __name__ == "__main__":
    main()
