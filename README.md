# Automated ETL Pipeline

A universal, configuration-driven ETL pipeline designed to automatically extract, clean, transform, validate, classify, and load CSV datasets into SQLite databases.

The project supports multiple dataset types through intelligent schema detection, automated data transformation, advanced data-quality validation, and configurable quality scoring.

---

## 1. Project Overview

The Automated ETL Pipeline is designed to process different CSV datasets without requiring manually defined transformation rules for every new dataset.

The pipeline identifies column structures, detects logical data types, normalizes data, performs validation, classifies records, calculates quality scores, and generates structured output reports.

### Supported Datasets

- Retail sales
- Employee records
- Student records
- Hospital patient records
- Contact validation datasets
- Custom CSV datasets

---

## 2. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Pipeline development |
| Pandas | Data manipulation and processing |
| SQLite | Database storage |
| SQL | Data analysis |
| Pytest | Automated testing |
| JSON | Configuration and reporting |
| Git | Version control |
| GitHub | Source-code management |

---

## 3. Project Architecture

```text
Automated ETL Pipeline/
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── rejected/
│   └── universal_pipeline.db
│
├── reports/
│   └── Quality reports (JSON)
│
├── logs/
│
├── sql/
│   ├── retail_sales_analysis.sql
│   ├── employee_analysis.sql
│   └── student_analysis.sql
│
├── src/
│   ├── universal/
│   │   ├── universal_pipeline.py
│   │   ├── universal_extract.py
│   │   ├── universal_transform.py
│   │   ├── universal_validate.py
│   │   ├── universal_load.py
│   │   ├── schema_detector.py
│   │   ├── text_handler.py
│   │   ├── missing_value_handler.py
│   │   ├── numeric_handler.py
│   │   ├── datetime_handler.py
│   │   ├── boolean_handler.py
│   │   ├── financial_handler.py
│   │   ├── conversion_tracker.py
│   │   ├── issue_tracker.py
│   │   ├── classification_engine.py
│   │   ├── quality_scorer.py
│   │   └── report_generator.py
│   │
│   ├── extract.py
│   ├── transform.py
│   ├── validate.py
│   ├── load.py
│   ├── config.py
│   ├── logger.py
│   └── main.py
│
├── tests/
│
├── config.json
├── requirements.txt
└── README.md
```

---

## 4. ETL Workflow

The universal pipeline follows five major stages.

### Stage 1: Extraction

- Accept CSV input files.
- Resolve input file paths.
- Detect CSV encoding.
- Detect CSV delimiters.
- Validate CSV structure.
- Extract records and columns.

### Stage 2: Transformation

- Standardize column names.
- Normalize text values.
- Handle missing-value representations.
- Automatically detect logical data types.
- Convert numeric values.
- Process financial values and currency units.
- Parse date and timestamp formats.
- Standardize Boolean values.
- Protect identifier columns.
- Track conversion failures.

### Stage 3: Validation

The pipeline uses seven validation modules:

1. Missing-value validation.
2. Duplicate validation.
3. Identifier validation.
4. Conversion-failure validation.
5. Numeric validation.
6. Date validation.
7. Contact validation.

Additional checks include:

- Invalid email addresses.
- Invalid phone numbers.
- Numeric outliers.
- Numeric range violations.
- Invalid dates.
- Future dates.
- Date-range violations.
- Chronological violations.
- Timezone mismatches.

### Stage 4: Intelligent Classification

Records are classified into three categories.

| Classification | Description |
|---|---|
| VALID | Records passing applicable validation rules |
| WARNING | Records containing non-critical data-quality issues |
| REJECTED | Records containing critical data-quality issues |

The classification engine also generates record-level explanations and classification summaries.

### Stage 5: Database Loading and Reporting

The pipeline:

- Loads eligible VALID and WARNING records.
- Creates dynamically structured SQLite tables.
- Generates processed CSV files.
- Separates valid, warning and rejected records.
- Generates comprehensive JSON quality reports.

---

## 5. Intelligent Data Quality Scoring

The pipeline includes a configurable data-quality scoring engine.

Each record receives a score between 0 and 100.

### Scoring Formula

Quality Score = Maximum Score − Total Issue Penalties

The minimum possible score is zero.

### Default Quality Grades

| Score | Grade |
|---|---|
| 90–100 | EXCELLENT |
| 75–89 | GOOD |
| 60–74 | FAIR |
| 40–59 | POOR |
| 0–39 | CRITICAL |

### Configurable Penalties

