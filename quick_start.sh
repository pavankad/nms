#!/bin/bash
# Quick Start Script for Mininet SNMP Network Monitoring
# This script provides a convenient way to start the monitoring system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    if command_exists pip3; then
        pip3 install -r requirements.txt
    elif command_exists pip; then
        pip install -r requirements.txt
    else
        print_error "Neither pip3 nor pip found. Please install pip first."
        exit 1
    fi
}

# Function to setup SNMP
setup_snmp() {
    print_status "Setting up SNMP daemon..."
    
    if [ ! -f "./setup_snmp.sh" ]; then
        print_error "setup_snmp.sh not found in current directory"
        exit 1
    fi
    
    chmod +x ./setup_snmp.sh
    ./setup_snmp.sh
}

# Function to test SNMP
test_snmp() {
    print_status "Testing SNMP configuration..."
    
    if snmpwalk -v2c -c public localhost 1.3.6.1.2.1.1.1.0 >/dev/null 2>&1; then
        print_success "SNMP is working correctly"
        return 0
    else
        print_warning "SNMP test failed. The monitoring may not work properly."
        return 1
    fi
}

# Function to start Mininet in background
start_mininet() {
    print_status "Starting Mininet network topology..."
    
    if [ ! -f "./mininet_topology.py" ]; then
        print_error "mininet_topology.py not found in current directory"
        exit 1
    fi
    
    # Check if Mininet is already running
    if pgrep -f "mininet_topology.py" >/dev/null; then
        print_warning "Mininet appears to be already running"
        return 0
    fi
    
    # Start Mininet in background
    nohup python3 mininet_topology.py >/dev/null 2>&1 &
    MININET_PID=$!
    
    # Wait a moment for network to initialize
    sleep 5
    
    # Check if Mininet started successfully
    if kill -0 $MININET_PID 2>/dev/null; then
        print_success "Mininet network started (PID: $MININET_PID)"
        echo $MININET_PID > /tmp/mininet_monitor.pid
    else
        print_error "Failed to start Mininet network"
        exit 1
    fi
}

# Function to start monitoring dashboard
start_dashboard() {
    print_status "Starting web monitoring dashboard..."
    
    if [ ! -f "./dashboard.py" ]; then
        print_error "dashboard.py not found in current directory"
        exit 1
    fi
    
    # Get current user (original user before sudo)
    ORIGINAL_USER=${SUDO_USER:-$USER}
    
    print_status "Starting dashboard as user: $ORIGINAL_USER"
    
    # Start dashboard as original user
    sudo -u $ORIGINAL_USER python3 dashboard.py --host 0.0.0.0 --port 5000 &
    DASHBOARD_PID=$!
    
    # Wait a moment for server to start
    sleep 3
    
    # Check if dashboard started successfully
    if kill -0 $DASHBOARD_PID 2>/dev/null; then
        print_success "Dashboard started (PID: $DASHBOARD_PID)"
        echo $DASHBOARD_PID > /tmp/dashboard_monitor.pid
        
        print_success "Web dashboard is available at: http://localhost:5000"
        print_status "You can also access it from other machines at: http://$(hostname -I | awk '{print $1}'):5000"
    else
        print_error "Failed to start dashboard"
        exit 1
    fi
}

# Function to stop services
stop_services() {
    print_status "Stopping monitoring services..."
    
    # Stop dashboard
    if [ -f "/tmp/dashboard_monitor.pid" ]; then
        DASHBOARD_PID=$(cat /tmp/dashboard_monitor.pid)
        if kill -0 $DASHBOARD_PID 2>/dev/null; then
            kill $DASHBOARD_PID
            print_success "Dashboard stopped"
        fi
        rm -f /tmp/dashboard_monitor.pid
    fi
    
    # Stop Mininet
    if [ -f "/tmp/mininet_monitor.pid" ]; then
        MININET_PID=$(cat /tmp/mininet_monitor.pid)
        if kill -0 $MININET_PID 2>/dev/null; then
            kill $MININET_PID
            print_success "Mininet stopped"
        fi
        rm -f /tmp/mininet_monitor.pid
    fi
    
    # Clean up Mininet processes
    mn -c >/dev/null 2>&1 || true
    
    print_success "All services stopped"
}

