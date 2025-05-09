# Outputs for Snowflake Data Warehouse MVP

output "database_name" {
  description = "Name of the created Snowflake database"
  value       = snowflake_database.financial_data.name
}

output "warehouse_name" {
  description = "Name of the created Snowflake warehouse"
  value       = snowflake_warehouse.financial_warehouse.name
}

output "price_data_table" {
  description = "Fully qualified name of the price data table"
  value       = "${snowflake_database.financial_data.name}.${snowflake_schema.market_data.name}.${snowflake_table.price_data.name}"
}

output "technical_indicators_table" {
  description = "Fully qualified name of the technical indicators table"
  value       = "${snowflake_database.financial_data.name}.${snowflake_schema.analytics.name}.${snowflake_table.technical_indicators.name}"
}

output "s3_stage_name" {
  description = "Fully qualified name of the S3 stage"
  value       = "${snowflake_database.financial_data.name}.${snowflake_schema.market_data.name}.${snowflake_stage.s3_stage.name}"
}

output "storage_integration_name" {
  description = "Name of the S3 storage integration"
  value       = snowflake_storage_integration.s3_integration.name
}
