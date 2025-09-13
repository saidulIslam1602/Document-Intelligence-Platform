#!/usr/bin/env python3
"""
Start the Document Intelligence Platform Demo
This will launch a web interface you can interact with
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def check_dependencies():
    """Check if required packages are installed"""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "python-multipart",
        "openai",
        "python-dotenv"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")
    
    if missing_packages:
        print(f"\n📦 Installing missing packages: {', '.join(missing_packages)}")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install"
            ] + missing_packages)
            print("✅ All packages installed successfully!")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install packages: {e}")
            return False
    
    return True

def start_dashboard():
    """Start the web dashboard"""
    print("\n🚀 Starting Document Intelligence Platform...")
    print("=" * 60)
    print("📱 Web Dashboard will open at: http://localhost:8000")
    print("🔑 Using OpenAI API for AI analysis")
    print("📄 Upload documents to see AI processing in action!")
    print("=" * 60)
    
    # Wait a moment then open browser
    def open_browser():
        time.sleep(3)
        webbrowser.open("http://localhost:8000")
    
    import threading
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Start the web server
    try:
        import uvicorn
        from web_dashboard import app
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down Document Intelligence Platform...")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        return False
    
    return True

def main():
    """Main function"""
    print("🚀 Document Intelligence Platform - Local Demo")
    print("=" * 60)
    
    # Check if .env file exists
    if not os.path.exists("local.env"):
        print("❌ local.env file not found!")
        print("💡 Make sure you have the environment file with your OpenAI API key")
        return False
    
    # Check dependencies
    if not check_dependencies():
        print("❌ Failed to install dependencies")
        return False
    
    # Start dashboard
    if not start_dashboard():
        print("❌ Failed to start dashboard")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)