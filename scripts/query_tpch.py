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

parser = argparse.ArgumentParser(description='query tpch')
parser.add_argument('-d', '--database', type=str, default='tpch', help='Database in PostgreSQL.')
parser.add_argument('-q', '--query', required=True, type=str, help='Query Type.',
                    choices=['q1/quantity', 'q1/base_price', 'q1/disc_price', 'q1/charge', 'q1/cnt',
                             'q5', 'q7', 'q7_cust_supp', 'q7_ps_cust_name', 'q7_ps_cust_year', 'q7_ps_order', 'q8'])
args = parser.parse_args()

conn = psycopg2.connect(database=args.database.lower(), user="postgres")
conn.autocommit = True
cursor = conn.cursor()

if args.query == 'q1/quantity':
    sql = '''select l_returnflag, l_linestatus, sum(l_quantity), concat('c', o_custkey), concat('s',l_suppkey)
        from orders, lineitem
        where l_orderkey=o_orderkey
         and l_shipdate <= date '1998-12-01'
        group by l_returnflag, l_linestatus, o_custkey, l_suppkey;'''
    execute(sql, args.database.lower(), 2)

if args.query == 'q1/base_price':
    sql = '''select l_returnflag, l_linestatus, sum(l_extendedprice), concat('c', o_custkey), concat('s',l_suppkey)
        from orders, lineitem
        where l_orderkey=o_orderkey
         and l_shipdate <= date '1998-12-01'
        group by l_returnflag, l_linestatus, o_custkey, l_suppkey;'''
    execute(sql, args.database.lower(), 2)

if args.query == 'q1/disc_price':
    sql = '''select l_returnflag, l_linestatus, sum(l_extendedprice*(1-l_discount)), concat('c', o_custkey), concat('s',l_suppkey)
        from orders, lineitem
        where l_orderkey=o_orderkey
         and l_shipdate <= date '1998-12-01'
        group by l_returnflag, l_linestatus, o_custkey, l_suppkey;'''

    execute(sql, args.database.lower(), 2)

if args.query == 'q1/charge':
    sql = '''select l_returnflag, l_linestatus, sum(l_extendedprice*(1-l_discount)*(1+l_tax)), concat('c', o_custkey), concat('s',l_suppkey)
        from orders, lineitem
        where l_orderkey=o_orderkey
         and l_shipdate <= date '1998-12-01'
        group by l_returnflag, l_linestatus, o_custkey, l_suppkey;'''

    execute(sql, args.database.lower(), 2)

if args.query == 'q1/cnt':
    sql = '''select l_returnflag, l_linestatus, count(1), concat('c', o_custkey), concat('s',l_suppkey)
        from orders, lineitem
        where l_orderkey=o_orderkey
         and l_shipdate <= date '1998-12-01'
        group by l_returnflag, l_linestatus, o_custkey, l_suppkey;'''

    execute(sql, args.database.lower(), 2)

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

if args.query == 'q7_cust_supp':
    sql = '''select n_name, l_extendedprice*(1-l_discount)/1000 as revenue, concat('s', supplier.s_suppkey), concat('c',customer.c_custkey)
             from supplier, lineitem, orders, customer, nation
             where s_suppkey = l_suppkey 
               and o_orderkey = l_orderkey
               and c_custkey = o_custkey
               and c_nationkey = n_nationkey
               and ((l_shipdate between date '1995-01-01' and date '1995-02-01') or (l_shipdate between date '1996-01-01' and date '1996-02-08'));'''

    execute(sql, args.database.lower(), 1)

# 6
if args.query == 'q7_ps_cust_name':
    sql = '''select n_name, count(1), concat('p', ps_partkey, '_s', ps_suppkey), concat('c',customer.c_custkey)
            from partsupp, lineitem, orders, customer, nation
            where ps_suppkey = l_suppkey
              and ps_partkey = l_partkey
              and o_orderkey = l_orderkey
              and c_custkey = o_custkey
              and c_nationkey = n_nationkey
              and l_shipdate between date '1995-01-01' and date '1995-2-28'
            group by n_name, ps_partkey, ps_suppkey, c_custkey;'''

    execute(sql, args.database.lower(), 1)

# 7
if args.query == 'q7_ps_cust_year':
    sql = '''select n_name, extract(year FROM l_shipdate), count(1), concat('p', ps_partkey, '_s', ps_suppkey), concat('c',customer.c_custkey)
            from partsupp, lineitem, orders, customer, nation
            where ps_suppkey = l_suppkey
              and ps_partkey = l_partkey
              and o_orderkey = l_orderkey
              and c_custkey = o_custkey
              and c_nationkey = n_nationkey
              and ((l_shipdate between date '1998-01-01' and date '1998-01-31') or (l_shipdate between date '1997-01-01' and date '1997-01-31'))
            group by n_name, extract(year FROM l_shipdate), ps_partkey, ps_suppkey, c_custkey;'''
    execute(sql, args.database.lower(), 2)

# 8
if args.query == 'q7_ps_order':
    sql = '''select l_shipdate, sum(l_extendedprice*(1-l_discount)/1000) as revenue, concat('p', ps_partkey, '_s', ps_suppkey), concat('o',o_orderkey)
            from partsupp, lineitem, orders
            where ps_suppkey = l_suppkey
              and ps_partkey = l_partkey
              and o_orderkey = l_orderkey
              and l_shipdate between date '1995-01-01' and date '1995-4-10'
            group by l_shipdate, ps_partkey, ps_suppkey, o_orderkey;'''
    execute(sql, args.database.lower(), 1)

if args.query == 'q8':
    sql = '''select extract(year from o_orderdate) as o_year, l_extendedprice * (1 - l_discount) as volume, concat('s', supplier.s_suppkey), concat('c',customer.c_custkey)
		from part, supplier, lineitem, orders, customer, nation n1, nation n2, region
		where
			p_partkey = l_partkey
			and s_suppkey = l_suppkey
			and l_orderkey = o_orderkey
			and o_custkey = c_custkey
			and c_nationkey = n1.n_nationkey
			and n1.n_regionkey = r_regionkey
			and s_nationkey = n2.n_nationkey'''
    execute(sql, args.database.lower(), 1)

cursor.close()
conn.close()
