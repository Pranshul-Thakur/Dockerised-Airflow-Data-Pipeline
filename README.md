# Dockerized Stock Data Pipeline with Airflow

This project implements a complete, containerized data pipeline that automatically fetches daily stock market data from the Yahoo Finance API, processes it, and stores it in a PostgreSQL database. The entire process is orchestrated by Apache Airflow and is fully containerized using Docker for easy, one-command deployment.

## Features

- **Automated Data Fetching**: Schedules hourly data ingestion from the free and reliable Yahoo Finance (yfinance) library.

- **Robust Orchestration**: Uses Apache Airflow running in a resilient standalone mode for scheduling, monitoring, and execution.

- **Persistent Data Storage**: Upserts data into an external PostgreSQL table, creating a historical record of daily stock prices.

- **Custom Containerized Environment**: Utilizes a custom Dockerfile to create a bespoke Airflow image with all necessary dependencies pre-installed, managed by Docker Compose for one-command deployment.

- **Resilient by Design**: Implements comprehensive error handling within the data fetching script and leverages Airflow's built-in retry mechanism.

- **Configurable**: Key parameters like stock symbols and the pipeline schedule are easily configured through environment variables in the docker-compose.yml file.

## Architectural Decisions and Troubleshooting Journey

The final architecture of this project was the result of an iterative development process, several adaptions were made to the original design. The hurdles are mentioned below as followed:

### Phase 1: Initial Approach and Network Failure

- **Initial Goal**: To create a fully containerized environment with separate services for Airflow and PostgreSQL, using the official postgres Docker image.
- **Problem Encountered**: A persistent, low-level network DNS error (`no such host`) prevented Docker from successfully pulling the postgres image from Docker Hub. Standard fixes (restarting Docker, changing host DNS, flushing cache) were unsuccessful, indicating a deep, stubborn issue with the host's Docker networking environment.
- **Decision**: Rather than continue to debug a fundamental host environment issue, the architecture was pivoted to bypass the problem. I decided to use a PostgreSQL server already installed locally on the host machine, eliminating the need to pull the postgres image.

---

### Phase 2: The Pivot to Local Postgres and the "Invisible" Error

- **New Goal**: Run the Airflow services in Docker and connect them to the local PostgreSQL database on the host machine.
- **Implementation**: The `docker-compose.yml` was modified to remove the postgres service, and the `DATABASE_URL` was configured to point to `host.docker.internal`.
- **Problem Encountered**: A bizarre and highly persistent issue arose where the Airflow containers would not read any environment variables. This caused Airflow to repeatedly fall back to its default SQLite configuration, resulting in `KeyError` exceptions for missing variables and `AirflowConfigException` errors due to executor incompatibility.

I systematically ruled out:
  - Incorrect `.env` filename
  - Incorrect `.env` file location
  - Incorrect `.env` file encoding (by recreating the file from scratch)
  - A broken Docker installation (by performing a full, clean reinstallation)

- **Final Diagnosis**: The root cause was identified as invalid whitespace characters (non-breaking spaces) used for indentation in the `docker-compose.yml` file, likely introduced via copy-pasting. The YAML parser silently failed to read the misformatted configuration blocks, leading to the containers starting with no environment variables.

---

### Phase 3: Final Architecture and Dependency Management

- **New Goal**: Create the most robust and simple configuration possible to eliminate any remaining environmental factors.
- **Implementation**:
  - I switched to the Airflow standalone command, which runs the scheduler, webserver, and worker in a single, resilient process ideal for local development.
  - The Airflow metadata backend was set to SQLite (managed internally by the standalone command) to simplify the core Airflow setup. The external PostgreSQL database was reserved solely for storing the final pipeline data, creating a clear separation of concerns.

- **Problem Encountered**: With the system running, I encountered a series of classic Python dependency and code-level bugs:
  - **API Paywall**: The initial data source (Alpha Vantage) returned an error indicating its endpoint was now a premium feature.
  - **Data Source Pivot**: Switched the pipeline to use the yfinance library for Yahoo Finance data.
  - **Dependency Conflict**: The yfinance library installed a sub-dependency (`multitasking`) with a bug that used incompatible Python 3.9+ syntax in our Python 3.8 environment, causing a `TypeError`.

- **Final Solution**: To definitively solve all dependency issues, a `Dockerfile` was created. This builds a custom Airflow image where all Python libraries (`yfinance`, `apache-airflow-providers-postgres`) are pre-installed, and the problematic multitasking library is pinned to a known-good version (`0.0.11`). This is the professional standard for creating reproducible and reliable containerized environments.

This iterative process led to the final, robust architecture that successfully meets all project requirements.

## Prerequisites

Before you begin, ensure you have the following installed and running on your system:

- Docker Desktop
- A local installation of PostgreSQL Server

## Project Structure

```
.
├── dags/
│   ├── stock_dag.py             # Airflow DAG definition
│   └── scripts/
│       └── fetch_and_store.py   # Python script for data fetching and processing
├── docker-compose.yml           # Docker Compose configuration
└── Dockerfile                   # Custom Docker image definition
```

## Setup and Installation

Follow these steps to set up and run the pipeline.

### 1. Prepare the PostgreSQL Database

Before launching, you must manually create the database, user, and table for the stock data. Connect to your local PostgreSQL instance as a superuser and run the following SQL commands:

```sql
-- Create the user and database
CREATE USER stocks WITH PASSWORD 'stocks_pw';
CREATE DATABASE stockdb;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE stockdb TO stocks;

-- Connect to the new database (\c stockdb) before running the next commands
CREATE TABLE IF NOT EXISTS stock_prices (
  symbol      TEXT        NOT NULL,
  ts          DATE        NOT NULL,
  open        NUMERIC,
  high        NUMERIC,
  low         NUMERIC,
  close       NUMERIC,
  volume      BIGINT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (symbol, ts)
);

GRANT ALL PRIVILEGES ON TABLE stock_prices TO stocks;
```

### 2. Configure PostgreSQL Network Access

Ensure your PostgreSQL server will accept connections from Docker. Add the following line to your pg_hba.conf file and restart your PostgreSQL service.

```
host    all             all             172.17.0.0/16           md5
```

## Running the Pipeline

### 1. Build the Custom Docker Image

This command reads the Dockerfile and builds your personalized Airflow image with all dependencies installed. This may take a few minutes.

```bash
docker-compose build
```

### 2. Launch the Airflow Service

This command starts the Airflow container in the background.

```bash
docker-compose up -d
```

## How to Verify

1. **Access the Airflow UI**: Wait 1-2 minutes for the service to initialize, then open your browser and navigate to http://localhost:8081.

2. **Login**: Use the credentials admin / admin.

3. **Check the DAG**: The stock_pipeline DAG should be visible with no import errors.

4. **Trigger a Run**: Click the Play button to start a manual run.

5. **Check the Data**: After the run succeeds (turns green), connect to your local stockdb database and run `SELECT * FROM stock_prices;` to see the results.