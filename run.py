#!/usr/bin/env python3
"""
Enhanced NLvoorelkaar Tool Launcher
Easy startup script with environment setup and error handling
"""

import sys
import os
import subprocess
import logging
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        print("Please upgrade Python and try again")
        return False
    return True

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        'customtkinter',
        'cryptography', 
        'requests',
        'beautifulsoup4',
        'aiohttp'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n🔧 Installing missing packages...")
        
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
            ])
            print("✅ Dependencies installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install dependencies")
            print("Please run: pip install -r requirements.txt")
            return False
    
    return True

def setup_environment():
    """Setup application environment"""
    # Add current directory to Python path
    current_dir = Path(__file__).parent.absolute()
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    # Create necessary directories
    directories = ['data', 'backups', 'logs']
    for directory in directories:
        dir_path = current_dir / directory
        dir_path.mkdir(exist_ok=True, mode=0o700)
    
    # Setup basic logging
    log_file = current_dir / 'logs' / 'startup.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def main():
    """Main launcher function"""
    print("🚀 Enhanced NLvoorelkaar Tool v2.0.0")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Setup environment
    print("🔧 Setting up environment...")
    setup_environment()
    
    # Check dependencies
    print("📦 Checking dependencies...")
    if not check_dependencies():
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Start application
    print("✅ Starting application...")
    try:
        from main import main as app_main
        app_main()
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure all files are present and try again")
        input("Press Enter to exit...")
        sys.exit(1)
    except (RuntimeError, TypeError, ValueError, OSError) as e:
        print(f"❌ Unexpected error: {e}")
        logging.exception("Application error")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()

