#!/usr/bin/env python3
"""
Enable RailCom Plus on ESU decoder (Phase 9 Part 3 - Research).

This script enables RailCom and RailCom Plus on ESU LokPilot/LokSound decoders.

Usage:
    python enable_railcom_plus.py <address>

Example:
    python enable_railcom_plus.py 1    # Enable on loco 1 (Gr.675 017 - ESU LokSound V4.0)

Requirements:
- ESU decoder (LokPilot 5, LokSound V4.0/V5.0)
- Locomotive on main track (operations mode programming)
- Track power ON

CVs modified:
- CV29: Enable RailCom (bit 3 = 1)
- CV106: Enable RailCom Plus (ESU-specific, value = 1)

Note:
- Hornby TXS decoders (loco 7) do NOT support RailCom
- Zimo MX630 (loco 4) supports RailCom but NOT RailCom Plus (ESU proprietary)
"""

import sys
import os
import time

# Add scripts to path (z21.py is in scripts/)
scripts_path = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, scripts_path)

from z21 import Z21


def enable_railcom_plus(z21, address):
    """
    Enable RailCom Plus on ESU decoder.

    Args:
        z21: Z21 instance
        address: Locomotive DCC address

    Returns:
        True if successful, False otherwise
    """
    print("=" * 70)
    print(f"ENABLE RAILCOM PLUS ON LOCO {address}")
    print("=" * 70)
    print()
    print("⚠️  IMPORTANT:")
    print("   - Place locomotive on MAIN track (not programming track)")
    print("   - Turn track power ON")
    print("   - This uses operations mode programming (POM)")
    print()

    # Check track power
    status = z21.get_status()
    if not status:
        print("❌ Failed to get Z21 status")
        return False

    if not status['track_power_on']:
        print("❌ Track power is OFF - cannot program on main")
        print("   Turn track power ON and try again")
        return False

    print("✅ Track power is ON")
    print()

    # Step 1: Read current CV29
    print("🔍 Step 1: Reading CV29 (Configuration bits)...")
    cv29 = z21.read_cv_on_main(address, 29)

    if cv29 is None:
        print("❌ Failed to read CV29")
        print()
        print("💡 Possible reasons:")
        print("   1. Decoder does not support CV read in operations mode")
        print("      (Hornby TXS decoders cannot read CVs on main)")
        print("   2. Locomotive not on track or no response")
        print("   3. Decoder address mismatch")
        print()
        print("⚠️  Will attempt to write CV29 anyway (blind write)")
        cv29 = 14  # Assume default value
    else:
        print(f"✅ Current CV29 = {cv29} (0b{cv29:08b})")

    print()

    # Step 2: Enable RailCom (CV29 bit 3)
    print("🔧 Step 2: Enabling RailCom (CV29 bit 3)...")

    if cv29 & 0x08:
        print("   ✓ RailCom already enabled in CV29")
    else:
        new_cv29 = cv29 | 0x08
        print(f"   Writing CV29 = {new_cv29} (0b{new_cv29:08b})")
        print("   Attempting 3 times (operations mode may require retry)...")

        # Retry write 3 times (ops mode has no ACK, best effort)
        for attempt in range(1, 4):
            print(f"   Attempt {attempt}/3...")
            z21.write_cv_ops_mode(address, 29, new_cv29)
            time.sleep(1.0)  # Wait for decoder to process

        print("   ✅ CV29 write commands sent (3x for reliability)")
        print("   ⚠️  No ACK in operations mode - decoder should accept")

    print()

    # Step 3: Enable RailCom Plus (CV106)
    print("🔧 Step 3: Enabling RailCom Plus (ESU CV106)...")
    print("   Writing CV106 = 1 (RailCom Plus enable)")
    print()
    print("   ℹ️  CV106 values (ESU-specific):")
    print("      0 = RailCom Plus disabled")
    print("      1 = RailCom Plus enabled (default)")
    print("      2 = RailCom Plus with extended data")
    print()
    print("   Attempting 3 times (operations mode may require retry)...")

    # Retry write 3 times (ops mode has no ACK, best effort)
    for attempt in range(1, 4):
        print(f"   Attempt {attempt}/3...")
        z21.write_cv_ops_mode(address, 106, 1)
        time.sleep(1.0)  # Wait for decoder to process

    print("   ✅ CV106 write commands sent (3x for reliability)")
    print("   ⚠️  No ACK in operations mode - decoder should accept")

    print()

    # Step 4: Optional - Set RailCom transmission interval (CV112-113)
    print("🔧 Step 4: Setting RailCom transmission interval (optional)...")
    print("   CV112-113 control how often decoder sends telemetry")
    print("   Default: 1000ms (1 second)")
    print("   Recommended: 2000ms (2 seconds) - reduces bus load")
    print()
    print("   Skipping for now - default is fine")
    print()

    # Summary
    print("=" * 70)
    print("✅ RAILCOM PLUS CONFIGURATION COMPLETE")
    print("=" * 70)
    print()
    print(f"🚂 Locomotive {address} should now transmit RailCom Plus telemetry")
    print()
    print("📋 What was configured:")
    print(f"   - CV29 bit 3 = 1 (RailCom enabled)")
    print(f"   - CV106 = 1 (RailCom Plus enabled)")
    print()
    print("🔬 Next step:")
    print("   Run test_railcom_listener.py to verify Z21 receives telemetry")
    print("   Command: python test_railcom_listener.py")
    print()
    print("💡 Test procedure:")
    print("   1. Keep this locomotive on track")
    print("   2. Move it around (change speed/direction)")
    print("   3. Monitor for RailCom packets (0x0088)")
    print()

    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python enable_railcom_plus.py <address>")
        print()
        print("Examples:")
        print("  python enable_railcom_plus.py 1    # Loco 1 (Gr.675 017 - ESU LokSound)")
        print("  python enable_railcom_plus.py 2    # Loco 2 (E656 182 - ESU LokPilot 5)")
        print("  python enable_railcom_plus.py 5    # Loco 5 (D645 014 - ESU LokPilot 5)")
        print()
        print("⚠️  ESU decoders only:")
        print("  - Loco 1, 2, 5, 6, 8: ESU LokPilot 5 or LokSound V4.0 ✅")
        print("  - Loco 7: Hornby TXS (NO RailCom support) ❌")
        print("  - Loco 4: Zimo MX630 (RailCom but NOT RailCom Plus) ⚠️")
        sys.exit(1)

    try:
        address = int(sys.argv[1])
    except ValueError:
        print(f"❌ Invalid address: {sys.argv[1]}")
        print("   Address must be a number (1-10239)")
        sys.exit(1)

    if address < 1 or address > 10239:
        print(f"❌ Address {address} out of range (1-10239)")
        sys.exit(1)

    # Check if this is a known non-ESU decoder
    if address == 7:
        print("⚠️  WARNING: Loco 7 (E656 239) has Hornby TXS decoder")
        print("   Hornby TXS does NOT support RailCom")
        print("   This script will not work for this locomotive")
        print()
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Aborted")
            sys.exit(0)

    if address == 4:
        print("⚠️  WARNING: Loco 4 (2048) has Zimo MX630 decoder")
        print("   Zimo supports RailCom but NOT RailCom Plus (ESU proprietary)")
        print("   You will get basic RailCom but no motor current telemetry")
        print()
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Aborted")
            sys.exit(0)

    # Connect to Z21
    z21 = Z21(verbose=True)

    try:
        result = enable_railcom_plus(z21, address)
        sys.exit(0 if result else 1)
    finally:
        z21.close()


if __name__ == '__main__':
    main()
