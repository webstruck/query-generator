#!/usr/bin/env python3
"""Web interface launcher for qgen."""

import os
import sys
import subprocess
import threading
import time
import webbrowser
from pathlib import Path
from rich.console import Console

console = Console()

def launch_web_interface(legacy=False):
    """Launch the QGen web interface with FastAPI backend and React frontend."""
    
    # Paths
    web_dir = Path(__file__).parent
    backend_file = web_dir / "backend.py"
    frontend_dir = web_dir / ("frontend-legacy" if legacy else "frontend")
    
    # Check if backend exists
    if not backend_file.exists():
        console.print("[red]❌ Backend file not found. Web interface not properly installed.[/red]")
        return
    
    # Check if frontend exists
    if not frontend_dir.exists():
        frontend_type = "legacy" if legacy else "default"
        console.print(f"[red]❌ {frontend_type.title()} frontend directory not found. Web interface not properly installed.[/red]")
        return
    
    try:
        # Get user's current working directory
        user_cwd = os.getcwd()
        
        # Start backend server with user's working directory
        console.print("🚀 Starting FastAPI backend server...")
        env = os.environ.copy()
        env['QGEN_USER_CWD'] = user_cwd
        backend_process = subprocess.Popen([
            sys.executable, str(backend_file)
        ], cwd=str(web_dir), env=env)
        
        # Start frontend dev server
        frontend_type = "legacy" if legacy else "default"
        dev_port = 5173 if legacy else 5174
        console.print(f"⚛️  Starting React development server ({frontend_type})...")
        frontend_process = subprocess.Popen([
            "npm", "run", "dev"
        ], cwd=str(frontend_dir))
        
        # Give servers time to start
        time.sleep(3)
        
        # Open browser
        browser_url = f"http://localhost:{dev_port}"
        console.print(f"🌐 Opening {frontend_type} web interface in browser...")
        webbrowser.open(browser_url)
        
        console.print(f"✅ {frontend_type.title()} web interface is running!")
        console.print(f"   Frontend: {browser_url}")
        console.print("   Backend API: http://localhost:8888")
        if legacy:
            console.print("   Default (Shadcn): http://localhost:5174 (if running)")
        else:
            console.print("   Legacy: http://localhost:5173 (if available)")
        console.print("")
        console.print("Press Ctrl+C to stop servers")
        
        # Wait for user to stop
        try:
            backend_process.wait()
        except KeyboardInterrupt:
            console.print("\n🛑 Stopping servers...")
            backend_process.terminate()
            frontend_process.terminate()
            
            # Wait for clean shutdown
            backend_process.wait()
            frontend_process.wait()
            
            console.print("✅ Servers stopped")
            
    except FileNotFoundError as e:
        if "npm" in str(e):
            console.print("[red]❌ npm not found. Please install Node.js and npm.[/red]")
        else:
            console.print(f"[red]❌ Error: {e}[/red]")
    except Exception as e:
        console.print(f"[red]❌ Failed to start web interface: {e}[/red]")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Launch QGen web interface')
    parser.add_argument('--shadcn', action='store_true', help='Launch shadcn/ui version instead of original')
    args = parser.parse_args()
    
    launch_web_interface(shadcn=args.shadcn)