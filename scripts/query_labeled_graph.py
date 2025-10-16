import argparse
import csv
import os
import time

import psycopg2

def get_writer(writers, direc, tup):
    """Get or create a CSV writer for the given nation."""
    if tup not in writers:
        filename = "group"
        for val in tup:
            filename += '_'
            if type(val) == str:
                filename += val.strip().replace('/', '_').replace(' ', '_')
            else:
                filename += str(val)
        filename += ".txt"
        filepath = direc + '/' + filename
        f = open(filepath, "w", newline='', encoding="utf-8")
        writer = csv.writer(f, delimiter=' ')
        writers[tup] = (f, writer)
    return writers[tup][1]

def execute(query, dbname, group_by_cnt):
    outdir = '../info/' + dbname + '_raw'
    if not os.path.exists(outdir):
        os.mkdir(outdir)

    start = time.time()
    cursor.execute(query)
    t = time.time() - start
    with open('../info/time.txt', "a", encoding="utf-8") as f:
        f.write(dbname + "\t" +     args.query + "\t" + str(t) + '\n')
    if not os.path.exists(outdir + '/' + args.query):
        os.makedirs(outdir + '/' + args.query, exist_ok=True)
    # Maintain file handles for each group
    writers = {}

    # Stream results row by row
    count = 0
    while True:
        rows = cursor.fetchmany(1000)  # adjustable chunk size
        if not rows:
            break
        for row in rows:
            writer = get_writer(writers, outdir + '/' + args.query, row[:group_by_cnt])
            writer.writerow(row[group_by_cnt:])
            count += 1

    # Close all files
    for f, _ in writers.values():
        f.close()

    print(f"Processed {count} rows into {len(writers)} group files.")
    return len(writers)

parser = argparse.ArgumentParser(description='query tpch')
parser.add_argument('-d', '--database', required=True, type=str, help='Database in PostgreSQL.')
parser.add_argument('-q', '--query', required=True, type=str, help='Query Type.',
                    choices=['q1','q2','q3','c2','triangle','q4','s2'])
args = parser.parse_args()

conn = psycopg2.connect(database=args.database.lower(), user="postgres")
conn.autocommit = True
cursor = conn.cursor()

if args.query == 'q1':
    sql = '''select label, 1, from_id, to_id from edge where from_id != to_id'''
    execute(sql, args.database.lower(), 1)

if args.query == 'q2':
    sql = ''' SELECT e1.label, 1, e1.from_id, e1.to_id, e2.to_id
            FROM edge as e1, edge as e2
            where e1.from_id != e1.to_id and e2.from_id != e2.to_id and e1.to_id = e2.from_id and e1.from_id != e2.to_id'''
    execute(sql, args.database.lower(), 1)

if args.query == 'q3':
    sql = ''' SELECT e1.label, 1, e1.from_id, e1.to_id, e2.to_id, e3.to_id
            FROM edge as e1, edge as e2, edge as e3
            where e1.from_id != e1.to_id and e2.from_id != e2.to_id and e3.from_id != e3.to_id
            and e1.to_id = e2.from_id and e1.from_id != e2.to_id
            and e2.to_id = e3.from_id and e3.to_id != e1.from_id and e3.to_id != e2.from_id'''
    execute(sql, args.database.lower(), 1)

if args.query == 'triangle':
    sql = ''' SELECT e1.label, 1, e1.from_id, e1.to_id, e2.to_id
            FROM edge as e1, edge as e2, edge as e3
            where e1.from_id != e1.to_id and e2.from_id != e2.to_id and e3.from_id != e3.to_id
            and e1.to_id = e2.from_id and e2.to_id = e3.from_id and e3.to_id = e1.from_id
            and e1.from_id < e2.from_id and e1.from_id < e3.from_id'''
    execute(sql, args.database.lower(), 1)

if args.query == 'c2':
    sql = ''' SELECT extract(year from e1.label), 1, e1.from_id, e1.to_id, e2.to_id
            FROM edge as e1, edge as e2
            where e1.from_id != e1.to_id and e2.from_id != e2.to_id
            and e1.to_id = e2.from_id and e2.to_id = e1.from_id'''
    execute(sql, args.database.lower(), 1)

if args.query == 'q4':
    sql = ''' SELECT extract(year from e4.label), 1, e1.from_id, e1.to_id, e2.to_id, e3.to_id, e4.to_id
            FROM edge as e1, edge as e2, edge as e3, edge as e4
            where e1.from_id != e1.to_id and e2.from_id != e2.to_id and e3.from_id != e3.to_id and e4.from_id != e4.to_id
            and e1.to_id = e2.from_id and e2.to_id != e1.from_id
            and e2.to_id = e3.from_id and e3.to_id != e1.from_id and e3.to_id != e2.from_id
            and e3.to_id = e4.from_id and e4.to_id != e1.from_id and e4.to_id != e2.from_id and e4.to_id != e3.from_id'''
    num_groups = execute(sql, args.database.lower(), 1)

if args.query == 's2':
    sql = ''' SELECT extract(year from e1.label), 1, e1.from_id, e1.to_id, e2.to_id
            FROM edge as e1, edge as e2
            where e1.from_id != e1.to_id and e2.from_id != e2.to_id
            and e1.from_id = e2.from_id and e1.to_id < e2.to_id'''
    execute(sql, args.database.lower(), 1)


cursor.close()
conn.close()
