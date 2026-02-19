import sqlite3
import json
import os
from conductor.client.worker.worker_task import worker_task

# Create database and insert fake data
def create_fake_database():
    if os.path.exists('fake_people.db'):
        return  # Database already exists, skip creation

    conn = sqlite3.connect('fake_people.db')
    cursor = conn.cursor()

    # Create table
    cursor.execute('''CREATE TABLE IF NOT EXISTS people (
        name TEXT,
        surname TEXT,
        birth_date TEXT,
        zip_code TEXT
    )''')

    # Insert fake data
    fake_data = [
        ('John', 'Doe', '1990-01-01', '12345'),
        ('Jane', 'Smith', '1985-05-15', '67890'),
        ('Bob', 'Johnson', '1992-03-20', '11111'),
        ('Alice', 'Williams', '1988-12-10', '22222'),
        ('Charlie', 'Brown', '1995-07-04', '33333')
    ]

    cursor.executemany('INSERT INTO people VALUES (?, ?, ?, ?)', fake_data)
    conn.commit()
    conn.close()


@worker_task(task_definition_name='query_sqlite')
def execute_sqlite_query(connection_string:str, query:str):
    """
    Executes a SQLite SELECT query on the specified database and returns the results as JSON.

    Args:
        connection_string (str): The SQLite database file path or connection string.
        query (str): The SQL SELECT query to execute.

    Returns:
        str: JSON string containing the query results.
    """
    try:
        db_path = os.path.join(os.getcwd(), connection_string)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(query)
        results = cursor.fetchall()

        columns = [desc[0] for desc in cursor.description]

        data = [dict(zip(columns, row)) for row in results]

        conn.close()

        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": str(e)})
