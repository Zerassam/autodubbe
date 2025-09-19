#!/usr/bin/env python3
"""
Setup script for AutoDubber - checks system dependencies and guides initial configuration.
"""
import os
import sys
import subprocess
import json
from pathlib import Path

def check_command(cmd):
    """Check if a command exists in PATH."""
    try:
        subprocess.run([cmd, '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def check_system_dependencies():
    """Check required system dependencies."""
    deps = {
        'ffmpeg': 'FFmpeg (for audio/video processing)',
        'yt-dlp': 'yt-dlp (for YouTube downloads)', 
        'whisper': 'OpenAI Whisper (for transcription)'
    }
    
    missing = []
    for cmd, desc in deps.items():
        if not check_command(cmd):
            missing.append(f"  - {cmd}: {desc}")
    
    if missing:
        print("❌ Missing system dependencies:")
        print("\n".join(missing))
        print("\nInstall instructions:")
        print("  Ubuntu/Debian: sudo apt install ffmpeg")
        print("  macOS: brew install ffmpeg")
        print("  yt-dlp: pip install yt-dlp")
        print("  whisper: pip install openai-whisper")
        return False
    
    print("✅ All system dependencies found")
    return True

def setup_config():
    """Guide user through configuration setup."""
    config_path = Path('config/config.json')
    example_path = Path('config/config.example.json')
    
    if config_path.exists():
        print("✅ Configuration file already exists")
        return True
    
    if not example_path.exists():
        print("❌ Example configuration file not found")
        return False
    
    print("📝 Setting up configuration...")
    
    # Load example config
    with open(example_path) as f:
        config = json.load(f)
    
    # Get user inputs
    channel_id = input("Enter source YouTube channel ID (UC...): ").strip()
    if channel_id:
        config['SOURCE_CHANNEL_ID'] = channel_id
    
    api_key = input("Enter YouTube Data API key (optional, press Enter to skip): ").strip()
    if api_key:
        config['YOUTUBE']['API_KEY'] = api_key
    
    # Save config
    config_path.parent.mkdir(exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Configuration saved to {config_path}")
    print("⚠️  Remember to:")
    print("   1. Add your YouTube OAuth client_secrets.json file")
    print("   2. Update API keys and credentials as needed")
    return True

def main():
    print("🚀 AutoDubber Setup")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    
    print(f"✅ Python {sys.version.split()[0]}")
    
    # Check system dependencies
    if not check_system_dependencies():
        return False
    
    # Setup configuration
    if not setup_config():
        return False
    
    print("\n🎉 Setup complete!")
    print("Next steps:")
    print("  1. Run: python pipeline_main.py")
    print("  2. Check logs/ directory for output")
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)