#!/usr/bin/env python3
"""
Simple SNMP Network Monitor using command-line tools
This version uses snmpwalk/snmpget commands instead of Python libraries
"""

import subprocess
import re
import time
import json
from datetime import datetime

class SimpleSnmpMonitor:
    def __init__(self, host='localhost', community='public'):
        self.host = host
        self.community = community
        
        # OID mappings
        self.oids = {
            'system_name': '1.3.6.1.2.1.1.5.0',
            'system_uptime': '1.3.6.1.2.1.1.3.0',
            'system_description': '1.3.6.1.2.1.1.1.0',
            'interfaces_count': '1.3.6.1.2.1.2.1.0',
            'interface_desc': '1.3.6.1.2.1.2.2.1.2',
            'interface_speed': '1.3.6.1.2.1.2.2.1.5',
            'interface_admin_status': '1.3.6.1.2.1.2.2.1.7',
            'interface_oper_status': '1.3.6.1.2.1.2.2.1.8',
            'interface_in_octets': '1.3.6.1.2.1.2.2.1.10',
            'interface_out_octets': '1.3.6.1.2.1.2.2.1.16',
            'interface_in_packets': '1.3.6.1.2.1.2.2.1.11',
            'interface_out_packets': '1.3.6.1.2.1.2.2.1.17',
        }
    
    def run_snmp_command(self, cmd):
        """Run an SNMP command and return the output"""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                print(f"SNMP command failed: {result.stderr.strip()}")
                return None
        except subprocess.TimeoutExpired:
            print("SNMP command timed out")
            return None
        except Exception as e:
            print(f"Error running SNMP command: {e}")
            return None
    
    def snmp_get(self, oid):
        """Get a single SNMP value"""
        cmd = f"snmpget -v2c -c {self.community} {self.host} {oid}"
        output = self.run_snmp_command(cmd)
        if output:
            # Parse output like: "iso.3.6.1.2.1.1.5.0 = STRING: ubuntu"
            match = re.search(r'= (STRING|INTEGER|Counter32|Counter64|Gauge32|Timeticks): (.+)', output)
            if match:
                return match.group(2).strip().strip('"')
        return None
    
    def snmp_walk(self, oid):
        """Walk an SNMP tree and return results"""
        cmd = f"snmpwalk -v2c -c {self.community} {self.host} {oid}"
        output = self.run_snmp_command(cmd)
        results = {}
        
        if output:
            for line in output.split('\n'):
                if line.strip():
                    # Parse each line
                    match = re.search(r'\.(\d+) = (?:STRING|INTEGER|Counter32|Counter64|Gauge32|Timeticks): (.+)', line)
                    if match:
                        index = match.group(1)
                        value = match.group(2).strip().strip('"')
                        # Try to convert to integer if possible
                        try:
                            value = int(value)
                        except ValueError:
                            pass
                        results[index] = value
        
        return results
    
    def get_system_info(self):
        """Get system information"""
        info = {}
        
        # System name
        name = self.snmp_get(self.oids['system_name'])
        info['system_name'] = name or 'Unknown'
        
        # System description
        desc = self.snmp_get(self.oids['system_description'])
        info['system_description'] = desc or 'Unknown'
        
        # Uptime
        uptime_str = self.snmp_get(self.oids['system_uptime'])
        if uptime_str:
            # Parse uptime like "(12345) 0:02:03.45"
            match = re.search(r'\((\d+)\)', uptime_str)
            if match:
                uptime_ticks = int(match.group(1))
                uptime_seconds = uptime_ticks / 100
                info['uptime_seconds'] = uptime_seconds
                info['uptime_formatted'] = self.format_uptime(uptime_seconds)
        
        # Interface count
        count = self.snmp_get(self.oids['interfaces_count'])
        info['interface_count'] = int(count) if count else 0
        
        return info
    
    def format_uptime(self, seconds):
        """Format uptime in human readable format"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{days}d {hours}h {minutes}m {secs}s"
    
    def get_interfaces(self):
        """Get interface information"""
        interfaces = {}
        
        # Get interface descriptions
        descriptions = self.snmp_walk(self.oids['interface_desc'])
        speeds = self.snmp_walk(self.oids['interface_speed'])
        admin_status = self.snmp_walk(self.oids['interface_admin_status'])
        oper_status = self.snmp_walk(self.oids['interface_oper_status'])
        
        for index in descriptions.keys():
            interface = {
                'index': index,
                'name': str(descriptions[index]),
                'speed': speeds.get(index, 0),
                'admin_status': admin_status.get(index, 0),
                'oper_status': oper_status.get(index, 0),
                'admin_status_text': self.get_status_text(admin_status.get(index, 0)),
                'oper_status_text': self.get_status_text(oper_status.get(index, 0))
            }
            interfaces[index] = interface
        
        return interfaces
    
    def get_status_text(self, status):
        """Convert numeric status to text"""
        status_map = {1: 'up', 2: 'down', 3: 'testing'}
        
        # Handle both numeric and text formats
        if isinstance(status, str):
            # Parse strings like "up(1)" or "down(2)"
            if '(' in status:
                try:
                    numeric_part = status.split('(')[1].split(')')[0]
                    status = int(numeric_part)
                except (IndexError, ValueError):
                    return status.lower()  # Return original if parsing fails
            else:
                # Handle direct text values
                status_lower = status.lower()
                if status_lower in ['up', 'down', 'testing']:
                    return status_lower
                # Try to convert to int
                try:
                    status = int(status)
                except ValueError:
                    return 'unknown'
        
        return status_map.get(int(status), 'unknown')
    
    def get_interface_stats(self):
        """Get interface statistics"""
        stats = {}
        
        in_octets = self.snmp_walk(self.oids['interface_in_octets'])
        out_octets = self.snmp_walk(self.oids['interface_out_octets'])
        in_packets = self.snmp_walk(self.oids['interface_in_packets'])
        out_packets = self.snmp_walk(self.oids['interface_out_packets'])
        
        for index in in_octets.keys():
            stats[index] = {
                'in_octets': in_octets.get(index, 0),
                'out_octets': out_octets.get(index, 0),
                'in_packets': in_packets.get(index, 0),
                'out_packets': out_packets.get(index, 0)
            }
        
        return stats
    
    def format_bytes(self, bytes_val):
        """Format bytes in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} TB"
    
    def monitor_once(self):
        """Perform single monitoring snapshot"""
        print("Simple SNMP Network Monitor")
        print("=" * 50)
        
        # Test SNMP connectivity first
        test_result = self.snmp_get('1.3.6.1.2.1.1.1.0')
        if not test_result:
            print("Error: Cannot connect to SNMP agent")
            print("Make sure SNMP daemon is running:")
            print("  sudo systemctl start snmpd")
            print("  sudo systemctl status snmpd")
            return
        
        print("✓ SNMP connection successful")
        print()
        
        # Get system information
        system_info = self.get_system_info()
        print("System Information:")
        print(f"  Name: {system_info['system_name']}")
        print(f"  Description: {system_info['system_description'][:60]}...")
        print(f"  Uptime: {system_info.get('uptime_formatted', 'Unknown')}")
        print(f"  Interfaces: {system_info['interface_count']}")
        print()
        
        # Get interfaces
        interfaces = self.get_interfaces()
        stats = self.get_interface_stats()
        
        print("Interface Information:")
        for index in sorted(interfaces.keys(), key=int):
            interface = interfaces[index]
            interface_stats = stats.get(index, {})
            
            print(f"\n  Interface {index}: {interface['name']}")
            print(f"    Status: {interface['admin_status_text']}/{interface['oper_status_text']}")
            print(f"    Speed: {interface['speed']} bps")
            
            in_bytes = interface_stats.get('in_octets', 0)
            out_bytes = interface_stats.get('out_octets', 0)
            in_pkts = interface_stats.get('in_packets', 0)
            out_pkts = interface_stats.get('out_packets', 0)
            
            print(f"    Traffic: In={self.format_bytes(in_bytes)}, Out={self.format_bytes(out_bytes)}")
            print(f"    Packets: In={in_pkts}, Out={out_pkts}")
    
    def monitor_continuous(self, interval=5):
        """Continuous monitoring with rate calculations"""
        print("Starting continuous SNMP monitoring...")
        print(f"Host: {self.host}, Community: {self.community}")
        print(f"Update interval: {interval} seconds")
        print("Press Ctrl+C to stop")
        print("=" * 70)
        
        previous_stats = None
        previous_time = None
        
        try:
            while True:
                current_time = time.time()
                
                # Get current data
                system_info = self.get_system_info()
                interfaces = self.get_interfaces()
                current_stats = self.get_interface_stats()
                
                # Clear screen (optional)
                print("\n" + "=" * 70)
                print(f"SNMP Monitor - {datetime.now().strftime('%H:%M:%S')}")
                print(f"System: {system_info['system_name']} | Uptime: {system_info.get('uptime_formatted', 'Unknown')}")
                print("=" * 70)
                
                # Display interface information
                for index in sorted(interfaces.keys(), key=int):
                    interface = interfaces[index]
                    current = current_stats.get(index, {})
                    
                    # Skip loopback for cleaner display
                    if 'lo' in interface['name'].lower():
                        continue
                    
                    print(f"\nInterface {index}: {interface['name']}")
                    print(f"  Status: {interface['admin_status_text']}/{interface['oper_status_text']}")
                    
                    in_bytes = current.get('in_octets', 0)
                    out_bytes = current.get('out_octets', 0)
                    in_pkts = current.get('in_packets', 0)
                    out_pkts = current.get('out_packets', 0)
                    
                    print(f"  Total: In={self.format_bytes(in_bytes)}, Out={self.format_bytes(out_bytes)}")
                    print(f"  Packets: In={in_pkts}, Out={out_pkts}")
                    
                    # Calculate rates if we have previous data
                    if previous_stats and previous_time and index in previous_stats:
                        time_diff = current_time - previous_time
                        prev = previous_stats[index]
                        
                        if time_diff > 0:
                            in_rate = max(0, (in_bytes - prev.get('in_octets', 0)) / time_diff)
                            out_rate = max(0, (out_bytes - prev.get('out_octets', 0)) / time_diff)
                            
                            in_mbps = in_rate * 8 / 1000000
                            out_mbps = out_rate * 8 / 1000000
                            
                            print(f"  Rates: In={in_mbps:.2f} Mbps, Out={out_mbps:.2f} Mbps")
                
                # Store for next iteration
                previous_stats = current_stats.copy()
                previous_time = current_time
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped.")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Simple SNMP Network Monitor')
    parser.add_argument('--host', default='localhost', help='SNMP host (default: localhost)')
    parser.add_argument('--community', default='public', help='SNMP community (default: public)')
    parser.add_argument('--interval', type=int, default=5, help='Monitoring interval (default: 5)')
    parser.add_argument('--once', action='store_true', help='Run once instead of continuous')
    
    args = parser.parse_args()
    
    monitor = SimpleSnmpMonitor(args.host, args.community)
    
    if args.once:
        monitor.monitor_once()
    else:
        monitor.monitor_continuous(args.interval)

if __name__ == '__main__':
    main()