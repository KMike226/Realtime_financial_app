# Snowflake Data Warehouse MVP Module

This module creates a minimal but functional Snowflake data warehouse setup for the real-time financial application.

## Features

- **Database**: `FINANCIAL_DATA` with schemas for market data and analytics
- **Warehouse**: `FINANCIAL_WAREHOUSE` (SMALL size, auto-suspend enabled)
- **Tables**: 
  - `PRICE_DATA`: Real-time price data from various sources
  - `TECHNICAL_INDICATORS`: Calculated technical indicators (RSI, MACD, SMA)
- **S3 Integration**: Automated data loading from S3 bucket
- **Automated Tasks**: Copy task runs every 5 minutes to load new data

## Usage

```hcl
module "snowflake" {
  source = "./modules/snowflake"
  
  snowflake_account  = "your-account.snowflakecomputing.com"
  snowflake_username = "your-username"
  snowflake_password = "your-password"
  snowflake_role     = "ACCOUNTADMIN"
  
  s3_bucket_name = "your-financial-data-bucket"
  s3_role_arn    = "arn:aws:iam::123456789012:role/snowflake-s3-role"
}
```

## Data Pipeline

1. **Data Ingestion**: Financial data is processed and stored in S3
2. **Automated Loading**: Snowflake task copies data from S3 every 5 minutes
3. **Analytics**: Technical indicators are calculated and stored
4. **Querying**: Data is available for real-time analytics

## MVP Limitations

- Uses SMALL warehouse (can be scaled up as needed)
- Basic error handling (ON_ERROR = 'CONTINUE')
- Simple JSON file format
- Minimal security (uses ACCOUNTADMIN role)

## Scaling Considerations

- Increase warehouse size for better performance
- Add more sophisticated data validation
- Implement proper role-based access control
- Add data retention policies
- Set up monitoring and alerting
