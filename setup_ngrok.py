#!/usr/bin/env python3
"""
Script to help set up ngrok for local development
This allows Twilio to reach your local Django server for webhooks
"""

import os
import subprocess
import sys
import time
import requests
from pathlib import Path

def check_ngrok_installed():
    """Check if ngrok is installed"""
    try:
        result = subprocess.run(['ngrok', 'version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ ngrok is installed: {result.stdout.strip()}")
            return True
        else:
            print("❌ ngrok is not installed or not in PATH")
            return False
    except FileNotFoundError:
        print("❌ ngrok is not installed or not in PATH")
        return False

def install_ngrok():
    """Install ngrok if not present"""
    print("📥 Installing ngrok...")
    
    # For Windows
    if sys.platform.startswith('win'):
        print("Please download ngrok from https://ngrok.com/download")
        print("Extract it to a folder and add that folder to your PATH")
        print("Or run: winget install ngrok")
        return False
    
    # For macOS
    elif sys.platform.startswith('darwin'):
        try:
            subprocess.run(['brew', 'install', 'ngrok'], check=True)
            return True
        except subprocess.CalledProcessError:
            print("Please install ngrok manually from https://ngrok.com/download")
            return False
    
    # For Linux
    else:
        try:
            subprocess.run(['snap', 'install', 'ngrok'], check=True)
            return True
        except subprocess.CalledProcessError:
            print("Please install ngrok manually from https://ngrok.com/download")
            return False

def start_ngrok(port=8000):
    """Start ngrok tunnel"""
    print(f"🚀 Starting ngrok tunnel on port {port}...")
    
    try:
        # Start ngrok in background
        process = subprocess.Popen(
            ['ngrok', 'http', str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a moment for ngrok to start
        time.sleep(3)
        
        # Get the public URL
        try:
            response = requests.get('http://localhost:4040/api/tunnels')
            if response.status_code == 200:
                tunnels = response.json()['tunnels']
                if tunnels:
                    public_url = tunnels[0]['public_url']
                    print(f"✅ ngrok tunnel started: {public_url}")
                    print(f"🔗 Your webhook base URL should be: {public_url}")
                    return public_url, process
        except requests.exceptions.RequestException:
            print("⚠️  Could not get ngrok tunnel info, but process started")
            return None, process
            
    except Exception as e:
        print(f"❌ Failed to start ngrok: {e}")
        return None, None

def update_env_file(webhook_url):
    """Update .env file with webhook URL"""
    env_file = Path('.env')
    
    if env_file.exists():
        # Read existing content
        with open(env_file, 'r') as f:
            content = f.read()
        
        # Update or add WEBHOOK_BASE_URL
        lines = content.split('\n')
        updated = False
        
        for i, line in enumerate(lines):
            if line.startswith('WEBHOOK_BASE_URL='):
                lines[i] = f'WEBHOOK_BASE_URL={webhook_url}'
                updated = True
                break
        
        if not updated:
            lines.append(f'WEBHOOK_BASE_URL={webhook_url}')
        
        # Write back
        with open(env_file, 'w') as f:
            f.write('\n'.join(lines))
        
        print(f"✅ Updated .env file with WEBHOOK_BASE_URL={webhook_url}")
    else:
        print(f"📝 Creating .env file with WEBHOOK_BASE_URL={webhook_url}")
        with open(env_file, 'w') as f:
            f.write(f'WEBHOOK_BASE_URL={webhook_url}\n')

def main():
    print("🔧 Setting up ngrok for Twilio webhooks...")
    print()
    
    # Check if ngrok is installed
    if not check_ngrok_installed():
        print("Would you like to install ngrok? (y/n): ", end="")
        if input().lower() == 'y':
            if not install_ngrok():
                print("Please install ngrok manually and run this script again.")
                return
        else:
            print("Please install ngrok manually and run this script again.")
            return
    
    # Start ngrok
    webhook_url, process = start_ngrok(8000)
    
    if webhook_url:
        # Update .env file
        update_env_file(webhook_url)
        
        print()
        print("🎉 Setup complete!")
        print(f"📞 Your Django server should now be accessible at: {webhook_url}")
        print("🌐 Twilio can now reach your webhooks")
        print()
        print("⚠️  Keep this terminal open while testing Twilio calls")
        print("🛑 Press Ctrl+C to stop ngrok when done")
        print()
        
        try:
            # Keep the process running
            process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Stopping ngrok...")
            process.terminate()
            process.wait()
            print("✅ ngrok stopped")
    else:
        print("❌ Failed to start ngrok tunnel")

if __name__ == "__main__":
    main()
