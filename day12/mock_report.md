# Incident Report: Missing Data in Silver Layer

## Overview
A severe data discrepancy was observed between the Kinesis incoming stream and the Snowflake `TRANSACTIONS` table.

Records missing: 847
Records recovered: 847

## Root Cause
A silent failure was introduced via the `v2` deployment of the Lambda `sigma-kinesis-producer`. The new Lambda code mapped the incoming field `merchant_name` to `merchant_nm`, which bypassed initial schema checks but failed silently during the Snowflake loading process because the columns did not match the target schema. This resulted in 847 valid JSON files landing in S3 but zero rows loading into Snowflake for the given time window.

## Fix Applied
1. Rolled back the Lambda function `sigma-kinesis-producer` alias from `v2` back to the stable `v1` version.
2. Filtered S3 for all files created between the failure window.
3. Passed the S3 `records_s3_key` of the 847 missing records to the Recovery Agent, which bypassed the Kinesis buffer and loaded the data directly into Snowflake.

## Next Steps
We have instantiated the CloudWatch alarms to detect any future divergence between the S3 Object Count and Snowflake Row Count.
