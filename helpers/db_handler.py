import csv
import sqlite3

def load_csv(cursor, file_name):
    '''
    Invert and load simple csv's to the database as tables
    taken from 
    '''
    with open(file_name, 'r') as csv_file:
        rows = list(csv.reader(csv_file))
        columns = zip(*rows)
        headers = next(columns)

    table_name = file_name.split('/')[-1].split('.')[0]
    
    create_table_stmt = ('CREATE TABLE IF NOT EXISTS '
                         '{table_name}{headers};').format(**locals())
    q_marks = ('?,' * len(headers))[:-1]
    insert_stmt = ('INSERT OR IGNORE INTO {table_name} '
                   'VALUES ({q_marks});').format(**locals())
    cursor.execute(create_table_stmt)
    cursor.executemany(insert_stmt, columns)

def create_db(db_name):
    '''
    Create a market_data qlpy database with requisite simple tables if
    none exist.
    '''
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    load_csv(cursor, 'data/rates_data.csv')
    load_csv(cursor, 'data/instruments.csv')
    load_csv(cursor, 'data/conventions.csv')

    conn.commit()

    return conn

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d
