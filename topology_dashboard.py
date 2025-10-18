#!/usr/bin/env python3
"""
Interactive Network Topology Dashboard
Displays visual network topology with clickable elements showing statistics
"""

import time
import json
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
from simple_snmp_monitor import SimpleSnmpMonitor
import signal
import sys
import os
import re

app = Flask(__name__)

class TopologyDashboard:
    def __init__(self, snmp_host='localhost', snmp_community='public'):
        self.monitor = SimpleSnmpMonitor(snmp_host, snmp_community)
        self.current_data = {}
        self.historical_data = []
        self.monitoring = False
        self.monitor_thread = None
        self.max_history_points = 100
        self.topology_cache = {}
        
    def start_monitoring(self, interval=5):
        """Start the monitoring thread"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        print(f"Started monitoring with {interval}s interval")
        
    def stop_monitoring(self):
        """Stop the monitoring thread"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        print("Monitoring stopped")
    
    def _monitor_loop(self, interval):
        """Main monitoring loop with topology detection"""
        previous_stats = None
        previous_time = None
        
        while self.monitoring:
            try:
                current_time = time.time()
                
                # Get current system and interface data
                system_info = self.monitor.get_system_info()
                interfaces = self.monitor.get_interfaces()
                current_stats = self.monitor.get_interface_stats()
                
                # Build topology information
                topology = self.build_topology(interfaces, current_stats)
                
                # Calculate rates if we have previous data
                rates = {}
                if previous_stats and previous_time:
                    time_diff = current_time - previous_time
                    if time_diff > 0:
                        for index in current_stats.keys():
                            if index in previous_stats:
                                curr = current_stats[index]
                                prev = previous_stats[index]
                                
                                in_rate = max(0, (curr['in_octets'] - prev['in_octets']) / time_diff)
                                out_rate = max(0, (curr['out_octets'] - prev['out_octets']) / time_diff)
                                in_pps = max(0, (curr['in_packets'] - prev['in_packets']) / time_diff)
                                out_pps = max(0, (curr['out_packets'] - prev['out_packets']) / time_diff)
                                
                                rates[index] = {
                                    'in_bps': in_rate,
                                    'out_bps': out_rate,
                                    'in_mbps': in_rate * 8 / 1000000,
                                    'out_mbps': out_rate * 8 / 1000000,
                                    'in_pps': in_pps,
                                    'out_pps': out_pps
                                }
                
                # Prepare dashboard data
                dashboard_data = {
                    'timestamp': datetime.now().isoformat(),
                    'system_info': system_info,
                    'topology': topology,
                    'interfaces': [],
                    'rates': rates
                }
                
                # Process interfaces with enhanced data
                for index in sorted(interfaces.keys(), key=int):
                    interface = interfaces[index]
                    stats = current_stats.get(index, {})
                    rate = rates.get(index, {})
                    
                    interface_data = {
                        'index': int(index),
                        'name': interface['name'],
                        'admin_status': interface['admin_status_text'],
                        'oper_status': interface['oper_status_text'],
                        'speed': interface['speed'],
                        'in_octets': stats.get('in_octets', 0),
                        'out_octets': stats.get('out_octets', 0),
                        'in_packets': stats.get('in_packets', 0),
                        'out_packets': stats.get('out_packets', 0),
                        'in_bps': rate.get('in_bps', 0),
                        'out_bps': rate.get('out_bps', 0),
                        'in_mbps': rate.get('in_mbps', 0),
                        'out_mbps': rate.get('out_mbps', 0),
                        'in_pps': rate.get('in_pps', 0),
                        'out_pps': rate.get('out_pps', 0)
                    }
                    dashboard_data['interfaces'].append(interface_data)
                
                # Store current data
                self.current_data = dashboard_data
                
                # Add to historical data
                self.historical_data.append(dashboard_data)
                if len(self.historical_data) > self.max_history_points:
                    self.historical_data.pop(0)
                
                # Store for next iteration
                previous_stats = current_stats.copy()
                previous_time = current_time
                
                time.sleep(interval)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(interval)
    
    def build_topology(self, interfaces, stats):
        """Build network topology from interface data"""
        nodes = []
        links = []
        
        # Identify different types of interfaces and create nodes
        switches = set()
        hosts = set()
        
        for index, interface in interfaces.items():
            name = interface['name']
            
            # Identify switches (s1, s2, etc.)
            if re.match(r's\d+', name):
                switch_name = name.split('-')[0] if '-' in name else name
                switches.add(switch_name)
            
            # Identify host interfaces (h1, h2, etc.)
            elif re.match(r'h\d+', name):
                host_name = name.split('-')[0] if '-' in name else name
                hosts.add(host_name)
            
            # Identify switch-to-switch or switch-to-host connections
            elif re.match(r's\d+-eth\d+', name):
                switch_name = name.split('-')[0]
                switches.add(switch_name)
        
        # Add switch nodes
        for switch in sorted(switches):
            switch_interfaces = [iface for idx, iface in interfaces.items() 
                               if iface['name'].startswith(switch)]
            
            total_traffic = sum(stats.get(idx, {}).get('in_octets', 0) + 
                              stats.get(idx, {}).get('out_octets', 0) 
                              for idx, iface in interfaces.items() 
                              if iface['name'].startswith(switch))
            
            nodes.append({
                'id': switch,
                'type': 'switch',
                'label': switch,
                'interfaces': len(switch_interfaces),
                'traffic': total_traffic,
                'status': 'up' if any(iface['oper_status_text'] == 'up' for iface in switch_interfaces) else 'down'
            })
        
        # Add host nodes  
        for host in sorted(hosts):
            host_interfaces = [iface for idx, iface in interfaces.items() 
                             if iface['name'].startswith(host)]
            
            total_traffic = sum(stats.get(idx, {}).get('in_octets', 0) + 
                              stats.get(idx, {}).get('out_octets', 0) 
                              for idx, iface in interfaces.items() 
                              if iface['name'].startswith(host))
            
            nodes.append({
                'id': host,
                'type': 'host',
                'label': host,
                'interfaces': len(host_interfaces),
                'traffic': total_traffic,
                'status': 'up' if any(iface['oper_status_text'] == 'up' for iface in host_interfaces) else 'down'
            })
        
        # Create links based on interface patterns
        processed_links = set()
        
        for index, interface in interfaces.items():
            name = interface['name']
            
            # Link pattern: s1-eth1 connects to something
            if re.match(r's\d+-eth\d+', name):
                switch_name = name.split('-')[0]
                port_num = name.split('eth')[1]
                
                # Try to find corresponding connection
                # This is a simplified heuristic - in real networks you'd need more sophisticated discovery
                link_id = f"{switch_name}-eth{port_num}"
                
                if link_id not in processed_links:
                    # Determine target based on common patterns
                    target = None
                    if port_num == '1':
                        target = f"h{switch_name[1:]}"  # s1-eth1 -> h1
                    elif port_num == '2':
                        target = f"h{int(switch_name[1:]) + 1}"  # s1-eth2 -> h2
                    else:
                        # Inter-switch links
                        target = f"s{int(port_num)}" if int(port_num) <= 3 else None
                    
                    if target and any(node['id'] == target for node in nodes):
                        link_stats = stats.get(index, {})
                        
                        links.append({
                            'source': switch_name,
                            'target': target,
                            'id': link_id,
                            'interface': name,
                            'traffic_in': link_stats.get('in_octets', 0),
                            'traffic_out': link_stats.get('out_octets', 0),
                            'packets_in': link_stats.get('in_packets', 0),
                            'packets_out': link_stats.get('out_packets', 0),
                            'status': interface['oper_status_text'],
                            'speed': interface['speed']
                        })
                        
                        processed_links.add(link_id)
        
        return {'nodes': nodes, 'links': links}
    
    def get_current_data(self):
        """Get current monitoring data"""
        return self.current_data if self.current_data else {'interfaces': [], 'system_info': {}, 'topology': {'nodes': [], 'links': []}}
    
    def get_node_details(self, node_id):
        """Get detailed information for a specific node"""
        if not self.current_data:
            return None
            
        # Find interfaces belonging to this node
        node_interfaces = []
        for interface in self.current_data.get('interfaces', []):
            if interface['name'].startswith(node_id):
                node_interfaces.append(interface)
        
        return {
            'id': node_id,
            'interfaces': node_interfaces,
            'total_interfaces': len(node_interfaces),
            'total_traffic_in': sum(iface['in_octets'] for iface in node_interfaces),
            'total_traffic_out': sum(iface['out_octets'] for iface in node_interfaces),
            'total_rate_in': sum(iface['in_mbps'] for iface in node_interfaces),
            'total_rate_out': sum(iface['out_mbps'] for iface in node_interfaces)
        }
    
    def get_link_details(self, link_id):
        """Get detailed information for a specific link"""
        if not self.current_data:
            return None
            
        # Find the interface corresponding to this link
        for interface in self.current_data.get('interfaces', []):
            if interface['name'] == link_id or link_id in interface['name']:
                return interface
        
        return None

