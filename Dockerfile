# Dockerfile
FROM apache/airflow:2.7.1

# Install the postgres provider, yfinance, and a compatible version of multitasking
RUN pip install --no-cache-dir apache-airflow-providers-postgres yfinance "multitasking==0.0.11"