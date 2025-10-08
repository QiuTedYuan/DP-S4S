import argparse
import psycopg2

parser = argparse.ArgumentParser(description='load graphs into PostgreSQL')
parser.add_argument('-p', '--path', required=True, type=str, help='Path to the graph, expect Path_edges.txt and Path_nodes.txt files.')
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
cursor.execute('''DROP TABLE IF EXISTS node''')
cursor.execute('''DROP TABLE IF EXISTS edge''')
cursor.execute('''CREATE TABLE node (ID INTEGER NOT NULL)''')
cursor.execute('''CREATE TABLE edge (FROM_ID INTEGER NOT NULL, TO_ID INTEGER NOT NULL)''')

cursor.execute('''CREATE INDEX on NODE using hash (ID)''')
cursor.execute('''CREATE INDEX on EDGE using hash (FROM_ID)''')
cursor.execute('''CREATE INDEX on EDGE using hash (TO_ID)''')

with open(args.path + "_edges.txt") as edges:
    cursor.copy_from(edges, "edge", sep=args.separator)

cursor.execute(''' SELECT count(*) FROM edge ''')
print("Loaded " + str(cursor.fetchone()[0]) + " edges")

with open(args.path + "_nodes.txt") as nodes:
    cursor.copy_from(nodes, "node")
cursor.execute(''' SELECT count(*) FROM node ''')
print("Loaded " + str(cursor.fetchone()[0]) + " nodes")

cursor.close()
conn.close()

