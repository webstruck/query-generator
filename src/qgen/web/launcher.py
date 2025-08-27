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

def launch_web_interface():
    """Launch the QGen web interface with FastAPI backend and React frontend."""
    
    # Paths
    web_dir = Path(__file__).parent
    backend_file = web_dir / "backend.py"
    frontend_dir = web_dir / "frontend"
    
    # Check if backend exists
    if not backend_file.exists():
        console.print("[red]❌ Backend file not found. Web interface not properly installed.[/red]")
        return
    
    # Check if frontend exists
    if not frontend_dir.exists():
        console.print("[red]❌ Frontend directory not found. Web interface not properly installed.[/red]")
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
        console.print("⚛️  Starting React development server...")
        frontend_process = subprocess.Popen([
            "npm", "run", "dev"
        ], cwd=str(frontend_dir))
        
        # Give servers time to start
        time.sleep(3)
        
        # Open browser
        console.print("🌐 Opening web interface in browser...")
        webbrowser.open("http://localhost:5173")
        
        console.print("✅ Web interface is running!")
        console.print("   Frontend: http://localhost:5173")
        console.print("   Backend API: http://localhost:8888")
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
    launch_web_interface()