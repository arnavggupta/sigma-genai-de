<<<<<<< HEAD
import shutil
import logging
import json
from datetime import datetime
=======
import os
import shutil
import json
import logging
from datetime import datetime
from pyspark.sql import SparkSession, Window
from pyspark.sql.functions import col, lit, broadcast, when, coalesce, sum, count, max, min, countDistinct
from pyspark.sql.types import StringType, FloatType, DateType
>>>>>>> faed0c6 (day7 done)

logging.basicConfig(level=logging.INFO)

def ingest_bronze(spark, input_path, output_path, run_date, run_id):
    try:
        logging.info("Starting ingest_bronze stage")
<<<<<<< HEAD
        partition_path = f"{output_path}/ingestion_timestamp={run_date}"
        shutil.rmtree(partition_path, ignore_errors=True)  # Idempotency: delete partition before write
        
        transactions_df = (spark.read.option("header", "true")
                           .option("inferSchema", "false")
                           .csv(input_path))
        
        transactions_df = (transactions_df.withColumn("ingestion_timestamp", lit(run_date))
                           .withColumn("source_file", lit("transactions.csv"))
                          .withColumn("pipeline_run_id", lit(run_id)))
        
        input_count = transactions_df.count()
        logging.info(f"[Stage: ingest_bronze] input_count: {input_count:,} rows")
        
        transactions_df.write.partitionBy("ingestion_timestamp").mode("overwrite").parquet(output_path)
        
        output_count = spark.read.parquet(output_path).where(col("ingestion_timestamp") == run_date).count()
        logging.info(f"[Stage: ingest_bronze] output_count: {output_count:,} rows")
        
=======
        transactions_df = (spark.read.format("csv")
                          .option("header", "true")
                          .option("inferSchema", "false")
                          .load(input_path)
                          .withColumn("ingestion_timestamp", lit(run_date))
                          .withColumn("source_file", lit("transactions.csv"))
                          .withColumn("pipeline_run_id", lit(run_id)))
        logging.info(f"[Stage: ingest_bronze] input_count: {transactions_df.count()} rows")

        merchants_df = (spark.read.format("csv")
                       .option("header", "true")
                        .option("inferSchema", "false")
                        .load(input_path.replace("transactions.csv", "merchants.csv"))
                        .withColumn("ingestion_timestamp", lit(run_date))
                       .withColumn("source_file", lit("merchants.csv"))
                       .withColumn("pipeline_run_id", lit(run_id)))
        logging.info(f"[Stage: ingest_bronze] input_count: {merchants_df.count()} rows")

        transactions_path = os.path.join(output_path, "transactions", f"ingestion_timestamp={run_date}")
        merchants_path = os.path.join(output_path, "merchants", f"ingestion_timestamp={run_date}")

        shutil.rmtree(transactions_path, ignore_errors=True)
        shutil.rmtree(merchants_path, ignore_errors=True)

        transactions_df.write.partitionBy("ingestion_timestamp").mode("overwrite").parquet(os.path.join(output_path, "transactions"))
        merchants_df.write.partitionBy("ingestion_timestamp").mode("overwrite").parquet(os.path.join(output_path, "merchants"))

        logging.info("Completed ingest_bronze stage")
>>>>>>> faed0c6 (day7 done)
    except Exception as e:
        logging.error(f"Error in ingest_bronze stage: {e}")
        raise

def transform_silver(spark, bronze_path, merchants_path, output_path, run_date):
    try:
        logging.info("Starting transform_silver stage")
