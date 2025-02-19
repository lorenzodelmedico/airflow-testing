from datetime import datetime, timedelta
import logging
import requests
import pandas as pd

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator

# Default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2023, 1, 1),
    'retries': 2,
    'retry_delay': timedelta(minutes=1),
    'email_on_failure': False,
    'email_on_retry': False,
    'email': ['your_email@example.com'],
}

dag = DAG(
    'etl_pipeline',
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False,
)

# Task 1.1: Ingest CSV from Cloud Storage
def ingest_csv(**kwargs):
    tmp_path = '/tmp/CO2_per_capita.csv'
    try: 
        csv_url = 'https://storage.googleapis.com/schoolofdata-datasets/Data-Analysis.Data-Visualization/CO2_per_capita.csv'
        df = pd.read_csv(csv_url, sep=";", engine='python', on_bad_lines='skip')
        df.to_csv(tmp_path, index=False)
        logging.info(f'CSV ingested and saved to {tmp_path}')
    except Exception:
        logging.exception("Error ingesting CSV")
    return tmp_path

ingest_csv_task = PythonOperator(
    task_id='ingest_csv',
    python_callable=ingest_csv,
    dag=dag,
)

# Task 1.2: Ingest data via API request to REST Countries API
def ingest_api(**kwargs):
    api_url = 'https://restcountries.com/v3.1/all'
    try: 
        response = requests.get(api_url)
        data = response.json()
        tmp_path = '/tmp/restcountries.json'
        with open(tmp_path, 'w') as f:
            f.write(str(data))
        logging.info(f'API data ingested and saved to {tmp_path}')
    except Exception:
        logging.exception("Error ingesting API")
    return tmp_path

ingest_api_task = PythonOperator(
    task_id='ingest_api',
    python_callable=ingest_api,
    dag=dag,
)

# Task 1.3: Ingest data from PostgreSQL
def ingest_postgres(**kwargs):
    # In a real-world scenario, use Airflow's PostgresHook to query your database.
    # Here we simulate ingestion.
    tmp_path = '/tmp/postgres_data.csv'
    try:
        data = {'id': [1, 2, 3], 'value': ['A', 'B', 'C']}
        df = pd.DataFrame(data)
        df.to_csv(tmp_path, index=False)
        logging.info(f'Postgres data ingested and saved to {tmp_path}')
    except Exception:
        logging.exception("Error ingesting CSV")
    return tmp_path

ingest_postgres_task = PythonOperator(
    task_id='ingest_postgres',
    python_callable=ingest_postgres,
    dag=dag,
)

# Task 2: Data Validation
def validate_data(**kwargs):
    # For demonstration, we'll assume validation is based on a simple check.
    # In practice, you would load the ingested files and perform checks (e.g., for missing values).
    validation_passed = False  # Stupid validation, always passes
    if validation_passed:
        logging.info("Validation passed.")
        return 'load_data'
    else:
        logging.error("Validation failed.")
        return 'send_alert'

validate_task = BranchPythonOperator(
    task_id='validate_data',
    python_callable=validate_data,
    dag=dag,
)

# Task 3: Load data into BigQuery if validation passes
load_data_task = BigQueryInsertJobOperator(
    task_id='load_data',
    configuration={
        "query": {
            "query": "SELECT 'Data loaded successfully' AS status",  # Replace with your actual load job SQL.
            "useLegacySql": False,
        }
    },
    dag=dag,
)

# Task 4: Send an alert if validation fails
def send_alert(**kwargs):
    # In practice, use EmailOperator or SlackAPIPostOperator.
    logging.error("Data validation failed. Alert sent!")
    logging.exception("Data validation failed.")
    return "alert_sent"

send_alert_task = PythonOperator(
    task_id='send_alert',
    python_callable=send_alert,
    dag=dag,
)

# Define dependencies:
# Ingest all data sources before validation.
[ingest_csv_task, ingest_api_task, ingest_postgres_task] >> validate_task

# Branching: if validation returns 'load_data', run load_data_task; if 'send_alert', run send_alert_task.
validate_task >> [load_data_task, send_alert_task]
