#!/usr/bin/env python3
"""
Test CV read in operations mode (POM) via Z21.

Usage:
    python test_cv_read.py <address> <cv_number> [expected_value]

Examples:
    python test_cv_read.py 2 4           # Read CV4 from loco 2
    python test_cv_read.py 2 4 14        # Read CV4, expect value 14

Note: Works ONLY on ESU decoders, NOT on Hornby TXS
"""

import sys
from z21 import Z21


def main():
    if len(sys.argv) < 3:
        print("Usage: python test_cv_read.py <address> <cv_number> [expected_value]")
        print()
        print("Examples:")
        print("  python test_cv_read.py 2 4           # Read CV4 from loco 2")
        print("  python test_cv_read.py 2 4 14        # Read CV4, expect value 14")
        print()
        print("Note: Works ONLY on ESU decoders, NOT on Hornby TXS")
        return

    address = int(sys.argv[1])
    cv_number = int(sys.argv[2])
    expected_value = int(sys.argv[3]) if len(sys.argv) > 3 else None

    print("=" * 60)
    print("TEST CV READ IN OPERATIONS MODE")
    print("=" * 60)
    print()
    print(f"Locomotiva: address {address}")
    print(f"CV da leggere: CV{cv_number}")
    if expected_value is not None:
        print(f"Valore atteso: {expected_value}")
    print()
    print("⚠️  Funziona SOLO su decoder ESU, NON su Hornby TXS")
    print()

    z21 = Z21(verbose=True)

    try:
        # Test lettura CV (con 3 retry distanziati 2s)
        value = z21.read_cv_on_main(
            address=address,
            cv_number=cv_number,
            timeout=2.0,
            retries=3
        )

        if value is not None:
            print(f"\n✅ Test SUPERATO!")
            print(f"   CV{cv_number} letto = {value}")
            if expected_value is not None:
                if value == expected_value:
                    print(f"   ✅ Valore CORRETTO (atteso {expected_value})")
                else:
                    print(f"   ⚠️  Valore diverso dall'atteso (atteso {expected_value}, letto {value})")
        else:
            print(f"\n❌ Test FALLITO: impossibile leggere CV{cv_number}")
            print("   Possibili cause:")
            print("   - Decoder non ESU (Hornby TXS non supporta read)")
            print("   - Locomotiva non sul binario o power OFF")
            print("   - Instabilità decoder ESU (riprova)")

    finally:
        z21.close()


if __name__ == '__main__':
    main()
