#!/usr/bin/env python
"""
Simple Mininet Network Topology for SNMP Monitoring (Linux Bridge Version)
This script creates a simple, reliable network topology using Linux bridges
that can be monitored using SNMP.
"""

from mininet.net import Mininet
from mininet.node import Host
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
from mininet.node import OVSBridge
import time

class SimpleTopology:
    def __init__(self):
        self.net = None
        
    def create_topology(self):
        """Create a simple network topology with Linux bridges"""
        info('*** Creating simple network topology for SNMP monitoring\n')
        
        # Create Mininet instance without controller (use Linux bridge)
        self.net = Mininet(
            switch=OVSBridge,
            link=TCLink,
            autoSetMacs=True,
            autoStaticArp=True
        )
        
        # Add a single switch (bridge)
        info('*** Adding switch\n')
        s1 = self.net.addSwitch('s1')
        
        # Add hosts
        info('*** Adding hosts\n')
        h1 = self.net.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01')
        h2 = self.net.addHost('h2', ip='10.0.0.2/24', mac='00:00:00:00:00:02')
        h3 = self.net.addHost('h3', ip='10.0.0.3/24', mac='00:00:00:00:00:03')
        h4 = self.net.addHost('h4', ip='10.0.0.4/24', mac='00:00:00:00:00:04')
        
        # Add links - all hosts connected to the same switch
        info('*** Adding links\n')
        self.net.addLink(h1, s1, bw=100)
        self.net.addLink(h2, s1, bw=100)  
        self.net.addLink(h3, s1, bw=100)
        self.net.addLink(h4, s1, bw=100)
        
        return self.net
    
    def start_network(self):
        """Start the network"""
        info('*** Starting network\n')
        self.net.start()
        
        # Wait a moment for network to initialize
        time.sleep(2)
        
        # Test connectivity
        info('*** Testing connectivity\n')
        result = self.net.pingAll()
        
        if result == 0:
            info('*** All connectivity tests passed!\n')
        else:
            info('*** Some connectivity tests failed\n')
            
        return result == 0
    
    def configure_snmp_on_hosts(self):
        """Configure SNMP monitoring on host interfaces"""
        info('*** Configuring SNMP monitoring\n')
        
        # Get all hosts
        hosts = self.net.hosts
        
        # Start SNMP daemon on each host (if available)
        for host in hosts:
            # This will only work if snmpd is installed and configured
            host.cmd('snmpd -Lsd -Lf /dev/null -p /tmp/snmpd_{}.pid 2>/dev/null &'.format(host.name))
    
    def generate_traffic(self):
        """Generate some network traffic for monitoring"""
        info('*** Generating network traffic\n')
        
        # Get hosts
        h1, h2, h3, h4 = self.net.get('h1', 'h2', 'h3', 'h4')
        
        # Start background ping traffic
        h1.cmd('ping -i 2 10.0.0.2 > /dev/null &')  # Slow ping from h1 to h2
        h3.cmd('ping -i 3 10.0.0.4 > /dev/null &')  # Slow ping from h3 to h4
        
        info('*** Background traffic started\n')
    
    def stop_network(self):
        """Stop the network"""
        if self.net:
            info('*** Stopping network\n')
            self.net.stop()

def main():
    """Main function to create and run the topology"""
    setLogLevel('info')
    
    # Create topology
    topo = SimpleTopology()
    net = topo.create_topology()
    
    try:
        # Start network
        success = topo.start_network()
        
        if not success:
            info('*** Warning: Connectivity issues detected\n')
        
        # Configure SNMP monitoring
        topo.configure_snmp_on_hosts()
        
        # Generate traffic for monitoring
        topo.generate_traffic()
        
        info('*** Network is running and ready for monitoring.\n')
        info('*** You can now test connectivity and monitor interfaces.\n')
        info('*** Example tests:\n')
        info('    h1 ping h2\n')
        info('    h1 ping -c 5 h3\n')
        info('    dump\n')
        info('    links\n')
        info('    net\n')
        info('*** Press Ctrl+C to stop...\n')
        
        # Start CLI for manual testing
        CLI(net)
        
    except KeyboardInterrupt:
        info('*** Keyboard interrupt received\n')
    finally:
        # Clean up
        topo.stop_network()

if __name__ == '__main__':
    main()