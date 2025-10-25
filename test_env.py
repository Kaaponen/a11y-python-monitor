#!/usr/bin/env python3
"""
Minimal test to check if the environment is working
"""

import sys
import os
import time

def test_imports():
    """Test basic module imports"""
    print("🧪 Testing module imports...")
    
    # Test basic imports
    try:
        import asyncio
        print("✅ asyncio imported")
    except Exception as e:
        print(f"❌ asyncio failed: {e}")
        return False
    
    # Test playwright import without async API
    try:
        import playwright
        print("✅ playwright base module imported")
    except Exception as e:
        print(f"❌ playwright failed: {e}")
        return False
    
    # Try importing the async API with timeout
    print("🔄 Testing playwright async API...")
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError("Import timeout")
    
    # Set a 10 second timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(10)
    
    try:
        from playwright.async_api import async_playwright
        signal.alarm(0)  # Cancel the alarm
        print("✅ playwright async API imported")
        return True
    except TimeoutError:
        signal.alarm(0)
        print("❌ playwright async API import timed out")
        return False
    except Exception as e:
        signal.alarm(0)
        print(f"❌ playwright async API failed: {e}")
        return False

def test_simple_streamlit():
    """Test if streamlit can import"""
    print("🧪 Testing Streamlit import...")
    
    try:
        # Try a very basic streamlit import
        import streamlit as st
        print("✅ Streamlit imported successfully")
        return True
    except Exception as e:
        print(f"❌ Streamlit import failed: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Environment Diagnostic Tool")
    print("=" * 40)
    
    # Test Python version
    print(f"🐍 Python: {sys.version}")
    print(f"📂 Working directory: {os.getcwd()}")
    
    # Test imports
    imports_ok = test_imports()
    streamlit_ok = test_simple_streamlit()
    
    print("\n📋 Summary:")
    print(f"✅ Basic imports: {'OK' if imports_ok else 'FAILED'}")
    print(f"✅ Streamlit: {'OK' if streamlit_ok else 'FAILED'}")
    
    if imports_ok and streamlit_ok:
        print("\n🎉 Environment appears to be working!")
        print("You can try running the scanner manually with:")
        print("  streamlit run src/ui/streamlit_app.py")
    else:
        print("\n💥 Environment has issues")
        print("Consider reinstalling dependencies:")
        print("  pip install --force-reinstall playwright streamlit")