# Making the API Accessible from Other Devices

The Drone Spots API is already configured to accept connections from other devices on your network. This guide explains how to access it from other devices.

## Quick Setup

### 1. Start the API Server

```bash
python drone_spots_api.py
```

The API binds to `0.0.0.0:8000` by default, which means it accepts connections from:
- Localhost (same machine): `http://localhost:8000`
- Other devices on your network: `http://<your-ip>:8000`

### 2. Find Your Network IP Address

#### Option A: Use the Helper Script (Recommended)

```bash
python get_network_ip.py
```

This will display your network IP address and the URLs you can use from other devices.

#### Option B: Manual Detection

**On Linux/macOS:**
```bash
# Method 1: Using ip command
ip addr show | grep "inet " | grep -v 127.0.0.1

# Method 2: Using ifconfig
ifconfig | grep "inet " | grep -v 127.0.0.1

# Method 3: Using hostname
hostname -I
```

**On Windows:**
```bash
ipconfig | findstr IPv4
```

Look for an IP address that starts with:
- `192.168.x.x` (most home networks)
- `10.x.x.x` (some home/office networks)
- `172.16.x.x` to `172.31.x.x` (some corporate networks)

### 3. Access from Other Devices

Once you have your IP address (e.g., `192.168.0.145`), you can access the API from any device on the same network:

- **API Root**: `http://192.168.0.145:8000`
- **API Docs**: `http://192.168.0.145:8000/docs`
- **Interactive Map**: `http://192.168.0.145:8000/map`

### 4. Configure Firewall (If Needed)

If other devices cannot connect, you may need to allow port 8000 through your firewall.

#### Linux (UFW)
```bash
sudo ufw allow 8000/tcp
sudo ufw reload
```

#### Linux (firewalld)
```bash
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

#### Windows Firewall
1. Open Windows Defender Firewall
2. Click "Advanced settings"
3. Click "Inbound Rules" → "New Rule"
4. Select "Port" → Next
5. Select "TCP" and enter port `8000`
6. Allow the connection
7. Apply to all profiles

#### macOS Firewall
1. System Preferences → Security & Privacy → Firewall
2. Click "Firewall Options"
3. Click "+" and add Python or Terminal
4. Allow incoming connections

## Testing Network Access

### From Another Device

**Using a web browser:**
```
http://<your-ip>:8000/docs
```

**Using curl (from another device):**
```bash
curl "http://<your-ip>:8000/search?address=Kuala%20Lumpur&radius_km=10"
```

**Using Python (from another device):**
```python
import requests
response = requests.get("http://<your-ip>:8000/spot-types")
print(response.json())
```

### From the Same Device

You can also test locally using the network IP:
```bash
curl "http://<your-ip>:8000/spot-types"
```

## Troubleshooting

### Cannot Connect from Other Devices

1. **Check if API is running:**
   ```bash
   # On the server machine
   curl http://localhost:8000/
   ```

2. **Check if API is bound to 0.0.0.0:**
   ```bash
   # Should show 0.0.0.0:8000
   netstat -tuln | grep 8000
   # Or on newer systems:
   ss -tuln | grep 8000
   ```

3. **Check firewall:**
   ```bash
   # Linux
   sudo ufw status
   # Or
   sudo firewall-cmd --list-all
   ```

4. **Verify devices are on same network:**
   - Both devices must be on the same Wi-Fi network or LAN
   - Check IP addresses are in the same subnet (e.g., both 192.168.1.x)

5. **Test with telnet (from another device):**
   ```bash
   telnet <your-ip> 8000
   # If connection succeeds, firewall is OK
   ```

### API Shows "Connection Refused"

- Make sure the API server is running
- Check if port 8000 is already in use: `lsof -i :8000` or `netstat -tuln | grep 8000`
- Try a different port by modifying `drone_spots_api.py` or using environment variables

### Router/Network Issues

- Some routers block inter-device communication - check router settings
- Corporate networks may have restrictions
- Mobile hotspots usually work fine

## Using the Exploration Script with Network IP

To test the API from another device or use the network IP in `explore_api.py`:

1. **Edit `explore_api.py`:**
   ```python
   USE_NETWORK_IP = True  # Change from False to True
   ```

2. **Or set the BASE_URL directly:**
   ```python
   BASE_URL = "http://192.168.0.145:8000"  # Your network IP
   ```

## Security Considerations

⚠️ **Important Security Notes:**

1. **Local Network Only**: The default configuration is for local network access only. For internet access, you need:
   - Port forwarding on your router
   - Proper security measures (authentication, HTTPS, etc.)

2. **Production Deployment**: For production use, consider:
   - Using a reverse proxy (nginx) with SSL/TLS
   - Implementing authentication
   - Rate limiting
   - Firewall rules to restrict access

3. **Development Use**: The current setup is suitable for:
   - Local development
   - Testing on the same network
   - Personal use

## Example: Access from Mobile Device

1. Start the API on your computer
2. Find your computer's IP: `python get_network_ip.py`
3. On your mobile device (same Wi-Fi), open browser
4. Navigate to: `http://<your-ip>:8000/docs`
5. You can now test the API from your mobile device!

## Example: Access from Another Computer

1. Start the API on Server (192.168.0.145)
2. On Client computer, open terminal
3. Test connection:
   ```bash
   curl http://192.168.0.145:8000/spot-types
   ```
4. Use in your application:
   ```python
   import requests
   api_url = "http://192.168.0.145:8000"
   response = requests.get(f"{api_url}/search", params={
       "address": "Kuala Lumpur",
       "radius_km": 10
   })
   ```

