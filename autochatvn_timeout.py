import subprocess
import threading
import calc
import sys
import os
import signal

def run_with_timeout(cmd, timeout_sec):
    """Run a command with a timeout on Linux."""

    def sigint_handler(signum, frame):
        print("Ctrl+C detected. Sending SIGINT to child process group...")
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGINT)
        except Exception:
            pass

    signal.signal(signal.SIGINT, sigint_handler)

    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            preexec_fn=os.setsid
        )

        proc.communicate(timeout=timeout_sec)

    except subprocess.TimeoutExpired:
        print("Forcefully killing the process group.")
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:
            proc.terminate()
        proc.communicate()
    except Exception as e:
        print(f"An error occurred: {e}")
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:
            proc.terminate()
        proc.communicate()
    exit()

# Example usage:
command = "python3 autochatvn.py"

if __name__ == "__main__" and len(sys.argv) >= 2:
    timeout_seconds = int(sys.argv[1])
else:
    timeout_seconds = calc.to_sec(5, 30, 0)

print("Run with limited time:", timeout_seconds)
run_with_timeout(command, timeout_seconds)