# Global dashboard instance
dashboard = None

@app.route('/')
def index():
    """Main dashboard page with topology"""
    return render_template('topology_dashboard.html')

@app.route('/api/current')
def api_current():
    """API endpoint for current data"""
    if dashboard:
        return jsonify(dashboard.get_current_data())
    return jsonify({'error': 'Dashboard not initialized'})

@app.route('/api/topology')
def api_topology():
    """API endpoint for topology data"""
    if dashboard and dashboard.current_data:
        return jsonify(dashboard.current_data.get('topology', {'nodes': [], 'links': []}))
    return jsonify({'nodes': [], 'links': []})

@app.route('/api/node/<node_id>')
def api_node_details(node_id):
    """API endpoint for node details"""
    if dashboard:
        details = dashboard.get_node_details(node_id)
        if details:
            return jsonify(details)
    return jsonify({'error': 'Node not found'})

@app.route('/api/link/<path:link_id>')
def api_link_details(link_id):
    """API endpoint for link details"""
    if dashboard:
        details = dashboard.get_link_details(link_id)
        if details:
            return jsonify(details)
    return jsonify({'error': 'Link not found'})

@app.route('/api/historical/<int:minutes>')
def api_historical(minutes):
    """API endpoint for historical data"""
    if dashboard:
        historical_data = []
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        for data_point in dashboard.historical_data:
            try:
                data_time = datetime.fromisoformat(data_point['timestamp'])
                if data_time >= cutoff_time:
                    historical_data.append(data_point)
            except:
                continue
        
        return jsonify(historical_data)
    return jsonify([])

