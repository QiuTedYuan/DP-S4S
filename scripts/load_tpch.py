import argparse
import psycopg2

parser = argparse.ArgumentParser(description='load graphs into PostgreSQL')
parser.add_argument('-p', '--path', required=True, type=str, help='Path to the TPCH files, expect path/customer.csv ...')
parser.add_argument('-s', '--separator', default='|', type=str, help='Seperator between columns.')
parser.add_argument('-d', '--database', required=True, type=str, help='Database in PostgreSQL.')
args = parser.parse_args()

conn = psycopg2.connect(database="postgres", user="postgres")
conn.autocommit = True
cursor = conn.cursor()
cursor.execute('''DROP DATABASE IF EXISTS ''' + args.database)
cursor.execute('''CREATE DATABASE ''' + args.database)
cursor.close()
conn.close()

print("Created database " + args.database)

conn = psycopg2.connect(database=args.database.lower(), user="postgres")
conn.autocommit = True
cursor = conn.cursor()
cursor.execute('''DROP TABLE IF EXISTS REGION''')
cursor.execute('''DROP TABLE IF EXISTS NATION''')
cursor.execute('''DROP TABLE IF EXISTS SUPPLIER''')
cursor.execute('''DROP TABLE IF EXISTS CUSTOMER''')
cursor.execute('''DROP TABLE IF EXISTS PART''')
cursor.execute('''DROP TABLE IF EXISTS PARTSUPP''')
cursor.execute('''DROP TABLE IF EXISTS ORDERS''')
cursor.execute('''DROP TABLE IF EXISTS LINEITEM''')

cursor.execute('''CREATE TABLE REGION (R_REGIONKEY INTEGER NOT NULL, R_NAME CHAR(25) NOT NULL, R_COMMENT VARCHAR(152))''')
cursor.execute('''CREATE TABLE NATION (N_NATIONKEY INTEGER NOT NULL, N_NAME CHAR(25) NOT NULL, N_REGIONKEY INTEGER NOT NULL, N_COMMENT VARCHAR(152))''')
cursor.execute('''CREATE TABLE SUPPLIER (S_SUPPKEY INTEGER NOT NULL, S_NAME CHAR(25) NOT NULL, S_ADDRESS VARCHAR(40) NOT NULL, S_NATIONKEY INTEGER NOT NULL, S_PHONE CHAR(15) NOT NULL, S_ACCTBAL DECIMAL(15,2) NOT NULL, S_COMMENT VARCHAR(101) NOT NULL)''')
cursor.execute('''CREATE TABLE CUSTOMER (C_CUSTKEY INTEGER NOT NULL, C_NAME VARCHAR(25) NOT NULL, C_ADDRESS VARCHAR(40) NOT NULL, C_NATIONKEY INTEGER NOT NULL, C_PHONE CHAR(15) NOT NULL, C_ACCTBAL DECIMAL(15,2) NOT NULL, C_MKTSEGMENT CHAR(10) NOT NULL, C_COMMENT VARCHAR(117) NOT NULL)''')
cursor.execute('''CREATE TABLE PART (P_PARTKEY INTEGER NOT NULL, P_NAME VARCHAR(55) NOT NULL, P_MFGR CHAR(25) NOT NULL, P_BRAND CHAR(10) NOT NULL, P_TYPE VARCHAR(25) NOT NULL, P_SIZE INTEGER NOT NULL, P_CONTAINER CHAR(10) NOT NULL, P_RETAILPRICE DECIMAL(15,2) NOT NULL, P_COMMENT VARCHAR(23) NOT NULL)''')
cursor.execute('''CREATE TABLE PARTSUPP (PS_PARTKEY INTEGER NOT NULL, PS_SUPPKEY INTEGER NOT NULL, PS_AVAILQTY INTEGER NOT NULL, PS_SUPPLYCOST DECIMAL(15,2) NOT NULL, PS_COMMENT VARCHAR(199) NOT NULL)''')
cursor.execute('''CREATE TABLE ORDERS (O_ORDERKEY INTEGER NOT NULL, O_CUSTKEY INTEGER NOT NULL, O_ORDERSTATUS CHAR(1) NOT NULL, O_TOTALPRICE DECIMAL(15,2) NOT NULL, O_ORDERDATE DATE NOT NULL, O_ORDERPRIORITY CHAR(15) NOT NULL, O_CLERK CHAR(15) NOT NULL, O_SHIPPRIORITY INTEGER NOT NULL, O_COMMENT VARCHAR(79) NOT NULL)''')
cursor.execute('''CREATE TABLE LINEITEM (L_ORDERKEY INTEGER NOT NULL, L_PARTKEY INTEGER NOT NULL, L_SUPPKEY INTEGER NOT NULL, L_LINENUMBER INTEGER NOT NULL, L_QUANTITY DECIMAL(15,2) NOT NULL, L_EXTENDEDPRICE DECIMAL(15,2) NOT NULL, L_DISCOUNT DECIMAL(15,2) NOT NULL, L_TAX DECIMAL(15,2) NOT NULL, L_RETURNFLAG CHAR(1) NOT NULL, L_LINESTATUS CHAR(1) NOT NULL, L_SHIPDATE DATE NOT NULL, L_COMMITDATE DATE NOT NULL, L_RECEIPTDATE DATE NOT NULL, L_SHIPINSTRUCT CHAR(25) NOT NULL, L_SHIPMODE CHAR(10) NOT NULL, L_COMMENT VARCHAR(44) NOT NULL)''')

