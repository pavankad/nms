#!/usr/bin/env python3
"""
SNMP Network Monitor for Mininet
This script monitors network interfaces and statistics using SNMP
"""

import time
import sys
import json
from datetime import datetime
import subprocess
import threading
from collections import defaultdict

# Import pysnmp components
try:
    # Try system package first (python3-pysnmp4)
    from pysnmp.hlapi import getCmd, nextCmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity
    print("Using system pysnmp package")
except ImportError:
    try:
        # Fallback to pip installed version
        import sys
        sys.path.insert(0, '/usr/lib/python3/dist-packages')
        from pysnmp.hlapi import getCmd, nextCmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity
        print("Using system pysnmp via explicit path")
    except ImportError as e:
        print(f"Error importing pysnmp: {e}")
        print("Please install pysnmp: sudo apt-get install python3-pysnmp4")
        sys.exit(1)

class SNMPMonitor:
    def __init__(self, target_host='localhost', community='public', port=161):
        self.target_host = target_host
        self.community = community
        self.port = port
        self.interface_data = {}
        self.previous_data = {}
        
        # Common SNMP OIDs for network monitoring
        self.oids = {
            'system_name': '1.3.6.1.2.1.1.5.0',
            'system_uptime': '1.3.6.1.2.1.1.3.0',
            'interfaces_count': '1.3.6.1.2.1.2.1.0',
            'interface_desc': '1.3.6.1.2.1.2.2.1.2',      # ifDescr
            'interface_type': '1.3.6.1.2.1.2.2.1.3',      # ifType
            'interface_mtu': '1.3.6.1.2.1.2.2.1.4',       # ifMtu
            'interface_speed': '1.3.6.1.2.1.2.2.1.5',     # ifSpeed
            'interface_admin_status': '1.3.6.1.2.1.2.2.1.7',  # ifAdminStatus
            'interface_oper_status': '1.3.6.1.2.1.2.2.1.8',   # ifOperStatus
            'interface_in_octets': '1.3.6.1.2.1.2.2.1.10',    # ifInOctets
            'interface_in_packets': '1.3.6.1.2.1.2.2.1.11',   # ifInUcastPkts
            'interface_in_errors': '1.3.6.1.2.1.2.2.1.14',    # ifInErrors
            'interface_out_octets': '1.3.6.1.2.1.2.2.1.16',   # ifOutOctets
            'interface_out_packets': '1.3.6.1.2.1.2.2.1.17',  # ifOutUcastPkts
            'interface_out_errors': '1.3.6.1.2.1.2.2.1.20',   # ifOutErrors
        }
    
    def snmp_get(self, oid):
        """Perform SNMP GET operation"""
        try:
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(self.community),
                UdpTransportTarget((self.target_host, self.port)),
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            )
            
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            
            if errorIndication:
                print(f"SNMP Error: {errorIndication}")
                return None
            elif errorStatus:
                error_location = varBinds[int(errorIndex) - 1][0] if errorIndex else "?"
                print(f"SNMP Error: {errorStatus.prettyPrint()} at {error_location}")
                return None
            else:
                for varBind in varBinds:
                    return varBind[1]
        except Exception as e:
            print(f"SNMP GET Error: {e}")
            return None
    
    def snmp_walk(self, oid):
        """Perform SNMP WALK operation"""
        results = {}
        try:
            for (errorIndication, errorStatus, errorIndex, varBinds) in nextCmd(
                SnmpEngine(),
                CommunityData(self.community),
                UdpTransportTarget((self.target_host, self.port)),
                ContextData(),
                ObjectType(ObjectIdentity(oid)),
                lexicographicMode=False):
                
                if errorIndication:
                    print(f"SNMP Error: {errorIndication}")
                    break
                elif errorStatus:
                    error_location = varBinds[int(errorIndex) - 1][0] if errorIndex else "?"
                    print(f"SNMP Error: {errorStatus.prettyPrint()} at {error_location}")
                    break
                else:
                    for varBind in varBinds:
                        oid_str = str(varBind[0])
                        value = varBind[1]
                        # Extract interface index from OID
                        if '.' in oid_str:
                            index = oid_str.split('.')[-1]
                            results[index] = value
        except Exception as e:
            print(f"SNMP WALK Error: {e}")
        
        return results
    
    def get_system_info(self):
        """Get basic system information"""
        info = {}
        info['system_name'] = str(self.snmp_get(self.oids['system_name']) or 'Unknown')
        uptime_ticks = self.snmp_get(self.oids['system_uptime'])
        if uptime_ticks:
            # Convert TimeTicks to seconds (1 tick = 1/100 second)
            uptime_seconds = int(uptime_ticks) / 100
            info['uptime_seconds'] = uptime_seconds
            info['uptime_formatted'] = self.format_uptime(uptime_seconds)
        
        interface_count = self.snmp_get(self.oids['interfaces_count'])
        info['interface_count'] = int(interface_count) if interface_count else 0
        
        return info
    
    def format_uptime(self, seconds):
        """Format uptime in human readable format"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{days}d {hours}h {minutes}m {secs}s"
    
    def get_interface_info(self):
        """Get detailed interface information"""
        interfaces = {}
        
        # Get interface descriptions
        descriptions = self.snmp_walk(self.oids['interface_desc'])
        speeds = self.snmp_walk(self.oids['interface_speed'])
        admin_status = self.snmp_walk(self.oids['interface_admin_status'])
        oper_status = self.snmp_walk(self.oids['interface_oper_status'])
        
        for index in descriptions.keys():
            interface = {
                'index': index,
                'description': str(descriptions[index]),
                'speed': int(speeds.get(index, 0)),
                'admin_status': int(admin_status.get(index, 0)),
                'oper_status': int(oper_status.get(index, 0)),
                'admin_status_text': self.get_status_text(int(admin_status.get(index, 0))),
                'oper_status_text': self.get_status_text(int(oper_status.get(index, 0)))
            }
            interfaces[index] = interface
        
        return interfaces
    
    def get_status_text(self, status):
        """Convert numeric status to text"""
        status_map = {1: 'up', 2: 'down', 3: 'testing'}
        return status_map.get(status, 'unknown')
    
    def get_interface_statistics(self):
        """Get interface traffic statistics"""
        stats = {}
        
        # Get traffic counters
        in_octets = self.snmp_walk(self.oids['interface_in_octets'])
        in_packets = self.snmp_walk(self.oids['interface_in_packets'])
        in_errors = self.snmp_walk(self.oids['interface_in_errors'])
        out_octets = self.snmp_walk(self.oids['interface_out_octets'])
        out_packets = self.snmp_walk(self.oids['interface_out_packets'])
        out_errors = self.snmp_walk(self.oids['interface_out_errors'])
        
        for index in in_octets.keys():
            stats[index] = {
                'in_octets': int(in_octets.get(index, 0)),
                'in_packets': int(in_packets.get(index, 0)),
                'in_errors': int(in_errors.get(index, 0)),
                'out_octets': int(out_octets.get(index, 0)),
                'out_packets': int(out_packets.get(index, 0)),
                'out_errors': int(out_errors.get(index, 0))
            }
        
        return stats
    
    def calculate_rates(self, current_stats, previous_stats, time_diff):
        """Calculate traffic rates from counters"""
        rates = {}
        
        for index in current_stats.keys():
            if index in previous_stats:
                curr = current_stats[index]
                prev = previous_stats[index]
                
                # Calculate bytes per second
                in_bps = max(0, (curr['in_octets'] - prev['in_octets']) / time_diff)
                out_bps = max(0, (curr['out_octets'] - prev['out_octets']) / time_diff)
                
                # Calculate packets per second
                in_pps = max(0, (curr['in_packets'] - prev['in_packets']) / time_diff)
                out_pps = max(0, (curr['out_packets'] - prev['out_packets']) / time_diff)
                
                rates[index] = {
                    'in_bps': in_bps,
                    'out_bps': out_bps,
                    'in_pps': in_pps,
                    'out_pps': out_pps,
                    'in_mbps': in_bps * 8 / 1000000,  # Convert to Mbps
                    'out_mbps': out_bps * 8 / 1000000
                }
        
        return rates
    
    def format_bytes(self, bytes_val):
        """Format bytes in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} TB"
    
    def monitor_continuous(self, interval=5):
        """Continuously monitor network interfaces"""
        print("Starting SNMP Network Monitor...")
        print(f"Target: {self.target_host}:{self.port}")
        print(f"Community: {self.community}")
        print(f"Monitoring interval: {interval} seconds")
        print("-" * 80)
        
        previous_stats = None
        previous_time = None
        
        try:
            while True:
                current_time = time.time()
                
                # Get system info
                system_info = self.get_system_info()
                
                # Get interface info
                interface_info = self.get_interface_info()
                
                # Get statistics
                current_stats = self.get_interface_statistics()
                
                # Clear screen and print header
                print(f"\n{'='*80}")
                print(f"SNMP Network Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"System: {system_info.get('system_name', 'Unknown')}")
                print(f"Uptime: {system_info.get('uptime_formatted', 'Unknown')}")
                print(f"Interfaces: {system_info.get('interface_count', 0)}")
                print(f"{'='*80}")
                
                # Display interface information and statistics
                for index in sorted(interface_info.keys(), key=int):
                    interface = interface_info[index]
                    stats = current_stats.get(index, {})
                    
                    # Skip loopback interface for cleaner output
                    if 'lo' in interface['description'].lower():
                        continue
                    
                    print(f"\nInterface {index}: {interface['description']}")
                    print(f"  Status: Admin={interface['admin_status_text']}, Oper={interface['oper_status_text']}")
                    print(f"  Speed: {interface['speed']} bps")
                    print(f"  Traffic: In={self.format_bytes(stats.get('in_octets', 0))}, Out={self.format_bytes(stats.get('out_octets', 0))}")
                    print(f"  Packets: In={stats.get('in_packets', 0)}, Out={stats.get('out_packets', 0)}")
                    print(f"  Errors:  In={stats.get('in_errors', 0)}, Out={stats.get('out_errors', 0)}")
                    
                    # Calculate and display rates if we have previous data
                    if previous_stats and previous_time:
                        time_diff = current_time - previous_time
                        rates = self.calculate_rates(current_stats, previous_stats, time_diff)
                        
                        if index in rates:
                            rate = rates[index]
                            print(f"  Rates:   In={rate['in_mbps']:.2f} Mbps, Out={rate['out_mbps']:.2f} Mbps")
                            print(f"           In={rate['in_pps']:.1f} pps, Out={rate['out_pps']:.1f} pps")
                
                # Store current data for next iteration
                previous_stats = current_stats.copy()
                previous_time = current_time
                
                # Wait for next iteration
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user.")
        except Exception as e:
            print(f"\nError during monitoring: {e}")
    
    def monitor_once(self):
        """Perform a single monitoring snapshot"""
        print("SNMP Network Monitor - Single Snapshot")
        print("-" * 50)
        
        # Get system info
        system_info = self.get_system_info()
        print(f"System Name: {system_info.get('system_name', 'Unknown')}")
        print(f"Uptime: {system_info.get('uptime_formatted', 'Unknown')}")
        print(f"Interface Count: {system_info.get('interface_count', 0)}")
        
        # Get interface info and statistics
        interface_info = self.get_interface_info()
        interface_stats = self.get_interface_statistics()
        
        print("\nInterface Details:")
        for index in sorted(interface_info.keys(), key=int):
            interface = interface_info[index]
            stats = interface_stats.get(index, {})
            
            print(f"\n  Interface {index}: {interface['description']}")
            print(f"    Status: {interface['admin_status_text']}/{interface['oper_status_text']}")
            print(f"    Speed: {interface['speed']} bps")
            print(f"    In:  {self.format_bytes(stats.get('in_octets', 0))} / {stats.get('in_packets', 0)} packets / {stats.get('in_errors', 0)} errors")
            print(f"    Out: {self.format_bytes(stats.get('out_octets', 0))} / {stats.get('out_packets', 0)} packets / {stats.get('out_errors', 0)} errors")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SNMP Network Monitor for Mininet')
    parser.add_argument('--host', default='localhost', help='Target SNMP host (default: localhost)')
    parser.add_argument('--community', default='public', help='SNMP community string (default: public)')
    parser.add_argument('--port', type=int, default=161, help='SNMP port (default: 161)')
    parser.add_argument('--interval', type=int, default=5, help='Monitoring interval in seconds (default: 5)')
    parser.add_argument('--once', action='store_true', help='Run once instead of continuous monitoring')
    
    args = parser.parse_args()
    
    # Create monitor instance
    monitor = SNMPMonitor(args.host, args.community, args.port)
    
    try:
        if args.once:
            monitor.monitor_once()
        else:
            monitor.monitor_continuous(args.interval)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()