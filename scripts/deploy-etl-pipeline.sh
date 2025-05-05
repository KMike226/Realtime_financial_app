#!/bin/bash
# ETL Pipeline Deployment Script
# Deploy S3 to Snowflake ETL pipeline with monitoring and scheduling

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ETL_DIR="$PROJECT_ROOT/etl-pipeline"
LOG_DIR="/var/log/etl-pipeline"
CONFIG_DIR="/etc/etl-pipeline"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# Install Python dependencies
install_dependencies() {
    log_info "Installing Python dependencies..."
    
    # Install required Python packages
    pip3 install --upgrade pip
    pip3 install pandas numpy snowflake-connector-python boto3 python-dotenv
    
    # Install system dependencies
    apt-get update
    apt-get install -y python3-pip python3-venv cron
    
    log_info "Dependencies installed successfully"
}

# Create directory structure
create_directories() {
    log_info "Creating directory structure..."
    
    mkdir -p "$ETL_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$ETL_DIR/scripts"
    mkdir -p "$ETL_DIR/config"
    mkdir -p "$ETL_DIR/logs"
    
    # Set permissions
    chown -R etl:etl "$ETL_DIR"
    chown -R etl:etl "$LOG_DIR"
    chmod 755 "$ETL_DIR"
    chmod 755 "$LOG_DIR"
    
    log_info "Directory structure created"
}

# Create ETL user
create_etl_user() {
    log_info "Creating ETL user..."
    
    if ! id "etl" &>/dev/null; then
        useradd -r -s /bin/bash -d "$ETL_DIR" etl
        log_info "ETL user created"
    else
        log_info "ETL user already exists"
    fi
}

# Deploy ETL scripts
deploy_scripts() {
    log_info "Deploying ETL scripts..."
    
    # Copy scripts
    cp "$SCRIPT_DIR/etl-s3-to-snowflake.py" "$ETL_DIR/scripts/"
    cp "$SCRIPT_DIR/data_transformer.py" "$ETL_DIR/scripts/"
    cp "$SCRIPT_DIR/etl-config.env" "$ETL_DIR/config/"
    
    # Make scripts executable
    chmod +x "$ETL_DIR/scripts/etl-s3-to-snowflake.py"
    chmod +x "$ETL_DIR/scripts/data_transformer.py"
    
    # Set ownership
    chown -R etl:etl "$ETL_DIR"
    
    log_info "ETL scripts deployed"
}

# Create systemd service
create_systemd_service() {
    log_info "Creating systemd service..."
    
    cat > /etc/systemd/system/etl-pipeline.service << EOF
[Unit]
Description=ETL Pipeline S3 to Snowflake
After=network.target

[Service]
Type=simple
User=etl
Group=etl
WorkingDirectory=$ETL_DIR
ExecStart=/usr/bin/python3 $ETL_DIR/scripts/etl-s3-to-snowflake.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=etl-pipeline

# Environment variables
Environment=PYTHONPATH=$ETL_DIR/scripts
EnvironmentFile=$ETL_DIR/config/etl-config.env

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    log_info "Systemd service created"
}

# Create cron job for scheduled runs
create_cron_job() {
    log_info "Creating cron job..."
    
    # Create cron script
    cat > "$ETL_DIR/scripts/run-etl.sh" << EOF
#!/bin/bash
# ETL Pipeline Cron Runner

export PYTHONPATH="$ETL_DIR/scripts"
cd "$ETL_DIR"

# Load environment variables
source "$ETL_DIR/config/etl-config.env"

# Run ETL pipeline
python3 "$ETL_DIR/scripts/etl-s3-to-snowflake.py" >> "$LOG_DIR/etl-cron.log" 2>&1

# Log completion
echo "\$(date): ETL pipeline completed" >> "$LOG_DIR/etl-cron.log"
EOF

    chmod +x "$ETL_DIR/scripts/run-etl.sh"
    chown etl:etl "$ETL_DIR/scripts/run-etl.sh"
    
    # Add cron job (every 5 minutes)
    (crontab -u etl -l 2>/dev/null; echo "*/5 * * * * $ETL_DIR/scripts/run-etl.sh") | crontab -u etl -
    
    log_info "Cron job created (runs every 5 minutes)"
}

# Create monitoring script
create_monitoring() {
    log_info "Creating monitoring script..."
    
    cat > "$ETL_DIR/scripts/monitor-etl.sh" << EOF
#!/bin/bash
# ETL Pipeline Monitoring Script

LOG_FILE="$LOG_DIR/etl-monitor.log"
ERROR_THRESHOLD=10
ALERT_EMAIL="admin@financial-platform.com"

# Check if ETL process is running
if ! pgrep -f "etl-s3-to-snowflake.py" > /dev/null; then
    echo "\$(date): ETL process not running" >> "\$LOG_FILE"
    # Send alert
    echo "ETL Pipeline Alert: Process not running" | mail -s "ETL Alert" "\$ALERT_EMAIL"
fi

# Check log for errors
ERROR_COUNT=\$(tail -n 100 "$LOG_DIR/etl-cron.log" | grep -i error | wc -l)
if [ "\$ERROR_COUNT" -gt "\$ERROR_THRESHOLD" ]; then
    echo "\$(date): High error count detected: \$ERROR_COUNT" >> "\$LOG_FILE"
    echo "ETL Pipeline Alert: High error count (\$ERROR_COUNT)" | mail -s "ETL Alert" "\$ALERT_EMAIL"
fi

# Check disk space
DISK_USAGE=\$(df "$LOG_DIR" | tail -1 | awk '{print \$5}' | sed 's/%//')
if [ "\$DISK_USAGE" -gt 80 ]; then
    echo "\$(date): High disk usage: \$DISK_USAGE%" >> "\$LOG_FILE"
    echo "ETL Pipeline Alert: High disk usage (\$DISK_USAGE%)" | mail -s "ETL Alert" "\$ALERT_EMAIL"
fi
EOF

    chmod +x "$ETL_DIR/scripts/monitor-etl.sh"
    chown etl:etl "$ETL_DIR/scripts/monitor-etl.sh"
    
    # Add monitoring cron job (every hour)
    (crontab -u etl -l 2>/dev/null; echo "0 * * * * $ETL_DIR/scripts/monitor-etl.sh") | crontab -u etl -
    
    log_info "Monitoring script created"
}

