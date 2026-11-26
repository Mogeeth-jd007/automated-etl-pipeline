
# ETL Performance Benchmarking and Scalability Analysis

## 1. Overview

The Universal Automated ETL Pipeline includes a performance benchmarking framework to evaluate processing speed, memory consumption, throughput, and scalability.

The framework uses synthetic CSV datasets and executes the actual batch ETL pipeline in isolated temporary environments.

## 2. Technology Stack

- Python
- Pandas
- psutil
- SQLite
- JSON
- Pytest

## 3. Benchmark Configuration

Three benchmark workloads were executed.

| Configuration | CSV Files | Records per File | Total Records |
|---|---:|---:|---:|
| Small | 10 | 100 | 1,000 |
| Medium | 50 | 100 | 5,000 |
| Large | 100 | 100 | 10,000 |

## 4. Benchmark Results

| Metric | 10 Files | 50 Files | 100 Files |
|---|---:|---:|---:|
| Execution Time (seconds) | 5.0393 | 15.6074 | 30.7612 |
| Average Time per File | 0.5039 | 0.3121 | 0.3076 |
| Throughput (files/sec) | 1.9844 | 3.2036 | 3.2508 |
| Peak Memory (MB) | 88.48 | 90.09 | 91.95 |
| Successful Files | 10 | 50 | 100 |
| Failed Files | 0 | 0 | 0 |
| Success Rate | 100% | 100% | 100% |

## 5. Performance Analysis

### Execution Time

The total execution time increases with the number of input files.

Processing 100 files required approximately 30.76 seconds.

### Throughput

Throughput improved from 1.9844 files per second at 10 files to 3.2508 files per second at 100 files.

This indicates improved workload utilization at larger batch sizes.

### Memory Consumption

Peak sampled process-tree memory increased from 88.48 MB to 91.95 MB.

The relatively small increase suggests stable memory consumption across the tested workloads.

### Reliability

All 160 benchmarked CSV files were successfully processed.

No failed or skipped files were reported.

## 6. Consolidated Results

- Benchmark configurations: 3
- Total files tested: 160
- Total records tested: 16,000
- Successful files: 160
- Failed files: 0
- Overall success rate: 100%
- Highest measured throughput: 3.2508 files/second
- Highest sampled memory consumption: 91.95 MB

## 7. Benchmark Execution Commands

Run the individual benchmarks:

```powershell
python -m benchmarks.benchmark_runner --scales 10
python -m benchmarks.benchmark_runner --scales 50
python -m benchmarks.benchmark_runner --scales 100
```

Generate the consolidated performance report:

```powershell
python -m benchmarks.performance_analyzer
```

Run performance analyzer tests:

```powershell
python -m pytest tests/test_performance_analyzer.py -v
```

## 8. Generated Reports

Individual benchmark reports:

`reports/performance_benchmark_*.json`

Consolidated performance report:

`reports/performance_comparison_report.json`

## 9. Limitations

- Benchmarks use synthetic datasets.
- Each CSV contains 100 records.
- Execution time includes subprocess startup overhead.
- Memory consumption is sampled process-tree RSS, not an exact continuous peak.
- Results represent the tested machine and environment.
- Larger workloads and repeated benchmark runs are required before establishing production capacity.

## 10. Conclusion

The Universal Automated ETL Pipeline successfully processed 10, 50, and 100 CSV files with a 100% success rate in the tested workloads.

The benchmarking framework provides measurable evidence of processing performance, throughput, memory consumption, and scalability.