<<<<<<< HEAD
        partition_path = f"{output_path}/transaction_date={run_date}"
        shutil.rmtree(partition_path, ignore_errors=True)  # Idempotency: delete partition before write
        
        transactions_df = (spark.read.parquet(bronze_path)
                          .where(col("ingestion_timestamp") == run_date))  # Partition pruning
        
        transactions_df = (transactions_df.withColumn("amount", col("amount").cast(FloatType()))
                          .withColumn("transaction_date", col("transaction_date").cast(DateType())))
        
        filtered_df = transactions_df.filter((col("transaction_id").isNotNull()) & (col("amount") >= 0))
        after_filter_count = filtered_df.count()
        logging.info(f"[Stage: transform_silver] after_filter_count: {after_filter_count:,} rows")
        
        deduped_df = (filtered_df.groupBy("transaction_id")
                  .agg(max_("ingestion_timestamp").alias("latest_timestamp")))
        deduped_transactions_df = filtered_df.join(deduped_df, on=["transaction_id", "ingestion_timestamp"], how="left_semi")
        after_dedup_count = deduped_transactions_df.count()
        logging.info(f"[Stage: transform_silver] after_dedup_count: {after_dedup_count:,} rows")
        
        merchants_df = (spark.read.option("header", "true")
                       .option("inferSchema", "false")
                       .csv(merchants_path)
                      .withColumn("merchant_id", col("merchant_id").cast(StringType())))
        merchants_df = merchants_df.cache()
        
        enriched_df = (deduped_transactions_df.join(merchants_df, on="merchant_id", how="left")
                      .withColumn("quality_flag", coalesce(col("merchant_name"), lit("UNMATCHED"))))
        
        enriched_df.write.partitionBy("transaction_date").mode("overwrite").parquet(output_path)
        
        output_count = spark.read.parquet(output_path).where(col("transaction_date") == run_date).count()
        logging.info(f"[Stage: transform_silver] output_count: {output_count:,} rows")
        
=======
        transactions_df = (spark.read.parquet(bronze_path)
                          .where(col("ingestion_timestamp") == run_date)
                          .withColumnRenamed("ingestion_timestamp", "transaction_date"))
        logging.info(f"[Stage: transform_silver] input_count: {transactions_df.count()} rows")

        merchants_df = (spark.read.parquet(merchants_path)
                      .where(col("ingestion_timestamp") == run_date)
                      .cache())
        logging.info(f"[Stage: transform_silver] input_count: {merchants_df.count()} rows")

        transactions_df = transactions_df.withColumn("amount", col("amount").cast(FloatType())) \
                                         .withColumn("transaction_date", col("transaction_date").cast(DateType())) \
                                        .withColumn("transaction_id", col("transaction_id").cast(StringType())) \
                                        .withColumn("merchant_id", col("merchant_id").cast(StringType()))

        transactions_df = transactions_df.filter((col("transaction_id").isNotNull()) & (col("amount") >= 0))
        logging.info(f"[Stage: transform_silver] after_filter_count: {transactions_df.count()} rows")

        transactions_dedup_df = (transactions_df.withColumn("row_number",
                                                            when(col("transaction_id").isNotNull(),
                                                                 (col("transaction_id") + col("ingestion_timestamp")).cast("double")))
                                               .orderBy("transaction_id", col("row_number").desc())
                                                .drop("row_number"))
        logging.info(f"[Stage: transform_silver] after_dedup_count: {transactions_dedup_df.count()} rows")

        enriched_df = (transactions_dedup_df.join(broadcast(merchants_df), "merchant_id", "left")
                       .withColumn("quality_flag",
                                   when(col("merchant_id").isNull(), "UNMATCHED").otherwise("CLEAN")))
        logging.info(f"[Stage: transform_silver] output_count: {enriched_df.count()} rows")

        enriched_path = os.path.join(output_path, "enriched", f"transaction_date={run_date}")
        shutil.rmtree(enriched_path, ignore_errors=True)

        enriched_df.write.partitionBy("transaction_date").mode("overwrite").parquet(output_path)

        logging.info("Completed transform_silver stage")
>>>>>>> faed0c6 (day7 done)
    except Exception as e:
        logging.error(f"Error in transform_silver stage: {e}")
        raise