# Create log rotation
setup_log_rotation() {
    log_info "Setting up log rotation..."
    
    cat > /etc/logrotate.d/etl-pipeline << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 etl etl
    postrotate
        systemctl reload etl-pipeline
    endscript
}
EOF

    log_info "Log rotation configured"
}

# Create configuration template
create_config_template() {
    log_info "Creating configuration template..."
    
    cat > "$ETL_DIR/config/etl-config.env.template" << EOF
# ETL Pipeline Configuration Template
# Copy this file to etl-config.env and update with your values

# Snowflake Connection Settings
SNOWFLAKE_USERNAME=your_snowflake_username
SNOWFLAKE_PASSWORD=your_snowflake_password
SNOWFLAKE_ACCOUNT=your_account.region
SNOWFLAKE_WAREHOUSE=FINANCIAL_WAREHOUSE
SNOWFLAKE_DATABASE=FINANCIAL_DATA
SNOWFLAKE_SCHEMA=MARKET_DATA
SNOWFLAKE_ROLE=your_role

# S3 Configuration
S3_BUCKET=financial-platform-dev-data-lake
S3_REGION=us-east-1

# ETL Pipeline Settings
ETL_BATCH_SIZE=1000
ETL_MAX_RETRIES=3
ETL_RETRY_DELAY=5
ETL_TIMEOUT=300

# Data Processing Settings
PRICE_DATA_PREFIX=processed/price_data
TECHNICAL_INDICATORS_PREFIX=processed/technical_indicators
ANOMALIES_PREFIX=processed/anomalies

# Snowflake Table Mappings
PRICE_DATA_TABLE=FINANCIAL_DATA.MARKET_DATA.PRICE_DATA
TECHNICAL_INDICATORS_TABLE=FINANCIAL_DATA.ANALYTICS.TECHNICAL_INDICATORS
ANOMALIES_TABLE=FINANCIAL_DATA.ANALYTICS.ANOMALIES

# Processing Windows (hours back to process)
PRICE_DATA_WINDOW=1
TECHNICAL_INDICATORS_WINDOW=2
ANOMALIES_WINDOW=24

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
LOG_FILE=$LOG_DIR/etl-pipeline.log

# Error Handling
ERROR_THRESHOLD=0.1
ALERT_EMAIL=admin@financial-platform.com

# Performance Settings
MAX_CONCURRENT_JOBS=5
MEMORY_LIMIT_MB=2048
CPU_LIMIT_CORES=2

# Data Quality Settings
MIN_PRICE_VALUE=0.01
MAX_PRICE_VALUE=1000000
MIN_VOLUME_VALUE=0
MAX_RSI_VALUE=100
MIN_RSI_VALUE=0
EOF

    log_info "Configuration template created"
}

# Start services
start_services() {
    log_info "Starting ETL services..."
    
    # Enable and start systemd service
    systemctl enable etl-pipeline
    systemctl start etl-pipeline
    
    # Check status
    if systemctl is-active --quiet etl-pipeline; then
        log_info "ETL pipeline service started successfully"
    else
        log_error "Failed to start ETL pipeline service"
        systemctl status etl-pipeline
        exit 1
    fi
}

# Test deployment
test_deployment() {
    log_info "Testing ETL deployment..."
    
    # Test Python script
    if python3 -c "import pandas, numpy, snowflake.connector, boto3" 2>/dev/null; then
        log_info "Python dependencies test passed"
    else
        log_error "Python dependencies test failed"
        exit 1
    fi
    
    # Test configuration file
    if [ -f "$ETL_DIR/config/etl-config.env" ]; then
        log_info "Configuration file test passed"
    else
        log_warn "Configuration file not found - using template"
        cp "$ETL_DIR/config/etl-config.env.template" "$ETL_DIR/config/etl-config.env"
    fi
    
    # Test service status
    if systemctl is-active --quiet etl-pipeline; then
        log_info "Service status test passed"
    else
        log_error "Service status test failed"
    fi
    
    log_info "Deployment test completed"
}

# Main deployment function
main() {
    log_info "Starting ETL Pipeline deployment..."
    
    check_root
    install_dependencies
    create_etl_user
    create_directories
    deploy_scripts
    create_systemd_service
    create_cron_job
    create_monitoring
    setup_log_rotation
    create_config_template
    start_services
    test_deployment
    
    log_info "ETL Pipeline deployment completed successfully!"
    log_info "Next steps:"
    log_info "1. Update configuration in $ETL_DIR/config/etl-config.env"
    log_info "2. Test the pipeline: systemctl status etl-pipeline"
    log_info "3. Check logs: tail -f $LOG_DIR/etl-cron.log"
    log_info "4. Monitor: $ETL_DIR/scripts/monitor-etl.sh"
}

# Run main function
main "$@"
