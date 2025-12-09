#!/usr/bin/env python3
"""
Resume Builder - One-Click Launcher

This script automates the setup and execution of the Resume Builder application.
It handles:
1. Virtual Environment creation
2. Dependency installation
3. Server startup
4. Browser launch
"""

import os
import sys
import subprocess
import venv
import time
import webbrowser
import platform
import signal
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).parent.absolute()
VENV_DIR = PROJECT_ROOT / ".venv"
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements-lite.txt"
HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}"


def print_step(message):
    print(f"\n[🚀] {message}")


def print_error(message):
    print(f"\n[❌] Error: {message}")


def get_python_exe():
    """Get the path to the Python executable in the virtual environment."""
    if platform.system() == "Windows":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def get_pip_exe():
    """Get the path to the Pip executable in the virtual environment."""
    if platform.system() == "Windows":
        return VENV_DIR / "Scripts" / "pip.exe"
    return VENV_DIR / "bin" / "pip"


def ensure_venv():
    """Create virtual environment if it doesn't exist."""
    if not VENV_DIR.exists():
        print_step(f"Creating virtual environment at {VENV_DIR}...")
        try:
            builder = venv.EnvBuilder(with_pip=True)
            builder.create(VENV_DIR)
        except Exception as e:
            print_error(f"Failed to create virtual environment: {e}")
            sys.exit(1)
    else:
        print_step("Virtual environment already exists.")


def install_dependencies():
    """Install dependencies from requirements-lite.txt."""
    pip_exe = get_pip_exe()
    if not pip_exe.exists():
        print_error("Pip not found in virtual environment!")
        sys.exit(1)

    print_step("Checking/Installing dependencies...")
    try:
        subprocess.check_call(
            [str(pip_exe), "install", "-r", str(REQUIREMENTS_FILE)],
            cwd=PROJECT_ROOT
        )
    except subprocess.CalledProcessError:
        print_error("Failed to install dependencies.")
        sys.exit(1)


def install_playwright_browsers():
    """Install Playwright browsers."""
    python_exe = get_python_exe()
    print_step("Checking Playwright browsers...")
    try:
        subprocess.check_call(
            [str(python_exe), "-m", "playwright", "install", "chromium"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL, # Suppress noisy output unless error
            stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        print_error("Failed to install Playwright browsers.")
        # Don't exit, scraping might just fail later
    except Exception:
        pass # Playwright might not be installed yet or other issue


def run_server():
    """Run the Uvicorn server using the venv python."""
    python_exe = get_python_exe()
    if not python_exe.exists():
        print_error("Python interpreter not found in virtual environment!")
        sys.exit(1)

    print_step("Starting Resume Builder Server...")
    print(f"    URL: {URL}")
    print("    Press Ctrl+C to stop.")

    # Set LITE_MODE environment variable
    env = os.environ.copy()
    env["LITE_MODE"] = "true"
    env["LOCAL_LLM_ENABLED"] = "true"
    # Ensure PYTHONPATH includes the project root
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    try:
        # Start uvicorn as a subprocess
        process = subprocess.Popen(
            [
                str(python_exe), "-m", "uvicorn", 
                "main:app", 
                "--host", HOST, 
                "--port", str(PORT),
                "--timeout-keep-alive", "300", # 5 minutes to match frontend
                "--reload"  # Useful for local tweaks
            ],
            cwd=PROJECT_ROOT,
            env=env
        )
        return process
    except Exception as e:
        print_error(f"Failed to start server: {e}")
        sys.exit(1)


def wait_for_server(max_retries=30):
    """Wait for server to be responsive."""
    import urllib.request
    
    print_step("Waiting for server to start...")
    for _ in range(max_retries):
        try:
            with urllib.request.urlopen(f"{URL}/health/live") as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def main():
    print("=" * 60)
    print("   RESUME BUILDER - LAUNCHER")
    print("=" * 60)

    # 1. Setup environment
    ensure_venv()
    
    # 2. Install dependencies
    install_dependencies()
    install_playwright_browsers()

    # 3. Initialize Database
    print_step("Initializing Database...")
    python_exe = get_python_exe()
    env = os.environ.copy()
    env["LITE_MODE"] = "true"
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    
    try:
        subprocess.check_call(
            [str(python_exe), "backend/init_db.py"],
            cwd=PROJECT_ROOT,
            env=env
        )
    except subprocess.CalledProcessError:
        print_error("Failed to initialize database.")
        sys.exit(1)

    # 4. Start Server
    server_process = run_server()

    # 5. Wait for healthy
    if wait_for_server():
        print_step("Server is Ready!")
        # 6. Open Browser
        print_step("Opening browser...")
        webbrowser.open(URL)
    else:
        print_error("Server failed to start in time.")
        server_process.terminate()
        sys.exit(1)

    # 7. Monitor Loop
    try:
        while True:
            time.sleep(1)
            if server_process.poll() is not None:
                print_error("Server process exited unexpectedly.")
                break
    except KeyboardInterrupt:
        print_step("Stopping server...")
    finally:
        server_process.terminate()
        server_process.wait()
        print_step("Goodbye!")


if __name__ == "__main__":
    main()
