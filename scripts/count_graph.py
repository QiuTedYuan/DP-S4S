import argparse

parser = argparse.ArgumentParser(description='Graph statistics.')
parser.add_argument('-i', '--input', required=True, type=str, help='Input file (edge list)')

args = parser.parse_args()

users: dict = {}
edge_count = 0

with open(args.input, 'r') as f:
    for tup in f.readlines():
        entries = tup.strip().split(' ')
        users[entries[0]] = users.get(entries[0], 0) + 1
        users[entries[1]] = users.get(entries[1], 0) + 1

print("vertices", len(users))
print("edges", sum(users.values()) / 2)
print("max degree", max(users.values()))



