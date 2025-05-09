# Snowflake Data Warehouse MVP Configuration
# Simple setup for real-time financial data analytics

terraform {
  required_providers {
    snowflake = {
      source  = "Snowflake-Labs/snowflake"
      version = "~> 0.90"
    }
  }
}

# Snowflake Provider Configuration
provider "snowflake" {
  account  = var.snowflake_account
  username = var.snowflake_username
  password = var.snowflake_password
  role     = var.snowflake_role
}

# Create Database for Financial Data
resource "snowflake_database" "financial_data" {
  name    = "FINANCIAL_DATA"
  comment = "Database for real-time financial market data"
}

# Create Schema for Market Data
resource "snowflake_schema" "market_data" {
  database = snowflake_database.financial_data.name
  name     = "MARKET_DATA"
  comment  = "Schema for market data tables"
}

# Create Schema for Analytics
resource "snowflake_schema" "analytics" {
  database = snowflake_database.financial_data.name
  name     = "ANALYTICS"
  comment  = "Schema for analytics and aggregated data"
}

# Create Warehouse for Processing
resource "snowflake_warehouse" "financial_warehouse" {
  name           = "FINANCIAL_WAREHOUSE"
  comment        = "Warehouse for financial data processing"
  warehouse_size = "SMALL"  # MVP: Start small, scale as needed
  
  auto_suspend = 60  # Auto-suspend after 1 minute of inactivity
  auto_resume  = true
}

# Create Table for Real-time Price Data
resource "snowflake_table" "price_data" {
  database = snowflake_database.financial_data.name
  schema   = snowflake_schema.market_data.name
  name     = "PRICE_DATA"
  comment  = "Real-time financial price data"

  column {
    name = "SYMBOL"
    type = "VARCHAR(20)"
  }
  
  column {
    name = "TIMESTAMP"
    type = "TIMESTAMP_NTZ"
  }
  
  column {
    name = "OPEN_PRICE"
    type = "DECIMAL(20,8)"
  }
  
  column {
    name = "HIGH_PRICE"
    type = "DECIMAL(20,8)"
  }
  
  column {
    name = "LOW_PRICE"
    type = "DECIMAL(20,8)"
  }
  
  column {
    name = "CLOSE_PRICE"
    type = "DECIMAL(20,8)"
  }
  
  column {
    name = "VOLUME"
    type = "BIGINT"
  }
  
  column {
    name = "SOURCE"
    type = "VARCHAR(50)"
  }
}

# Create Table for Technical Indicators
resource "snowflake_table" "technical_indicators" {
  database = snowflake_database.financial_data.name
  schema   = snowflake_schema.analytics.name
  name     = "TECHNICAL_INDICATORS"
  comment  = "Calculated technical indicators"

  column {
    name = "SYMBOL"
    type = "VARCHAR(20)"
  }
  
  column {
    name = "TIMESTAMP"
    type = "TIMESTAMP_NTZ"
  }
  
  column {
    name = "RSI"
    type = "DECIMAL(5,2)"
  }
  
  column {
    name = "MACD"
    type = "DECIMAL(20,8)"
  }
  
  column {
    name = "MACD_SIGNAL"
    type = "DECIMAL(20,8)"
  }
  
  column {
    name = "MACD_HISTOGRAM"
    type = "DECIMAL(20,8)"
  }
  
  column {
    name = "SMA_20"
    type = "DECIMAL(20,8)"
  }
  
  column {
    name = "SMA_50"
    type = "DECIMAL(20,8)"
  }
}

# Create Storage Integration for S3
resource "snowflake_storage_integration" "s3_integration" {
  name    = "S3_FINANCIAL_DATA"
  type    = "EXTERNAL_STAGE"
  enabled = true

  storage_provider         = "S3"
  storage_aws_role_arn     = var.s3_role_arn
  storage_allowed_locations = ["s3://${var.s3_bucket_name}/processed/"]
}

# Create External Stage for S3 Data Loading
resource "snowflake_stage" "s3_stage" {
  name                = "S3_STAGE"
  database            = snowflake_database.financial_data.name
  schema              = snowflake_schema.market_data.name
  url                 = "s3://${var.s3_bucket_name}/processed/"
  storage_integration = snowflake_storage_integration.s3_integration.name
  
  file_format = "TYPE = JSON"
  comment      = "External stage for loading data from S3"
}

# Create Copy Task for Automated Data Loading
resource "snowflake_task" "load_price_data" {
  database = snowflake_database.financial_data.name
  schema   = snowflake_schema.market_data.name
  name     = "LOAD_PRICE_DATA"
  comment  = "Automated task to load price data from S3"

  warehouse = snowflake_warehouse.financial_warehouse.name
  schedule  = "USING CRON 0 */5 * * * *"  # Every 5 minutes

  sql = <<-SQL
    COPY INTO ${snowflake_database.financial_data.name}.${snowflake_schema.market_data.name}.PRICE_DATA
    FROM @${snowflake_database.financial_data.name}.${snowflake_schema.market_data.name}.S3_STAGE
    FILE_FORMAT = (TYPE = 'JSON')
    PATTERN = '.*price_data.*'
    ON_ERROR = 'CONTINUE'
  SQL
}

# Grant Usage on Warehouse
resource "snowflake_warehouse_grant" "usage" {
  warehouse_name = snowflake_warehouse.financial_warehouse.name
  privilege      = "USAGE"
  roles          = [var.snowflake_role]
}

# Grant Usage on Database
resource "snowflake_database_grant" "usage" {
  database_name = snowflake_database.financial_data.name
  privilege     = "USAGE"
  roles         = [var.snowflake_role]
}

# Grant Usage on Schema
resource "snowflake_schema_grant" "usage" {
  database_name = snowflake_database.financial_data.name
  schema_name   = snowflake_schema.market_data.name
  privilege     = "USAGE"
  roles         = [var.snowflake_role]
}

# Grant Select on Tables
resource "snowflake_table_grant" "select_price_data" {
  database_name = snowflake_database.financial_data.name
  schema_name   = snowflake_schema.market_data.name
  table_name    = snowflake_table.price_data.name
  privilege     = "SELECT"
  roles         = [var.snowflake_role]
}

resource "snowflake_table_grant" "select_technical_indicators" {
  database_name = snowflake_database.financial_data.name
  schema_name   = snowflake_schema.analytics.name
  table_name    = snowflake_table.technical_indicators.name
  privilege     = "SELECT"
  roles         = [var.snowflake_role]
}
