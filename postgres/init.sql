-- Create airflow user
CREATE USER airflow WITH PASSWORD 'airflow';
CREATE DATABASE airflow WITH OWNER airflow;
GRANT ALL PRIVILEGES ON DATABASE airflow TO airflow;