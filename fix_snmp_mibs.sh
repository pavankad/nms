#!/bin/bash
# Fix SNMP MIB Loading Issues
# This script resolves common MIB loading problems

echo "=== Fixing SNMP MIB Loading Issues ==="

# Check if running as root for system-wide fixes
if [ "$EUID" -eq 0 ]; then
    SYSTEM_WIDE=true
    echo "Running as root - applying system-wide fixes"
else
    SYSTEM_WIDE=false
    echo "Running as user - applying user-specific fixes"
fi

# Create SNMP client configuration directory
mkdir -p ~/.snmp

# Configure MIB loading for current user
echo "Configuring MIB loading for current user..."
echo "mibs +ALL" > ~/.snmp/snmp.conf
echo "defCommunity public" >> ~/.snmp/snmp.conf

if [ "$SYSTEM_WIDE" = true ]; then
    # System-wide MIB configuration
    echo "Configuring system-wide MIB loading..."
    
    # Create system SNMP client config if it doesn't exist
    if [ ! -f /etc/snmp/snmp.conf ]; then
        touch /etc/snmp/snmp.conf
    fi
    
    # Add MIB loading directive if not present
    if ! grep -q "mibs +" /etc/snmp/snmp.conf; then
        echo "mibs +ALL" >> /etc/snmp/snmp.conf
    fi
    
    # Ensure MIBs directory exists and has correct permissions
    mkdir -p /usr/share/snmp/mibs
    chmod 755 /usr/share/snmp/mibs
    
    # Download MIBs if not already present
    if [ ! -d "/usr/share/snmp/mibs/ietf" ]; then
        echo "Downloading additional MIBs..."
        download-mibs || echo "Warning: Could not download additional MIBs"
    fi
fi

# Test SNMP functionality
echo ""
echo "Testing SNMP functionality..."

# Test 1: Basic numeric OID (should always work)
echo -n "Testing basic SNMP connectivity... "
if snmpget -v2c -c public localhost 1.3.6.1.2.1.1.1.0 >/dev/null 2>&1; then
    echo "✓ SUCCESS"
else
    echo "✗ FAILED - SNMP daemon may not be running"
    echo "Try: sudo systemctl start snmpd"
fi

# Test 2: System MIB with numeric OID
echo -n "Testing system MIB (numeric)... "
if snmpwalk -v2c -c public localhost 1.3.6.1.2.1.1 >/dev/null 2>&1; then
    echo "✓ SUCCESS"
else
    echo "✗ FAILED"
fi

# Test 3: System MIB with symbolic name
echo -n "Testing system MIB (symbolic)... "
if snmpwalk -v2c -c public -m ALL localhost system >/dev/null 2>&1; then
    echo "✓ SUCCESS - MIBs loaded correctly"
else
    echo "! WARNING - MIBs not fully loaded, but SNMP works with numeric OIDs"
fi

# Test 4: Interface MIB
echo -n "Testing interface MIB... "
if snmpwalk -v2c -c public localhost 1.3.6.1.2.1.2.2.1.2 >/dev/null 2>&1; then
    echo "✓ SUCCESS"
else
    echo "✗ FAILED"
fi

echo ""
echo "=== SNMP Test Commands ==="
echo "Use these commands to test SNMP manually:"
echo ""
echo "# Basic system information (numeric OID - always works):"
echo "snmpwalk -v2c -c public localhost 1.3.6.1.2.1.1"
echo ""
echo "# System information (symbolic name - requires MIBs):"
echo "snmpwalk -v2c -c public -m ALL localhost system"
echo ""
echo "# Interface information:"
echo "snmpwalk -v2c -c public localhost 1.3.6.1.2.1.2.2.1.2"
echo ""
echo "# System uptime:"
echo "snmpget -v2c -c public localhost 1.3.6.1.2.1.1.3.0"
echo ""

echo "=== Troubleshooting Tips ==="
echo "1. If symbolic names don't work, use numeric OIDs"
echo "2. Check SNMP daemon: sudo systemctl status snmpd"
echo "3. View SNMP logs: sudo tail -f /var/log/snmpd.log"
echo "4. Restart SNMP daemon: sudo systemctl restart snmpd"
echo ""

# Show current MIB configuration
echo "=== Current MIB Configuration ==="
echo "User config (~/.snmp/snmp.conf):"
if [ -f ~/.snmp/snmp.conf ]; then
    cat ~/.snmp/snmp.conf
else
    echo "  Not found"
fi

if [ "$SYSTEM_WIDE" = true ] && [ -f /etc/snmp/snmp.conf ]; then
    echo ""
    echo "System config (/etc/snmp/snmp.conf):"
    cat /etc/snmp/snmp.conf
fi

echo ""
echo "=== Fix Complete ==="
echo "SNMP should now work with both numeric OIDs and symbolic names (if MIBs are available)"