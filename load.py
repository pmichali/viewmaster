import sys
import os.path
from datetime import datetime
import pandas
import sqlite3
from pickle import FALSE

from sqlalchemy.types import Integer, DECIMAL


def load_excel(excel_file):
    """Populate database from Excel file."""
    if not os.path.isfile(excel_file):
        print(f"ERROR! No file {excel_file}\n\n")
        sys.exit(1)
    movies = pandas.read_excel(
        excel_file, 
        sheet_name='Alphabetical',
        header=0
    )
    # Set ID
    movies['id'] = range(1, len(movies) + 1)
    # Fix missing values
    movies.loc[pandas.isna(movies['rating']), 'rating'] = '?'
    movies.loc[pandas.isna(movies['duration']), 'duration'] = '00:00'
    movies.loc[pandas.isna(movies['aspect']), 'aspect'] = '?'
    movies.loc[pandas.isna(movies['audio']), 'audio'] = '?'
    movies.loc[pandas.isna(movies['collection']), 'collection'] = ''
    movies.loc[pandas.isna(movies['cost']), 'cost'] = '0.0'
    print(movies.head())
    db_conn = sqlite3.connect('movies.db')
    print(f"Columns: {movies.columns}")
    c = db_conn.cursor()
    c.execute("""
CREATE TABLE movies2 (
    title varchar(60) NOT NULL,
    release integer NOT NULL,
    category varchar(20) NOT NULL,
    rating varchar(5) default('?'),
    duration timestamp default('00:00'),
    format varchar(3) NOT NULL,
    aspect varchar(10) default('?'),
    audio varchar(10) default('?'),
    collection varchar(10) default(''),
    cost decimal default('0'),
    paid bool,
    bad bool,
    id integer PRIMARY KEY
);
"""
    )
    movies.to_sql(
        'movies2',
        db_conn,
        if_exists='append',
        index=False,
    )
    db_conn.close()
    print("Done!")

    
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("ERROR! Incorrect number of arguments\nUSAGE: load FILENAME.XLSX\n\n")
        sys.exit(1)
    load_excel(sys.argv[1])