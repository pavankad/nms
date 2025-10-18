#!/usr/bin/env python
"""
Mininet Network Topology for SNMP Monitoring
This script creates a network topology with multiple switches and hosts
that can be monitored using SNMP.
"""

from mininet.net import Mininet
from mininet.node import Controller, OVSKernelSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
from mininet.topo import Topo
import time
import os
import subprocess

class SNMPTopology:
    def __init__(self):
        self.net = None
        
    def create_topology(self):
        """Create a network topology with switches and hosts"""
        info('*** Creating network topology for SNMP monitoring\n')
        
        # Create Mininet instance with learning switch behavior
        self.net = Mininet(
            controller=Controller,
            switch=OVSKernelSwitch,
            link=TCLink,
            autoSetMacs=True,
            autoStaticArp=True,  # Automatically set static ARP entries
            waitConnected=True   # Wait for switches to connect to controller
        )
        
        # Add controller
        info('*** Adding controller\n')
        c0 = self.net.addController('c0', port=6653)
        
        # Add switches
        info('*** Adding switches\n')
        s1 = self.net.addSwitch('s1', protocols='OpenFlow13')
        s2 = self.net.addSwitch('s2', protocols='OpenFlow13')
        s3 = self.net.addSwitch('s3', protocols='OpenFlow13')
        
        # Add hosts with explicit MAC addresses
        info('*** Adding hosts\n')
        h1 = self.net.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01')
        h2 = self.net.addHost('h2', ip='10.0.0.2/24', mac='00:00:00:00:00:02')
        h3 = self.net.addHost('h3', ip='10.0.0.3/24', mac='00:00:00:00:00:03')
        h4 = self.net.addHost('h4', ip='10.0.0.4/24', mac='00:00:00:00:00:04')
        
        # Add links with bandwidth limitations for monitoring
        info('*** Adding links\n')
        self.net.addLink(h1, s1, bw=10)  # 10 Mbps
        self.net.addLink(h2, s1, bw=10)
        self.net.addLink(h3, s2, bw=20)  # 20 Mbps
        self.net.addLink(h4, s3, bw=15)  # 15 Mbps
        
        # Connect switches
        self.net.addLink(s1, s2, bw=100)  # 100 Mbps backbone
        self.net.addLink(s2, s3, bw=100)
        self.net.addLink(s1, s3, bw=50)   # 50 Mbps redundant link
        
        return self.net
    
    def start_network(self):
        """Start the network and configure SNMP"""
        info('*** Starting network\n')
        self.net.start()
        
        # Wait for controller and switches to initialize
        info('*** Waiting for network initialization\n')
        time.sleep(5)
        
        # Install flow rules for basic connectivity
        self.install_flow_rules()
        
        # Configure switch interfaces for SNMP monitoring
        self.configure_snmp_on_switches()
        
        # Test connectivity
        info('*** Testing connectivity\n')
        result = self.net.pingAll()
        
        if result > 0:
            info('*** Some pings failed, installing additional flow rules\n')
            self.install_backup_flow_rules()
            time.sleep(2)
            self.net.pingAll()
    
    def install_flow_rules(self):
        """Install basic flow rules for connectivity"""
        info('*** Installing flow rules for connectivity\n')
        
        # Get switches
        s1, s2, s3 = self.net.get('s1', 's2', 's3')
        
        # Install flow rules to enable learning switch behavior
        for switch in [s1, s2, s3]:
            # Allow all traffic and let switch learn
            switch.cmd('ovs-ofctl add-flow {} "actions=NORMAL"'.format(switch.name))
    
    def install_backup_flow_rules(self):
        """Install more specific flow rules if needed"""
        info('*** Installing backup flow rules\n')
        
        # Get switches and hosts
        s1, s2, s3 = self.net.get('s1', 's2', 's3')
        h1, h2, h3, h4 = self.net.get('h1', 'h2', 'h3', 'h4')
        
        # Clear existing flows and install specific ones
        for switch in [s1, s2, s3]:
            switch.cmd('ovs-ofctl del-flows {}'.format(switch.name))
            switch.cmd('ovs-ofctl add-flow {} "actions=NORMAL"'.format(switch.name))
            
        # Force ARP resolution
        h1.cmd('arping -c 3 10.0.0.2')
        h2.cmd('arping -c 3 10.0.0.1')
        h3.cmd('arping -c 3 10.0.0.1')  
        h4.cmd('arping -c 3 10.0.0.1')
        
    def configure_snmp_on_switches(self):
        """Configure SNMP on switches for monitoring"""
        info('*** Configuring SNMP on switches\n')
        
        switches = ['s1', 's2', 's3']
        for switch_name in switches:
            switch = self.net.get(switch_name)
            # Enable SNMP on the switch namespace
            switch.cmd('ip netns exec {} snmpd -Lsd -Lf /dev/null -p /var/run/snmpd.pid -a'.format(switch_name))
    
    def generate_traffic(self):
        """Generate some network traffic for monitoring"""
        info('*** Generating network traffic\n')
        
        # Get hosts
        h1, h2, h3, h4 = self.net.get('h1', 'h2', 'h3', 'h4')
        
        # Start background traffic
        h1.cmd('ping -i 0.5 10.0.0.2 &')  # Ping from h1 to h2
        h3.cmd('ping -i 0.3 10.0.0.4 &')  # Ping from h3 to h4
        
        # Start iperf servers on some hosts
        h2.cmd('iperf -s &')
        h4.cmd('iperf -s &')
        
        time.sleep(2)
        
        # Start iperf clients
        h1.cmd('iperf -c 10.0.0.2 -t 60 &')  # 60 second test
        h3.cmd('iperf -c 10.0.0.4 -t 60 &')
    
    def stop_network(self):
        """Stop the network"""
        if self.net:
            info('*** Stopping network\n')
            self.net.stop()

def main():
    """Main function to create and run the topology"""
    setLogLevel('info')
    
    # Create topology
    topo = SNMPTopology()
    net = topo.create_topology()
    
    try:
        # Start network
        topo.start_network()
        
        # Generate traffic for monitoring
        topo.generate_traffic()
        
        info('*** Network is running. You can now monitor it using SNMP.\n')
        info('*** Switch interfaces are available for SNMP polling.\n')
        info('*** Run the SNMP monitoring script in another terminal.\n')
        info('*** Press Enter to access CLI or Ctrl+C to stop...\n')
        
        # Start CLI for manual testing
        CLI(net)
        
    except KeyboardInterrupt:
        info('*** Keyboard interrupt received\n')
    finally:
        # Clean up
        topo.stop_network()

if __name__ == '__main__':
    main()