<<<<<<< HEAD
def build_merchant_performance(spark, silver_path, output_path, run_date):
    try:
        logging.info("Starting build_merchant_performance stage")
        partition_path = f"{output_path}/date={run_date}"
        shutil.rmtree(partition_path, ignore_errors=True)  # Idempotency: delete partition before write
        
        silver_df = spark.read.parquet(silver_path).filter(col("date") == run_date)  # Partition pruning
        
        completed_df = silver_df.filter(col("status") == "COMPLETED")
        
        revenue_df = completed_df.groupBy("merchant_id", "merchant_name", "category", "city", "date") \
          .agg(sum("amount").alias("total_revenue"), count("*").alias("txn_count"))
        
        all_txns_df = silver_df.groupBy("merchant_id", "merchant_name", "category", "city", "date") \
          .agg(count("*").alias("total_txns"), count(when(col("status") == "FAILED", 1)).alias("failed_txns"))
        
        failure_rate_df = all_txns_df.withColumn("failure_rate_pct", (col("failed_txns") / col("total_txns") * 100).cast(FloatType()))
        
        merchant_performance_df = revenue_df.join(failure_rate_df, ["merchant_id", "merchant_name", "category", "city", "date"], "left") \
            .select("merchant_id", "merchant_name", "category", "city", "date", "total_revenue", "txn_count", "failure_rate_pct")
        
        merchant_performance_df.write.partitionBy("date").mode("overwrite").parquet(output_path)
        
=======
def build_merchant_performance(spark, silver_df, output_path, run_date):
    try:
        logging.info("Starting build_merchant_performance stage")
        completed_tx_df = silver_df.filter(col("status") == "COMPLETED")
        logging.info(f"[Stage: build_merchant_performance] input_count: {completed_tx_df.count()} rows")

        merchant_performance_df = completed_tx_df.groupBy(
            "merchant_id", "merchant_name", "category", "city", "date"
        ).agg(
            sum(col("amount")).alias("total_revenue"),
            count("*").alias("txn_count")
        )
        logging.info(f"[Stage: build_merchant_performance] after_aggregation_count: {merchant_performance_df.count()} rows")

        all_tx_df = silver_df.groupBy("merchant_id", "date").agg(
            count(when(col("status") == "FAILED", 1)).alias("failed_count"),
            count("*").alias("total_count")
        )

        failure_rate_df = all_tx_df.withColumn(
            "failure_rate_pct",
            (col("failed_count") / col("total_count") * 100).cast(FloatType())
        )

        final_df = merchant_performance_df.join(
            failure_rate_df, ["merchant_id", "date"], "left"
        ).select(
            "merchant_id", "merchant_name", "category", "city", "date",
            "total_revenue", "txn_count", "failure_rate_pct"
        )
        logging.info(f"[Stage: build_merchant_performance] output_count: {final_df.count()} rows")

        shutil.rmtree(output_path, ignore_errors=True)
        final_df.write.partitionBy("date").mode("overwrite").parquet(output_path)

        logging.info("Completed build_merchant_performance stage")
>>>>>>> faed0c6 (day7 done)
    except Exception as e:
        logging.error(f"Error in build_merchant_performance stage: {e}")
        raise

<<<<<<< HEAD
def build_customer_ltv(spark, silver_path, output_path):
    try:
        logging.info("Starting build_customer_ltv stage")
        
        silver_df = spark.read.parquet(silver_path)
        
        completed_df = silver_df.filter(col("status") == "COMPLETED")
        
        ltv_df = completed_df.groupBy("customer_id") \
          .agg(sum("amount").alias("total_spent"), count("*").alias("total_txns"), avg("amount").alias("avg_txn_value"), 
                 first("transaction_date").alias("first_txn_date"), last("transaction_date").alias("last_txn_date"), 
                 mode("payment_method").alias("preferred_payment_method"))
        
        ltv_df.write.mode("overwrite").parquet(output_path)
        
=======
def build_customer_ltv(spark, silver_df, output_path):
    try:
        logging.info("Starting build_customer_ltv stage")
        completed_tx_df = silver_df.filter(col("status") == "COMPLETED")
        logging.info(f"[Stage: build_customer_ltv] input_count: {completed_tx_df.count()} rows")

        customer_ltv_df = completed_tx_df.groupBy("customer_id").agg(
            sum(col("amount")).alias("total_spent"),
            count("*").alias("total_txns"),
            coalesce(max(col("payment_method")), lit(None)).alias("preferred_payment_method"),
            min(col("transaction_date")).alias("first_txn_date"),
            max(col("transaction_date")).alias("last_txn_date")
        )
        logging.info(f"[Stage: build_customer_ltv] output_count: {customer_ltv_df.count()} rows")

        shutil.rmtree(output_path, ignore_errors=True)
        customer_ltv_df.write.mode("overwrite").parquet(output_path)

        logging.info("Completed build_customer_ltv stage")
