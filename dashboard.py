#!/usr/bin/env python3
"""
Real-time Network Monitoring Dashboard for Mininet SNMP
This script creates a web-based dashboard to visualize network statistics
"""

import time
import json
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify
from snmp_monitor import SNMPMonitor
import queue
import signal
import sys

app = Flask(__name__)

class NetworkDashboard:
    def __init__(self, snmp_host='localhost', snmp_community='public'):
        self.snmp_monitor = SNMPMonitor(snmp_host, snmp_community)
        self.data_queue = queue.Queue(maxsize=100)  # Store last 100 data points
        self.current_data = {}
        self.historical_data = []
        self.monitoring = False
        self.monitor_thread = None
        
    def start_monitoring(self, interval=5):
        """Start the monitoring thread"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop the monitoring thread"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
    
    def _monitor_loop(self, interval):
        """Main monitoring loop"""
        previous_stats = None
        previous_time = None
        
        while self.monitoring:
            try:
                current_time = time.time()
                
                # Get current data
                system_info = self.snmp_monitor.get_system_info()
                interface_info = self.snmp_monitor.get_interface_info()
                current_stats = self.snmp_monitor.get_interface_statistics()
                
                # Calculate rates if we have previous data
                rates = {}
                if previous_stats and previous_time:
                    time_diff = current_time - previous_time
                    rates = self.snmp_monitor.calculate_rates(current_stats, previous_stats, time_diff)
                
                # Prepare data for dashboard
                dashboard_data = {
                    'timestamp': datetime.now().isoformat(),
                    'system_info': system_info,
                    'interfaces': []
                }
                
                for index in sorted(interface_info.keys(), key=int):
                    interface = interface_info[index]
                    stats = current_stats.get(index, {})
                    rate = rates.get(index, {})
                    
                    interface_data = {
                        'index': index,
                        'name': interface['description'],
                        'admin_status': interface['admin_status_text'],
                        'oper_status': interface['oper_status_text'],
                        'speed': interface['speed'],
                        'in_octets': stats.get('in_octets', 0),
                        'out_octets': stats.get('out_octets', 0),
                        'in_packets': stats.get('in_packets', 0),
                        'out_packets': stats.get('out_packets', 0),
                        'in_errors': stats.get('in_errors', 0),
                        'out_errors': stats.get('out_errors', 0),
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
                
                # Add to historical data (keep last 100 points)
                self.historical_data.append(dashboard_data)
                if len(self.historical_data) > 100:
                    self.historical_data.pop(0)
                
                # Store for next iteration
                previous_stats = current_stats.copy()
                previous_time = current_time
                
                time.sleep(interval)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(interval)
    
    def get_current_data(self):
        """Get current monitoring data"""
        return self.current_data
    
    def get_historical_data(self, minutes=30):
        """Get historical data for specified minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        filtered_data = []
        for data_point in self.historical_data:
            data_time = datetime.fromisoformat(data_point['timestamp'])
            if data_time >= cutoff_time:
                filtered_data.append(data_point)
        
        return filtered_data

# Global dashboard instance
dashboard = NetworkDashboard()

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/current')
def api_current():
    """API endpoint for current data"""
    return jsonify(dashboard.get_current_data())

@app.route('/api/historical/<int:minutes>')
def api_historical(minutes):
    """API endpoint for historical data"""
    return jsonify(dashboard.get_historical_data(minutes))

@app.route('/api/status')
def api_status():
    """API endpoint for monitoring status"""
    return jsonify({
        'monitoring': dashboard.monitoring,
        'data_points': len(dashboard.historical_data),
        'last_update': dashboard.current_data.get('timestamp', None)
    })