for table in ['region', 'nation', 'supplier', 'customer', 'part', 'partsupp', 'orders', 'lineitem']:
    with open(args.path + '/' + table + '.csv') as f:
        cursor.copy_from(f, table, sep=args.separator)
    cursor.execute(''' SELECT count(*) from ''' + table)
    print("Loaded " + str(cursor.fetchone()[0]) + " records for " + table)

cursor.execute('''CREATE INDEX R_I on REGION(R_REGIONKEY)''')
cursor.execute('''CLUSTER REGION USING R_I''')
cursor.execute('''CREATE INDEX N_I on NATION(N_NATIONKEY)''')
cursor.execute('''CLUSTER NATION USING N_I''')
cursor.execute('''CREATE INDEX S_I on SUPPLIER(S_SUPPKEY)''')
cursor.execute('''CLUSTER SUPPLIER USING S_I''')
cursor.execute('''CREATE INDEX C_I on CUSTOMER(C_CUSTKEY)''')
cursor.execute('''CLUSTER CUSTOMER USING C_I''')
cursor.execute('''CREATE INDEX P_I on PART(P_PARTKEY)''')
cursor.execute('''CLUSTER PART USING P_I''')
cursor.execute('''CREATE INDEX PS_I on PARTSUPP(PS_PARTKEY, PS_SUPPKEY)''')
cursor.execute('''CLUSTER PARTSUPP USING PS_I''')
cursor.execute('''CREATE INDEX O_I on ORDERS(O_ORDERKEY)''')
cursor.execute('''CLUSTER ORDERS USING O_I''')
cursor.execute('''CREATE INDEX L_I on LINEITEM(L_PARTKEY,L_SUPPKEY)''')
cursor.execute('''CLUSTER LINEITEM USING L_I''')

cursor.execute("ALTER TABLE REGION ADD PRIMARY KEY (R_REGIONKEY)")
cursor.execute("ALTER TABLE NATION ADD PRIMARY KEY (N_NATIONKEY)")
cursor.execute("ALTER TABLE SUPPLIER ADD PRIMARY KEY (S_SUPPKEY)")
cursor.execute("ALTER TABLE CUSTOMER ADD PRIMARY KEY (C_CUSTKEY)")
cursor.execute("ALTER TABLE PART ADD PRIMARY KEY (P_PARTKEY)")
cursor.execute("ALTER TABLE PARTSUPP ADD PRIMARY KEY (PS_PARTKEY,PS_SUPPKEY)")
cursor.execute("ALTER TABLE ORDERS ADD PRIMARY KEY (O_ORDERKEY)")
cursor.execute("ALTER TABLE LINEITEM ADD PRIMARY KEY (L_ORDERKEY,L_LINENUMBER)")

cursor.execute("ALTER TABLE NATION ADD FOREIGN KEY (N_REGIONKEY) references REGION")
cursor.execute("ALTER TABLE SUPPLIER ADD FOREIGN KEY (S_NATIONKEY) references NATION")
cursor.execute("ALTER TABLE CUSTOMER ADD FOREIGN KEY (C_NATIONKEY) references NATION")
cursor.execute("ALTER TABLE PARTSUPP ADD FOREIGN KEY (PS_SUPPKEY) references SUPPLIER")
cursor.execute("ALTER TABLE PARTSUPP ADD FOREIGN KEY (PS_PARTKEY) references PART")
cursor.execute("ALTER TABLE ORDERS ADD FOREIGN KEY (O_CUSTKEY) references CUSTOMER")
cursor.execute("ALTER TABLE LINEITEM ADD FOREIGN KEY (L_ORDERKEY) references ORDERS")
cursor.execute("ALTER TABLE LINEITEM ADD FOREIGN KEY (L_PARTKEY,L_SUPPKEY) references PARTSUPP")


cursor.close()
conn.close()

