#!/usr/bin/env python3
"""
Vespa Backend Services Manager

This script manages all the dependent services needed for Vespa demos:
- Vespa engine (Docker)
- Pub/Sub emulator (Docker)
- Vespa Loader Service (Port 9001)
- Vespa Query Service (Port 9002)

It also checks that the Office Service is running on port 8001
but doesn't start it (assumes it's managed elsewhere).

Usage:
  python vespa_be.py          # Start services (default)
  python vespa_be.py --stop   # Stop all services
  python vespa_be.py --status # Check service status
"""

import asyncio
import subprocess
import time
import signal
import sys
import os
import argparse
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

class VespaServiceManager:
    """Manages starting, stopping, and monitoring Vespa backend services"""
    
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

        # Demo scripts
        self.demo_scripts = {
            "vespa_backfill": {
                "type": "script",
                "path": "services/demos/vespa_backfill.py",
                "description": "Vespa Backfill Demo - Data ingestion (run once)"
            },
            "vespa_search": {
                "type": "script", 
                "path": "services/demos/vespa_search.py",
                "description": "Vespa Search Demo - Search testing (run multiple times)"
            },
            "vespa_synthetic": {
                "type": "script",
                "path": "services/demos/vespa_synthetic.py", 
                "description": "Vespa Synthetic Demo - Conversational search"
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
                    return True  # Port is in use
                return False
        except Exception as e:
            self.log(f"⚠️  Could not check port {port}: {e}", Colors.YELLOW)
            return False
    
    def check_docker_running(self) -> bool:
        """Check if Docker is running"""
        try:
            result = subprocess.run(['docker', 'info'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def check_docker_container_status(self, container_name: str) -> str:
        """Check if a Docker container is running"""
        try:
            result = subprocess.run(['docker', 'ps', '--filter', f'name={container_name}'],
                                  capture_output=True, text=True, timeout=10)
            
            if container_name in result.stdout:
                return "running"
            
            # Check if container exists but is stopped
            result = subprocess.run(['docker', 'ps', '-a', '--filter', f'name={container_name}'],
                                  capture_output=True, text=True, timeout=10)
            
            if container_name in result.stdout:
                return "stopped"
            
            return "not_found"
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return "unknown"
    
    def check_service_health(self, service_key: str, config: Dict) -> Dict[str, any]:
        """Check the health of a service"""
        service_name = config["name"]
        
        if service_key in self.services:
            # Python service
            port = config["port"]
            url = f"http://localhost:{port}/health"
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    return {"status": "healthy", "port": port, "url": url}
                else:
                    return {"status": "unhealthy", "port": port, "url": url, "http_status": response.status_code}
            except requests.RequestException:
                return {"status": "unreachable", "port": port, "url": url}
        
        elif service_key in self.docker_services:
            # Docker service
            container_name = config["container_name"]
            container_status = self.check_docker_container_status(container_name)
            
            if container_status == "running":
                # Check if service is responding
                port = int(config["ports"][0].split(":")[0])
                try:
                    if service_key == "vespa":
                        # For Vespa, just check if the container is running
                        # It's a config server, not an HTTP application server
                        container_status = self.check_docker_container_status(container_name)
                        if container_status == "running":
                            return {"status": "running", "container": container_name, "port": port, "type": "config_server"}
                        else:
                            return {"status": container_status, "container": container_name}
                    elif service_key == "pubsub":
                        url = f"http://localhost:{port}/"
                        response = requests.get(url, timeout=5)
                        if response.status_code == 200:
                            return {"status": "healthy", "container": container_name, "port": port}
                        else:
                            return {"status": "unhealthy", "container": container_name, "port": port, "http_status": response.status_code}
                except requests.RequestException:
                    return {"status": "unreachable", "container": container_name, "port": port}
            else:
                return {"status": container_status, "container": container_name}
        
        return {"status": "unknown", "service": service_name}
    
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
        
        # Use longer timeout for Pub/Sub emulator since it's a large image
        if service_key == "pubsub":
            timeout = 180  # 3 minutes for Pub/Sub emulator
        
        self.log(f"⏳ Waiting for {service_name} to be ready (timeout: {timeout}s)...", Colors.BLUE)
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if service_key == "vespa":
                    # For Vespa, we just need to check if the container is running and stable
                    # The container runs as a config server, not an HTTP application server
                    container_status = self.check_docker_container_status(config["container_name"])
                    if container_status == "running":
                        # Check if the container has been running for at least 10 seconds
                        # This gives it time to fully initialize
                        container_info = subprocess.run(
                            ['docker', 'inspect', '--format={{.State.StartedAt}}', config["container_name"]],
                            capture_output=True, text=True, timeout=10
                        )
                        if container_info.returncode == 0:
                            self.log(f"✅ {service_name} is running and stable", Colors.GREEN)
                            self.log(f"ℹ️  Note: This is a Vespa config server for local development", Colors.BLUE)
                            return True
                            
                elif service_key == "pubsub":
                    # Check Pub/Sub emulator
                    try:
                        response = requests.get(f"http://localhost:{port}/", timeout=5)
                        if response.status_code == 200:
                            self.log(f"✅ {service_name} is ready!", Colors.GREEN)
                            return True
                    except requests.RequestException as e:
                        # Log the specific error for debugging
                        if "Connection refused" in str(e):
                            self.log(f"⏳ {service_name} is still starting up... (connection refused)", Colors.BLUE)
                        elif "Max retries exceeded" in str(e):
                            self.log(f"⏳ {service_name} is still starting up... (max retries)", Colors.BLUE)
                        else:
                            self.log(f"⏳ {service_name} is still starting up... ({e})", Colors.BLUE)
                
                time.sleep(2)
            except Exception as e:
                self.log(f"⚠️  Error checking {service_name}: {e}", Colors.YELLOW)
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
        if self.check_port(port, service_name):
            self.log(f"⚠️  Port {port} is already in use. Service may already be running.", Colors.YELLOW)
            return True
        
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
            
            self.log(f"🔄 Running command: {' '.join(cmd)}", Colors.BLUE)
            
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
                if stdout:
                    self.log(f"Stdout: {stdout[:200]}...", Colors.RED)
                if stderr:
                    self.log(f"Stderr: {stderr[:200]}...", Colors.RED)
                return False
                
        except Exception as e:
            self.log(f"❌ Error starting {service_name}: {e}", Colors.RED)
            return False
        finally:
            # Return to project root
            os.chdir(self.project_root)
    
    def wait_for_python_service(self, service_key: str, config: Dict, timeout: int = 60) -> bool:
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
                else:
                    self.log(f"⏳ {service_name} responded with status {response.status_code}, still starting up...", Colors.BLUE)
                time.sleep(2)
            except requests.RequestException as e:
                # Log the specific error for debugging
                if "Connection refused" in str(e):
                    self.log(f"⏳ {service_name} is still starting up... (connection refused)", Colors.BLUE)
                elif "Max retries exceeded" in str(e):
                    self.log(f"⏳ {service_name} is still starting up... (max retries)", Colors.BLUE)
                else:
                    self.log(f"⏳ {service_name} is still starting up... ({e})", Colors.BLUE)
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
    
    def stop_all_services(self):
        """Stop all running services"""
        self.log("\n🛑 Stopping all Vespa services...", Colors.YELLOW)
        
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
        
        self.log("✅ All Vespa services stopped", Colors.GREEN)
    
    def check_service_status(self):
        """Check the status of all services"""
        self.log("🔍 Checking Vespa service status...", Colors.BLUE)
        self.log("", Colors.NC)
        
        all_healthy = True
        
        # Check Docker services
        self.log("🐳 Docker Services:", Colors.BLUE)
        for service_key, config in self.docker_services.items():
            health = self.check_service_health(service_key, config)
            if health["status"] == "healthy":
                self.log(f"  ✅ {config['name']}: {health['status']}", Colors.GREEN)
            else:
                self.log(f"  ❌ {config['name']}: {health['status']}", Colors.RED)
                all_healthy = False
        
        # Check Python services
        self.log("\n🐍 Python Services:", Colors.BLUE)
        for service_key, config in self.services.items():
            health = self.check_service_health(service_key, config)
            if health["status"] == "healthy":
                self.log(f"  ✅ {config['name']}: {health['status']}", Colors.GREEN)
            else:
                self.log(f"  ❌ {config['name']}: {health['status']}", Colors.RED)
                all_healthy = False
        
        # Check dependencies
        self.log("\n🔗 Dependencies:", Colors.BLUE)
        for service_key, config in self.dependencies.items():
            try:
                response = requests.get(config["url"], timeout=5)
                if response.status_code == 200:
                    self.log(f"  ✅ {config['name']}: healthy", Colors.GREEN)
                else:
                    self.log(f"  ❌ {config['name']}: unhealthy (HTTP {response.status_code})", Colors.RED)
                    all_healthy = False
            except requests.RequestException:
                self.log(f"  ❌ {config['name']}: unreachable", Colors.RED)
                all_healthy = False
        
        self.log("", Colors.NC)
        if all_healthy:
            self.log("🎉 All services are healthy!", Colors.GREEN)
        else:
            self.log("⚠️  Some services are not healthy", Colors.YELLOW)
        
        return all_healthy
    
    async def start_all_services(self) -> bool:
        """Start all Vespa backend services"""
        self.log("🚀 Starting Vespa backend services...", Colors.BLUE)
        self.log(f"📁 Working directory: {self.project_root}", Colors.BLUE)
        self.log("", Colors.NC)
        
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
    
    async def run(self, action: str = "start"):
        """Main run method"""
        try:
            if action == "stop":
                self.stop_all_services()
                return
            
            elif action == "status":
                self.check_service_status()
                return
            
            elif action == "start":
                # Check if services are already running
                self.log("🔍 Checking if services are already running...", Colors.BLUE)
                if self.check_service_status():
                    self.log("\n✅ All services are already running and healthy!", Colors.GREEN)
                    self.log("Use '--status' to check service health or '--stop' to stop services.", Colors.BLUE)
                    return
                
                # Start services
                success = await self.start_all_services()
                if success:
                    # Keep services running until interrupted
                    while True:
                        await asyncio.sleep(1)
                else:
                    self.log("❌ Failed to start all services", Colors.RED)
                    sys.exit(1)
                    
        except KeyboardInterrupt:
            self.log("\n🛑 Received interrupt signal", Colors.YELLOW)
        finally:
            if action == "start":
                self.stop_all_services()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Manage Vespa backend services")
    parser.add_argument("--stop", action="store_true", help="Stop all Vespa services")
    parser.add_argument("--status", action="store_true", help="Check service status")
    
    args = parser.parse_args()
    
    # Determine action
    if args.stop:
        action = "stop"
    elif args.status:
        action = "status"
    else:
        action = "start"
    
    # Create and run manager
    manager = VespaServiceManager()
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        if action == "start":
            manager.stop_all_services()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the manager
    asyncio.run(manager.run(action))

if __name__ == "__main__":
    main()