def create_topology_template():
    """Create the HTML template for the topology dashboard"""
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(template_dir, exist_ok=True)
    
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Network Topology Monitor</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            height: 100vh;
            overflow: hidden;
        }
        
        .dashboard {
            display: grid;
            grid-template-columns: 1fr 400px;
            grid-template-rows: auto 1fr;
            height: 100vh;
            gap: 10px;
            padding: 10px;
        }
        
        .header {
            grid-column: 1 / -1;
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            padding: 15px 25px;
            border-radius: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            color: #667eea;
            font-size: 1.8em;
            font-weight: 600;
        }
        
        .status-info {
            display: flex;
            align-items: center;
            gap: 15px;
            font-size: 0.9em;
        }
        
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #4CAF50;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .topology-container {
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 20px;
            overflow: hidden;
            position: relative;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        
        .sidebar {
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 20px;
            overflow-y: auto;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        
        .topology-svg {
            width: 100%;
            height: 100%;
            border-radius: 8px;
        }
        
        /* Node styles */
        .node {
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .node:hover {
            transform: scale(1.1);
        }
        
        .node.switch {
            fill: #667eea;
            stroke: #5a6fd8;
            stroke-width: 3;
        }
        
        .node.host {
            fill: #4CAF50;
            stroke: #45a049;
            stroke-width: 3;
        }
        
        .node.selected {
            stroke: #ff6b6b;
            stroke-width: 4;
            filter: drop-shadow(0 0 10px rgba(255,107,107,0.6));
        }
        
        /* Link styles */
        .link {
            stroke: #999;
            stroke-width: 2;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .link:hover {
            stroke: #667eea;
            stroke-width: 4;
        }
        
        .link.selected {
            stroke: #ff6b6b;
            stroke-width: 4;
        }
        
        .link.high-traffic {
            stroke: #ff9800;
            stroke-width: 3;
        }
        
        /* Text styles */
        .node-label {
            fill: white;
            font-size: 12px;
            font-weight: bold;
            text-anchor: middle;
            pointer-events: none;
        }
        
        .link-label {
            fill: #666;
            font-size: 10px;
            text-anchor: middle;
            pointer-events: none;
        }
        
        /* Details panel */
        .details-panel {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            border-left: 4px solid #667eea;
        }
        
        .details-title {
            font-size: 1.3em;
            font-weight: 600;
            margin-bottom: 15px;
            color: #333;
        }
        
        .metric-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            padding: 5px 0;
            border-bottom: 1px solid #eee;
        }
        
        .metric-label {
            font-weight: 500;
            color: #666;
        }
        
        .metric-value {
            font-weight: 600;
            color: #333;
        }
        
        /* Statistics panel */
        .stats-panel {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
        }
        
        .stats-title {
            font-size: 1.1em;
            font-weight: 600;
            margin-bottom: 10px;
            color: #667eea;
        }
        
        /* Legend */
        .legend {
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(255,255,255,0.9);
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            margin-bottom: 8px;
            font-size: 0.9em;
        }
        
        .legend-color {
            width: 16px;
            height: 16px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        /* Controls */
        .controls {
            margin-bottom: 20px;
        }
        
        .btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            margin-right: 8px;
            font-size: 0.9em;
            transition: background 0.3s ease;
        }
        
        .btn:hover {
            background: #5a6fd8;
        }
        
        /* Responsive design */
        @media (max-width: 1024px) {
            .dashboard {
                grid-template-columns: 1fr;
                grid-template-rows: auto 1fr 300px;
            }
            
            .sidebar {
                height: 300px;
            }
        }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>🌐 Network Topology Monitor</h1>
            <div class="status-info">
                <div class="status-dot" id="statusDot"></div>
                <span id="statusText">Connecting...</span>
                <span>|</span>
                <span>Last Update: <span id="lastUpdate">Never</span></span>
            </div>
        </div>
        
        <div class="topology-container">
            <svg class="topology-svg" id="topologySvg"></svg>
            
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background: #667eea;"></div>
                    <span>Switch</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #4CAF50;"></div>
                    <span>Host</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #ff9800;"></div>
                    <span>High Traffic Link</span>
                </div>
            </div>
        </div>
        
        <div class="sidebar">
            <div class="controls">
                <button class="btn" onclick="refreshTopology()">🔄 Refresh</button>
                <button class="btn" onclick="resetView()">🏠 Reset View</button>
                <button class="btn" onclick="toggleAutoRefresh()" id="autoRefreshBtn">⏹️ Stop Auto</button>
            </div>
            
            <div class="stats-panel">
                <div class="stats-title">📊 Network Overview</div>
                <div id="networkStats">
                    <div class="metric-row">
                        <span class="metric-label">Nodes:</span>
                        <span class="metric-value" id="nodeCount">-</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Links:</span>
                        <span class="metric-value" id="linkCount">-</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Total Traffic:</span>
                        <span class="metric-value" id="totalTraffic">-</span>
                    </div>
                </div>
            </div>
            
            <div class="details-panel" id="detailsPanel" style="display: none;">
                <div class="details-title" id="detailsTitle">Select a node or link</div>
                <div id="detailsContent"></div>
            </div>
        </div>
    </div>

    <script>
        let topology = { nodes: [], links: [] };
        let simulation;
        let autoRefresh = true;
        let refreshTimer;
        const refreshInterval = 5000;

        // Initialize D3 force simulation
        function initTopology() {
            const svg = d3.select("#topologySvg");
            const width = svg.node().getBoundingClientRect().width;
            const height = svg.node().getBoundingClientRect().height;

            // Clear existing content
            svg.selectAll("*").remove();

            // Create groups for links and nodes
            const linkGroup = svg.append("g").attr("class", "links");
            const nodeGroup = svg.append("g").attr("class", "nodes");
            const labelGroup = svg.append("g").attr("class", "labels");

            // Set up force simulation
            simulation = d3.forceSimulation()
                .force("link", d3.forceLink().id(d => d.id).distance(150))
                .force("charge", d3.forceManyBody().strength(-300))
                .force("center", d3.forceCenter(width / 2, height / 2))
                .force("collision", d3.forceCollide().radius(40));

            updateTopology();
        }

        function updateTopology() {
            if (!topology.nodes.length) return;

            const svg = d3.select("#topologySvg");
            const width = svg.node().getBoundingClientRect().width;
            const height = svg.node().getBoundingClientRect().height;

            // Update links
            const links = svg.select(".links")
                .selectAll(".link")
                .data(topology.links, d => d.id);

            links.enter()
                .append("line")
                .attr("class", "link")
                .style("stroke-width", d => Math.max(2, Math.log(d.traffic_in + d.traffic_out + 1)))
                .classed("high-traffic", d => (d.traffic_in + d.traffic_out) > 1000000)
                .on("click", handleLinkClick)
                .merge(links);

            links.exit().remove();

            // Update nodes
            const nodes = svg.select(".nodes")
                .selectAll(".node")
                .data(topology.nodes, d => d.id);

            const nodeEnter = nodes.enter()
                .append("circle")
                .attr("class", d => `node ${d.type}`)
                .attr("r", d => d.type === 'switch' ? 25 : 20)
                .on("click", handleNodeClick)
                .call(d3.drag()
                    .on("start", dragStarted)
                    .on("drag", dragged)
                    .on("end", dragEnded));

            nodeEnter.merge(nodes);
            nodes.exit().remove();

            // Update labels
            const labels = svg.select(".labels")
                .selectAll(".node-label")
                .data(topology.nodes, d => d.id);

            labels.enter()
                .append("text")
                .attr("class", "node-label")
                .text(d => d.label)
                .merge(labels);

            labels.exit().remove();

            // Update simulation
            simulation.nodes(topology.nodes);
            simulation.force("link").links(topology.links);
            simulation.alpha(0.3).restart();

            // Update positions
            simulation.on("tick", () => {
                svg.selectAll(".link")
                    .attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);

                svg.selectAll(".node")
                    .attr("cx", d => Math.max(25, Math.min(width - 25, d.x)))
                    .attr("cy", d => Math.max(25, Math.min(height - 25, d.y)));

                svg.selectAll(".node-label")
                    .attr("x", d => Math.max(25, Math.min(width - 25, d.x)))
                    .attr("y", d => Math.max(25, Math.min(height - 25, d.y + 5)));
            });

            updateNetworkStats();
        }

        function handleNodeClick(event, d) {
            // Clear previous selections
            d3.selectAll(".node").classed("selected", false);
            d3.selectAll(".link").classed("selected", false);

            // Select clicked node
            d3.select(event.target).classed("selected", true);

            // Fetch and display node details
            fetch(`/api/node/${d.id}`)
                .then(response => response.json())
                .then(data => displayNodeDetails(data))
                .catch(error => console.error('Error fetching node details:', error));
        }

        function handleLinkClick(event, d) {
            // Clear previous selections
            d3.selectAll(".node").classed("selected", false);
            d3.selectAll(".link").classed("selected", false);

            // Select clicked link
            d3.select(event.target).classed("selected", true);

            // Fetch and display link details
            fetch(`/api/link/${d.interface}`)
                .then(response => response.json())
                .then(data => displayLinkDetails(data))
                .catch(error => console.error('Error fetching link details:', error));
        }

        function displayNodeDetails(data) {
            const panel = document.getElementById('detailsPanel');
            const title = document.getElementById('detailsTitle');
            const content = document.getElementById('detailsContent');

            title.textContent = `${data.id.toUpperCase()} Details`;
            
            content.innerHTML = `
                <div class="metric-row">
                    <span class="metric-label">Type:</span>
                    <span class="metric-value">${data.id.startsWith('s') ? 'Switch' : 'Host'}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Interfaces:</span>
                    <span class="metric-value">${data.total_interfaces}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Traffic In:</span>
                    <span class="metric-value">${formatBytes(data.total_traffic_in)}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Traffic Out:</span>
                    <span class="metric-value">${formatBytes(data.total_traffic_out)}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Rate In:</span>
                    <span class="metric-value">${data.total_rate_in.toFixed(2)} Mbps</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Rate Out:</span>
                    <span class="metric-value">${data.total_rate_out.toFixed(2)} Mbps</span>
                </div>
            `;

            if (data.interfaces && data.interfaces.length > 0) {
                content.innerHTML += '<hr style="margin: 15px 0;"><strong>Interfaces:</strong>';
                data.interfaces.forEach(iface => {
                    content.innerHTML += `
                        <div style="margin: 10px 0; padding: 10px; background: #f0f0f0; border-radius: 4px;">
                            <strong>${iface.name}</strong><br>
                            Status: ${iface.oper_status} | 
                            Traffic: ${formatBytes(iface.in_octets)} / ${formatBytes(iface.out_octets)}<br>
                            Rate: ${iface.in_mbps.toFixed(2)} / ${iface.out_mbps.toFixed(2)} Mbps
                        </div>
                    `;
                });
            }

            panel.style.display = 'block';
        }

        function displayLinkDetails(data) {
            const panel = document.getElementById('detailsPanel');
            const title = document.getElementById('detailsTitle');
            const content = document.getElementById('detailsContent');

            title.textContent = `Link: ${data.name}`;
            
            content.innerHTML = `
                <div class="metric-row">
                    <span class="metric-label">Interface:</span>
                    <span class="metric-value">${data.name}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Status:</span>
                    <span class="metric-value">${data.oper_status}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Speed:</span>
                    <span class="metric-value">${data.speed} bps</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Traffic In:</span>
                    <span class="metric-value">${formatBytes(data.in_octets)}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Traffic Out:</span>
                    <span class="metric-value">${formatBytes(data.out_octets)}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Rate In:</span>
                    <span class="metric-value">${data.in_mbps.toFixed(2)} Mbps</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Rate Out:</span>
                    <span class="metric-value">${data.out_mbps.toFixed(2)} Mbps</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Packets In:</span>
                    <span class="metric-value">${data.in_packets}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Packets Out:</span>
                    <span class="metric-value">${data.out_packets}</span>
                </div>
            `;

            panel.style.display = 'block';
        }

        function updateNetworkStats() {
            document.getElementById('nodeCount').textContent = topology.nodes.length;
            document.getElementById('linkCount').textContent = topology.links.length;
            
            const totalTraffic = topology.links.reduce((sum, link) => 
                sum + link.traffic_in + link.traffic_out, 0);
            document.getElementById('totalTraffic').textContent = formatBytes(totalTraffic);
        }

        function formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        async function refreshTopology() {
            try {
                document.getElementById('statusText').textContent = 'Updating...';
                
                const response = await fetch('/api/topology');
                const data = await response.json();
                
                if (data.nodes && data.links) {
                    topology = data;
                    updateTopology();
                    document.getElementById('statusText').textContent = 'Connected';
                    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
                }
            } catch (error) {
                console.error('Error fetching topology:', error);
                document.getElementById('statusText').textContent = 'Error';
            }
        }

        function resetView() {
            if (simulation) {
                simulation.alpha(1).restart();
            }
            // Clear selections
            d3.selectAll(".node").classed("selected", false);
            d3.selectAll(".link").classed("selected", false);
            document.getElementById('detailsPanel').style.display = 'none';
        }

        function toggleAutoRefresh() {
            autoRefresh = !autoRefresh;
            const btn = document.getElementById('autoRefreshBtn');
            
            if (autoRefresh) {
                btn.textContent = '⏹️ Stop Auto';
                startAutoRefresh();
            } else {
                btn.textContent = '▶️ Start Auto';
                if (refreshTimer) clearInterval(refreshTimer);
            }
        }

        function startAutoRefresh() {
            if (refreshTimer) clearInterval(refreshTimer);
            refreshTimer = setInterval(refreshTopology, refreshInterval);
        }

        // Drag functions
        function dragStarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }

        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }

        function dragEnded(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }

        // Initialize when page loads
        window.onload = function() {
            initTopology();
            refreshTopology();
            if (autoRefresh) startAutoRefresh();
        };

        // Handle window resize
        window.onresize = function() {
            initTopology();
        };

        // Cleanup
        window.onbeforeunload = function() {
            if (refreshTimer) clearInterval(refreshTimer);
        };
    </script>
