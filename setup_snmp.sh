#!/bin/bash
# SNMP Setup Script for Mininet Network Monitoring
# This script installs and configures SNMP daemon for network monitoring

set -e

echo "=== SNMP Setup for Mininet Network Monitoring ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script as root (use sudo)"
    exit 1
fi

# Update package lists
echo "Updating package lists..."
apt-get update

# Install SNMP packages
echo "Installing SNMP packages..."
apt-get install -y snmp snmp-mibs-downloader snmpd

# Install Python SNMP libraries
echo "Installing Python SNMP libraries..."
pip3 install pysnmp

# Download MIB files
echo "Downloading MIB files..."
download-mibs

# Configure MIB loading
echo "Configuring MIB loading..."
if [ ! -f /etc/snmp/snmp.conf ]; then
    touch /etc/snmp/snmp.conf
fi

# Enable MIB loading in client configuration
grep -q "mibs +" /etc/snmp/snmp.conf || echo "mibs +ALL" >> /etc/snmp/snmp.conf

# Alternative: Create user-specific MIB config
mkdir -p ~/.snmp
echo "mibs +ALL" > ~/.snmp/snmp.conf

# Backup original config
if [ -f /etc/snmp/snmpd.conf ]; then
    echo "Backing up original SNMP configuration..."
    cp /etc/snmp/snmpd.conf /etc/snmp/snmpd.conf.backup
fi

# Copy our configuration
echo "Installing custom SNMP configuration..."
cp snmpd.conf /etc/snmp/snmpd.conf

# Set proper permissions
chmod 644 /etc/snmp/snmpd.conf

# Create log directory
mkdir -p /var/log
touch /var/log/snmpd.log
chmod 644 /var/log/snmpd.log

# Enable and start SNMP daemon
echo "Starting SNMP daemon..."
systemctl enable snmpd
systemctl restart snmpd

# Test SNMP configuration
echo "Testing SNMP configuration..."
sleep 2
if snmpwalk -v2c -c public localhost 1.3.6.1.2.1.1.1.0 > /dev/null 2>&1; then
    echo "✓ SNMP is working correctly"
else
    echo "✗ SNMP configuration test failed"
    echo "Check /var/log/snmpd.log for errors"
fi

# Show status
echo "SNMP daemon status:"
systemctl status snmpd --no-pager

echo ""
echo "=== SNMP Setup Complete ==="
echo "SNMP daemon is running on UDP port 161"
echo "Community strings:"
echo "  - Public (read-only): public"
echo "  - Private (read-write): private"
echo ""
echo "Test SNMP with:"
echo "  snmpwalk -v2c -c public localhost system"
echo ""
echo "Log file: /var/log/snmpd.log"
echo "Config file: /etc/snmp/snmpd.conf"