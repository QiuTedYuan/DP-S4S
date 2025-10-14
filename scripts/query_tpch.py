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
    outdir = '../info/' + dbname
    if not os.path.exists(outdir):
        os.mkdir(outdir)

    start = time.time()
    cursor.execute(query)
    t = time.time() - start
    with open('../info/time.txt', "a", encoding="utf-8") as f:
        f.write(dbname + "\t" +     args.query + "\t" + str(t) + '\n')
    if not os.path.exists(outdir + '/' + args.query):
        os.mkdir(outdir + '/' + args.query)
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

parser = argparse.ArgumentParser(description='query tpch')
parser.add_argument('-d', '--database', type=str, default='tpch', help='Database in PostgreSQL.')
parser.add_argument('-q', '--query', required=True, type=str, help='Query Type.', choices=['q5', 'q7', 'q7_one_nation'])
args = parser.parse_args()

conn = psycopg2.connect(database=args.database.lower(), user="postgres")
conn.autocommit = True
cursor = conn.cursor()

if args.query == 'q1':
    sql = '''select l_returnflag, l_linestatus, l_quantity, c_custkey, s_suppkey
    from supplier, customer, orders, lineitem
    where l_orderkey=o_orderkey
    and l_suppkey=s_suppkey
    and c_custkey=o_custkey;'''

if args.query == 'q5':
    sql = '''select n_name, l_extendedprice*(1-l_discount)/1000, concat('s',supplier.S_SUPPKEY), concat('c',customer.C_CUSTKEY)
                        from supplier, lineitem, orders, customer, nation, region
                        where c_custkey = o_custkey
                        and l_orderkey = o_orderkey
                        and l_suppkey = s_suppkey
                        and c_nationkey = s_nationkey
                        and s_nationkey = n_nationkey
                        and n_regionkey = r_regionkey;'''
    execute(sql, args.database.lower(), 1)

if args.query == 'q7':
    sql = '''select n1.n_name, n2.n_name, extract(year FROM l_shipdate), l_extendedprice*(1-l_discount)/1000 as revenue, concat('s', supplier.s_suppkey), concat('c',customer.c_custkey)
             from supplier, lineitem, orders, customer, nation n1, nation n2  
             where s_suppkey = l_suppkey 
               and o_orderkey = l_orderkey
               and c_custkey = o_custkey
               and c_nationkey = n1.n_nationkey
               and s_nationkey = n2.n_nationkey
               and ((l_shipdate between date '1995-01-01' and date '1995-02-01') or (l_shipdate between date '1996-01-01' and date '1996-02-08'));'''
    execute(sql, args.database.lower(), 3)

if args.query == 'q7_one_nation':
    sql = '''select n_name, l_extendedprice*(1-l_discount)/1000 as revenue, concat('s', supplier.s_suppkey), concat('c',customer.c_custkey)
             from supplier, lineitem, orders, customer, nation
             where s_suppkey = l_suppkey 
               and o_orderkey = l_orderkey
               and c_custkey = o_custkey
               and c_nationkey = n_nationkey
               and ((l_shipdate between date '1995-01-01' and date '1995-02-01') or (l_shipdate between date '1996-01-01' and date '1996-02-08'));'''

    execute(sql, args.database.lower(), 1)

cursor.close()
conn.close()
