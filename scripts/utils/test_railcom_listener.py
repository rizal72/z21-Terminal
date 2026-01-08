#!/usr/bin/env python3
"""
Test RailCom support on Z21 White (Phase 9 Part 3 - Research).

This script verifies if Z21 White (HW 0x0203) supports RailCom reception via LAN.

Usage:
    python test_railcom_listener.py [duration_seconds]

Tests:
1. Subscribe to RailCom broadcasts (LAN_SYSTEMSTATE_DATACHANGED)
2. Monitor for LAN_RAILCOM_DATACHANGED (0x0088) packets
3. Report findings after timeout

Expected outcome:
- If Z21 White supports RailCom: Receives 0x0088 packets with loco telemetry
- If not supported: No 0x0088 packets after 60s timeout
"""

import sys
import os
import time
import struct

# Add scripts to path (z21.py is in scripts/)
scripts_path = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, scripts_path)

from z21 import Z21


def test_railcom_support(duration_seconds=60):
    """
    Test if Z21 supports RailCom reception.

    Args:
        duration_seconds: How long to listen for RailCom packets (default 60s)
    """
    print("=" * 70)
    print("TEST Z21 RAILCOM SUPPORT")
    print("=" * 70)
    print()
    print("Testing if Z21 White (HW 0x0203) supports RailCom reception via LAN")
    print()

    z21 = Z21(verbose=True)

    try:
        # Step 1: Get hardware info to confirm Z21 model
        hw_info = z21.get_hw_info()
        if not hw_info:
            print("❌ Failed to get Z21 hardware info")
            return False

        hw_type = hw_info['hw_type']

        # Map hardware type to model name
        hw_models = {
            0x0201: "Z21 White",
            0x0202: "Z21 Black",
            0x0203: "Z21 White (newer)",
            0x0211: "Z21 Pro",
            0x0212: "smartRail"
        }
        hw_model = hw_models.get(hw_type, f"Unknown (0x{hw_type:04X})")

        print(f"\n📋 Z21 Model: {hw_model} (0x{hw_type:04X})")
        print(f"   Firmware: {hw_info['fw_version']}")
        print()

        # Step 2: Subscribe to RailCom broadcasts
        print("📡 Subscribing to Z21 broadcasts...")
        print("   Sending LAN_SET_BROADCASTFLAGS with RailCom flag enabled")
        print()

        # Broadcast flags:
        # Bit 0: Driving/switching information
        # Bit 1: RMBus data changed (decoder feedback)
        # Bit 2: System state changed
        # Bit 3: RailCom data changed (0x0088) <-- THIS IS WHAT WE NEED
        # Bit 16: CAN detector

        broadcast_flags = 0x00000001 | 0x00000008  # Bit 0 + Bit 3 (driving info + RailCom)
        broadcast_data = struct.pack('<I', broadcast_flags)

        z21._send_packet(z21.LAN_SET_BROADCASTFLAGS, broadcast_data)

        # Wait for ACK
        time.sleep(0.5)

        # Step 3: Monitor for RailCom packets
        print(f"🔊 Listening for RailCom packets (0x0088) for {duration_seconds} seconds...")
        print("   Move locomotives on track to trigger RailCom transmission")
        print("   Press Ctrl+C to stop early")
        print()

        start_time = time.time()
        railcom_packets = []
        other_packets = []

        while time.time() - start_time < duration_seconds:
            # Non-blocking receive with short timeout
            response = z21._receive_packet(timeout=1.0)

            if response:
                header, payload = response

                if header == 0x0088:  # LAN_RAILCOM_DATACHANGED
                    railcom_packets.append((time.time(), payload))
                    print(f"✅ RailCom packet received! (0x0088) - Length: {len(payload)} bytes")
                    print(f"   Raw data: {payload.hex()}")

                    # Try to parse address (first 2 bytes, little-endian)
                    if len(payload) >= 2:
                        address = struct.unpack('<H', payload[0:2])[0]
                        print(f"   Loco address: {address}")
                    print()
                else:
                    other_packets.append(header)

            # Show progress every 10 seconds
            elapsed = int(time.time() - start_time)
            if elapsed % 10 == 0 and elapsed > 0:
                remaining = duration_seconds - elapsed
                print(f"   ... still listening ({remaining}s remaining) ...")

        # Step 4: Report results
        print("\n" + "=" * 70)
        print("TEST RESULTS")
        print("=" * 70)
        print()

        print(f"📊 Statistics:")
        print(f"   Duration: {duration_seconds}s")
        print(f"   RailCom packets (0x0088): {len(railcom_packets)}")
        print(f"   Other Z21 packets: {len(set(other_packets))}")
        print()

        if railcom_packets:
            print("✅ SUCCESS - Z21 White DOES support RailCom reception!")
            print()
            print(f"   Received {len(railcom_packets)} RailCom packet(s)")
            print("   Z21 White (0x0203) can receive RailCom Plus telemetry")
            print("   Phase 9 Part 3 implementation is FEASIBLE ✅")
            print()
            print("📋 RailCom packets captured:")
            for i, (timestamp, payload) in enumerate(railcom_packets[:5], 1):
                print(f"   Packet {i}: {len(payload)} bytes - {payload.hex()}")
            if len(railcom_packets) > 5:
                print(f"   ... and {len(railcom_packets) - 5} more")
            return True
        else:
            print("❌ FAILURE - Z21 White does NOT support RailCom reception")
            print()
            print("   No 0x0088 packets received after monitoring for 60s")
            print("   Z21 White (0x0203) likely does not expose RailCom via LAN")
            print("   Phase 9 Part 3 implementation is NOT FEASIBLE ❌")
            print()
            print("💡 Possible reasons:")
            print("   1. Z21 White hardware limitation (entry-level model)")
            print("   2. RailCom not enabled on decoders (CV29 bit 3)")
            print("   3. No locomotives with RailCom running on track")
            print("   4. RailCom requires Z21 Black or Z21 Pro")
            print()
            print("📋 Other packets received (sample):")
            unique_headers = list(set(other_packets))[:10]
            for header in unique_headers:
                print(f"   0x{header:04X}")
            return False

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user (Ctrl+C)")
        return False

    finally:
        z21.close()


def main():
    duration = 60  # Default 60 seconds

    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            print(f"Invalid duration: {sys.argv[1]}")
            print("Usage: python test_railcom_listener.py [duration_seconds]")
            sys.exit(1)

    result = test_railcom_support(duration_seconds=duration)

    # Exit code: 0 if RailCom supported, 1 if not
    sys.exit(0 if result else 1)


if __name__ == '__main__':
    main()
