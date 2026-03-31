import argparse
import subprocess
import time
import socket
import sys

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def run_with_server(server_cmd, port, test_cmd):
    print(f"🚀 Starting server: {server_cmd}")
    server_process = subprocess.Popen(server_cmd, shell=True)
    
    print(f"⏳ Waiting for port {port} to open...")
    start_time = time.time()
    while not is_port_open(port):
        if time.time() - start_time > 60:
            print("❌ Timeout waiting for server to start.")
            server_process.terminate()
            sys.exit(1)
        time.sleep(1)
    
    print(f"✅ Server is ready on port {port}. Running tests: {' '.join(test_cmd)}")
    try:
        test_result = subprocess.run(test_cmd)
        return test_result.returncode
    finally:
        print("🛑 Cleaning up server...")
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run tests with a local development server.")
    parser.add_argument("--server", required=True, help="Command to start the server (e.g., 'npm run dev')")
    parser.add_argument("--port", type=int, required=True, help="Port the server is expected to run on")
    parser.add_argument("test_cmd", nargs="+", help="Test command to execute")
    
    args = parser.parse_args()
    sys.exit(run_with_server(args.server, args.port, args.test_cmd))
