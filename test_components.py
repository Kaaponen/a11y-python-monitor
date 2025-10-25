#!/usr/bin/env python3
"""
Test script to verify all components work
"""
import sys
import asyncio

def test_imports():
    """Test that all imports work"""
    try:
        print("🔍 Testing imports...")
        
        # Core imports
        from playwright.async_api import async_playwright
        print("✅ Playwright - OK")
        
        from src.scanner.core import run_axe
        print("✅ Scanner core - OK")
        
        from src.performance.fallback_cache import get_fallback_cache
        print("✅ Performance cache - OK")
        
        import streamlit
        print("✅ Streamlit - OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

async def test_simple_scan():
    """Test simple scan functionality"""
    try:
        print("\n🚀 Testing simple scan...")
        
        # Use the simple test scanner
        from test_simple_scan import simple_scan
        result = await simple_scan("https://www.example.com")
        
        if result and 'violations' in result:
            print(f"✅ Scan successful! Found {len(result['violations'])} violations")
            return True
        else:
            print("❌ Scan failed or no results")
            return False
            
    except Exception as e:
        print(f"❌ Scan error: {e}")
        return False

def test_cache():
    """Test cache functionality"""
    try:
        print("\n📦 Testing cache...")
        
        cache = get_fallback_cache()
        
        # Test basic cache operations
        asyncio.run(cache.set('test', 'value', 60))
        result = asyncio.run(cache.get('test'))
        
        if result == 'value':
            print("✅ Cache - OK")
            stats = cache.get_stats()
            print(f"   Cache stats: {stats['hit_rate']}% hit rate")
            return True
        else:
            print("❌ Cache - Failed")
            return False
            
    except Exception as e:
        print(f"❌ Cache error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Saavutettavuusskanneri - Component Tests\n")
    
    tests = [
        ("Imports", test_imports),
        ("Cache", test_cache),
        ("Simple Scan", lambda: asyncio.run(test_simple_scan()))
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} test crashed: {e}")
            results.append((name, False))
    
    print("\n" + "="*50)
    print("📊 TEST RESULTS:")
    print("="*50)
    
    passed = 0
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("\n🎉 All tests passed! Scanner is ready to use.")
        print("\nNext steps:")
        print("1. Start web UI: streamlit run src/ui/streamlit_app.py")
        print("2. Or use CLI: python cli.py scan https://example.com")
    else:
        print(f"\n⚠️  {len(results) - passed} tests failed. Check dependencies.")

if __name__ == "__main__":
    from src.performance.fallback_cache import get_fallback_cache
    main()