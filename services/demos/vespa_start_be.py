#!/usr/bin/env python3
"""
Vespa Backend Services Starter

This script starts all the dependent services needed for Vespa demos:
- Vespa engine (Docker)
- Pub/Sub emulator (Docker)
- Vespa Loader Service (Port 9001)
- Vespa Query Service (Port 9002)

It also checks that the Office Service is running on port 8001
but doesn't start it (assumes it's managed elsewhere).
"""

import asyncio
import subprocess
import time
import signal
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional
import requests
import json

# Colors for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

class VespaServiceStarter:
    """Manages starting and monitoring Vespa backend services"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.processes: Dict[str, subprocess.Popen] = {}
        self.pid_files: Dict[str, str] = {}
        
        # Service configurations
        self.services = {
            "vespa_loader": {
                "name": "Vespa Loader Service",
                "port": 9001,
                "module": "services.vespa_loader.main:app",
                "directory": "services/vespa_loader"
            },
            "vespa_query": {
                "name": "Vespa Query Service", 
                "port": 9002,
                "module": "services.vespa_query.main:app",
                "directory": "services/vespa_query"
            }
        }
        
        # Docker services
        self.docker_services = {
            "vespa": {
                "name": "Vespa Engine",
                "image": "vespaengine/vespa",
                "ports": ["8080:8080", "19092:19092"],
                "container_name": "vespa",
                "hostname": "vespa-container"
            },
            "pubsub": {
                "name": "Pub/Sub Emulator",
                "image": "gcr.io/google.com/cloudsdktool/google-cloud-cli:latest",
                "ports": ["8085:8085"],
                "container_name": "pubsub-emulator",
                "command": ["gcloud", "beta", "emulators", "pubsub", "start", "--host-port=0.0.0.0:8085"]
            }
        }
        
        # Dependencies to check (but not start)
        self.dependencies = {
            "office": {
                "name": "Office Service",
                "port": 8001,
                "url": "http://localhost:8001/health"
            }
        }
    
    def log(self, message: str, color: str = Colors.NC):
        """Print colored log message"""
        print(f"{color}{message}{Colors.NC}")
    
    def check_port(self, port: int, service_name: str) -> bool:
        """Check if a port is available"""
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', port))
                if result == 0:
                    self.log(f"❌ Port {port} is already in use by {service_name}", Colors.RED)
                    return False
                return True
        except Exception as e:
            self.log(f"⚠️  Could not check port {port}: {e}", Colors.YELLOW)
            return True
    
    def check_docker_running(self) -> bool:
        """Check if Docker is running"""
        try:
            result = subprocess.run(['docker', 'info'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def start_docker_service(self, service_key: str, config: Dict) -> bool:
        """Start a Docker service"""
        service_name = config["name"]
        container_name = config["container_name"]
        
        # Check if container already exists
        try:
            result = subprocess.run(['docker', 'ps', '-a', '--filter', f'name={container_name}'],
                                  capture_output=True, text=True, timeout=10)
            
            if container_name in result.stdout:
                # Container exists, check if running
                result = subprocess.run(['docker', 'ps', '--filter', f'name={container_name}'],
                                      capture_output=True, text=True, timeout=10)
                
                if container_name in result.stdout:
                    self.log(f"✅ {service_name} is already running", Colors.GREEN)
                    return True
                else:
                    # Start existing container
                    self.log(f"🔄 Starting existing {service_name} container...", Colors.BLUE)
                    subprocess.run(['docker', 'start', container_name], check=True)
                    return True
            else:
                # Create and start new container
                self.log(f"🔄 Creating and starting {service_name}...", Colors.BLUE)
                
                cmd = ['docker', 'run', '-d', '--name', container_name]
                
                if 'hostname' in config:
                    cmd.extend(['--hostname', config['hostname']])
                
                for port_mapping in config['ports']:
                    cmd.extend(['-p', port_mapping])
                
                cmd.append(config['image'])
                
                if 'command' in config:
                    cmd.extend(config['command'])
                
                subprocess.run(cmd, check=True)
                return True
                
        except subprocess.CalledProcessError as e:
            self.log(f"❌ Failed to start {service_name}: {e}", Colors.RED)
            return False
        except Exception as e:
            self.log(f"❌ Error starting {service_name}: {e}", Colors.RED)
            return False
    
    def wait_for_docker_service(self, service_key: str, config: Dict, timeout: int = 60) -> bool:
        """Wait for a Docker service to be ready"""
        service_name = config["name"]
        port = int(config["ports"][0].split(":")[0])
        
        self.log(f"⏳ Waiting for {service_name} to be ready (timeout: {timeout}s)...", Colors.BLUE)
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if service_key == "vespa":
                    # Check Vespa status endpoint
                    response = requests.get(f"http://localhost:{port}/application/v2/status", timeout=5)
                    if response.status_code == 200:
                        self.log(f"✅ {service_name} is ready!", Colors.GREEN)
                        return True
                elif service_key == "pubsub":
                    # Check Pub/Sub emulator
                    response = requests.get(f"http://localhost:{port}/", timeout=5)
                    if response.status_code == 200:
                        self.log(f"✅ {service_name} is ready!", Colors.GREEN)
                        return True
                
                time.sleep(2)
            except requests.RequestException:
                time.sleep(2)
                continue
        
        self.log(f"❌ {service_name} failed to start within {timeout} seconds", Colors.RED)
        return False
    
    def start_python_service(self, service_key: str, config: Dict) -> bool:
        """Start a Python service using uvicorn"""
        service_name = config["name"]
        port = config["port"]
        module = config["module"]
        directory = config["directory"]
        
        # Check if port is available
        if not self.check_port(port, service_name):
            return False
        
        self.log(f"🔄 Starting {service_name} on port {port}...", Colors.BLUE)
        
        try:
            # Change to service directory
            service_dir = self.project_root / directory
            os.chdir(service_dir)
            
            # Start service with uvicorn
            cmd = [
                sys.executable, "-m", "uvicorn", module,
                "--host", "0.0.0.0",
                "--port", str(port),
                "--reload"
            ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Store process for cleanup
            self.processes[service_key] = process
            self.pid_files[service_key] = str(process.pid)
            
            # Wait a moment for startup
            time.sleep(3)
            
            # Check if process is still running
            if process.poll() is None:
                self.log(f"✅ {service_name} started with PID {process.pid}", Colors.GREEN)
                return True
            else:
                stdout, stderr = process.communicate()
                self.log(f"❌ {service_name} failed to start", Colors.RED)
                if stderr:
                    self.log(f"Error: {stderr}", Colors.RED)
                return False
                
        except Exception as e:
            self.log(f"❌ Error starting {service_name}: {e}", Colors.RED)
            return False
        finally:
            # Return to project root
            os.chdir(self.project_root)
    
    def wait_for_python_service(self, service_key: str, config: Dict, timeout: int = 30) -> bool:
        """Wait for a Python service to be ready"""
        service_name = config["name"]
        port = config["port"]
        
        self.log(f"⏳ Waiting for {service_name} to be ready (timeout: {timeout}s)...", Colors.BLUE)
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"http://localhost:{port}/health", timeout=5)
                if response.status_code == 200:
                    self.log(f"✅ {service_name} is ready!", Colors.GREEN)
                    return True
                time.sleep(2)
            except requests.RequestException:
                time.sleep(2)
                continue
        
        self.log(f"❌ {service_name} failed to start within {timeout} seconds", Colors.RED)
        return False
    
    def check_dependency(self, service_key: str, config: Dict) -> bool:
        """Check if a dependency service is running"""
        service_name = config["name"]
        port = config["port"]
        url = config["url"]
        
        self.log(f"🔍 Checking {service_name} on port {port}...", Colors.BLUE)
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                self.log(f"✅ {service_name} is running and healthy", Colors.GREEN)
                return True
            else:
                self.log(f"⚠️  {service_name} responded with status {response.status_code}", Colors.YELLOW)
                return False
        except requests.RequestException as e:
            self.log(f"❌ {service_name} is not accessible: {e}", Colors.RED)
            self.log(f"   Please start {service_name} manually:", Colors.YELLOW)
            self.log(f"   cd services/office && python -m uvicorn app.main:app --reload --port {port}", Colors.YELLOW)
            return False
    
    def cleanup(self):
        """Cleanup all started processes"""
        self.log("\n🛑 Stopping all services...", Colors.YELLOW)
        
        # Stop Python services
        for service_key, process in self.processes.items():
            if process.poll() is None:
                self.log(f"🛑 Stopping {service_key}...", Colors.YELLOW)
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        
        # Stop Docker containers
        for service_key, config in self.docker_services.items():
            container_name = config["container_name"]
            try:
                subprocess.run(['docker', 'stop', container_name], 
                             capture_output=True, timeout=10)
                self.log(f"🛑 Stopped {container_name}", Colors.YELLOW)
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                pass
        
        self.log("✅ All services stopped", Colors.GREEN)
    
    async def start_all_services(self) -> bool:
        """Start all Vespa backend services"""
        self.log("🚀 Starting Vespa backend services...", Colors.BLUE)
        self.log(f"📁 Working directory: {self.project_root}", Colors.BLUE)
        self.log("")
        
        # Check Docker
        if not self.check_docker_running():
            self.log("❌ Docker is not running. Please start Docker and try again.", Colors.RED)
            return False
        
        # Check dependencies first
        self.log("🔍 Checking dependencies...", Colors.BLUE)
        for service_key, config in self.dependencies.items():
            if not self.check_dependency(service_key, config):
                self.log(f"❌ Dependency {config['name']} is not available", Colors.RED)
                return False
        
        # Start Docker services
        self.log("\n🐳 Starting Docker services...", Colors.BLUE)
        for service_key, config in self.docker_services.items():
            if not self.start_docker_service(service_key, config):
                return False
            
            if not self.wait_for_docker_service(service_key, config):
                return False
        
        # Start Python services
        self.log("\n🐍 Starting Python services...", Colors.BLUE)
        for service_key, config in self.services.items():
            if not self.start_python_service(service_key, config):
                return False
            
            if not self.wait_for_python_service(service_key, config):
                return False
        
        self.log("\n🎉 All Vespa backend services are running!", Colors.GREEN)
        self.log("", Colors.NC)
        self.log("Services Status:", Colors.BLUE)
        self.log("  ✅ Vespa Engine: http://localhost:8080", Colors.GREEN)
        self.log("  ✅ Pub/Sub Emulator: http://localhost:8085", Colors.GREEN)
        self.log("  ✅ Vespa Loader Service: http://localhost:9001", Colors.GREEN)
        self.log("  ✅ Vespa Query Service: http://localhost:9002", Colors.GREEN)
        self.log("  ✅ Office Service: http://localhost:8001 (dependency)", Colors.GREEN)
        self.log("", Colors.NC)
        self.log("Next steps:", Colors.BLUE)
        self.log("  1. Seed demo data: python scripts/seed-demo-data.py --user-id demo_user_1", Colors.NC)
        self.log("  2. Run full demo: python services/demos/vespa_full.py", Colors.NC)
        self.log("  3. Test chat: python services/demos/vespa_chat.py", Colors.NC)
        self.log("", Colors.NC)
        self.log("Press Ctrl+C to stop all services", Colors.YELLOW)
        
        return True
    
    async def run(self):
        """Main run method"""
        try:
            success = await self.start_all_services()
            if success:
                # Keep services running until interrupted
                while True:
                    await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.log("\n🛑 Received interrupt signal", Colors.YELLOW)
        finally:
            self.cleanup()

def main():
    """Main entry point"""
    starter = VespaServiceStarter()
    
    # Set up signal handlers
    def signal_handler(signum, frame):
        starter.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the starter
    asyncio.run(starter.run())

if __name__ == "__main__":
    main()
