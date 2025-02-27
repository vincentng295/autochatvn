import subprocess
import os
import json

def run_with_timeout(cmd, timeout_sec):
    """Run a command with a timeout on Windows."""
    try:
        # Start the process
        proc = subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        
        # Wait for the process to complete or timeout
        proc.communicate(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        # Timeout occurred. Notify and write to exitnow.txt
        print(f"Process timed out after {timeout_sec} seconds. Terminating...")
        proc.terminate()  # Sends SIGTERM to the process
        proc.communicate()  # Ensure the process exits cleanly
    except Exception as e:
        print(f"An error occurred: {e}")
        proc.terminate()
        proc.communicate()

# Example usage:
command = "python autochatvn.py"
timeout_seconds = 18000  # Adjust timeout as needed

event_path = os.getenv('GITHUB_EVENT_PATH', "")
if event_path != "":
    # Read the event data from the file
    try:
        with open(event_path, 'r') as f:
            event_data = json.load(f)
            # Extract the inputs from the event payload
            # Example for workflow_dispatch input
            inputs_data = event_data.get('inputs', {})
            timeout_seconds = int(inputs_data.get("timelimit", "18000"))
    except Exception:
        pass

run_with_timeout(command, timeout_seconds)
