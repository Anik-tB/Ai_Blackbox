"""
Subprocess bootstrap wrapper for `aidbg run <cmd>`.
Automatically initializes the aidbg agent, registers hooks, and executes the user program.
"""

import os
import sys
import subprocess
import aidbg.agent.collector as collector

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m aidbg.agent.bootstrap <command> [args...]")
        sys.exit(1)

    # Initialize agent
    endpoint = os.environ.get("AIDBG_ENDPOINT", "http://127.0.0.1:8765/api/v1/incidents/ingest")
    collector.init(endpoint_url=endpoint, service_name=os.environ.get("AIDBG_SERVICE", "app"))

    # Execute the target command
    target_cmd = sys.argv[1:]
    try:
        proc = subprocess.run(target_cmd)
        sys.exit(proc.returncode)
    except Exception as e:
        collector.capture_exception()
        raise e

if __name__ == "__main__":
    main()