Scoring penalties are maintained in `config.json`.

Examples:

| Issue | Default Penalty |
|---|---:|
| Invalid email | 10 |
| Invalid phone | 10 |
| Missing value | 8 |
| Conversion failure | 12 |
| Numeric outlier | 8 |
| Future date | 8 |
| Duplicate record | 40 |
| Empty record | 50 |

The scoring engine supports custom penalty values without modifying the Python scoring module.

### Record-Level Scoring

Each processed record receives:

- `quality_status`
- `quality_reasons`
- `quality_score`
- `quality_grade`

### Dataset-Level Scoring

The pipeline calculates:

- Average dataset quality score.
- Overall dataset quality grade.
- Minimum record score.
- Maximum record score.
- Quality-grade distribution.

Classification and numerical quality scoring operate independently.

---

## 6. Configuration Management

The project uses `config.json` for centralized configuration.

It maintains:

- Active dataset selection.
- Dataset profiles.
- Input and output directories.
- Database settings.
- Validation requirements.
- Transformation settings.
- Quality-scoring penalties.
- Severity-based fallback penalties.

This approach makes the pipeline easier to maintain and extend.

---

## 7. Supported Output Formats

| Output | Purpose |
|---|---|
| Processed CSV | Complete transformed and classified records |
| Valid CSV | Valid records |
| Warning CSV | Records containing warnings |
| Rejected CSV | Rejected records |
| JSON | Detailed data-quality and transformation reports |
| SQLite | Structured database storage |

The universal pipeline uses a dynamically generated table for each input dataset.

---

## 8. Running the Pipeline

### Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

### Universal automated pipeline

Place your CSV file inside:

```text
data/raw/
```

Run:

```powershell
python src/main.py --file your_dataset.csv
```

Example:

```powershell
python src/main.py --file contact_validation_test.csv
```

The universal pipeline automatically performs extraction, transformation, validation, classification, quality scoring, database loading and report generation.

### Existing dataset profiles

Retail:

```powershell
python src/main.py --dataset retail
```

Employee:

```powershell
python src/main.py --dataset employee
```

Student:

```powershell
python src/main.py --dataset student
```

---

## 9. Database

The project uses SQLite for persistent data storage.

The universal pipeline stores processed eligible records in:

```text
data/universal_pipeline.db
```

The table name is generated from the input CSV filename.

The database stores:

- Original dataset columns.
- Transformed values.
- Quality classification.
- Quality scores.
- Quality grades.
- Quality explanations.

---

## 10. Automated Testing

The project uses Pytest for unit testing and integration testing.

Test coverage includes:

- Extraction.
- Transformation.
- Schema detection.
- Data-type conversion.
- Missing-value handling.
- Date and numeric processing.
- Validation modules.
- Issue tracking.
- Classification.
- Quality scoring.
- Database loading.
- Pipeline integration.

### Run all tests

```powershell
python -m pytest -v
```

### Run quality scoring tests

```powershell
python -m pytest tests/test_quality_scorer.py -v
```

### Run classification tests

```powershell
python -m pytest tests/test_classification_engine.py -v
```

**Latest confirmed full regression result: 394 tests passed.**

---

## 11. Logging

Centralized logging is implemented to monitor pipeline execution.

Logs capture:

- Extraction activities.
- Transformation operations.
- Validation results.
- Classification results.
- Database loading.
- Pipeline execution errors.

Log files are maintained in the `logs/` directory.

---

## 12. Skills Demonstrated

- Python programming.
- Pandas data processing.
- Universal ETL architecture.
- Automated schema detection.
- Data cleaning and transformation.
- Data-quality engineering.
- Intelligent record classification.
- Configurable quality scoring.
- JSON configuration management.
- SQLite database integration.
- SQL analytics.
- Unit and integration testing.
- Git and GitHub.

---

## 13. Future Improvements

Potential future enhancements include:

- Automated file discovery and monitoring.
- Scheduled pipeline execution.
- Failure recovery and retry mechanisms.
- Pipeline execution history.
- Dashboard integration.
- Cloud storage integration.
- Azure Data Engineering integration.
- Apache Airflow orchestration.
- Large-scale processing with Apache Spark.
- Advanced data-quality monitoring.

---

## 14. Project Objective

The primary objective of this project is to develop a reusable and extensible ETL system capable of processing different CSV datasets with minimal manual intervention.

The project demonstrates practical data engineering concepts, including automated extraction, intelligent transformation, data validation, classification, quality measurement, database integration, reporting and automated testing.