# Function to show status
show_status() {
    print_status "Checking service status..."
    
    # Check SNMP
    if systemctl is-active --quiet snmpd; then
        print_success "SNMP daemon: Running"
    else
        print_warning "SNMP daemon: Not running"
    fi
    
    # Check Mininet
    if [ -f "/tmp/mininet_monitor.pid" ] && kill -0 $(cat /tmp/mininet_monitor.pid) 2>/dev/null; then
        print_success "Mininet network: Running (PID: $(cat /tmp/mininet_monitor.pid))"
    else
        print_warning "Mininet network: Not running"
    fi
    
    # Check Dashboard
    if [ -f "/tmp/dashboard_monitor.pid" ] && kill -0 $(cat /tmp/dashboard_monitor.pid) 2>/dev/null; then
        print_success "Web dashboard: Running (PID: $(cat /tmp/dashboard_monitor.pid))"
        print_status "Dashboard URL: http://localhost:5000"
    else
        print_warning "Web dashboard: Not running"
    fi
}

# Function to show help
show_help() {
    echo "Mininet SNMP Network Monitoring - Quick Start Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  setup     - Install dependencies and configure SNMP (requires root)"
    echo "  start     - Start Mininet network and monitoring dashboard"
    echo "  stop      - Stop all monitoring services"
    echo "  restart   - Stop and start all services"
    echo "  status    - Show status of all services"
    echo "  monitor   - Start command-line monitoring (interactive)"
    echo "  test      - Test SNMP configuration"
    echo "  help      - Show this help message"
    echo ""
    echo "Examples:"
    echo "  sudo $0 setup     # First time setup"
    echo "  sudo $0 start     # Start monitoring"
    echo "  $0 monitor        # Command-line monitoring"
    echo "  sudo $0 stop      # Stop all services"
    echo ""
    echo "Note: Most commands require root privileges (use sudo)"
}

# Main script logic
case "${1:-help}" in
    setup)
        check_root
        print_status "Setting up Mininet SNMP Network Monitoring..."
        install_dependencies
        setup_snmp
        test_snmp
        print_success "Setup completed successfully!"
        echo ""
        print_status "Next steps:"
        echo "  1. Run 'sudo $0 start' to start monitoring"
        echo "  2. Open http://localhost:5000 in your browser"
        ;;
    
    start)
        check_root
        print_status "Starting Mininet SNMP Network Monitoring..."
        
        # Check if SNMP is running
        if ! systemctl is-active --quiet snmpd; then
            print_warning "SNMP daemon not running. Starting it..."
            systemctl start snmpd
        fi
        
        start_mininet
        start_dashboard
        
        print_success "Monitoring system started successfully!"
        echo ""
        print_status "Services running:"
        echo "  - Mininet network topology"
        echo "  - Web monitoring dashboard at http://localhost:5000"
        echo ""
        print_status "To stop the monitoring system, run: sudo $0 stop"
        ;;
    
    stop)
        check_root
        stop_services
        ;;
    
    restart)
        check_root
        print_status "Restarting monitoring services..."
        stop_services
        sleep 2
        start_mininet
        start_dashboard
        print_success "Services restarted successfully!"
        ;;
    
    status)
        show_status
        ;;
    
    monitor)
        print_status "Starting command-line monitoring..."
        if [ ! -f "./snmp_monitor.py" ]; then
            print_error "snmp_monitor.py not found in current directory"
            exit 1
        fi
        python3 snmp_monitor.py
        ;;
    
    test)
        test_snmp
        ;;
    
    help|--help|-h)
        show_help
        ;;
    
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac