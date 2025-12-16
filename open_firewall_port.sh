#!/bin/bash
# Script to open firewall port 8001 for the Drone Spots API

echo "=========================================="
echo "Opening Firewall Port 8001"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  This script needs sudo privileges to modify firewall rules."
    echo "   Please run: sudo bash open_firewall_port.sh"
    exit 1
fi

# Check if UFW is available
if command -v ufw &> /dev/null; then
    echo "📋 Checking UFW status..."
    ufw status
    
    echo ""
    echo "🔓 Opening port 8001 for API access..."
    ufw allow 8001/tcp comment "Drone Spots API"
    
    echo ""
    echo "🔄 Reloading firewall..."
    ufw reload
    
    echo ""
    echo "✅ Firewall updated!"
    echo ""
    ufw status | grep 8001
    
    echo ""
    echo "=========================================="
    echo "Port 8001 is now open!"
    echo "API should be accessible from other PCs at:"
    echo "  http://192.168.0.145:8001"
    echo "  http://192.168.0.145:8001/docs"
    echo "=========================================="
else
    echo "⚠️  UFW not found. Trying iptables..."
    
    # Check if iptables rule already exists
    if iptables -C INPUT -p tcp --dport 8001 -j ACCEPT 2>/dev/null; then
        echo "✅ Port 8001 is already allowed in iptables"
    else
        echo "🔓 Adding iptables rule for port 8001..."
        iptables -A INPUT -p tcp --dport 8001 -j ACCEPT
        echo "💾 Saving iptables rules..."
        
        # Try to save rules (method depends on distribution)
        if command -v netfilter-persistent &> /dev/null; then
            netfilter-persistent save
        elif command -v iptables-save &> /dev/null; then
            iptables-save > /etc/iptables/rules.v4 2>/dev/null || \
            iptables-save > /etc/iptables.rules 2>/dev/null || \
            echo "⚠️  Could not save iptables rules automatically. Run 'iptables-save > /etc/iptables/rules.v4' manually."
        fi
        
        echo "✅ Port 8001 is now open in iptables!"
    fi
    
    echo ""
    echo "=========================================="
    echo "Port 8001 is now open!"
    echo "API should be accessible from other PCs at:"
    echo "  http://192.168.0.145:8001"
    echo "  http://192.168.0.145:8001/docs"
    echo "=========================================="
fi

