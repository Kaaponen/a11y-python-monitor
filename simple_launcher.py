#!/usr/bin/env python3
"""
Simplified accessibility scanner launcher that bypasses problematic imports
"""

import sys
import os
import asyncio
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

def check_dependencies():
    """Check that required dependencies are available"""
    try:
        import playwright
        print("✅ Playwright available")
        return True
    except ImportError:
        print("❌ Playwright not found. Install with: pip install playwright")
        return False

def run_simple_scan(url: str):
    """Run a simplified scan without performance optimizations"""
    import asyncio
    from playwright.async_api import async_playwright
    import json
    
    async def scan():
        async with async_playwright() as p:
            print(f"🚀 Starting scan for: {url}")
            
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # Navigate to page
                response = await page.goto(url, wait_until='networkidle', timeout=30000)
                
                if not response or response.status >= 400:
                    print(f"❌ Failed to load page: HTTP {response.status if response else 'No response'}")
                    return None
                
                print("📄 Page loaded successfully")
                
                # Load axe-core
                axe_js_url = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.7.2/axe.min.js"
                await page.add_script_tag(url=axe_js_url)
                print("🔧 Axe-core loaded")
                
                # Run axe analysis
                axe_results = await page.evaluate("""
                    () => {
                        return new Promise((resolve, reject) => {
                            axe.run((err, results) => {
                                if (err) reject(err);
                                else resolve(results);
                            });
                        });
                    }
                """)
                
                print("✅ Scan completed!")
                return axe_results
                
            except Exception as e:
                print(f"❌ Error during scan: {e}")
                return None
            finally:
                await browser.close()
    
    return asyncio.run(scan())

def run_streamlit():
    """Try to run Streamlit with error handling"""
    try:
        import subprocess
        import time
        
        print("🚀 Starting Streamlit...")
        
        # Use subprocess to avoid import issues
        cmd = [
            sys.executable, 
            "-m", 
            "streamlit", 
            "run", 
            "src/ui/streamlit_app.py",
            "--server.port", "8503"
        ]
        
        process = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit and check if it started
        time.sleep(3)
        
        if process.poll() is None:  # Still running
            print("✅ Streamlit started successfully!")
            print("🌐 Open browser: http://localhost:8503")
            print("⏹️  Press Ctrl+C to stop")
            try:
                process.wait()
            except KeyboardInterrupt:
                print("\n👋 Stopping Streamlit...")
                process.terminate()
                process.wait()
        else:
            # Process ended, check for errors
            stdout, stderr = process.communicate()
            print(f"❌ Streamlit failed to start:")
            if stderr:
                print(f"Error: {stderr}")
            if stdout:
                print(f"Output: {stdout}")
                
    except Exception as e:
        print(f"❌ Failed to start Streamlit: {e}")

def main():
    """Main function"""
    print("🧪 A11y Scanner - Simple Launcher")
    print("=" * 50)
    
    if not check_dependencies():
        return 1
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            # Run simple test
            url = sys.argv[2] if len(sys.argv) > 2 else "https://example.com"
            result = run_simple_scan(url)
            if result:
                violations = len(result.get('violations', []))
                passes = len(result.get('passes', []))
                print(f"📊 Results: {violations} violations, {passes} passes")
            return 0 if result else 1
        elif sys.argv[1] == "web":
            # Run web UI
            run_streamlit()
            return 0
    
    print("Usage:")
    print("  python simple_launcher.py test [url]  - Run simple test")
    print("  python simple_launcher.py web        - Start web UI")
    return 0

if __name__ == "__main__":
    exit(main())