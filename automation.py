#!/usr/bin/env python3
import subprocess
import logging
import argparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DockerManager:
    @staticmethod
    def build():
        logger.info("Building Docker image...")
        subprocess.run(["docker", "build", "-t", "nechecker:latest", "."])
        logger.info("✅ Built")
    
    @staticmethod
    def start():
        logger.info("Starting containers...")
        subprocess.run(["docker-compose", "up", "-d"])
        logger.info("✅ Started")
    
    @staticmethod
    def stop():
        logger.info("Stopping containers...")
        subprocess.run(["docker-compose", "down"])
        logger.info("✅ Stopped")
    
    @staticmethod
    def health():
        try:
            import requests
            r = requests.get("http://localhost:8001/", timeout=5)
            print(f"✅ App healthy: {r.status_code}")
        except:
            print("❌ App unhealthy")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('cmd', choices=['build', 'start', 'stop', 'health'])
    args = parser.parse_args()
    
    if args.cmd == 'build': DockerManager.build()
    elif args.cmd == 'start': DockerManager.start()
    elif args.cmd == 'stop': DockerManager.stop()
    elif args.cmd == 'health': DockerManager.health()
