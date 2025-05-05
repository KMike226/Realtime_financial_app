# ETL Pipeline: S3 to Snowflake

A robust Extract, Transform, and Load (ETL) pipeline for transferring financial data from AWS S3 to Snowflake data warehouse.

## 🚀 Features

- **Real-time Data Processing**: Processes data in near real-time with configurable windows
- **Data Quality Validation**: Comprehensive data validation and cleaning
- **Error Handling**: Robust error handling with retry logic and alerting
- **Monitoring**: Built-in monitoring and logging capabilities
- **Scalable**: Designed to handle large volumes of financial data
- **Configurable**: Flexible configuration for different environments

## 📁 Project Structure

```
scripts/
├── etl-s3-to-snowflake.py      # Main ETL pipeline script
├── data_transformer.py         # Data transformation utilities
├── etl-config.env              # Configuration file
├── etl-requirements.txt        # Python dependencies
├── deploy-etl-pipeline.sh      # Deployment script
└── README.md                   # This file
```

## 🛠️ Installation

### Prerequisites

- Python 3.8+
- AWS CLI configured
- Snowflake account with appropriate permissions
- Linux/Unix environment

### Quick Setup

1. **Clone and navigate to the project**:
   ```bash
   cd /path/to/your/project/scripts
   ```

2. **Install dependencies**:
   ```bash
   pip install -r etl-requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp etl-config.env.template etl-config.env
   # Edit etl-config.env with your settings
   ```

4. **Deploy the pipeline**:
   ```bash
   sudo ./deploy-etl-pipeline.sh
   ```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SNOWFLAKE_USERNAME` | Snowflake username | `your_username` |
| `SNOWFLAKE_PASSWORD` | Snowflake password | `your_password` |
| `SNOWFLAKE_ACCOUNT` | Snowflake account | `your_account.region` |
| `SNOWFLAKE_WAREHOUSE` | Snowflake warehouse | `FINANCIAL_WAREHOUSE` |
| `SNOWFLAKE_DATABASE` | Snowflake database | `FINANCIAL_DATA` |
| `SNOWFLAKE_SCHEMA` | Snowflake schema | `MARKET_DATA` |
| `S3_BUCKET` | S3 bucket name | `financial-platform-dev-data-lake` |

### Data Sources Configuration

The pipeline processes the following data types:

1. **Price Data**: Real-time stock/crypto price information
2. **Technical Indicators**: Calculated technical analysis indicators
3. **Anomalies**: Detected anomalies in financial data

## 🔄 Data Flow

```
S3 Bucket → Extract → Transform → Validate → Load → Snowflake
    ↓           ↓         ↓         ↓        ↓
  Raw Data   Cleaned   Enriched   Quality   Analytics
             Data      Data      Checked   Ready
```

### Data Transformation Process

1. **Extract**: Read data from S3 with configurable time windows
2. **Transform**: Clean, validate, and enrich data
3. **Validate**: Apply data quality rules and anomaly detection
4. **Load**: Insert validated data into Snowflake tables

## 📊 Data Quality Rules

### Price Data Validation
- Symbol format validation (1-5 uppercase letters)
- Price range validation (0.01 - 1,000,000)
- OHLC relationship validation
- Volume validation (non-negative)
- Timestamp validation

### Technical Indicators Validation
- RSI range validation (0-100)
- MACD value validation
- SMA value validation (positive values)
- Symbol format validation

## 🚨 Monitoring and Alerting

### Built-in Monitoring
- Process health monitoring
- Error rate monitoring
- Disk space monitoring
- Data quality monitoring

### Alerting
- Email alerts for critical issues
- Log-based alerting
- Performance metrics tracking

## 🔧 Usage

### Manual Execution

```bash
# Run ETL pipeline manually
python3 etl-s3-to-snowflake.py

# Run with specific configuration
export ETL_CONFIG_FILE=/path/to/config.env
python3 etl-s3-to-snowflake.py
```

### Service Management

```bash
# Start service
sudo systemctl start etl-pipeline

# Stop service
sudo systemctl stop etl-pipeline

# Check status
sudo systemctl status etl-pipeline

# View logs
sudo journalctl -u etl-pipeline -f
```

### Cron Jobs

The deployment script automatically sets up cron jobs:
- **ETL Pipeline**: Runs every 5 minutes
- **Monitoring**: Runs every hour

## 📈 Performance Tuning

### Configuration Options

- `ETL_BATCH_SIZE`: Number of records to process per batch
- `MAX_CONCURRENT_JOBS`: Maximum concurrent processing jobs
- `MEMORY_LIMIT_MB`: Memory limit for the process
- `CPU_LIMIT_CORES`: CPU core limit

### Optimization Tips

1. **Batch Size**: Adjust based on available memory
2. **Time Windows**: Optimize based on data volume
3. **Concurrent Jobs**: Balance between throughput and resource usage
4. **Retry Logic**: Configure appropriate retry delays

## 🐛 Troubleshooting

### Common Issues

1. **Connection Errors**:
   - Verify Snowflake credentials
   - Check network connectivity
   - Validate AWS permissions

2. **Data Quality Issues**:
   - Review validation rules
   - Check source data format
   - Verify transformation logic

3. **Performance Issues**:
   - Monitor resource usage
   - Adjust batch sizes
   - Optimize queries

### Log Files

- **Main Log**: `/var/log/etl-pipeline/etl-pipeline.log`
- **Cron Log**: `/var/log/etl-pipeline/etl-cron.log`
- **Monitor Log**: `/var/log/etl-pipeline/etl-monitor.log`

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python3 etl-s3-to-snowflake.py
```

## 🔒 Security

### Best Practices

1. **Credentials**: Store in environment variables or secure vaults
2. **Permissions**: Use least privilege principle
3. **Encryption**: Enable encryption in transit and at rest
4. **Auditing**: Enable audit logging for compliance

### Network Security

- Use VPC endpoints for S3 access
- Configure security groups appropriately
- Enable SSL/TLS for all connections

## 📚 API Reference

### S3ToSnowflakeETL Class

```python
class S3ToSnowflakeETL:
    def __init__(self, config: Dict[str, Any])
    def extract_from_s3(self, bucket: str, prefix: str, hours_back: int) -> List[Dict[str, Any]]
    def transform_data(self, raw_data: List[Dict[str, Any]], data_type: str) -> pd.DataFrame
    def load_to_snowflake(self, df: pd.DataFrame, table_name: str) -> bool
    def run_etl_pipeline(self, data_sources: List[Dict[str, str]]) -> Dict[str, bool]
```

### DataTransformer Class

```python
class DataTransformer:
    def __init__(self, config: Dict[str, Any])
    def validate_and_clean_price_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]
    def validate_and_clean_technical_indicators(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]
    def enrich_data(self, df: pd.DataFrame, data_type: str) -> pd.DataFrame
    def detect_anomalies(self, df: pd.DataFrame, data_type: str) -> pd.DataFrame
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the logs for error details

---

**Note**: This is an MVP implementation focused on core functionality. For production use, consider additional features like:
- Advanced error recovery
- Data lineage tracking
- Performance metrics dashboard
- Automated testing suite
- CI/CD pipeline integration
