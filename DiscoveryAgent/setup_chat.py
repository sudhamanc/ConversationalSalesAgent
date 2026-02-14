"""Setup script to configure your Gemini API key"""

import os
from pathlib import Path

def setup_env_file():
    """Interactive setup to create .env file"""
    
    print("\n" + "="*60)
    print("Prospect Chat Configuration Setup")
    print("="*60)
    
    # Check if .env already exists
    env_file = Path(".env")
    if env_file.exists():
        print("\n⚠️  .env file already exists!")
        overwrite = input("Do you want to overwrite it? (y/n): ").strip().lower()
        if overwrite != 'y':
            print("Setup cancelled.")
            return
    
    # Get API key
    print("\n📝 Get your Gemini API key:")
    print("   1. Go to: https://makersuite.google.com/app/apikey")
    print("   2. Sign in with your Google account")
    print("   3. Click 'Create API Key'")
    print("   4. Copy the key (starts with AIza...)\n")
    
    api_key = input("Paste your Gemini API key: ").strip()
    
    if not api_key:
        print("❌ API key cannot be empty!")
        return
    
    if not api_key.startswith("AIza"):
        print("⚠️  Warning: API key doesn't look like a Google API key")
        print("   (Should start with 'AIza')")
        confirm = input("Continue anyway? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Setup cancelled.")
            return
    
    # Get model (with default)
    print("\n📦 Choose Gemini model:")
    print("   1. gemini-2.0-flash-exp (Recommended - Fast, latest features)")
    print("   2. gemini-1.5-pro (Stable, production-ready)")
    print("   3. gemini-1.5-flash (Fast, lower cost)")
    
    model_choice = input("\nEnter choice (1-3) or press Enter for default [1]: ").strip()
    
    models = {
        "1": "gemini-2.0-flash-exp",
        "2": "gemini-1.5-pro",
        "3": "gemini-1.5-flash",
        "": "gemini-2.0-flash-exp"
    }
    
    model = models.get(model_choice, "gemini-2.0-flash-exp")
    
    # Get port (with default)
    port = input("\nServer port [8080]: ").strip() or "8080"
    
    # Create .env content
    env_content = f"""# Prospect Chat Configuration
# Created by setup_chat.py

# Gemini API Configuration
GOOGLE_API_KEY='{api_key}'
GEMINI_MODEL='{model}'

# Server Configuration
PORT={port}

# Database Configuration (auto-detected)
DB_PATH='discover_prospecting_clean.db'
"""
    
    # Write .env file
    try:
        with open(".env", "w") as f:
            f.write(env_content)
        
        print("\n✅ Configuration saved to .env")
        print("\n" + "="*60)
        print("Next Steps:")
        print("="*60)
        print("1. Install dependencies:")
        print("   pip install google-generativeai python-dotenv fastapi uvicorn")
        print("\n2. Start the server:")
        print("   python main_server.py")
        print("\n3. Test the chat:")
        print("   python test_chat.py")
        print("\n4. Or visit the API docs:")
        print("   http://localhost:8080/docs")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error creating .env file: {str(e)}")
        return

def check_dependencies():
    """Check if required packages are installed"""
    
    print("\n🔍 Checking dependencies...")
    
    packages = {
        "google.genai": "google-genai",
        "dotenv": "python-dotenv",
        "fastapi": "fastapi",
        "uvicorn": "uvicorn"
    }
    
    missing = []
    
    for module_name, package_name in packages.items():
        try:
            __import__(module_name)
            print(f"  ✅ {package_name}")
        except ImportError:
            print(f"  ❌ {package_name} (missing)")
            missing.append(package_name)
    
    if missing:
        print(f"\n📦 Install missing packages with:")
        print(f"   pip install {' '.join(missing)}")
        return False
    
    print("\n✅ All dependencies installed!")
    return True

def verify_database():
    """Check if database file exists"""
    
    print("\n🗄️  Checking database...")
    
    db_file = Path("data/discover_prospecting_clean.db")
    if db_file.exists():
        size_mb = db_file.stat().st_size / (1024 * 1024)
        print(f"  ✅ Database found ({size_mb:.2f} MB)")
        return True
    else:
        print("  ❌ Database not found: data/discover_prospecting_clean.db")
        print("     Make sure the database file is in the data/ directory")
        return False

def main():
    """Run the setup wizard"""
    
    print("\n🚀 Prospect Chat Setup Wizard")
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    # Check database
    db_ok = verify_database()
    
    if not deps_ok or not db_ok:
        print("\n⚠️  Please resolve the issues above before continuing.")
        return
    
    # Run env setup
    print("\n" + "="*60)
    input("Press Enter to configure your API key...")
    setup_env_file()

if __name__ == "__main__":
    main()
