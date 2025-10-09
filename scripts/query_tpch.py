import argparse
import csv
import os
import time

import psycopg2

parser = argparse.ArgumentParser(description='query tpch')
parser.add_argument('-d', '--database', type=str, default='tpch', help='Database in PostgreSQL.')
parser.add_argument('-q', '--query', required=True, type=str, help='Query Type.', choices=['all', 'q5'])
args = parser.parse_args()

conn = psycopg2.connect(database=args.database.lower(), user="postgres")
conn.autocommit = True
cursor = conn.cursor()

outdir = '../info/' + args.database.lower()
if not os.path.exists(outdir):
    os.mkdir(outdir)

if args.query == 'all' or args.query == 'q5':
    start = time.time()
    cursor.execute('''select n_name, l_extendedprice*(1-l_discount)/1000, concat('s',supplier.S_SUPPKEY), concat('c',customer.C_CUSTKEY)
                        from supplier, lineitem, orders, customer, nation, region
                        where c_custkey = o_custkey
                        and l_orderkey = o_orderkey
                        and l_suppkey = s_suppkey
                        and c_nationkey = s_nationkey
                        and s_nationkey = n_nationkey
                        and n_regionkey = r_regionkey;''')
    t = time.time() - start
    with open(outdir + '/time.txt', "w", encoding="utf-8") as f:
        f.write("q5\t" + str(t) + '\n')

    if not os.path.exists(outdir +'/q5'):
        os.mkdir(outdir + '/q5')

    # Maintain file handles for each group
    writers = {}

    def get_writer(n_name):
        """Get or create a CSV writer for the given nation."""
        if n_name not in writers:
            filename = f"{n_name.strip().replace('/', '_').replace(' ', '_')}.txt"
            filepath = outdir + '/q5/n_name_' + filename
            f = open(filepath, "w", newline='', encoding="utf-8")
            writer = csv.writer(f, delimiter=' ')
            writers[n_name] = (f, writer)
        return writers[n_name][1]


    # Stream results row by row
    count = 0
    while True:
        rows = cursor.fetchmany(1000)  # adjustable chunk size
        if not rows:
            break
        for n_name, revenue, s_suppkey, c_custkey in rows:
            writer = get_writer(n_name)
            writer.writerow([revenue, s_suppkey, c_custkey])
            count += 1

    # Close all files
    for f, _ in writers.values():
        f.close()

    print(f"Processed {count} rows into {len(writers)} group files.")

cursor.close()
conn.close()
