-- Snowflake Test Queries MVP
-- Simple queries to validate data ingestion and basic analytics

-- Test 1: Check if tables exist and have data
SELECT 
    TABLE_CATALOG,
    TABLE_SCHEMA,
    TABLE_NAME,
    ROW_COUNT
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_CATALOG = 'FINANCIAL_DATA'
ORDER BY TABLE_SCHEMA, TABLE_NAME;

-- Test 2: Count records in price data table
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT SYMBOL) as unique_symbols,
    MIN(TIMESTAMP) as earliest_timestamp,
    MAX(TIMESTAMP) as latest_timestamp
FROM FINANCIAL_DATA.MARKET_DATA.PRICE_DATA;

-- Test 3: Sample price data for validation
SELECT 
    SYMBOL,
    TIMESTAMP,
    OPEN_PRICE,
    HIGH_PRICE,
    LOW_PRICE,
    CLOSE_PRICE,
    VOLUME,
    SOURCE
FROM FINANCIAL_DATA.MARKET_DATA.PRICE_DATA
ORDER BY TIMESTAMP DESC
LIMIT 10;

-- Test 4: Check technical indicators data
SELECT 
    COUNT(*) as total_indicators,
    COUNT(DISTINCT SYMBOL) as unique_symbols,
    AVG(RSI) as avg_rsi,
    AVG(MACD) as avg_macd
FROM FINANCIAL_DATA.ANALYTICS.TECHNICAL_INDICATORS;

-- Test 5: Sample technical indicators
SELECT 
    SYMBOL,
    TIMESTAMP,
    RSI,
    MACD,
    MACD_SIGNAL,
    MACD_HISTOGRAM,
    SMA_20,
    SMA_50
FROM FINANCIAL_DATA.ANALYTICS.TECHNICAL_INDICATORS
ORDER BY TIMESTAMP DESC
LIMIT 10;

-- Test 6: Basic analytics query - Price trends
SELECT 
    SYMBOL,
    DATE_TRUNC('HOUR', TIMESTAMP) as hour_bucket,
    AVG(CLOSE_PRICE) as avg_price,
    MAX(HIGH_PRICE) as max_price,
    MIN(LOW_PRICE) as min_price,
    SUM(VOLUME) as total_volume
FROM FINANCIAL_DATA.MARKET_DATA.PRICE_DATA
WHERE TIMESTAMP >= DATEADD(HOUR, -24, CURRENT_TIMESTAMP())
GROUP BY SYMBOL, hour_bucket
ORDER BY SYMBOL, hour_bucket;

-- Test 7: RSI analysis
SELECT 
    SYMBOL,
    RSI,
    CASE 
        WHEN RSI > 70 THEN 'Overbought'
        WHEN RSI < 30 THEN 'Oversold'
        ELSE 'Neutral'
    END as rsi_signal,
    TIMESTAMP
FROM FINANCIAL_DATA.ANALYTICS.TECHNICAL_INDICATORS
WHERE TIMESTAMP >= DATEADD(HOUR, -1, CURRENT_TIMESTAMP())
ORDER BY TIMESTAMP DESC;

-- Test 8: MACD signal analysis
SELECT 
    SYMBOL,
    MACD,
    MACD_SIGNAL,
    MACD_HISTOGRAM,
    CASE 
        WHEN MACD > MACD_SIGNAL AND MACD_HISTOGRAM > 0 THEN 'Bullish'
        WHEN MACD < MACD_SIGNAL AND MACD_HISTOGRAM < 0 THEN 'Bearish'
        ELSE 'Neutral'
    END as macd_signal,
    TIMESTAMP
FROM FINANCIAL_DATA.ANALYTICS.TECHNICAL_INDICATORS
WHERE TIMESTAMP >= DATEADD(HOUR, -1, CURRENT_TIMESTAMP())
ORDER BY TIMESTAMP DESC;

-- Test 9: Data quality checks
SELECT 
    'Price Data Quality' as check_type,
    COUNT(*) as total_records,
    COUNT(CASE WHEN SYMBOL IS NULL THEN 1 END) as null_symbols,
    COUNT(CASE WHEN CLOSE_PRICE <= 0 THEN 1 END) as invalid_prices,
    COUNT(CASE WHEN VOLUME < 0 THEN 1 END) as negative_volume
FROM FINANCIAL_DATA.MARKET_DATA.PRICE_DATA

UNION ALL

SELECT 
    'Technical Indicators Quality' as check_type,
    COUNT(*) as total_records,
    COUNT(CASE WHEN SYMBOL IS NULL THEN 1 END) as null_symbols,
    COUNT(CASE WHEN RSI < 0 OR RSI > 100 THEN 1 END) as invalid_rsi,
    COUNT(CASE WHEN MACD IS NULL THEN 1 END) as null_macd
FROM FINANCIAL_DATA.ANALYTICS.TECHNICAL_INDICATORS;

-- Test 10: Performance test - Simple aggregation
SELECT 
    SYMBOL,
    COUNT(*) as record_count,
    AVG(CLOSE_PRICE) as avg_price,
    STDDEV(CLOSE_PRICE) as price_volatility
FROM FINANCIAL_DATA.MARKET_DATA.PRICE_DATA
GROUP BY SYMBOL
ORDER BY record_count DESC;