>>>>>>> faed0c6 (day7 done)
    except Exception as e:
        logging.error(f"Error in build_customer_ltv stage: {e}")
        raise

<<<<<<< HEAD
def build_daily_summary(spark, silver_path, output_path, run_date):
    try:
        logging.info("Starting build_daily_summary stage")
        partition_path = f"{output_path}/date={run_date}"
        shutil.rmtree(partition_path, ignore_errors=True)  # Idempotency: delete partition before write
        
        silver_df = spark.read.parquet(silver_path).filter(col("date") == run_date)  # Partition pruning
        
        total_revenue_df = silver_df.filter(col("status") == "COMPLETED") \
           .groupBy("date").agg(sum("amount").alias("total_revenue"), count("*").alias("total_txns"))
        
        unique_customers_df = silver_df.groupBy("date").agg(countDistinct("customer_id").alias("unique_customers"))
        
        unique_merchants_df = silver_df.groupBy("date").agg(countDistinct("merchant_id").alias("unique_merchants"))
        
        all_txns_df = silver_df.groupBy("date").agg(count("*").alias("total_txns"), count(when(col("status") == "FAILED", 1)).alias("failed_txns"))
        
        failure_rate_df = all_txns_df.withColumn("failure_rate_pct", (col("failed_txns") / col("total_txns") * 100).cast(FloatType()))
        
        daily_summary_df = total_revenue_df.join(unique_customers_df, "date", "inner") \
          .join(unique_merchants_df, "date", "inner") \
          .join(failure_rate_df, "date", "left") \
          .select("date", "total_revenue", "total_txns", "unique_customers", "unique_merchants", "failure_rate_pct")
        
        daily_summary_df.write.partitionBy("date").mode("overwrite").parquet(output_path)
        
=======
def build_daily_summary(spark, silver_df, output_path, run_date):
    try:
        logging.info("Starting build_daily_summary stage")
        daily_summary_df = silver_df.groupBy("date").agg(
            sum(when(col("status") == "COMPLETED", col("amount")).otherwise(lit(0))).alias("total_revenue"),
            count("*").alias("total_txns"),
            count(when(col("status") == "FAILED", 1)).alias("failed_txn_count"),
            countDistinct("customer_id").alias("unique_customers"),
            countDistinct("merchant_id").alias("unique_merchants")
        )
        logging.info(f"[Stage: build_daily_summary] after_aggregation_count: {daily_summary_df.count()} rows")

        daily_summary_df = daily_summary_df.withColumn(
            "failure_rate_pct",
            (col("failed_txn_count") / col("total_txns") * 100).cast(FloatType())
        ).select("date", "total_revenue", "total_txns", "unique_customers", "unique_merchants", "failure_rate_pct")

        shutil.rmtree(output_path, ignore_errors=True)
        daily_summary_df.write.partitionBy("date").mode("overwrite").parquet(output_path)

        logging.info("Completed build_daily_summary stage")
>>>>>>> faed0c6 (day7 done)
    except Exception as e:
        logging.error(f"Error in build_daily_summary stage: {e}")
        raise

def run_gold(spark, silver_path, gold_output_dir, run_date):
    try:
        logging.info("Starting run_gold stage")
<<<<<<< HEAD
        
        run_metadata = {"run_date": run_date, "silver_path": silver_path, "gold_output_dir": gold_output_dir}
        
        build_merchant_performance(spark, silver_path, f"{gold_output_dir}/merchant_performance", run_date)
        build_customer_ltv(spark, silver_path, f"{gold_output_dir}/customer_ltv")
        build_daily_summary(spark, silver_path, f"{gold_output_dir}/daily_summary", run_date)
        
        spark.sparkContext.parallelize([run_metadata]).write.json(f"{gold_output_dir}/run_metadata")
        
    except Exception as e:
        logging.error(f"Error in run_gold stage: {e}")
        raise

