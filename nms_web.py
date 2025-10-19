#!/usr/bin/env python3
"""
Network Management System (NMS) - Web Interface
Interactive topology visualization and device management
"""

import json
import time
import threading
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from nms_discovery import DeviceDiscovery

app = Flask(__name__)
app.config['SECRET_KEY'] = 'nms-secret-key-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

class NMSWebInterface:
    def __init__(self):
        self.discovery = DeviceDiscovery()
        self.monitoring_active = False
        self.monitor_thread = None
        self.last_stats = {}
        
    def start_monitoring(self, interval=10):
        """Start background monitoring of discovered devices"""
        if self.monitoring_active:
            return
            
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop, 
            args=(interval,), 
            daemon=True
        )
        self.monitor_thread.start()
        print(f"🔄 Started monitoring with {interval}s interval")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring_active = False
        print("⏹️  Stopped monitoring")
    
    def _monitoring_loop(self, interval):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                for ip in self.discovery.discovered_devices.keys():
                    stats = self.discovery.get_device_stats(ip)
                    if stats:
                        self.last_stats[ip] = stats
                        # Emit real-time updates via WebSocket
                        socketio.emit('device_stats_update', {
                            'device_ip': ip,
                            'stats': stats
                        })
                
                time.sleep(interval)
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(interval)

# Global NMS instance
nms = NMSWebInterface()

@app.route('/')
def index():
    """Main NMS dashboard"""
    return render_template('nms_dashboard.html')

