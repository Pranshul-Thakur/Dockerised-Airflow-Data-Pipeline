import os
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from scripts.fetch_and_store import run_once

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def fetch_task():
    symbols = [s.strip().upper() for s in os.getenv("SYMBOLS", "AAPL").split(",") if s.strip()]
    run_once(symbols)

with DAG(
    'stock_pipeline',
    default_args=default_args,
    description='Fetch stock data from Alpha Vantage and upsert into Postgres',
    schedule_interval=os.getenv("SCHEDULE_CRON", "0 * * * *"),
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['stocks'],
) as dag:
    fetch_and_store = PythonOperator(
        task_id='fetch_and_store',
        python_callable=fetch_task
    )