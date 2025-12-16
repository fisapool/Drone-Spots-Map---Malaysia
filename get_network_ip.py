#!/usr/bin/env python3
"""
Utility script to get the local network IP address for accessing the API from other devices.
"""

import socket
import sys

def get_local_ip():
    """Get the local network IP address"""
    try:
        # Connect to a remote address (doesn't actually send data)
        # This gets the IP of the interface used to reach that address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Using Google's DNS as a target (doesn't actually connect)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        # Fallback: try to get hostname IP
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            if ip.startswith("127."):
                # If it's localhost, try alternative method
                return None
            return ip
        except:
            return None

def get_all_ips():
    """Get all network interface IP addresses"""
    import subprocess
    ips = []
    
    try:
        # Try using ip command (Linux)
        result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'inet ' in line and '127.0.0.1' not in line:
                    ip = line.strip().split()[1].split('/')[0]
                    if not ip.startswith('127.'):
                        ips.append(ip)
    except:
        pass
    
    try:
        # Try using ifconfig (Linux/macOS)
        result = subprocess.run(['ifconfig'], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'inet ' in line and '127.0.0.1' not in line:
                    parts = line.strip().split()
                    for i, part in enumerate(parts):
                        if part == 'inet' and i + 1 < len(parts):
                            ip = parts[i + 1]
                            if not ip.startswith('127.'):
                                ips.append(ip)
                            break
    except:
        pass
    
    return list(set(ips))  # Remove duplicates

if __name__ == "__main__":
    print("=" * 60)
    print("  Network IP Address Detection")
    print("=" * 60)
    print()
    
    # Get primary IP
    primary_ip = get_local_ip()
    if primary_ip:
        print(f"✅ Primary Network IP: {primary_ip}")
        print(f"   API URL: http://{primary_ip}:8000")
        print(f"   API Docs: http://{primary_ip}:8000/docs")
        print()
    
    # Get all IPs
    all_ips = get_all_ips()
    if all_ips:
        print("📡 All Network Interfaces:")
        for ip in all_ips:
            print(f"   - {ip}")
            print(f"     API URL: http://{ip}:8000")
        print()
    
    if not primary_ip and not all_ips:
        print("⚠️  Could not detect network IP address.")
        print("   Please check your network configuration manually.")
        print()
        print("   On Linux/macOS: run 'ip addr' or 'ifconfig'")
        print("   On Windows: run 'ipconfig'")
        sys.exit(1)
    
    print("=" * 60)
    print("💡 To access from other devices on the same network:")
    print(f"   1. Make sure the API is running: python drone_spots_api.py")
    print(f"   2. Use the IP address above (e.g., http://{primary_ip or all_ips[0]}:8000)")
    print(f"   3. Ensure your firewall allows connections on port 8000")
    print("=" * 60)