@app.route('/api/discover', methods=['POST'])
def api_discover():
    """Trigger network discovery"""
    data = request.get_json() or {}
    network_range = data.get('network_range', '127.0.0.1/32')
    community = data.get('community', 'public')
    
    try:
        # Update discovery settings
        nms.discovery.community = community
        
        # Perform discovery
        if network_range == '127.0.0.1/32':
            devices = nms.discovery.discover_localhost()
        else:
            devices = nms.discovery.discover_network_range(network_range)
        
        # Build topology
        topology = nms.discovery.build_topology()
        
        return jsonify({
            'success': True,
            'devices_found': len(devices),
            'topology': topology
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/topology')
def api_topology():
    """Get current network topology"""
    return jsonify(nms.discovery.topology)

@app.route('/api/devices')
def api_devices():
    """Get all discovered devices"""
    return jsonify(nms.discovery.discovered_devices)

@app.route('/api/device/<device_ip>/stats')
def api_device_stats(device_ip):
    """Get current stats for a specific device"""
    stats = nms.discovery.get_device_stats(device_ip)
    if stats:
        return jsonify(stats)
    else:
        return jsonify({'error': 'Device not found or not accessible'}), 404

@app.route('/api/device/<device_ip>/config')
def api_device_config(device_ip):
    """Get configuration information for a specific device"""
    try:
        config = nms.discovery.get_device_config(device_ip)
        if config:
            return jsonify(config)
        else:
            return jsonify({'error': 'Device configuration not available'}), 404
    except Exception as e:
        return jsonify({'error': f'Error fetching config: {str(e)}'}), 500

@app.route('/api/device/<device_ip>/full')
def api_device_full(device_ip):
    """Get complete device information (stats + config)"""
    try:
        # Get both stats and config
        stats = nms.discovery.get_device_stats(device_ip)
        config = nms.discovery.get_device_config(device_ip)
        device_info = nms.discovery.discovered_devices.get(device_ip, {})
        
        result = {
            'device_info': device_info,
            'stats': stats or {},
            'config': config or {},
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Error fetching device data: {str(e)}'}), 500

@app.route('/api/monitoring/start', methods=['POST'])
def api_start_monitoring():
    """Start real-time monitoring"""
    data = request.get_json() or {}
    interval = data.get('interval', 10)
    
    nms.start_monitoring(interval)
    return jsonify({'success': True, 'monitoring': True})

@app.route('/api/monitoring/stop', methods=['POST'])
def api_stop_monitoring():
    """Stop real-time monitoring"""
    nms.stop_monitoring()
    return jsonify({'success': True, 'monitoring': False})

@app.route('/api/monitoring/status')
def api_monitoring_status():
    """Get monitoring status"""
    return jsonify({
        'monitoring': nms.monitoring_active,
        'devices': len(nms.discovery.discovered_devices),
        'last_update': datetime.now().isoformat()
    })

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    emit('connected', {'message': 'Connected to NMS'})

@socketio.on('request_device_stats')
def handle_device_stats_request(data):
    """Handle request for device stats"""
    device_ip = data.get('device_ip')
    if device_ip:
        stats = nms.discovery.get_device_stats(device_ip)
        emit('device_stats_response', {
            'device_ip': device_ip,
            'stats': stats
        })

def create_nms_template():
    """Create the HTML template for NMS dashboard"""
    import os
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(template_dir, exist_ok=True)
    
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Network Management System (NMS)</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        
        .header {
            background: rgba(255,255,255,0.95);
            padding: 15px 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 20px;
        }
        
        .header h1 {
            color: #667eea;
            font-size: 1.8em;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .controls {
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }
        
        .btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
        }
        
        .btn:hover { background: #5a6fd8; transform: translateY(-1px); }
        .btn-success { background: #28a745; }
        .btn-danger { background: #dc3545; }
        .btn-warning { background: #ffc107; color: #333; }
        
        .status-indicator {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }
        
        .status-connected {
            background: #d4edda;
            color: #155724;
        }
        
        .status-disconnected {
            background: #f8d7da;
            color: #721c24;
        }
        
        .main-container {
            display: flex;
            height: calc(100vh - 80px);
            background: rgba(255,255,255,0.95);
            margin: 20px;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .sidebar {
            width: 300px;
            background: #f8f9fa;
            border-right: 1px solid #dee2e6;
            overflow-y: auto;
        }
        
        .sidebar-section {
            padding: 20px;
            border-bottom: 1px solid #dee2e6;
        }
        
        .sidebar-section h3 {
            margin-bottom: 15px;
            color: #495057;
            font-size: 1.1em;
        }
        
        .device-list {
            max-height: 300px;
            overflow-y: auto;
        }
        
        .device-item {
            padding: 10px;
            margin: 5px 0;
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .device-item:hover {
            background: #e3f2fd;
            border-color: #667eea;
        }
        
        .device-item.selected {
            background: #667eea;
            color: white;
            border-color: #5a6fd8;
        }
        
        .device-name {
            font-weight: 600;
            margin-bottom: 2px;
        }
        
        .device-details {
            font-size: 12px;
            opacity: 0.7;
        }
        
        .topology-container {
            flex: 1;
            position: relative;
            background: white;
        }
        
        .topology-svg {
            width: 100%;
            height: 100%;
        }
        
        .node {
            cursor: pointer;
            /* Completely disable all transitions and animations to prevent flickering */
            transition: none !important;
            animation: none !important;
            transform: none !important;
        }
        
        .node:hover {
            /* Completely disable transforms to prevent any layout changes */
            transform: none !important;
            opacity: 0.8;
            cursor: pointer;
            /* Disable hover transitions */
            transition: none !important;
        }
        
        .node.selected {
            stroke: #ff6b6b;
            stroke-width: 3px;
        }
        
        .node-switch {
            fill: #667eea;
        }
        
        .node-host {
            fill: #28a745;
        }
        
        .node-router {
            fill: #ffc107;
        }
        
        .node-unknown {
            fill: #6c757d;
        }
        
        .link {
            stroke: #adb5bd;
            stroke-width: 2px;
            fill: none;
            cursor: pointer;
        }
        
        .link-switch_link {
            stroke: #667eea;
            stroke-width: 3px;
        }
        
        .link-host_link {
            stroke: #28a745;
            stroke-width: 3px;
        }
        
        .link.selected {
            stroke: #ff6b6b;
            stroke-width: 4px;
        }
        
        .node-text {
            fill: white;
            font-size: 12px;
            font-weight: 500;
            text-anchor: middle;
            dominant-baseline: middle;
            pointer-events: none;
        }
        
        .device-stats {
            position: absolute;
            top: 20px;
            right: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            width: 400px;
            max-height: 80vh;
            overflow: hidden;
            display: none;
            z-index: 1000;
        }
        
        .stats-header {
            padding: 15px 20px;
            border-bottom: 1px solid #e9ecef;
            background: #f8f9fa;
        }
        
        .stats-title {
            font-size: 1.1em;
            font-weight: 600;
            color: #333;
            margin: 0;
        }
        
        .stats-subtitle {
            font-size: 0.85em;
            color: #6c757d;
            margin: 4px 0 0 0;
        }
        
        /* Tabbed interface styles */
        .device-tabs {
            display: flex;
            border-bottom: 1px solid #e9ecef;
            background: #f8f9fa;
            margin: 0;
        }
        
        .tab-button {
            background: none;
            border: none;
            padding: 10px 12px;
            cursor: pointer;
            font-size: 11px;
            color: #6c757d;
            transition: all 0.2s;
            border-bottom: 2px solid transparent;
            flex: 1;
            text-align: center;
        }
        
        .tab-button:hover {
            background: #e9ecef;
            color: #333;
        }
        
        .tab-button.active {
            color: #667eea;
            border-bottom-color: #667eea;
            background: white;
            font-weight: 600;
        }
        
        .tab-content {
            display: none;
            padding: 15px 20px;
            max-height: 60vh;
            overflow-y: auto;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .stat-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-bottom: 15px;
        }
        
        .stat-item {
            background: #f8f9fa;
            padding: 8px;
            border-radius: 4px;
            text-align: center;
        }
        
        .stat-label {
            font-size: 10px;
            color: #6c757d;
            margin-bottom: 2px;
            text-transform: uppercase;
            font-weight: 600;
        }
        
        .stat-value {
            font-size: 12px;
            font-weight: 600;
            color: #333;
        }
        
        .config-section h4 {
            margin: 12px 0 6px 0;
            color: #333;
            font-size: 12px;
            border-bottom: 1px solid #e9ecef;
            padding-bottom: 3px;
            font-weight: 600;
        }
        
        .config-section h4:first-child {
            margin-top: 0;
        }
        
        .config-item {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            padding: 4px 0;
            font-size: 10px;
            border-bottom: 1px solid #f8f9fa;
        }
        
        .config-label {
            font-weight: 600;
            color: #555;
            min-width: 50px;
        }
        
        .config-value {
            text-align: right;
            color: #333;
            word-break: break-word;
            max-width: 200px;
            font-size: 10px;
        }
        
        .interface-list h4 {
            margin: 0 0 8px 0;
            color: #333;
            font-size: 12px;
            font-weight: 600;
        }
        
        .interface-item {
            background: #f8f9fa;
            border-radius: 4px;
            padding: 6px;
            margin-bottom: 5px;
            border-left: 3px solid #667eea;
        }
        
        .interface-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 4px;
        }
        
        .interface-name {
            font-weight: 600;
            color: #333;
            font-size: 11px;
        }
        
        .interface-status {
            font-size: 9px;
            padding: 1px 4px;
            border-radius: 2px;
            background: rgba(255, 255, 255, 0.8);
            font-weight: 600;
        }
        
        .interface-details {
            font-size: 9px;
            line-height: 1.2;
        }
        
        .interface-detail {
            margin-bottom: 2px;
        }
        
        .interface-detail span {
            font-weight: 600;
            color: #555;
        }
        
        .interface-stats {
            margin-top: 4px;
            padding-top: 4px;
            border-top: 1px solid #e9ecef;
            font-size: 8px;
        }
        
        .stat-pair {
            display: flex;
            justify-content: space-between;
            margin-bottom: 1px;
        }
        
        .stat-pair span {
            font-weight: 600;
            color: #555;
        }
        
        .stats-section h4 {
            margin: 0 0 8px 0;
            color: #333;
            font-size: 12px;
            font-weight: 600;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .stat-item {
            padding: 8px;
            background: #f8f9fa;
            border-radius: 4px;
            text-align: center;
        }
        
        .stat-label {
            font-size: 0.8em;
            color: #6c757d;
            margin-bottom: 2px;
        }
        
        .stat-value {
            font-weight: 600;
            color: #333;
        }
        
        .interface-list {
            margin-top: 15px;
        }
        
        .interface-item {
            padding: 8px;
            margin: 5px 0;
            background: #f8f9fa;
            border-radius: 4px;
            border-left: 3px solid #667eea;
        }
        
        .interface-name {
            font-weight: 600;
            margin-bottom: 3px;
        }
        
        .interface-stats {
            font-size: 0.85em;
            color: #6c757d;
        }
        
        .discovery-form {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        
        .form-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        
        .form-group label {
            font-weight: 500;
            font-size: 0.9em;
        }
        
        .form-group input {
            padding: 8px;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            font-size: 14px;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #6c757d;
        }
        
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }
        
        .success {
            background: #d4edda;
            color: #155724;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }
        
        @media (max-width: 768px) {
            .main-container {
                flex-direction: column;
                margin: 10px;
            }
            
            .sidebar {
                width: 100%;
                height: 300px;
            }
            
            .device-stats {
                position: relative;
                top: 0;
                right: 0;
                margin: 20px;
                max-width: none;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🌐 Network Management System</h1>
        <div class="controls">
            <span class="status-indicator" id="connectionStatus">
                <span id="statusDot">🔴</span>
                <span id="statusText">Disconnected</span>
            </span>
            <button class="btn" onclick="startDiscovery()">🔍 Discover</button>
            <button class="btn btn-success" onclick="startMonitoring()" id="monitorBtn">▶️ Start Monitor</button>
            <button class="btn btn-warning" onclick="refreshTopology()">🔄 Refresh</button>
        </div>
    </div>
    
    <div class="main-container">
        <div class="sidebar">
            <div class="sidebar-section">
                <h3>🔍 Discovery</h3>
                <div class="discovery-form">
                    <div class="form-group">
                        <label for="networkRange">Network Range:</label>
                        <input type="text" id="networkRange" value="127.0.0.1/32" placeholder="192.168.1.0/24">
                    </div>
                    <div class="form-group">
                        <label for="community">SNMP Community:</label>
                        <input type="text" id="community" value="public" placeholder="public">
                    </div>
                    <button class="btn" onclick="startDiscovery()">Start Discovery</button>
                </div>
                <div id="discoveryStatus"></div>
            </div>
            
            <div class="sidebar-section">
                <h3>📱 Devices (<span id="deviceCount">0</span>)</h3>
                <div class="device-list" id="deviceList">
                    <div class="loading">No devices discovered yet</div>
                </div>
            </div>
            
            <div class="sidebar-section">
                <h3>📊 Monitoring</h3>
                <div>
                    <p>Status: <span id="monitoringStatus">Stopped</span></p>
                    <p>Interval: <span id="monitoringInterval">10s</span></p>
                    <p>Last Update: <span id="lastUpdate">Never</span></p>
                </div>
            </div>
        </div>
        
        <div class="topology-container">
            <svg class="topology-svg" id="topologySvg"></svg>
            
            <div class="device-stats" id="deviceStats">
                <div class="stats-header">
                    <div class="stats-title" id="statsTitle">Device Statistics</div>
                    <div class="stats-subtitle" id="statsSubtitle">Select a device to view details</div>
                </div>
                
                <div id="statsContent">
                    <!-- Tabbed content will be populated dynamically -->
                </div>
            </div>
        </div>
    </div>

    <script>
        // Global variables
        let socket = io();
        let topology = { nodes: [], links: [] };
        let devices = {};
        let selectedDevice = null;
        let simulation = null;
        let monitoring = false;
        
        // Socket.IO event handlers
        socket.on('connect', function() {
            updateConnectionStatus(true);
        });
        
        socket.on('disconnect', function() {
            updateConnectionStatus(false);
        });
        
        socket.on('device_stats_update', function(data) {
            if (selectedDevice === data.device_ip) {
                updateDeviceStats(data.stats);
            }
            updateLastUpdate();
        });
        
        function updateConnectionStatus(connected) {
            const statusElement = document.getElementById('connectionStatus');
            const dotElement = document.getElementById('statusDot');
            const textElement = document.getElementById('statusText');
            
            if (connected) {
                statusElement.className = 'status-indicator status-connected';
                dotElement.textContent = '🟢';
                textElement.textContent = 'Connected';
            } else {
                statusElement.className = 'status-indicator status-disconnected';
                dotElement.textContent = '🔴';
                textElement.textContent = 'Disconnected';
            }
        }
        
        async function startDiscovery() {
            const networkRange = document.getElementById('networkRange').value;
            const community = document.getElementById('community').value;
            const statusDiv = document.getElementById('discoveryStatus');
            
            statusDiv.innerHTML = '<div class="loading">🔍 Discovering devices...</div>';
            
            try {
                const response = await fetch('/api/discover', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ network_range: networkRange, community: community })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    statusDiv.innerHTML = `<div class="success">✅ Found ${result.devices_found} devices</div>`;
                    topology = result.topology;
                    await loadDevices();
                    renderTopology();
                    updateDeviceList();
                } else {
                    statusDiv.innerHTML = `<div class="error">❌ Error: ${result.error}</div>`;
                }
            } catch (error) {
                statusDiv.innerHTML = `<div class="error">❌ Network error: ${error.message}</div>`;
            }
        }
        
        async function loadDevices() {
            try {
                const response = await fetch('/api/devices');
                devices = await response.json();
            } catch (error) {
                console.error('Error loading devices:', error);
            }
        }
        
        async function refreshTopology() {
            try {
                const response = await fetch('/api/topology');
                topology = await response.json();
                await loadDevices();
                renderTopology();
                updateDeviceList();
            } catch (error) {
                console.error('Error refreshing topology:', error);
            }
        }
        
        function updateDeviceList() {
            const deviceList = document.getElementById('deviceList');
            const deviceCount = document.getElementById('deviceCount');
            
            if (Object.keys(devices).length === 0) {
                deviceList.innerHTML = '<div class="loading">No devices discovered yet</div>';
                deviceCount.textContent = '0';
                return;
            }
            
            deviceCount.textContent = Object.keys(devices).length;
            
            let html = '';
            for (const [ip, device] of Object.entries(devices)) {
                html += `
                    <div class="device-item" onclick="selectDevice('${ip}')" data-device="${ip}">
                        <div class="device-name">${device.system_name}</div>
                        <div class="device-details">
                            ${ip} | ${device.device_type} | ${Object.keys(device.interfaces).length} interfaces
                        </div>
                    </div>
                `;
            }
            
            deviceList.innerHTML = html;
        }
        
        function selectDevice(deviceIp) {
            // Clear link selection
            selectedLink = null;
            d3.selectAll('.link').classed('selected', false);
            
            selectedDevice = deviceIp;
            
            // Update device list selection
            document.querySelectorAll('.device-item').forEach(item => {
                item.classList.remove('selected');
            });
            
            const deviceElement = document.querySelector(`[data-device="${deviceIp}"]`);
            if (deviceElement) {
                deviceElement.classList.add('selected');
            }
            
            // Update topology selection
            d3.selectAll('.node').classed('selected', false);
            d3.selectAll(`[data-device="${deviceIp}"]`).classed('selected', true);
            
            // Load device stats
            loadDeviceStats(deviceIp);
            
            // Show stats panel
            document.getElementById('deviceStats').style.display = 'block';
        }
        
        async function loadDeviceStats(deviceIp) {
            try {
                // Use the new full device info endpoint
                const response = await fetch(`/api/device/${deviceIp}/full`);
                const data = await response.json();
                
                if (data.error) {
                    document.getElementById('statsTitle').textContent = 'Error';
                    document.getElementById('statsSubtitle').textContent = data.error;
                    return;
                }
                
                updateDeviceStats(data);
            } catch (error) {
                console.error('Error loading device stats:', error);
                document.getElementById('statsTitle').textContent = 'Error';
                document.getElementById('statsSubtitle').textContent = 'Failed to load device information';
            }
        }
        
        function updateDeviceStats(data) {
            if (!selectedDevice || !data) return;
            
            const deviceInfo = data.device_info || {};
            const stats = data.stats || {};
            const config = data.config || {};
            
            // Update header
            const hostname = config.basic_info?.hostname || deviceInfo.system_name || selectedDevice;
            const deviceType = config.network_config?.device_type || deviceInfo.device_type || 'Unknown';
            
            document.getElementById('statsTitle').textContent = hostname;
            document.getElementById('statsSubtitle').textContent = `${selectedDevice} | ${deviceType}`;
            
            // Create tabbed interface for configuration and statistics
            const statsContent = document.getElementById('statsContent');
            statsContent.innerHTML = `
                <div class="device-tabs">
                    <button class="tab-button active" onclick="showTab('overview')">Overview</button>
                    <button class="tab-button" onclick="showTab('config')">Configuration</button>
                    <button class="tab-button" onclick="showTab('interfaces')">Interfaces</button>
                    <button class="tab-button" onclick="showTab('stats')">Statistics</button>
                </div>
                
                <div id="tab-overview" class="tab-content active">
                    <div class="stat-grid">
                        <div class="stat-item">
                            <div class="stat-label">Hostname</div>
                            <div class="stat-value">${hostname}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">IP Address</div>
                            <div class="stat-value">${selectedDevice}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Device Type</div>
                            <div class="stat-value">${deviceType}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Uptime</div>
                            <div class="stat-value">${stats.system_info?.uptime_formatted || config.basic_info?.uptime || 'Unknown'}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Interfaces</div>
                            <div class="stat-value">${stats.system_info?.interface_count || config.network_config?.interfaces?.length || 0}</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-label">Location</div>
                            <div class="stat-value">${config.basic_info?.location || deviceInfo.system_location || 'Unknown'}</div>
                        </div>
                    </div>
                </div>
                
                <div id="tab-config" class="tab-content">
                    <div class="config-section">
                        <h4>Basic Configuration</h4>
                        <div class="config-item">
                            <span class="config-label">Description:</span>
                            <span class="config-value">${config.basic_info?.description || 'N/A'}</span>
                        </div>
                        <div class="config-item">
                            <span class="config-label">Contact:</span>
                            <span class="config-value">${config.basic_info?.contact || 'Unknown'}</span>
                        </div>
                        <div class="config-item">
                            <span class="config-label">Services:</span>
                            <span class="config-value">${config.basic_info?.services || 'Unknown'}</span>
                        </div>
                        
                        ${config.mininet_info ? `
                        <h4>Mininet Configuration</h4>
                        <div class="config-item">
                            <span class="config-label">Node Type:</span>
                            <span class="config-value">${config.mininet_info.node_type}</span>
                        </div>
                        ${config.mininet_info.connected_to ? `
                        <div class="config-item">
                            <span class="config-label">Connected To:</span>
                            <span class="config-value">${config.mininet_info.connected_to}</span>
                        </div>` : ''}
                        ${config.mininet_info.connected_hosts ? `
                        <div class="config-item">
                            <span class="config-label">Connected Hosts:</span>
                            <span class="config-value">${config.mininet_info.connected_hosts.join(', ')}</span>
                        </div>` : ''}
                        ` : ''}
                        
                        ${config.openflow_config ? `
                        <h4>OpenFlow Configuration</h4>
                        <div class="config-item">
                            <span class="config-label">Datapath ID:</span>
                            <span class="config-value">${config.openflow_config.datapath_id}</span>
                        </div>
                        <div class="config-item">
                            <span class="config-label">Controller:</span>
                            <span class="config-value">${config.openflow_config.controller_ip}:${config.openflow_config.controller_port}</span>
                        </div>
                        <div class="config-item">
                            <span class="config-label">Protocol Version:</span>
                            <span class="config-value">${config.openflow_config.protocol_version}</span>
                        </div>` : ''}
                    </div>
                </div>
                
                <div id="tab-interfaces" class="tab-content">
                    <div class="interface-list">
                        ${generateInterfaceList(stats.interfaces || {}, config.network_config?.interfaces || [])}
                    </div>
                </div>
                
                <div id="tab-stats" class="tab-content">
                    <div class="stats-section">
                        <h4>System Statistics</h4>
                        <div class="stat-grid">
                            <div class="stat-item">
                                <div class="stat-label">Last Updated</div>
                                <div class="stat-value">${new Date(data.timestamp || Date.now()).toLocaleTimeString()}</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-label">SNMP Accessible</div>
                                <div class="stat-value">${config.capabilities?.supports_snmp ? 'Yes' : 'No'}</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-label">Manageable</div>
                                <div class="stat-value">${config.capabilities?.manageable ? 'Yes' : 'No'}</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-label">Virtual Device</div>
                                <div class="stat-value">${config.capabilities?.virtual ? 'Yes' : 'No'}</div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        function generateInterfaceList(statsInterfaces, configInterfaces) {
            let html = '<h4>Network Interfaces:</h4>';
            
            // Combine stats and config data
            const interfaceMap = new Map();
            
            // Add config data
            if (configInterfaces) {
                configInterfaces.forEach(iface => {
                    interfaceMap.set(iface.name, { ...iface, hasConfig: true });
                });
            }
            
            // Add/update with stats data
            if (statsInterfaces) {
                Object.entries(statsInterfaces).forEach(([index, iface]) => {
                    const existing = interfaceMap.get(iface.name) || {};
                    interfaceMap.set(iface.name, { ...existing, ...iface, hasStats: true, index });
                });
            }
            
            if (interfaceMap.size === 0) {
                return '<p>No interface information available</p>';
            }
            
            interfaceMap.forEach((iface, name) => {
                if (name.includes('lo') || name.includes('sit0')) return;
                
                const statusColor = iface.oper_status === 'up' ? '#28a745' : '#dc3545';
                const speedText = iface.speed ? `${Math.round(iface.speed / 1000000)} Mbps` : 'Unknown';
                
                html += `
                    <div class="interface-item">
                        <div class="interface-header">
                            <span class="interface-name">${name}</span>
                            <span class="interface-status" style="color: ${statusColor}">
                                ${iface.oper_status || 'unknown'}
                            </span>
                        </div>
                        <div class="interface-details">
                            <div class="interface-detail">
                                <span>Type:</span> ${iface.type || 'Unknown'}
                            </div>
                            <div class="interface-detail">
                                <span>Speed:</span> ${speedText}
                            </div>
                            <div class="interface-detail">
                                <span>Admin Status:</span> ${iface.admin_status || 'unknown'}
                            </div>
                            ${iface.description ? `
                            <div class="interface-detail">
                                <span>Description:</span> ${iface.description}
                            </div>` : ''}
                            ${iface.hasStats ? `
                            <div class="interface-stats">
                                <div class="stat-pair">
                                    <span>RX:</span> ${formatBytes(iface.in_octets || 0)} (${iface.in_packets || 0} packets)
                                </div>
                                <div class="stat-pair">
                                    <span>TX:</span> ${formatBytes(iface.out_octets || 0)} (${iface.out_packets || 0} packets)
                                </div>
                            </div>` : ''}
                        </div>
                    </div>
                `;
            });
            
            return html;
        }
        
        function showTab(tabName) {
            console.log('Switching to tab:', tabName);
            
            // Hide all tab contents
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Remove active class from all tab buttons
            document.querySelectorAll('.tab-button').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Show selected tab
            const targetTab = document.getElementById(`tab-${tabName}`);
            if (targetTab) {
                targetTab.classList.add('active');
                console.log('Activated tab:', tabName);
            } else {
                console.error('Tab not found:', `tab-${tabName}`);
            }
            
            // Set active button
            if (event && event.target) {
                event.target.classList.add('active');
            }
        }
        
        function formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
        
        function formatBandwidth(bps) {
            if (!bps || bps === 0) return 'Unknown';
            const k = 1000;
            const sizes = ['bps', 'Kbps', 'Mbps', 'Gbps'];
            const i = Math.floor(Math.log(bps) / Math.log(k));
            return parseFloat((bps / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
        }
        
        async function startMonitoring() {
            const button = document.getElementById('monitorBtn');
            
            if (monitoring) {
                // Stop monitoring
                await fetch('/api/monitoring/stop', { method: 'POST' });
                monitoring = false;
                button.innerHTML = '▶️ Start Monitor';
                button.className = 'btn btn-success';
                document.getElementById('monitoringStatus').textContent = 'Stopped';
            } else {
                // Start monitoring
                await fetch('/api/monitoring/start', { method: 'POST' });
                monitoring = true;
                button.innerHTML = '⏹️ Stop Monitor';
                button.className = 'btn btn-danger';
                document.getElementById('monitoringStatus').textContent = 'Running';
            }
        }
        
        function updateLastUpdate() {
            document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
        }
        
        function renderTopology() {
            const svg = d3.select('#topologySvg');
            svg.selectAll('*').remove();
            
            if (!topology.nodes.length) {
                svg.append('text')
                    .attr('x', '50%')
                    .attr('y', '50%')
                    .attr('text-anchor', 'middle')
                    .attr('dominant-baseline', 'middle')
                    .style('font-size', '18px')
                    .style('fill', '#6c757d')
                    .text('No topology data available. Run discovery first.');
                return;
            }
            
            const width = svg.node().clientWidth;
            const height = svg.node().clientHeight;
            console.log('SVG dimensions:', width, 'x', height);
            console.log('Topology nodes before positioning:', topology.nodes.map(n => ({id: n.id, type: n.type, label: n.label})));
            
            // Set SVG attributes explicitly
            svg.attr('viewBox', `0 0 ${width} ${height}`)
               .attr('preserveAspectRatio', 'xMidYMid meet')
               .style('overflow', 'visible');
            
            // Ensure minimum dimensions
            const minWidth = 600;
            const minHeight = 400;
            const actualWidth = Math.max(width, minWidth);
            const actualHeight = Math.max(height, minHeight);
            console.log('Using dimensions:', actualWidth, 'x', actualHeight);
            
            // Option 1: Use static positioning to completely eliminate flicker
            const useStaticLayout = topology.nodes.length <= 5; // Use static for small topologies
            console.log('Using static layout:', useStaticLayout, 'for', topology.nodes.length, 'nodes');
            
            if (useStaticLayout) {
                // Position nodes in a simple pattern
                topology.nodes.forEach((node, i) => {
                    if (node.type === 'switch' || node.type === 'virtual_switch') {
                        node.x = actualWidth / 2;
                        node.y = actualHeight / 2;
                        console.log('Positioned switch', node.id, 'at', node.x, node.y);
                    } else {
                        // Position hosts in a circle around the switch
                        const hostCount = topology.nodes.filter(n => n.type !== 'switch' && n.type !== 'virtual_switch').length;
                        const hostIndex = topology.nodes.slice(0, i).filter(n => n.type !== 'switch' && n.type !== 'virtual_switch').length;
                        const angle = (hostIndex * 2 * Math.PI) / hostCount;
                        const radius = Math.min(actualWidth, actualHeight) * 0.3;
                        node.x = actualWidth / 2 + radius * Math.cos(angle);
                        node.y = actualHeight / 2 + radius * Math.sin(angle);
                        console.log('Positioned host', node.id, 'at', node.x, node.y, 'angle:', angle);
                    }
                });
                
                // No simulation needed for static layout
                simulation = null;
                console.log('All nodes positioned:', topology.nodes.map(n => ({id: n.id, x: n.x, y: n.y, fx: n.fx, fy: n.fy})));
            } else {
                // Use force simulation with anti-flicker settings
                simulation = d3.forceSimulation(topology.nodes)
                    .force('link', d3.forceLink(topology.links).id(d => d.id).distance(100).strength(0.5))
                    .force('charge', d3.forceManyBody().strength(-100))
                    .force('center', d3.forceCenter(width / 2, height / 2))
                    .force('collision', d3.forceCollide().radius(30))
                    .alphaTarget(0)
                    .alphaDecay(0.05)
                    .velocityDecay(0.8);
                
                // Stop simulation more aggressively to prevent flicker
                let tickCount = 0;
                const maxTicks = 100;
                
                simulation.on('tick', () => {
                    tickCount++;
                    
                    link
                        .attr('x1', d => d.source.x)
                        .attr('y1', d => d.source.y)
                        .attr('x2', d => d.target.x)
                        .attr('y2', d => d.target.y);
                    
                    node
                        .attr('transform', d => `translate(${d.x},${d.y})`);
                    
                    // Stop simulation after max ticks or when energy is low
                    if (tickCount > maxTicks || simulation.alpha() < 0.01) {
                        simulation.stop();
                    }
                });
                
                // Force stop after 2 seconds regardless
                setTimeout(() => {
                    if (simulation) {
                        simulation.stop();
                    }
                }, 2000);
            }

            
            // Add links
            const link = svg.append('g')
                .attr('class', 'links')
                .selectAll('line')
                .data(topology.links)
                .enter().append('line')
                .attr('class', d => `link link-${d.type}`)
                .attr('data-link', d => {
                    const s = (d.source && d.source.id) ? d.source.id : d.source;
                    const t = (d.target && d.target.id) ? d.target.id : d.target;
                    return `${s}-${t}`;
                })
                .on('click', function(event, d) {
                    // Prevent node click handlers from firing
                    event.stopPropagation();
                    selectLink(d);
                });
            
            // Add nodes - use direct positioning instead of transform groups
            const nodeCircles = svg.append('g')
                .attr('class', 'nodes')
                .selectAll('circle')
                .data(topology.nodes)
                .enter().append('circle')
                .attr('class', d => `node node-${d.type}`)
                .attr('data-device', d => d.id)
                .attr('cx', d => d.x)
                .attr('cy', d => d.y)
                .attr('r', 25)
                .style('fill', d => d.type === 'switch' || d.type === 'virtual_switch' ? '#667eea' : '#28a745')
                .style('stroke', '#333')
                .style('stroke-width', '2px')
                .style('opacity', '1')
                .style('cursor', 'pointer')
                .on('click', function(event, d) {
                    event.stopPropagation();
                    selectDevice(d.id);
                });
            
            // Add node labels directly positioned
            const nodeLabels = svg.append('g')
                .attr('class', 'node-labels')
                .selectAll('text')
                .data(topology.nodes)
                .enter().append('text')
                .attr('class', 'node-text')
                .attr('x', d => d.x)
                .attr('y', d => d.y)
                .attr('dy', '.35em')
                .style('text-anchor', 'middle')
                .style('dominant-baseline', 'middle')
                .style('fill', 'white')
                .style('font-size', '12px')
                .style('font-weight', 'bold')
                .style('pointer-events', 'none')
                .text(d => d.label.length > 10 ? d.label.substring(0, 8) + '...' : d.label);
            
            // Only add drag behavior if NOT using static layout
            if (!useStaticLayout) {
                nodeCircles.call(d3.drag()
                    .on('start', dragstarted)
                    .on('drag', dragged)
                    .on('end', dragended));
            }
            
            console.log('Created', nodeCircles.size(), 'node circles with direct positioning');
            console.log('Created', nodeLabels.size(), 'node labels with direct positioning');
            
            // For static layout, positioning is already applied via cx/cy attributes
            if (useStaticLayout) {
                // Fix all node positions permanently
                topology.nodes.forEach(node => {
                    node.fx = node.x;  // Fix X position
                    node.fy = node.y;  // Fix Y position
                });
                
                // Position links by finding the actual node objects
                link
                    .attr('x1', d => {
                        const sourceNode = topology.nodes.find(n => n.id === (d.source.id || d.source));
                        return sourceNode ? sourceNode.x : actualWidth/2;
                    })
                    .attr('y1', d => {
                        const sourceNode = topology.nodes.find(n => n.id === (d.source.id || d.source));
                        return sourceNode ? sourceNode.y : actualHeight/2;
                    })
                    .attr('x2', d => {
                        const targetNode = topology.nodes.find(n => n.id === (d.target.id || d.target));
                        return targetNode ? targetNode.x : actualWidth/2;
                    })
                    .attr('y2', d => {
                        const targetNode = topology.nodes.find(n => n.id === (d.target.id || d.target));
                        return targetNode ? targetNode.y : actualHeight/2;
                    });
                    
                console.log('Static positioning applied - nodes should not move');
                
                // Debug: Check actual DOM elements
                console.log('Node elements in DOM:');
                nodeCircles.each(function(d, i) {
                    const element = d3.select(this);
                    const cx = element.attr('cx');
                    const cy = element.attr('cy');
                    const circleClass = element.attr('class');
                    const circleStyle = element.style('fill');
                    console.log(`Node ${d.id}: cx=${cx}, cy=${cy}, class=${circleClass}, fill=${circleStyle}`);
                });
            }

            // Preserve selection when re-rendering
            if (selectedDevice) {
                try { d3.selectAll(`[data-device="${selectedDevice}"]`).classed('selected', true); } catch(e) {}
            }
            if (selectedLink) {
                try { d3.selectAll(`[data-link="${selectedLink}"]`).classed('selected', true); } catch(e) {}
            }
            
            function dragstarted(event, d) {
                if (useStaticLayout) {
                    // Completely disable drag in static layout
                    event.sourceEvent.preventDefault();
                    return;
                }
                if (simulation && !event.active) simulation.alphaTarget(0.1).restart();
                d.fx = d.x;
                d.fy = d.y;
                // Stop simulation quickly after drag
                if (simulation) setTimeout(() => simulation.alphaTarget(0), 500);
            }
            
            function dragged(event, d) {
                if (useStaticLayout) {
                    // Completely disable drag in static layout
                    event.sourceEvent.preventDefault();
                    return;
                }
                d.fx = event.x;
                d.fy = event.y;
                d.x = event.x;
                d.y = event.y;
                
                // Update circle position
                d3.select(this).attr('cx', d.x).attr('cy', d.y);
                
                // Update label position
                svg.selectAll('.node-text').filter(function(td) { return td.id === d.id; })
                   .attr('x', d.x).attr('y', d.y);
                
                // Update connected links
                link
                    .attr('x1', l => {
                        const sourceNode = topology.nodes.find(n => n.id === l.source);
                        return sourceNode ? sourceNode.x : actualWidth/2;
                    })
                    .attr('y1', l => {
                        const sourceNode = topology.nodes.find(n => n.id === l.source);
                        return sourceNode ? sourceNode.y : actualHeight/2;
                    })
                    .attr('x2', l => {
                        const targetNode = topology.nodes.find(n => n.id === l.target);
                        return targetNode ? targetNode.x : actualWidth/2;
                    })
                    .attr('y2', l => {
                        const targetNode = topology.nodes.find(n => n.id === l.target);
                        return targetNode ? targetNode.y : actualHeight/2;
                    });
            }
            
            function dragended(event, d) {
                if (useStaticLayout) {
                    // Completely disable drag in static layout
                    event.sourceEvent.preventDefault();
                    return;
                }
                if (simulation && !event.active) simulation.alphaTarget(0);
                // Keep node fixed after dragging to prevent continued movement
                d.fx = event.x;
                d.fy = event.y;
                d.x = event.x;
                d.y = event.y;
            }
        }

        // Selected link id (format: "source-target")
        let selectedLink = null;

        function selectLink(linkData) {
            // Normalize link id
            const s = (linkData.source && linkData.source.id) ? linkData.source.id : linkData.source;
            const t = (linkData.target && linkData.target.id) ? linkData.target.id : linkData.target;
            const linkId = `${s}-${t}`;

            // Clear node selection
            selectedDevice = null;
            document.querySelectorAll('.device-item').forEach(item => item.classList.remove('selected'));
            d3.selectAll('.node').classed('selected', false);

            // Toggle link selection
            if (selectedLink === linkId) {
                // Deselect
                selectedLink = null;
                d3.selectAll('.link').classed('selected', false);
                document.getElementById('deviceStats').style.display = 'none';
                return;
            }

            selectedLink = linkId;
            d3.selectAll('.link').classed('selected', false);
            d3.selectAll(`[data-link="${linkId}"]`).classed('selected', true);

            // Show link details in stats panel
            const linkInfo = {
                id: linkId,
                type: linkData.type || 'link',
                source: (linkData.source && linkData.source.label) ? linkData.source.label : (linkData.source && linkData.source.id) ? linkData.source.id : String(linkData.source),
                target: (linkData.target && linkData.target.label) ? linkData.target.label : (linkData.target && linkData.target.id) ? linkData.target.id : String(linkData.target),
                bandwidth: linkData.bandwidth || 'Unknown',
                metadata: linkData
            };

            // Populate stats panel with link details
            const statsTitle = document.getElementById('statsTitle');
            const statsSubtitle = document.getElementById('statsSubtitle');
            const statsGrid = document.getElementById('statsGrid');
            const interfaceList = document.getElementById('interfaceList');

            statsTitle.textContent = `Link: ${linkInfo.source} ↔ ${linkInfo.target}`;
            statsSubtitle.textContent = `${linkInfo.type} | ${linkInfo.bandwidth}`;

            statsGrid.innerHTML = `
                <div class="stat-item">
                    <div class="stat-label">Source Device</div>
                    <div class="stat-value">${linkInfo.source}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Target Device</div>
                    <div class="stat-value">${linkInfo.target}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Link Type</div>
                    <div class="stat-value">${linkInfo.type}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Bandwidth</div>
                    <div class="stat-value">${linkInfo.bandwidth}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Status</div>
                    <div class="stat-value" style="color: #28a745;">Active</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Protocol</div>
                    <div class="stat-value">Ethernet</div>
                </div>
            `;

            interfaceList.innerHTML = `
                <h4>Link Configuration</h4>
                <div class="interface-item">
                    <div class="interface-name">Connection Details</div>
                    <div class="interface-stats">
                        Source: ${devices[linkData.source] ? devices[linkData.source].system_name : linkData.source}<br>
                        Target: ${devices[linkData.target] ? devices[linkData.target].system_name : linkData.target}<br>
                        Type: ${linkInfo.type}<br>
                        Bandwidth: ${linkInfo.bandwidth}
                    </div>
                </div>
                <h4>Raw Link Data</h4>
                <pre style="white-space:pre-wrap;word-break:break-word;font-size:11px;background:#f8f9fa;padding:10px;border-radius:4px;">${JSON.stringify(linkData, null, 2)}</pre>
            `;
            document.getElementById('deviceStats').style.display = 'block';
        }
        
        // Initialize
        window.addEventListener('resize', () => {
            if (simulation) {
                const svg = d3.select('#topologySvg');
                const width = svg.node().clientWidth;
                const height = svg.node().clientHeight;
                simulation.force('center', d3.forceCenter(width / 2, height / 2));
                simulation.alpha(0.3).restart();
            }
        });
        
        // Load initial data
        refreshTopology();
    </script>
</body>
</html>'''
    
    with open(os.path.join(template_dir, 'nms_dashboard.html'), 'w') as f:
        f.write(html_content)

def main():
    """Main function to run the NMS web interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Network Management System - Web Interface')
    parser.add_argument('--port', type=int, default=5000, help='Web server port (default: 5000)')
    parser.add_argument('--host', default='0.0.0.0', help='Web server host (default: 0.0.0.0)')
    parser.add_argument('--community', default='public', help='Default SNMP community')
    
    args = parser.parse_args()
    
    # Set default SNMP community
    nms.discovery.community = args.community
    
    # Create dashboard template
    create_nms_template()
    
    print("🚀 Starting Network Management System...")
    print(f"   Web Interface: http://localhost:{args.port}")
    print(f"   SNMP Community: {args.community}")
    print("   Features:")
    print("     - 🔍 Network Discovery")
    print("     - 🗺️  Topology Visualization") 
    print("     - 📊 Real-time Monitoring")
    print("     - 📱 Device Management")
    print("   Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        socketio.run(app, host=args.host, port=args.port, debug=False)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down NMS...")
        nms.stop_monitoring()

if __name__ == '__main__':
    main()