import subprocess
import time
import sys
import os
import signal
import datetime

# Configuration
SCRIPTS = [
    {
        "name": "RAG Trader",
        "path": "scripts/run_rag_paper_trading.py",
        "restart_delay": 5,
        "critical": True
    },
    {
        "name": "Live Dashboard",
        "path": "src/interface/live_dashboard_nicegui.py",
        "restart_delay": 5,
        "critical": False
    }
]

processes = {}
should_run = True

def log(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [SUPERVISOR] {message}")

def start_process(script_config):
    name = script_config["name"]
    path = script_config["path"]
    
    log(f"Starting {name} ({path})...")
    
    # Use the same python interpreter as the supervisor
    python_exe = sys.executable
    
    try:
        # Start as a subprocess
        # Creation flags for new console window on Windows (optional, but good for debugging)
        creationflags = subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        
        p = subprocess.Popen(
            [python_exe, path],
            creationflags=creationflags,
            cwd=os.getcwd()
        )
        processes[name] = {
            "process": p,
            "config": script_config,
            "start_time": time.time()
        }
        log(f"✅ {name} started with PID {p.pid}")
    except Exception as e:
        log(f"❌ Failed to start {name}: {e}")

def stop_all():
    global should_run
    should_run = False
    log("Stopping all services...")
    for name, info in processes.items():
        p = info["process"]
        if p.poll() is None:  # If running
            log(f"Terminating {name} (PID {p.pid})...")
            p.terminate()
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                log(f"Force killing {name}...")
                p.kill()
    log("All services stopped.")

def signal_handler(sig, frame):
    log("Received shutdown signal.")
    stop_all()
    sys.exit(0)

def monitor_loop():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Initial start
    for script in SCRIPTS:
        start_process(script)

    log("🚀 Supervisor running. Press Ctrl+C to stop system.")

    while should_run:
        for name, info in list(processes.items()):
            p = info["process"]
            config = info["config"]
            
            # Check if process has exited
            return_code = p.poll()
            
            if return_code is not None:
                log(f"⚠️ {name} exited with code {return_code}")
                
                # Restart logic
                delay = config["restart_delay"]
                log(f"Restarting {name} in {delay} seconds...")
                time.sleep(delay)
                start_process(config)
        
        time.sleep(2)

if __name__ == "__main__":
    # Ensure we are in the project root
    if not os.path.exists("scripts") or not os.path.exists("src"):
        log("❌ Error: Please run this script from the project root directory (e.g., python scripts/supervisor.py)")
        sys.exit(1)
        
    monitor_loop()
