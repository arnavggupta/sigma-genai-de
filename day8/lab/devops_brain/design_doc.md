<<<<<<< HEAD
# Data Pipeline Design Document

## What This Pipeline Does
This pipeline ingests transaction data from both clean and dirty sources, processes it, and stores it in three layers: Bronze, Silver, and Gold. The Bronze layer stores raw data, the Silver layer stores cleaned and enriched data, and the Gold layer stores aggregated metrics.

## Data Flow Diagram

```
+----------------+      +--------------------+      +--------------------+      +--------------------+
| TRANSACTIONS   | ---> | bronze_transactions| ---> | silver_transactions| ---> | gold_merchant_perf |
| (Clean & Dirty)|      |                    |      |                    |      |                    |
+----------------+      +--------------------+      +--------------------+      +--------------------+
                                                                                     |
                                                                                 +--------------------+
                                                                                 | gold_daily_summary  |
                                                                                 +--------------------+
```

## Key Design Decisions
- **Layered Approach**: The pipeline uses a three-tier architecture (Bronze, Silver, Gold) to separate raw data, cleaned data, and aggregated metrics.
- **Data Enrichment**: The Silver layer enriches transaction data by joining it with merchant information, making it more useful for analysis.
- **Aggregation**: The Gold layer computes metrics like merchant performance and daily summaries, providing valuable insights.
- **Data Quality Flags**: The Silver layer includes quality flags to distinguish between clean and potentially problematic data.

## Known Limitations
- **Data Duplication**: The pipeline does not handle duplicate transactions within a single run.
- **Limited Error Handling**: The pipeline has minimal error handling, which could be improved for robustness.
- **Single-Run Processing**: The pipeline processes all transactions in a single run, which may not be suitable for very large datasets.
- **Static Merchant Data**: Merchant data is loaded once and not updated unless the pipeline is rerun.

## Dependencies
- **DuckDB**: The pipeline uses DuckDB for data storage and processing.
- **MERCHANTS**: A list of merchant data used for enriching transactions.
- **TRANSACTIONS_CLEAN and TRANSACTIONS_DIRTY**: Lists of clean and dirty transaction data, respectively.
=======
# Pipeline Design Document

## What This Pipeline Does

This pipeline ingests transaction data from both clean and dirty sources, processes it through multiple stages (Bronze, Silver, Gold), and generates merchant performance metrics and daily summaries.

## Data Flow Diagram

```plaintext
+---------------------+       +---------------------+       +---------------------+       +---------------------+
| Source: TRANSACTIONS| --->  | Bronze: bronze_txns | --->  | Silver: silver_txns | --->  | Gold: gold_metrics  |
| (Clean & Dirty)     |       |                     |       |                     |       |                      |
+---------------------+       +---------------------+       +---------------------+       +---------------------+
                                                                                           |
                                                                                           |
                                                                                           |
                                                                                           |
+---------------------+       +---------------------+       +---------------------+       +---------------------+
| Source: MERCHANTS   | --->  | Bronze: bronze_txns | --->  | Silver: silver_txns | --->  | Gold: gold_metrics   |
|                     |       |                     |       |                     |       |                      |
+---------------------+       +---------------------+       +---------------------+       +---------------------+
```

## Key Design Decisions

- **Layered Processing**: The pipeline uses a three-tier (Bronze, Silver, Gold) approach to ensure data quality and transformation are handled in distinct stages.
- **Quality Flags**: Introduced quality flags in the Silver layer to distinguish between clean and potentially problematic data.
- **Aggregation at Gold**: Aggregation and reporting are performed in the Gold layer to provide insights and metrics.
- **DuckDB for Storage**: DuckDB is chosen for its performance and ease of use for analytical queries.

## Known Limitations

- **Single-threaded**: The pipeline runs sequentially, which may not be optimal for large datasets.
- **No Error Handling**: Basic error handling is implemented, but more robust mechanisms could be added.
- **Static Merchant Data**: Merchant data is loaded once and not updated dynamically.
- **Limited Data Validation**: The pipeline assumes the input data is in a specific format and does not perform extensive validation.

## Dependencies

- **DuckDB**: For data storage and querying.
- **MERCHANTS**: A list of merchant data used for enriching transaction records.
- **TRANSACTIONS_CLEAN & TRANSACTIONS_DIRTY**: Source data for the pipeline.
- **AWS S3**: For potential future data storage and retrieval (not currently used in the provided code).
>>>>>>> b8ad18c (day8 Done)
