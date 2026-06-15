@echo off
REM =============================================================================
REM Upload synthetic data to S3 (spec-compliant paths per REQ-DDL-05)
REM =============================================================================
REM Paths:
REM   energy_consumption: s3://bucket/raw/energy_consumption/reporting_year=Y/reporting_month=M/
REM   loan_portfolio:     s3://bucket/raw/loan_portfolio/reporting_year=Y/
REM   hr_metrics:         s3://bucket/raw/hr_metrics/reporting_year=Y/
REM =============================================================================

SET BUCKET=esg-data-raw-061039769766
SET DATA_DIR=%~dp0..\data\synthetic

echo === Uploading energy_consumption (24 partition folders) ===
aws s3 cp "%DATA_DIR%\energy_consumption" s3://%BUCKET%/raw/energy_consumption/ --recursive --exclude "*.csv"

echo === Uploading loan_portfolio (2 partition folders) ===
aws s3 cp "%DATA_DIR%\loan_portfolio" s3://%BUCKET%/raw/loan_portfolio/ --recursive --exclude "*.csv"

echo === Uploading hr_metrics (2 partition folders) ===
aws s3 cp "%DATA_DIR%\hr_metrics" s3://%BUCKET%/raw/hr_metrics/ --recursive --exclude "*.csv"

echo.
echo === Verifying uploads ===
aws s3 ls s3://%BUCKET%/raw/ --recursive --summarize

echo.
echo Done!
pause
