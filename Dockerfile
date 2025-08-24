# Dockerfile
FROM apache/airflow:2.7.1

# Install the postgres provider package
RUN pip install --no-cache-dir apache-airflow-providers-postgres