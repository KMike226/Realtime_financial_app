#!/usr/bin/env python3
"""
Snowflake Test Runner MVP
Simple script to run test queries and validate Snowflake setup
"""

import snowflake.connector
import json
import logging
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SnowflakeTester:
    """MVP Snowflake testing utility"""
    
    def __init__(self, account: str, username: str, password: str, role: str = "ACCOUNTADMIN"):
        self.account = account
        self.username = username
        self.password = password
        self.role = role
        self.connection = None
    
    def connect(self) -> bool:
        """Connect to Snowflake"""
        try:
            self.connection = snowflake.connector.connect(
                account=self.account,
                user=self.username,
                password=self.password,
                role=self.role,
                warehouse='FINANCIAL_WAREHOUSE',
                database='FINANCIAL_DATA',
                schema='MARKET_DATA'
            )
            logger.info("Successfully connected to Snowflake")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {e}")
            return False
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a query and return results"""
        if not self.connection:
            logger.error("Not connected to Snowflake")
            return []
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            
            # Get column names
            columns = [desc[0] for desc in cursor.description]
            
            # Fetch results
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            cursor.close()
            return results
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return []
    
    def test_table_existence(self) -> bool:
        """Test if required tables exist"""
        query = """
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_CATALOG = 'FINANCIAL_DATA'
        AND TABLE_NAME IN ('PRICE_DATA', 'TECHNICAL_INDICATORS')
        """
        
        results = self.execute_query(query)
        table_names = [row['TABLE_NAME'] for row in results]
        
        expected_tables = ['PRICE_DATA', 'TECHNICAL_INDICATORS']
        missing_tables = set(expected_tables) - set(table_names)
        
        if missing_tables:
            logger.error(f"Missing tables: {missing_tables}")
            return False
        
        logger.info("All required tables exist")
        return True
    
    def test_data_ingestion(self) -> bool:
        """Test if data has been ingested"""
        # Test price data
        price_query = "SELECT COUNT(*) as count FROM FINANCIAL_DATA.MARKET_DATA.PRICE_DATA"
        price_results = self.execute_query(price_query)
        price_count = price_results[0]['COUNT'] if price_results else 0
        
        # Test technical indicators
        indicator_query = "SELECT COUNT(*) as count FROM FINANCIAL_DATA.ANALYTICS.TECHNICAL_INDICATORS"
        indicator_results = self.execute_query(indicator_query)
        indicator_count = indicator_results[0]['COUNT'] if indicator_results else 0
        
        logger.info(f"Price data records: {price_count}")
        logger.info(f"Technical indicator records: {indicator_count}")
        
        return price_count > 0 or indicator_count > 0
    
    def test_basic_analytics(self) -> bool:
        """Test basic analytics queries"""
        try:
            # Test aggregation query
            query = """
            SELECT 
                SYMBOL,
                COUNT(*) as record_count,
                AVG(CLOSE_PRICE) as avg_price
            FROM FINANCIAL_DATA.MARKET_DATA.PRICE_DATA
            GROUP BY SYMBOL
            LIMIT 5
            """
            
            results = self.execute_query(query)
            
            if results:
                logger.info("Basic analytics test passed")
                for row in results:
                    logger.info(f"Symbol: {row['SYMBOL']}, Records: {row['RECORD_COUNT']}, Avg Price: {row['AVG_PRICE']}")
                return True
            else:
                logger.warning("No data found for analytics test")
                return False
                
        except Exception as e:
            logger.error(f"Analytics test failed: {e}")
            return False
    
    def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests and return results"""
        if not self.connect():
            return {"connection": False}
        
        tests = {
            "connection": True,
            "table_existence": self.test_table_existence(),
            "data_ingestion": self.test_data_ingestion(),
            "basic_analytics": self.test_basic_analytics()
        }
        
        # Close connection
        if self.connection:
            self.connection.close()
        
        return tests
    
    def generate_test_report(self, results: Dict[str, bool]) -> str:
        """Generate a test report"""
        report = "=== Snowflake MVP Test Report ===\n\n"
        
        for test_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            report += f"{test_name}: {status}\n"
        
        report += f"\nOverall: {'✅ ALL TESTS PASSED' if all(results.values()) else '❌ SOME TESTS FAILED'}\n"
        
        return report

def main():
    """Example usage of Snowflake tester"""
    
    # Configuration - replace with your actual values
    config = {
        "account": "your-account.snowflakecomputing.com",
        "username": "your-username",
        "password": "your-password",
        "role": "ACCOUNTADMIN"
    }
    
    tester = SnowflakeTester(**config)
    results = tester.run_all_tests()
    report = tester.generate_test_report(results)
    
    print(report)
    
    # Save report to file
    with open("snowflake-test-report.txt", "w") as f:
        f.write(report)
    
    logger.info("Test report saved to snowflake-test-report.txt")

if __name__ == "__main__":
    main()