def main():
    try:
        logging.info("Starting main function")
        
        spark = (SparkSession.builder
                .appName("Sigma DataTech Transaction Analytics Pipeline")
                 .getOrCreate())
        
        input_path = "s3://sigma-datatech/bronze/transactions.csv"
        bronze_path = "s3://sigma-datatech/silver/transactions"
        merchants_path = "s3://sigma-datatech/bronze/merchants.csv"
        output_path = "s3://sigma-datatech/silver/transactions"
        gold_output_dir = "s3://sigma-datatech/gold"
        run_date = "2026-05-27"
        run_id = "run_id_20260527"
        
        started_at = datetime.now().isoformat()
        
        ingest_bronze(spark, input_path, bronze_path, run_date, run_id)
        transform_silver(spark, bronze_path, merchants_path, output_path, run_date)
        
        run_gold(spark, output_path, gold_output_dir, run_date)
        
        completed_at = datetime.now().isoformat()
        
        run_metadata = {
            "pipeline_name": "Sigma DataTech Transaction Analytics Pipeline",
            "run_date": run_date,
            "run_id": run_id,
            "run_status": "SUCCESS",
            "started_at": started_at,
            "completed_at": completed_at
        }
        
        with open(f"s3://sigma-datatech/metadata/run_metadata_{run_date}.json", "w") as f:
            json.dump(run_metadata, f)
            
    except Exception as e:
        logging.error(f"Error in main function: {e}")
        run_metadata["run_status"] = "FAILED"
        run_metadata["error_message"] = str(e)
        
        with open(f"s3://sigma-datatech/metadata/run_metadata_{run_date}.json", "w") as f:
            json.dump(run_metadata, f)
        
        raise

if __name__ == "__main__":
    main()
=======
        run_metadata = {
            "run_date": run_date,
            "status": "SUCCESS",
            "started_at": datetime.now().isoformat(),
            "tables": {
                "merchant_performance": {"row_count": 0},
                "customer_ltv": {"row_count": 0},
                "daily_summary": {"row_count": 0}
            }
        }

        silver_df = spark.read.parquet(silver_path)
        logging.info(f"[Stage: run_gold] input_count: {silver_df.count()} rows")

        build_merchant_performance(spark, silver_df, f"{gold_output_dir}/merchant_performance", run_date)
        build_customer_ltv(spark, silver_df, f"{gold_output_dir}/customer_ltv")
        build_daily_summary(spark, silver_df, f"{gold_output_dir}/daily_summary", run_date)

        run_metadata["completed_at"] = datetime.now().isoformat()

        with open(f"{gold_output_dir}/run_metadata_{run_date}.json", "w") as f:
            json.dump(run_metadata, f)

        logging.info("Completed run_gold stage")
    except Exception as e:
        run_metadata["status"] = "FAILED"
        run_metadata["error_message"] = str(e)
        run_metadata["completed_at"] = datetime.now().isoformat()

        with open(f"{gold_output_dir}/run_metadata_{run_date}.json", "w") as f:
            json.dump(run_metadata, f)

        logging.error(f"Error in run_gold stage: {e}")
        raise

def main(spark, input_path, merchants_path, output_path, run_date, run_id):
    try:
        logging.info("Starting main pipeline")
        ingest_bronze(spark, input_path, output_path, run_date, run_id)
        transform_silver(spark, os.path.join(output_path, "transactions"), os.path.join(output_path, "merchants"), output_path, run_date)
        run_gold(spark, os.path.join(output_path, "enriched"), output_path, run_date)
        logging.info("Completed main pipeline")
    except Exception as e:
        logging.error(f"Error in main pipeline: {e}")
        raise

if __name__ == "__main__":
    spark = (SparkSession.builder
            .appName("Sigma DataTech Transaction Analytics Pipeline")
             .getOrCreate())

    input_path = "s3://your-bucket/input/"
    merchants_path = "s3://your-bucket/merchants/"
    output_path = "s3://your-bucket/output/"
    run_date = "2026-05-27"
    run_id = "run-001"

    main(spark, input_path, merchants_path, output_path, run_date, run_id)
>>>>>>> faed0c6 (day7 done)