def create_dashboard_template():
    """Create the HTML template for the dashboard"""
    template_dir = '/home/pavan/nms/templates'
    import os
    os.makedirs(template_dir, exist_ok=True)
    
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mininet SNMP Network Monitor</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .header { background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .system-info { background-color: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .interface-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }
        .interface-card { background-color: white; padding: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .interface-header { font-weight: bold; font-size: 1.1em; margin-bottom: 10px; padding-bottom: 5px; border-bottom: 2px solid #3498db; }
        .status-up { color: #27ae60; }
        .status-down { color: #e74c3c; }
        .metric { display: flex; justify-content: space-between; margin: 5px 0; }
        .metric-label { font-weight: bold; }
        .chart-container { background-color: white; padding: 20px; border-radius: 5px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .error { color: #e74c3c; text-align: center; padding: 20px; }
        .loading { text-align: center; padding: 20px; }
        .controls { background-color: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        button { background-color: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 3px; cursor: pointer; margin-right: 10px; }
        button:hover { background-color: #2980b9; }
        .refresh-indicator { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-left: 10px; }
        .refresh-active { background-color: #27ae60; }
        .refresh-inactive { background-color: #e74c3c; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Mininet SNMP Network Monitor</h1>
        <p>Real-time network interface monitoring dashboard</p>
        <span>Status: <span id="status">Connecting...</span></span>
        <span class="refresh-indicator" id="refreshIndicator"></span>
    </div>
    
    <div class="controls">
        <button onclick="refreshData()">Refresh Now</button>
        <button onclick="toggleAutoRefresh()" id="autoRefreshBtn">Stop Auto-refresh</button>
        <span>Auto-refresh: <span id="refreshInterval">5</span> seconds</span>
    </div>
    
    <div class="system-info" id="systemInfo">
        <div class="loading">Loading system information...</div>
    </div>
    
    <div class="chart-container">
        <h3>Network Traffic (Mbps)</h3>
        <canvas id="trafficChart"></canvas>
    </div>
    
    <div class="interface-grid" id="interfaceGrid">
        <div class="loading">Loading interface data...</div>
    </div>

    <script>
        let autoRefresh = true;
        let refreshTimer;
        let chart;
        const refreshInterval = 5000; // 5 seconds

        // Initialize chart
        function initChart() {
            const ctx = document.getElementById('trafficChart').getContext('2d');
            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: []
                },
                options: {
                    responsive: true,
                    animation: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Mbps'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: 'Time'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top'
                        }
                    }
                }
            });
        }

        // Update chart with new data
        function updateChart(historicalData) {
            if (!chart || !historicalData.length) return;

            const labels = [];
            const datasets = {};

            // Process historical data
            historicalData.forEach(dataPoint => {
                const time = new Date(dataPoint.timestamp).toLocaleTimeString();
                labels.push(time);

                dataPoint.interfaces.forEach(interface => {
                    if (interface.name.includes('lo')) return; // Skip loopback

                    const inKey = `${interface.name} In`;
                    const outKey = `${interface.name} Out`;

                    if (!datasets[inKey]) {
                        datasets[inKey] = {
                            label: inKey,
                            data: [],
                            borderColor: `hsl(${Object.keys(datasets).length * 60}, 70%, 50%)`,
                            backgroundColor: `hsla(${Object.keys(datasets).length * 60}, 70%, 50%, 0.1)`,
                            fill: false
                        };
                    }
                    if (!datasets[outKey]) {
                        datasets[outKey] = {
                            label: outKey,
                            data: [],
                            borderColor: `hsl(${Object.keys(datasets).length * 60}, 70%, 50%)`,
                            backgroundColor: `hsla(${Object.keys(datasets).length * 60}, 70%, 50%, 0.1)`,
                            fill: false
                        };
                    }

                    datasets[inKey].data.push(interface.in_mbps || 0);
                    datasets[outKey].data.push(interface.out_mbps || 0);
                });
            });

            // Keep only last 20 data points
            const maxPoints = 20;
            if (labels.length > maxPoints) {
                labels.splice(0, labels.length - maxPoints);
                Object.values(datasets).forEach(dataset => {
                    dataset.data.splice(0, dataset.data.length - maxPoints);
                });
            }

            chart.data.labels = labels;
            chart.data.datasets = Object.values(datasets);
            chart.update('none');
        }

        // Format bytes for display
        function formatBytes(bytes) {
            const units = ['B', 'KB', 'MB', 'GB'];
            let value = bytes;
            let unitIndex = 0;
            
            while (value >= 1024 && unitIndex < units.length - 1) {
                value /= 1024;
                unitIndex++;
            }
            
            return `${value.toFixed(2)} ${units[unitIndex]}`;
        }

        // Update interface display
        function updateInterfaces(data) {
            const grid = document.getElementById('interfaceGrid');
            
            if (!data.interfaces || data.interfaces.length === 0) {
                grid.innerHTML = '<div class="error">No interface data available</div>';
                return;
            }

            grid.innerHTML = '';
            
            data.interfaces.forEach(interface => {
                if (interface.name.includes('lo')) return; // Skip loopback

                const card = document.createElement('div');
                card.className = 'interface-card';
                
                const statusClass = interface.oper_status === 'up' ? 'status-up' : 'status-down';
                
                card.innerHTML = `
                    <div class="interface-header">${interface.name} (Index: ${interface.index})</div>
                    <div class="metric">
                        <span class="metric-label">Status:</span>
                        <span class="${statusClass}">${interface.admin_status}/${interface.oper_status}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Speed:</span>
                        <span>${interface.speed} bps</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Traffic In:</span>
                        <span>${formatBytes(interface.in_octets)} (${(interface.in_mbps || 0).toFixed(2)} Mbps)</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Traffic Out:</span>
                        <span>${formatBytes(interface.out_octets)} (${(interface.out_mbps || 0).toFixed(2)} Mbps)</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Packets In:</span>
                        <span>${interface.in_packets} (${(interface.in_pps || 0).toFixed(1)} pps)</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Packets Out:</span>
                        <span>${interface.out_packets} (${(interface.out_pps || 0).toFixed(1)} pps)</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Errors:</span>
                        <span>In: ${interface.in_errors}, Out: ${interface.out_errors}</span>
                    </div>
                `;
                
                grid.appendChild(card);
            });
        }

        // Update system information
        function updateSystemInfo(data) {
            const systemInfo = document.getElementById('systemInfo');
            
            if (!data.system_info) {
                systemInfo.innerHTML = '<div class="error">No system information available</div>';
                return;
            }

            const info = data.system_info;
            systemInfo.innerHTML = `
                <h3>System Information</h3>
                <div class="metric">
                    <span class="metric-label">System Name:</span>
                    <span>${info.system_name || 'Unknown'}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Uptime:</span>
                    <span>${info.uptime_formatted || 'Unknown'}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Interface Count:</span>
                    <span>${info.interface_count || 0}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Last Update:</span>
                    <span>${new Date(data.timestamp).toLocaleString()}</span>
                </div>
            `;
        }

        // Refresh data from server
        async function refreshData() {
            try {
                document.getElementById('refreshIndicator').className = 'refresh-indicator refresh-active';
                
                // Get current data
                const currentResponse = await fetch('/api/current');
                const currentData = await currentResponse.json();
                
                if (currentData && Object.keys(currentData).length > 0) {
                    updateSystemInfo(currentData);
                    updateInterfaces(currentData);
                    document.getElementById('status').textContent = 'Connected';
                    
                    // Get historical data for chart
                    const historicalResponse = await fetch('/api/historical/10');
                    const historicalData = await historicalResponse.json();
                    updateChart(historicalData);
                } else {
                    throw new Error('No data received');
                }
                
            } catch (error) {
                console.error('Error refreshing data:', error);
                document.getElementById('status').textContent = 'Error: ' + error.message;
                document.getElementById('systemInfo').innerHTML = '<div class="error">Failed to load data. Please check if SNMP is running.</div>';
                document.getElementById('interfaceGrid').innerHTML = '<div class="error">Failed to load interface data.</div>';
            } finally {
                document.getElementById('refreshIndicator').className = 'refresh-indicator refresh-inactive';
            }
        }

        // Toggle auto-refresh
        function toggleAutoRefresh() {
            autoRefresh = !autoRefresh;
            const btn = document.getElementById('autoRefreshBtn');
            
            if (autoRefresh) {
                btn.textContent = 'Stop Auto-refresh';
                startAutoRefresh();
            } else {
                btn.textContent = 'Start Auto-refresh';
                if (refreshTimer) {
                    clearInterval(refreshTimer);
                }
            }
        }

        // Start auto-refresh timer
        function startAutoRefresh() {
            if (refreshTimer) {
                clearInterval(refreshTimer);
            }
            
            refreshTimer = setInterval(refreshData, refreshInterval);
        }

        // Initialize dashboard
        window.onload = function() {
            initChart();
            refreshData();
            if (autoRefresh) {
                startAutoRefresh();
            }
        };

        // Cleanup on page unload
        window.onbeforeunload = function() {
            if (refreshTimer) {
                clearInterval(refreshTimer);
            }
        };
    </script>
</body>
</html>'''
    
    with open('/home/pavan/nms/templates/dashboard.html', 'w') as f:
        f.write(html_content)

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print('\nShutting down dashboard...')
    dashboard.stop_monitoring()
    sys.exit(0)

def main():
    """Main function to run the dashboard"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Network Monitoring Dashboard for Mininet SNMP')
    parser.add_argument('--host', default='localhost', help='SNMP host (default: localhost)')
    parser.add_argument('--community', default='public', help='SNMP community (default: public)')
    parser.add_argument('--port', type=int, default=5000, help='Web server port (default: 5000)')
    parser.add_argument('--interval', type=int, default=5, help='Monitoring interval in seconds (default: 5)')
    
    args = parser.parse_args()
    
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create dashboard template
    create_dashboard_template()
    
    # Initialize dashboard
    global dashboard
    dashboard = NetworkDashboard(args.host, args.community)
    
    # Start monitoring
    dashboard.start_monitoring(args.interval)
    
    print(f"Starting Network Monitoring Dashboard...")
    print(f"SNMP Host: {args.host}")
    print(f"SNMP Community: {args.community}")
    print(f"Monitoring Interval: {args.interval} seconds")
    print(f"Web Interface: http://localhost:{args.port}")
    print("Press Ctrl+C to stop the dashboard")
    
    # Start web server
    try:
        app.run(host='0.0.0.0', port=args.port, debug=False)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == '__main__':
    main()