</body>
</html>'''
    
    with open(os.path.join(template_dir, 'topology_dashboard.html'), 'w') as f:
        f.write(html_content)

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print('\nShutting down topology dashboard...')
    if dashboard:
        dashboard.stop_monitoring()
    sys.exit(0)

def main():
    """Main function to run the topology dashboard"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Interactive Network Topology Dashboard')
    parser.add_argument('--host', default='localhost', help='SNMP host (default: localhost)')
    parser.add_argument('--community', default='public', help='SNMP community (default: public)')
    parser.add_argument('--port', type=int, default=5001, help='Web server port (default: 5001)')
    parser.add_argument('--interval', type=int, default=5, help='Monitoring interval in seconds (default: 5)')
    
    args = parser.parse_args()
    
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create template
    create_topology_template()
    
    # Test SNMP connectivity first
    test_monitor = SimpleSnmpMonitor(args.host, args.community)
    test_result = test_monitor.snmp_get('1.3.6.1.2.1.1.1.0')
    
    if not test_result:
        print("❌ Error: Cannot connect to SNMP agent")
        print("Please ensure SNMP daemon is running and accessible")
        sys.exit(1)
    
    print("✅ SNMP connection test successful")
    
    # Initialize dashboard
    global dashboard
    dashboard = TopologyDashboard(args.host, args.community)
    
    # Start monitoring
    dashboard.start_monitoring(args.interval)
    
    print(f"🚀 Starting Interactive Topology Dashboard...")
    print(f"   SNMP Host: {args.host}")
    print(f"   SNMP Community: {args.community}")
    print(f"   Monitoring Interval: {args.interval} seconds")
    print(f"   Web Interface: http://localhost:{args.port}")
    print("   Click on nodes and links to view detailed statistics")
    print("   Press Ctrl+C to stop")
    print("=" * 60)
    
    # Start web server
    try:
        app.run(host='0.0.0.0', port=args.port, debug=False)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == '__main__':
    main()