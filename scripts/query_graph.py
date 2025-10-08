import argparse
import os
import time

import psycopg2

parser = argparse.ArgumentParser(description='load graphs into PostgreSQL')
parser.add_argument('-d', '--database', required=True, type=str, help='Database in PostgreSQL.')
parser.add_argument('-q', '--query', required=True, type=str, help='Query Type.', choices=['all','l2','l2','l3','triangle','rectangle'])
args = parser.parse_args()

conn = psycopg2.connect(database=args.database.lower(), user="postgres")
conn.autocommit = True
cursor = conn.cursor()

if not os.path.exists('../info/' + args.database.lower()):
    os.mkdir('../info/' + args.database.lower())


if args.query == 'all' or args.query == 'l1':
    start = time.time()
    cursor.execute(''' SELECT 1, from_id, to_id FROM edge where from_id < to_id''')
    t = time.time() - start
    with open('../info/' + args.database.lower() + '/l1.txt', "w", encoding="utf-8") as f:
        for row in cursor:
            f.write("\t".join(map(str, row)) + "\n")
    with open('../info/' + args.database.lower() + '/time.txt', "w", encoding="utf-8") as f:
        f.write("l1\t" + str(t) + '\n')


if args.query == 'all' or args.query == 'l2':
    start = time.time()
    cursor.execute(''' SELECT 1, e1.from_id, e1.to_id, e2.to_id FROM edge as e1, edge as e2 where e1.to_id = e2.from_id and e1.from_id < e2.to_id''')
    t = time.time() - start
    with open('../info/' + args.database.lower() + '/l2.txt', "w", encoding="utf-8") as f:
        for row in cursor:
            f.write("\t".join(map(str, row)) + "\n")
    with open('../info/' + args.database.lower() + '/time.txt', "a", encoding="utf-8") as f:
        f.write("l2\t" + str(t) + '\n')

if args.query == 'all' or args.query == 'triangle':
    start = time.time()
    cursor.execute(''' SELECT 1, e1.from_id, e1.to_id, e2.to_id FROM edge as e1, edge as e2, edge as e3
                    where e1.to_id = e2.from_id and e2.to_id = e3.from_id and e3.to_id = e1.from_id
                    and e1.from_id < e2.from_id and e2.from_id < e3.from_id''')
    t = time.time() - start
    with open('../info/' + args.database.lower() + '/triangle.txt', "w", encoding="utf-8") as f:
        for row in cursor:
            f.write("\t".join(map(str, row)) + "\n")
    with open('../info/' + args.database.lower() + '/time.txt', "a", encoding="utf-8") as f:
        f.write("triangle\t" + str(t) + '\n')


if args.query == 'all' or args.query == 'rectangle':
    start = time.time()
    cursor.execute(''' SELECT 1, e1.from_id, e1.to_id, e2.to_id FROM edge as e1, edge as e2, edge as e3, edge as e4
                    where e1.to_id = e2.from_id and e2.to_id = e3.from_id and e3.to_id = e4.from_id and e4.to_id = e1.from_id
                    and e1.from_id < e2.from_id and e1.from_id < e3.from_id and e1.from_id < e4.from_id and e2.from_id < e4.from_id''')
    t = time.time() - start
    with open('../info/' + args.database.lower() + '/rectangle.txt', "w", encoding="utf-8") as f:
        for row in cursor:
            f.write("\t".join(map(str, row)) + "\n")
    with open('../info/' + args.database.lower() + '/time.txt', "a", encoding="utf-8") as f:
        f.write("rectangle\t" + str(t) + '\n')


# if args.query == 'all' or args.query == 'l3':
#     start = time.time()
#     cursor.execute(''' SELECT 1, e1.from_id, e1.to_id, e2.to_id, e3.to_id FROM edge as e1, edge as e2, edge as e3
#                     where e1.to_id = e2.from_id and e2.to_id <> e1.from_id and e2.to_id = e3.from_id
#                     and e3.to_id <> e2.from_id and e3.to_id > e1.from_id''')
#     t = time.time() - start
#     with open('../info/' + args.database.lower() + '/l3.txt', "w", encoding="utf-8") as f:
#         for row in cursor:
#             f.write("\t".join(map(str, row)) + "\n")
#     with open('../info/' + args.database.lower() + '/l3_time.txt', "a", encoding="utf-8") as f:
#         f.write("l3\t" + str(t) + '\n')

cursor.close()
conn.close()

