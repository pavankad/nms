# Mininet SNMP Network Monitoring Setup Guide

This guide provides detailed steps to monitor Mininet networks using SNMP. The setup includes a network topology, SNMP configuration, monitoring scripts, and a web-based dashboard.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Running the System](#running-the-system)
5. [Monitoring Options](#monitoring-options)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Usage](#advanced-usage)

## Prerequisites

### System Requirements
- Ubuntu 18.04+ or similar Linux distribution
- Python 3.6+
- Root access for SNMP daemon installation
- Mininet installed
- Minimum 2GB RAM
- Network connectivity

### Required Packages
The setup script will install these automatically, but you can install them manually:

```bash
# System packages
sudo apt-get update
sudo apt-get install -y snmp snmp-mibs-downloader snmpd

# Python packages
pip3 install pysnmp flask
```

## Installation

### Step 1: Clone or Download the Monitoring System

The monitoring system consists of several files:
- `mininet_topology.py` - Creates the network topology
- `snmpd.conf` - SNMP daemon configuration
- `setup_snmp.sh` - Automated SNMP setup script
- `snmp_monitor.py` - Command-line monitoring script
- `dashboard.py` - Web-based monitoring dashboard

### Step 2: Run the SNMP Setup Script

**IMPORTANT**: This must be run as root to configure the SNMP daemon.

```bash
sudo ./setup_snmp.sh
```

This script will:
- Install SNMP packages
- Download MIB files
- Configure SNMP daemon with proper community strings
- Start and enable the SNMP service
- Test the SNMP configuration

### Step 3: Verify SNMP Installation

Test SNMP functionality:

```bash
# Test basic SNMP functionality
snmpwalk -v2c -c public localhost 1.3.6.1.2.1.1

# Test interface information
snmpwalk -v2c -c public localhost 1.3.6.1.2.1.2.2.1.2

# Alternative: Load MIBs and use symbolic names
snmpwalk -v2c -c public -m ALL localhost system
```

If these commands return data, SNMP is working correctly.

## Configuration

### SNMP Configuration Details

The `snmpd.conf` file contains:

```
# Community strings
rocommunity public          # Read-only access
rwcommunity private         # Read-write access (use with caution)

# System information
sysLocation "Mininet Lab Environment"
sysContact "Network Administrator <admin@example.com>"
sysName "Mininet-SNMP-Monitor"

# Listen on all interfaces
agentAddress udp:161
```

### Network Topology Configuration

The `mininet_topology.py` script creates:
- 3 switches (s1, s2, s3)
- 4 hosts (h1-h4) with IP addresses 10.0.0.1-10.0.0.4
- Various link speeds for realistic monitoring (10-100 Mbps)
- Automatic traffic generation for testing

You can modify the topology by editing the `create_topology()` method.

## Running the System

### Step 1: Start the Mininet Network

Open a terminal and run:

```bash
sudo python3 mininet_topology.py
```

This will:
- Create the network topology
- Configure SNMP on switches
- Generate background traffic
- Start the Mininet CLI

Keep this terminal open during monitoring.

### Step 2: Choose Your Monitoring Method

You have three monitoring options:

#### Option A: Command-Line Monitor (Basic)

```bash
# Single snapshot
python3 snmp_monitor.py --once

# Continuous monitoring (default 5-second intervals)
python3 snmp_monitor.py

# Custom interval monitoring
python3 snmp_monitor.py --interval 10
```

#### Option B: Web Dashboard (Recommended)

**New Integrated Dashboard:**
```bash
# Start the integrated web dashboard (uses simple_snmp_monitor.py)
python3 web_dashboard.py

# Custom configuration
python3 web_dashboard.py --host localhost --port 8080 --interval 3
```

**Original Dashboard (requires pysnmp library):**
```bash
# If you have pysnmp working
python3 dashboard.py

# Custom configuration
python3 dashboard.py --host localhost --port 8080 --interval 3
```

Then open your web browser and go to: `http://localhost:5000` or your custom port

#### Option C: Remote Monitoring

```bash
# Monitor a remote Mininet instance
python3 snmp_monitor.py --host 192.168.1.100 --community public

# Remote dashboard
python3 dashboard.py --host 192.168.1.100
```

## Monitoring Options

### Command-Line Monitor Features

The `snmp_monitor.py` script provides:

- **System Information**: hostname, uptime, interface count
- **Interface Details**: status, speed, description
- **Traffic Statistics**: bytes, packets, errors
- **Rate Calculations**: Mbps, packets per second
- **Real-time Updates**: configurable intervals

Example output:
```
================================================================================
SNMP Network Monitor - 2024-10-18 14:30:15
System: Mininet-SNMP-Monitor
Uptime: 0d 2h 15m 32s
Interfaces: 8
================================================================================

Interface 1: s1-eth1
  Status: Admin=up, Oper=up
  Speed: 10000000 bps
  Traffic: In=125.43 MB, Out=98.76 MB
  Packets: In=156789, Out=134567
  Errors:  In=0, Out=0
  Rates:   In=2.45 Mbps, Out=1.87 Mbps
           In=324.5 pps, Out=298.1 pps
```

### Web Dashboard Features

The `dashboard.py` provides:

- **Real-time Interface Monitoring**: Live traffic statistics
- **Historical Charts**: Traffic trends over time
- **System Overview**: Uptime, interface count, status
- **Interactive Interface**: Start/stop monitoring, refresh controls
- **Responsive Design**: Works on desktop and mobile devices

Dashboard includes:
- System information panel
- Real-time traffic charts (using Chart.js)
- Interface cards with detailed statistics
- Auto-refresh functionality
- Error handling and status indicators

## Troubleshooting

### Common Issues and Solutions

#### 1. SNMP Not Working

**Symptoms**: `snmpwalk` commands fail or return no data

**Solutions**:
```bash
# Check SNMP daemon status
sudo systemctl status snmpd

# Check SNMP configuration
sudo snmpd -Dread_config -f

# View SNMP logs
tail -f /var/log/snmpd.log

# Restart SNMP daemon
sudo systemctl restart snmpd
```

#### 2. Permission Denied Errors

**Symptoms**: Cannot start Mininet or SNMP configuration fails

**Solutions**:
```bash
# Run Mininet as root
sudo python3 mininet_topology.py

# Check file permissions
ls -la snmpd.conf
sudo chown root:root /etc/snmp/snmpd.conf
sudo chmod 644 /etc/snmp/snmpd.conf
```

#### 3. Python Module Import Errors

**Symptoms**: `ModuleNotFoundError` for pysnmp, flask, etc.

**Solutions**:
```bash
# Install missing Python packages
pip3 install pysnmp flask

# For system-wide installation
sudo pip3 install pysnmp flask

# Check Python path
python3 -c "import sys; print(sys.path)"
```

#### 4. Network Interface Not Showing

**Symptoms**: Interfaces don't appear in monitoring output

**Solutions**:
```bash
# Check Mininet network status
sudo mn --test pingall

# Verify interface creation
ip link show

# Check SNMP interface MIBs
snmpwalk -v2c -c public localhost 1.3.6.1.2.1.2.2.1.2
```

#### 5. Dashboard Not Loading

**Symptoms**: Web dashboard shows errors or doesn't load

**Solutions**:
```bash
# Check Flask server status
python3 dashboard.py --host 0.0.0.0 --port 5000

# Verify firewall settings
sudo ufw status
sudo ufw allow 5000

# Check browser console for JavaScript errors
# Open browser developer tools (F12)
```

### Log Files and Debugging

Important log files:
- `/var/log/snmpd.log` - SNMP daemon logs
- Terminal output from scripts - Real-time debugging
- Browser console - Dashboard JavaScript errors

Enable verbose debugging:
```bash
# SNMP debugging
sudo snmpd -f -Dread_config,access_control

# Python script debugging
python3 -u snmp_monitor.py  # Unbuffered output
```

## Advanced Usage

### Custom SNMP Communities

Edit `/etc/snmp/snmpd.conf` to add custom community strings:

```
# Custom read-only community
rocommunity mycompany 192.168.1.0/24

# Custom read-write community (be careful!)
rwcommunity admin_access 192.168.1.10
```

### SNMP v3 Security

For enhanced security, configure SNMP v3:

```
# Add to snmpd.conf
createUser authUser MD5 mypassword
rouser authUser

# Use in monitoring scripts
python3 snmp_monitor.py --version 3 --user authUser --auth mypassword
```

### Custom Network Topologies

Modify `mininet_topology.py` to create different topologies:

```python
def create_custom_topology(self):
    # Add more switches
    s4 = self.net.addSwitch('s4')
    s5 = self.net.addSwitch('s5')
    
    # Add more hosts
    for i in range(5, 11):
        host = self.net.addHost(f'h{i}', ip=f'10.0.0.{i}/24')
        self.net.addLink(host, s4, bw=100)
    
    # Create redundant links
    self.net.addLink(s4, s5, bw=1000)  # 1 Gbps link
```

### Automated Monitoring Scripts

Create automated monitoring with cron:

```bash
# Add to crontab (crontab -e)
*/5 * * * * /usr/bin/python3 /home/pavan/nms/snmp_monitor.py --once >> /var/log/network_monitor.log 2>&1
```

### Integration with Other Tools

Export monitoring data:

```python
# In snmp_monitor.py, add JSON export
def export_json(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

# Usage
current_data = monitor.get_current_data()
export_json(current_data, f'/var/log/network_data_{timestamp}.json')
```

### Performance Optimization

For large networks:

1. **Reduce polling frequency** for less critical interfaces
2. **Use SNMP bulk operations** for better performance
3. **Implement data filtering** to reduce processing overhead
4. **Use database storage** for historical data instead of memory

### Alerting and Notifications

Add alerting capabilities:

```python
def check_alerts(interface_data):
    alerts = []
    for interface in interface_data:
        # High error rate alert
        if interface['in_errors'] > 100:
            alerts.append(f"High error rate on {interface['name']}")
        
        # High utilization alert
        if interface['in_mbps'] > interface['speed'] * 0.8:
            alerts.append(f"High utilization on {interface['name']}")
    
    return alerts
```

## Security Considerations

1. **Change default SNMP community strings** in production
2. **Restrict SNMP access** to specific IP ranges
3. **Use SNMP v3** with authentication and encryption
4. **Firewall SNMP ports** (UDP 161/162) appropriately
5. **Monitor SNMP access logs** for unauthorized attempts
6. **Regularly update SNMP software** for security patches

## Performance Monitoring Metrics

Key metrics to monitor:
- **Interface utilization** (percentage of bandwidth used)
- **Packet loss** (errors vs. total packets)
- **Latency** (through additional ping monitoring)
- **Throughput** (actual vs. configured speeds)
- **Error rates** (interface errors over time)

## Conclusion

This comprehensive setup provides a complete SNMP monitoring solution for Mininet networks. The system offers both command-line and web-based monitoring options, making it suitable for development, testing, and educational purposes.

For production deployments, consider implementing additional security measures, database storage for historical data, and integration with enterprise monitoring tools.

## Support and Contributing

For issues or improvements:
1. Check the troubleshooting section
2. Review log files for error messages
3. Test with simplified configurations
4. Verify all prerequisites are met

The monitoring system is designed to be modular and extensible, allowing for easy customization based on specific requirements.# nms
