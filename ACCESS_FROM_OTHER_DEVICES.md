# Access Enhanced Map from Other Devices

## Quick Access

Your network IP: **192.168.0.145**

### Option 1: Python HTTP Server (Port 8888)
```
http://192.168.0.145:8888/map_spots_enhanced.html
```

### Option 2: If your API is running (Port 8001)
If your drone spots API is running, you can access the map through it:
```
http://192.168.0.145:8001/map
```

### Option 3: Configure Apache/Nginx to serve the file

If you want to use Apache (port 8080) or Nginx, you can:

**For Apache:**
1. Copy the file to Apache's document root:
   ```bash
   sudo cp map_spots_enhanced.html /var/www/html/
   ```
2. Access via:
   ```
   http://192.168.0.145:8080/map_spots_enhanced.html
   ```

**For Nginx:**
1. Copy the file to Nginx's document root:
   ```bash
   sudo cp map_spots_enhanced.html /var/www/html/
   ```
2. Access via:
   ```
   http://192.168.0.145/map_spots_enhanced.html
   ```

## Start Python Server Manually

If the server isn't running, start it with:

```bash
cd /home/arif/drones
python3 -m http.server 8888 --bind 0.0.0.0
```

Then access from other devices:
```
http://192.168.0.145:8888/map_spots_enhanced.html
```

## Firewall Configuration

If you can't access from other devices, allow the port:

```bash
# Ubuntu/Debian
sudo ufw allow 8888/tcp

# Or for port 8001 (if using API)
sudo ufw allow 8001/tcp
```

## Troubleshooting

1. **Check if server is running:**
   ```bash
   ps aux | grep "http.server"
   ```

2. **Check if port is accessible:**
   ```bash
   curl http://localhost:8888/map_spots_enhanced.html
   ```

3. **Check firewall:**
   ```bash
   sudo ufw status
   ```

4. **Verify network connectivity:**
   From another device, ping your server:
   ```bash
   ping 192.168.0.145
   ```

