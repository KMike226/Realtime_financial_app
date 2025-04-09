#!/usr/bin/env python3
"""
Technical Indicators Engine pour l'analyse financière
Implémentation des indicateurs techniques: MA, RSI, MACD, Bollinger Bands
"""

import sys
import math
from typing import List, Dict, Any, Optional
from datetime import datetime

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, lit, when, avg, stddev, max as spark_max, min as spark_min,
    lag, lead, window, expr, current_timestamp, to_timestamp,
    round as spark_round, abs as spark_abs, sum as spark_sum,
    row_number, rank, dense_rank, percent_rank, cume_dist
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, 
    TimestampType, IntegerType, BooleanType
)
from pyspark.sql.window import Window
import boto3

class TechnicalIndicatorsEngine:
    """Moteur de calcul des indicateurs techniques"""
    
    def __init__(self, spark_session: SparkSession = None):
        """Initialisation du moteur d'indicateurs"""
        self.spark = spark_session or SparkSession.builder.getOrCreate()
        self.spark.sparkContext.setLogLevel("WARN")
        
        print("📈 Technical Indicators Engine initialisé")

    def calculate_simple_moving_average(self, df: DataFrame, price_col: str = "close", 
                                       periods: List[int] = [5, 10, 20, 50, 200]) -> DataFrame:
        """Calcule les moyennes mobiles simples (SMA)"""
        print(f"📊 Calcul des SMA pour les périodes: {periods}")
        
        result_df = df
        window_symbol = Window.partitionBy("symbol").orderBy("timestamp")
        
        for period in periods:
            window_period = window_symbol.rowsBetween(-period + 1, 0)
            result_df = result_df.withColumn(
                f"sma_{period}", 
                avg(price_col).over(window_period)
            )
        
        return result_df

    def calculate_exponential_moving_average(self, df: DataFrame, price_col: str = "close",
                                           periods: List[int] = [12, 26, 50]) -> DataFrame:
        """Calcule les moyennes mobiles exponentielles (EMA)"""
        print(f"📈 Calcul des EMA pour les périodes: {periods}")
        
        result_df = df
        window_symbol = Window.partitionBy("symbol").orderBy("timestamp")
        
        for period in periods:
            alpha = 2.0 / (period + 1)
            
            # Calcul EMA avec formule récursive
            result_df = result_df.withColumn(
                f"ema_{period}_temp",
                when(
                    row_number().over(window_symbol) == 1,
                    col(price_col)
                ).otherwise(
                    alpha * col(price_col) + (1 - alpha) * lag(f"ema_{period}_temp", 1).over(window_symbol)
                )
            ).withColumn(
                f"ema_{period}", col(f"ema_{period}_temp")
            ).drop(f"ema_{period}_temp")
        
        return result_df

    def calculate_rsi(self, df: DataFrame, price_col: str = "close", period: int = 14) -> DataFrame:
        """Calcule l'indice de force relative (RSI)"""
        print(f"🔄 Calcul du RSI (période: {period})")
        
        window_symbol = Window.partitionBy("symbol").orderBy("timestamp")
        window_rsi = window_symbol.rowsBetween(-period + 1, 0)
        
        # Calcul des gains et pertes
        df_with_changes = df.withColumn(
            "price_change", col(price_col) - lag(price_col, 1).over(window_symbol)
        ).withColumn(
            "gain", when(col("price_change") > 0, col("price_change")).otherwise(0)
        ).withColumn(
            "loss", when(col("price_change") < 0, spark_abs(col("price_change"))).otherwise(0)
        )
        
        # Moyennes mobiles des gains et pertes
        df_rsi = df_with_changes.withColumn(
            "avg_gain", avg("gain").over(window_rsi)
        ).withColumn(
            "avg_loss", avg("loss").over(window_rsi)
        ).withColumn(
            # Calcul RSI
            "rs", col("avg_gain") / col("avg_loss")
        ).withColumn(
            "rsi", 100 - (100 / (1 + col("rs")))
        ).withColumn(
            # Signaux RSI
            "rsi_signal", when(col("rsi") > 70, "OVERBOUGHT")
                         .when(col("rsi") < 30, "OVERSOLD")
                         .otherwise("NEUTRAL")
        )
        
        return df_rsi

    def calculate_macd(self, df: DataFrame, price_col: str = "close", 
                      fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> DataFrame:
        """Calcule le MACD (Moving Average Convergence Divergence)"""
        print(f"📊 Calcul du MACD ({fast_period}, {slow_period}, {signal_period})")
        
        # Calcul des EMA
        df_ema = self.calculate_exponential_moving_average(df, price_col, [fast_period, slow_period])
        
        # Calcul du MACD Line
        df_macd = df_ema.withColumn(
            "macd_line", col(f"ema_{fast_period}") - col(f"ema_{slow_period}")
        )
        
        # Calcul de la Signal Line (EMA du MACD)
        window_symbol = Window.partitionBy("symbol").orderBy("timestamp")
        alpha_signal = 2.0 / (signal_period + 1)
        
        df_signal = df_macd.withColumn(
            "signal_line_temp",
            when(
                row_number().over(window_symbol) == 1,
                col("macd_line")
            ).otherwise(
                alpha_signal * col("macd_line") + (1 - alpha_signal) * lag("signal_line_temp", 1).over(window_symbol)
            )
        ).withColumn(
            "signal_line", col("signal_line_temp")
        ).drop("signal_line_temp")
        
        # Calcul du Histogram
        df_histogram = df_signal.withColumn(
            "macd_histogram", col("macd_line") - col("signal_line")
        ).withColumn(
            # Signaux MACD
            "macd_signal", when(
                (col("macd_line") > col("signal_line")) & 
                (lag("macd_line", 1).over(window_symbol) <= lag("signal_line", 1).over(window_symbol)),
                "BULLISH_CROSSOVER"
            ).when(
                (col("macd_line") < col("signal_line")) & 
                (lag("macd_line", 1).over(window_symbol) >= lag("signal_line", 1).over(window_symbol)),
                "BEARISH_CROSSOVER"
            ).otherwise("NO_SIGNAL")
        )
        
        return df_histogram

    def calculate_bollinger_bands(self, df: DataFrame, price_col: str = "close", 
                                period: int = 20, std_dev: float = 2.0) -> DataFrame:
        """Calcule les Bandes de Bollinger"""
        print(f"📏 Calcul des Bandes de Bollinger (période: {period}, std: {std_dev})")
        
        window_symbol = Window.partitionBy("symbol").orderBy("timestamp")
        window_bb = window_symbol.rowsBetween(-period + 1, 0)
        
        df_bb = df.withColumn(
            "bb_middle", avg(price_col).over(window_bb)
        ).withColumn(
            "bb_std", stddev(price_col).over(window_bb)
        ).withColumn(
            "bb_upper", col("bb_middle") + (std_dev * col("bb_std"))
        ).withColumn(
            "bb_lower", col("bb_middle") - (std_dev * col("bb_std"))
        ).withColumn(
            # Position du prix dans les bandes
            "bb_position", (col(price_col) - col("bb_lower")) / (col("bb_upper") - col("bb_lower"))
        ).withColumn(
            # Signaux Bollinger
            "bb_signal", when(col(price_col) > col("bb_upper"), "OVERBOUGHT")
                       .when(col(price_col) < col("bb_lower"), "OVERSOLD")
                       .otherwise("NEUTRAL")
        ).withColumn(
            # Largeur des bandes (volatilité)
            "bb_width", (col("bb_upper") - col("bb_lower")) / col("bb_middle")
        )
        
        return df_bb

    def calculate_stochastic(self, df: DataFrame, period: int = 14, k_period: int = 3, d_period: int = 3) -> DataFrame:
        """Calcule l'oscillateur stochastique"""
        print(f"🎯 Calcul du Stochastique ({period}, {k_period}, {d_period})")
        
        window_symbol = Window.partitionBy("symbol").orderBy("timestamp")
        window_stoch = window_symbol.rowsBetween(-period + 1, 0)
        
        df_stoch = df.withColumn(
            "lowest_low", min("low").over(window_stoch)
        ).withColumn(
            "highest_high", max("high").over(window_stoch)
        ).withColumn(
            # %K
            "stoch_k", 100 * (col("close") - col("lowest_low")) / (col("highest_high") - col("lowest_low"))
        )
        
        # %D (moyenne mobile de %K)
        window_k = window_symbol.rowsBetween(-k_period + 1, 0)
        df_d = df_stoch.withColumn(
            "stoch_d", avg("stoch_k").over(window_k)
        )
        
        # Signaux stochastique
        df_signals = df_d.withColumn(
            "stoch_signal", when(
                (col("stoch_k") > col("stoch_d")) & 
                (lag("stoch_k", 1).over(window_symbol) <= lag("stoch_d", 1).over(window_symbol)),
                "BULLISH_CROSSOVER"
            ).when(
                (col("stoch_k") < col("stoch_d")) & 
                (lag("stoch_k", 1).over(window_symbol) >= lag("stoch_d", 1).over(window_symbol)),
                "BEARISH_CROSSOVER"
            ).otherwise("NO_SIGNAL")
        )
        
        return df_signals

    def calculate_williams_r(self, df: DataFrame, period: int = 14) -> DataFrame:
        """Calcule l'indicateur Williams %R"""
        print(f"📉 Calcul du Williams %R (période: {period})")
        
        window_symbol = Window.partitionBy("symbol").orderBy("timestamp")
        window_wr = window_symbol.rowsBetween(-period + 1, 0)
        
        df_wr = df.withColumn(
            "highest_high", max("high").over(window_wr)
        ).withColumn(
            "lowest_low", min("low").over(window_wr)
        ).withColumn(
            "williams_r", -100 * (col("highest_high") - col("close")) / (col("highest_high") - col("lowest_low"))
        ).withColumn(
            "williams_signal", when(col("williams_r") > -20, "OVERBOUGHT")
                             .when(col("williams_r") < -80, "OVERSOLD")
                             .otherwise("NEUTRAL")
        )
        
        return df_wr

    def calculate_atr(self, df: DataFrame, period: int = 14) -> DataFrame:
        """Calcule l'Average True Range (ATR)"""
        print(f"📏 Calcul de l'ATR (période: {period})")
        
        window_symbol = Window.partitionBy("symbol").orderBy("timestamp")
        window_atr = window_symbol.rowsBetween(-period + 1, 0)
        
        df_atr = df.withColumn(
            "prev_close", lag("close", 1).over(window_symbol)
        ).withColumn(
            "tr1", col("high") - col("low")
        ).withColumn(
            "tr2", spark_abs(col("high") - col("prev_close"))
        ).withColumn(
            "tr3", spark_abs(col("low") - col("prev_close"))
        ).withColumn(
            "true_range", spark_max(spark_max(col("tr1"), col("tr2")), col("tr3"))
        ).withColumn(
            "atr", avg("true_range").over(window_atr)
        ).withColumn(
            "atr_percent", (col("atr") / col("close")) * 100
        )
        
        return df_atr

    def calculate_all_indicators(self, df: DataFrame) -> DataFrame:
        """Calcule tous les indicateurs techniques"""
        print("🚀 Calcul de tous les indicateurs techniques...")
        
        # Moyennes mobiles
        df_sma = self.calculate_simple_moving_average(df)
        df_ema = self.calculate_exponential_moving_average(df_sma)
        
        # Oscillateurs
        df_rsi = self.calculate_rsi(df_ema)
        df_stoch = self.calculate_stochastic(df_rsi)
        df_williams = self.calculate_williams_r(df_stoch)
        
        # MACD
        df_macd = self.calculate_macd(df_williams)
        
        # Bollinger Bands
        df_bb = self.calculate_bollinger_bands(df_macd)
        
        # ATR
        df_atr = self.calculate_atr(df_bb)
        
        # Signaux composites
        df_signals = df_atr.withColumn(
            "composite_signal", when(
                (col("rsi_signal") == "OVERSOLD") & 
                (col("bb_signal") == "OVERSOLD") & 
                (col("macd_signal") == "BULLISH_CROSSOVER"),
                "STRONG_BUY"
            ).when(
                (col("rsi_signal") == "OVERBOUGHT") & 
                (col("bb_signal") == "OVERBOUGHT") & 
                (col("macd_signal") == "BEARISH_CROSSOVER"),
                "STRONG_SELL"
            ).when(
                (col("rsi_signal") == "OVERSOLD") | 
                (col("bb_signal") == "OVERSOLD"),
                "BUY"
            ).when(
                (col("rsi_signal") == "OVERBOUGHT") | 
                (col("bb_signal") == "OVERBOUGHT"),
                "SELL"
            ).otherwise("HOLD")
        )
        
        print("✅ Tous les indicateurs techniques calculés")
        return df_signals

    def generate_trading_signals(self, df: DataFrame) -> DataFrame:
        """Génère des signaux de trading basés sur les indicateurs"""
        print("📊 Génération des signaux de trading...")
        
        df_signals = df.withColumn(
            "signal_strength", when(col("composite_signal") == "STRONG_BUY", 4)
                            .when(col("composite_signal") == "STRONG_SELL", -4)
                            .when(col("composite_signal") == "BUY", 2)
                            .when(col("composite_signal") == "SELL", -2)
                            .otherwise(0)
        ).withColumn(
            "confidence_level", when(
                (col("rsi") < 30) & (col("bb_position") < 0.2) & (col("macd_line") > col("signal_line")),
                0.9
            ).when(
                (col("rsi") > 70) & (col("bb_position") > 0.8) & (col("macd_line") < col("signal_line")),
                0.9
            ).when(
                (col("rsi") < 40) | (col("bb_position") < 0.3),
                0.7
            ).when(
                (col("rsi") > 60) | (col("bb_position") > 0.7),
                0.7
            ).otherwise(0.5)
        )
        
        return df_signals

def main():
    """Fonction principale pour tester les indicateurs"""
    print("🚀 Démarrage du Technical Indicators Engine")
    
    # Initialisation Spark
    spark = SparkSession.builder \
        .appName("TechnicalIndicatorsEngine") \
        .getOrCreate()
    
    try:
        # Création d'un DataFrame de test
        test_data = [
            ("AAPL", "2025-01-01 09:00:00", 150.0, 155.0, 148.0, 152.0, 1000000),
            ("AAPL", "2025-01-01 09:01:00", 152.0, 158.0, 151.0, 156.0, 1200000),
            ("AAPL", "2025-01-01 09:02:00", 156.0, 160.0, 154.0, 158.0, 1100000),
        ]
        
        schema = StructType([
            StructField("symbol", StringType(), True),
            StructField("timestamp", StringType(), True),
            StructField("open", DoubleType(), True),
            StructField("high", DoubleType(), True),
            StructField("low", DoubleType(), True),
            StructField("close", DoubleType(), True),
            StructField("volume", IntegerType(), True)
        ])
        
        df = spark.createDataFrame(test_data, schema)
        
        # Initialisation du moteur
        engine = TechnicalIndicatorsEngine(spark)
        
        # Calcul de tous les indicateurs
        df_with_indicators = engine.calculate_all_indicators(df)
        
        # Génération des signaux
        df_with_signals = engine.generate_trading_signals(df_with_indicators)
        
        # Affichage des résultats
        print("📊 Résultats des indicateurs techniques:")
        df_with_signals.select(
            "symbol", "timestamp", "close", "rsi", "macd_line", "signal_line",
            "bb_upper", "bb_lower", "composite_signal", "signal_strength"
        ).show(truncate=False)
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)
        
    finally:
        spark.stop()
    
    print("🎉 Technical Indicators Engine terminé")

if __name__ == "__main__":
    main()
