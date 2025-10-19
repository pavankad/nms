# Network Management System (NMS)

A web-based network monitoring system that discovers devices via SNMP, builds interactive topology visualizations, and provides real-time monitoring with clickable device details.

## � Required Installations

### System Dependencies
```bash
# Install SNMP tools and Python dependencies
sudo apt-get update
sudo apt-get install snmp snmp-mibs-downloader python3 python3-pip

# Install Mininet for testing (optional)
sudo apt-get install mininet
```

### Python Dependencies
```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install required packages
pip install flask flask-socketio
```

## � Quick Start

### 1. Create Mininet Test Network
```bash
# Start the test topology (1 switch + 4 hosts)
sudo python3 simple_topology.py
```

### 2. Run Web Application
```bash
# In a new terminal, start the NMS web interface
python3 nms_web.py
```

### 3. Access Web Interface
Open your browser and go to: **http://localhost:5000**

## �️ Using the NMS

### Discovery
1. Click **"🔍 Discover"** button or enter network range (default: `127.0.0.1/32`)
2. System will discover SNMP-enabled devices and build topology

### Topology Visualization
- Interactive D3.js network diagram shows discovered devices
- **Click nodes** to view detailed device information (stats, config, interfaces)
- **Click links** to view connection details
- Nodes are color-coded: Blue (switches), Green (hosts)

### Real-time Monitoring
- Click **"▶️ Start Monitor"** for live interface statistics
- Data updates every 10 seconds via WebSocket
- View real-time packet counts, bandwidth usage, and interface status

## 📁 File Structure
```
nms/
├── nms_web.py              # Main Flask web application
├── nms_discovery.py        # Network discovery engine
├── simple_snmp_monitor.py  # SNMP monitoring utilities
├── simple_topology.py      # Mininet test topology
├── templates/              # Web interface templates
└── README.md               # This file
```

## 🧪 Testing with Mininet

The included `simple_topology.py` creates a test network with:
- 1 OpenVSwitch (s1)
- 4 hosts (h1-h4) connected to the switch
- SNMP monitoring enabled on localhost

This allows you to test all NMS features without requiring physical network equipment.

## 🔍 Troubleshooting

### SNMP Issues
```bash
# Test SNMP connectivity
snmpwalk -v2c -c public localhost 1.3.6.1.2.1.1.1.0

# Check if SNMP daemon is running
sudo systemctl status snmpd
sudo systemctl start snmpd  # Start if needed
```

### Port Already in Use
```bash
# Find and kill process using port 5000
sudo lsof -ti:5000 | xargs sudo kill -9

# Or run on different port
python3 nms_web.py --port 8080
```

## ✨ Features

- **Device Discovery**: Automatic SNMP-based network scanning
- **Interactive Topology**: D3.js visualization with clickable elements  
- **Real-time Monitoring**: Live interface statistics and status
- **Device Details**: Comprehensive information panels with tabs
- **Mininet Support**: Virtual topology detection and visualization
