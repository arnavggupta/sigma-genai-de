# Chaos Log — Team Name: Sigma Squad
## Day 12 | Wednesday 4 June 2026

---

## Pre-Exercise Answer (fill before Phase 1)

**Question:** Should the 9 tool functions be one Lambda or separate Lambdas? What breaks if they are one?

**Your answer:**
Separate Lambdas are much better for security, performance, and blast radius. If they were one giant Lambda, a bug in the Snowflake query tool could crash the entire MCP server, taking down the Incident Report tool with it. Also, from a security standpoint, the Incident Report tool shouldn't need Snowflake access, but if they were combined, the single Lambda would need excessive IAM and Snowflake permissions (violating least privilege).

---

## Phase 2 — Manual Investigation

*You have 60 minutes. Find the root cause before the agents do.*

**Records in Kinesis (02:00–02:20 UTC):** N/A (Migrated to S3) records sent

**Records in S3 (02:00–02:20 UTC):** 17 files, 0 bytes total (zero-byte files)

**Records in Snowflake (02:00–02:20):** 0 rows loaded

---

**Failure timestamp:** 02:10 UTC (exact, from CloudWatch)

**What changed at that timestamp:**
A new version (v2) of the producer Lambda was published and the LIVE alias was shifted to it.

**Root cause (your hypothesis):**
The junior developer deployed a broken Lambda update (v2) that changed the date format and column names (like `merchant_name` to `merchant_nm`). When it attempted to write to S3, the pipeline corrupted the files or created 0-byte files. Snowflake's COPY INTO (or Snowpipe) process ignored these empty files, causing a complete halt in data loading despite the producer technically still running.

**Why no alert fired:**
No alerts fired because there were no traditional errors. The Lambda executed successfully without throwing exceptions, S3 received the files, and Snowflake didn't throw an error—it just loaded 0 rows. Since there was no "Row Divergence" alarm set up to compare incoming traffic vs loaded rows, it failed silently.

**Time taken to find this:** 15 minutes

---

**Signals you connected:**
1. Zero rows in Snowflake for the current hour.
2. S3 had new files, but they were exactly 0 bytes.
3. CloudWatch showed a Lambda version update at the exact same minute the zero-byte files started appearing.

**Signal you missed (fill this in Phase 3 after seeing the agent output):**
I didn't realize the specific schema changes (`merchant_nm`) inside the code were the root cause until the agent pointed out the specific payload differences.

---

## Phase 3 — Comparison

**What I found (Phase 2 manual):**
- Time taken: 15 minutes
- Root cause found? Yes
- SLA breach identified? Yes
- Prevention created? No

**What the agent found (Phase 3):**
- Time taken: 60 seconds
- Root cause found? Yes
- SLA breach identified? Yes
- Prevention created? Yes (3 live alarms)

**What I missed that the agent caught:**
The agent immediately rolled back the Lambda alias and quarantined the bad rows, whereas I only identified the issue but didn't take automated remediation steps.

**Why the agent caught it:**
The agent is an orchestration layer that isn't just an observer; it has active tool access (rollback, query, quarantine) and the Hardening Agent explicitly enforces preventative controls post-incident.

---

## Judgment Questions

**Forensics Agent:**
*The agent found the root cause by correlating Lambda version history with Snowflake query history. What is the one CloudWatch alarm that would have caught this at 02:12 instead of 09:03? Write it as a metric alarm definition.*

Your answer:
A row divergence alarm or an S3 file size alarm. Specifically, a CloudWatch Metric Math alarm checking `(Incoming_Requests) - (Snowflake_Rows_Loaded) > 100`. If this breaches, it means data is entering the system but not making it to the warehouse. Alternatively, an alarm on S3 zero-byte files `GreaterThanThreshold = 1`.

---

**Recovery Agent:**
*The recovery used transaction_id as the idempotency key. What happens if a legitimate duplicate transaction_id exists in the source data? How would you change the deduplication logic?*

Your answer:
If a legitimate duplicate exists, the MERGE INTO statement might fail or overwrite valid data unexpectedly. The deduplication logic should be improved to use a composite key (e.g., `transaction_id` + `transaction_date` + `merchant_name`) or introduce a robust row-hash comparison before merging to ensure we aren't discarding valid split transactions.

---

**Hardening Agent:**
*The sigma-lambda-version-change alarm fires on any Lambda error spike after a version change. Your team deploys 20 Lambda functions per day in prod. Would you keep this alarm? If yes, how do you stop it from spamming? If no, what replaces it?*

Your answer:
I would keep it, but it needs an anomaly detection band rather than a static threshold. Deployments often cause brief cold-start spikes or minor blips. We should change the alarm to evaluate over 3 consecutive 5-minute periods, or use AWS CloudWatch Anomaly Detection so it only fires if the error rate deviates significantly from the historical post-deployment baseline.

---

## Your Honest Reflection

**Which part of the manual investigation took longest and why:**
Tracking down the exact minute the Lambda version changed and manually querying the S3 bucket size took the most time because it required switching between AWS Console screens and running separate CLI commands.

**What would have happened if this hit prod at 2 AM with no agents:**
It would have caused a massive SLA breach. By the time engineers woke up and logged in, millions of records would be lost or quarantined, and we would spend 4+ hours manually recovering data.

**One thing you would add to this platform that none of the 6 agents currently do:**
A "Communication Agent" that automatically opens a Slack thread, tags the exact developer who pushed the broken code (by querying git commit history), and updates stakeholders every 5 minutes until the incident is fully resolved.

---

*Push this file to your team fork before the Phase 2 checkpoint.*
*Incomplete answers are flagged by validate_day12.py*
