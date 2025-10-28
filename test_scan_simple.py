#!/usr/bin/env python3
"""
Simple test script to verify scanning functionality
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.scanner.core import run_axe


async def test_simple_scan():
    """Test a simple scan to verify functionality"""
    test_url = "https://example.com"

    print(f"🧪 Testing scan for: {test_url}")

    try:
        result = await run_axe(test_url)

        print("✅ Scan completed successfully!")
        print(f"📊 Violations found: {len(result.get('violations', []))}")
        print(f"✅ Passes: {len(result.get('passes', []))}")
        print(f"❓ Incomplete: {len(result.get('incomplete', []))}")

        if result.get("violations"):
            print("\n📋 Violations:")
            for i, violation in enumerate(result["violations"][:3], 1):  # Show first 3
                print(f"  {i}. {violation.get('help', 'Unknown')}")

        return True

    except Exception as e:
        print(f"❌ Scan failed: {e}")
        return False


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        success = loop.run_until_complete(test_simple_scan())
        if success:
            print("\n🎉 Test passed! Scanner is working correctly.")
        else:
            print("\n💥 Test failed! Check the errors above.")
            sys.exit(1)
    finally:
        loop.close()
