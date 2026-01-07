#!/usr/bin/env python3
"""
Test Z21 track-level telemetry (Phase 9 - Motor Load Monitoring).

Usage:
    python test_z21_telemetry.py

Tests the new telemetry parsing in z21.py::get_status()
"""

import sys
import os

# Add scripts to path (z21.py is in scripts/)
scripts_path = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, scripts_path)

from z21 import Z21


def main():
    print("=" * 60)
    print("TEST Z21 TRACK-LEVEL TELEMETRY")
    print("=" * 60)
    print()
    print("Testing new telemetry parsing in z21.py::get_status()")
    print()

    z21 = Z21(verbose=True)

    try:
        status = z21.get_status()

        if status:
            print("\n" + "=" * 60)
            print("✅ TEST PASSED - Telemetry data received")
            print("=" * 60)
            print()

            # Status bits
            print("📊 Z21 Status:")
            print(f"  Track Power: {'ON' if status['track_power_on'] else 'OFF'}")
            print(f"  Emergency Stop: {'YES' if status['emergency_stop'] else 'NO'}")
            print(f"  Programming Mode: {'YES' if status['programming_mode'] else 'NO'}")
            print(f"  Short Circuit: {'YES' if status['short_circuit'] else 'NO'}")
            print()

            # Telemetry data
            if 'telemetry' in status:
                t = status['telemetry']
                print("🔌 Track Telemetry:")
                print(f"  Main Current: {t['main_current_ma']} mA")
                print(f"  Prog Current: {t['prog_current_ma']} mA")
                print(f"  Filtered Current: {t['filtered_current_ma']} mA")
                print(f"  Z21 Temperature: {t['temperature_c']:.1f} °C")
                print(f"  Supply Voltage: {t['supply_voltage_v']:.2f} V")
                print(f"  VCC Voltage: {t['vcc_voltage_v']:.2f} V")
                print()

                # Quality checks
                print("🔍 Quality Checks:")

                # Voltage check
                if t['supply_voltage_v'] < 14.0:
                    print("  ⚠️  WARNING: Supply voltage low (< 14V) - Check power supply or track resistance")
                elif t['supply_voltage_v'] > 18.0:
                    print("  ⚠️  WARNING: Supply voltage high (> 18V) - Check power supply")
                else:
                    print(f"  ✅ Supply voltage OK ({t['supply_voltage_v']:.2f}V in normal range 14-18V)")

                # Current check
                if t['main_current_ma'] > 2000:
                    print(f"  ⚠️  WARNING: High track current ({t['main_current_ma']}mA) - Possible short circuit or excessive load")
                elif t['main_current_ma'] > 500:
                    print(f"  ✅ Track current OK ({t['main_current_ma']}mA - locomotives running)")
                else:
                    print(f"  ✅ Track current low ({t['main_current_ma']}mA - idle or no locomotives)")

                # Temperature check
                if t['temperature_c'] > 60.0:
                    print(f"  ⚠️  WARNING: Z21 temperature high ({t['temperature_c']:.1f}°C) - Check ventilation")
                elif t['temperature_c'] > 50.0:
                    print(f"  ⚠️  CAUTION: Z21 temperature elevated ({t['temperature_c']:.1f}°C) - Monitor closely")
                else:
                    print(f"  ✅ Z21 temperature OK ({t['temperature_c']:.1f}°C)")

            else:
                print("❌ No telemetry data in response (unexpected)")
        else:
            print("\n" + "=" * 60)
            print("❌ TEST FAILED - No response from Z21")
            print("=" * 60)
            print()
            print("Possible causes:")
            print("  - Z21 not connected")
            print("  - Z21 not powered on")
            print("  - Wrong IP address (check Z21_IP environment variable)")
            print("  - Network issues")

    finally:
        z21.close()


if __name__ == '__main__':
    main()
