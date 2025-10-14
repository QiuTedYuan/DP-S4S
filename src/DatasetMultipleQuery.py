import pathlib as pl
from functools import cache

import numpy as np

from NoiseGen import NoiseGenerator


class UserQueryMap:
    def __init__(self):
        self.user_to_query = {}
        self.query_to_user = {}

    def add(self, user, query):
        if user not in self.user_to_query:
            self.user_to_query[user] = set()
        if query not in self.query_to_user:
            self.query_to_user[query] = set()
        self.user_to_query[user].add(query)
        self.query_to_user[query].add(user)

    def get_queries(self, user):
        return self.user_to_query[user]

    def get_users(self, query):
        return self.query_to_user[query]

# a normalized dataset with normalized edges for vertices [0 ... num_vertices-1]
# downward sensitivity is the max contribution of a user
class DatasetMultipleQuery:
    def __init__(self):
        # normalize users to [0,...,n-1] and edges correspondingly
        self.user_cnt = 0
        self.__id_mapping__: dict = {}
        self.query_records = []
        self.query_values = []
        self.user_query_map = UserQueryMap()
        self.cumulative_record_counts = [0]

    def add_query_records(self, edges, values):
        for idx, edge in enumerate(edges):
            normal_edge = []
            for user in edge:
                if user in self.__id_mapping__:
                    user = self.__id_mapping__[user]
                else:
                    self.__id_mapping__[user] = self.user_cnt
                    user = self.user_cnt
                    self.user_cnt += 1
                normal_edge.append(user)
                self.user_query_map.add(user, idx)
            edges[idx] = normal_edge
        self.query_records.append(edges)
        self.query_values.append(values)
        self.cumulative_record_counts.append(self.cumulative_record_counts[-1] + len(edges))

    @classmethod
    def from_folder(cls, prefix):
        dataset = cls()
        path = pl.Path(prefix)
        files = [f for f in path.rglob("*") if f.is_file()]
        for file in files:
            values = []
            edges = []
            with open(file, 'rb') as f:
                for tup in f.readlines():
                    entries = tup.split()
                    value = float(entries[0])
                    values.append(value)
                    edges.append(entries[1:])
            dataset.add_query_records(edges, values)
        return dataset

    def num_queries(self):
        return len(self.query_records)

    def num_users(self):
        return self.user_cnt

    def num_records_of_query(self, idx):
        return len(self.query_records[idx])

    @cache
    def num_records_total(self):
        return sum([len(x) for x in self.query_records])

    @cache
    def user_contribution_total(self):
        return sum([len(x) for x in self.user_query_map.user_to_query.values()])

    def get_record(self, query, idx):
        return self.query_records[query][idx]

    def get_record_idx(self, query, idx):
        return self.cumulative_record_counts[query] + idx

    @cache
    def query_results(self):
        return np.array([sum(x) for x in self.query_values])

    @cache
    def l2_downward_sensitivity(self):
        contribs = {}
        for query in range(self.num_queries()):
            query_contrib = {}
            for record in range(self.num_records_of_query(query)):
                for user in self.query_records[query][record]:
                    query_contrib[user] = query_contrib.get(user, 0) + self.query_values[query][record]
            for user in query_contrib:
                contribs[user] = contribs.get(user, 0) + np.power(query_contrib[user], 2)
        if not len(contribs):
            return 0
        return np.sqrt(max(contribs.values()))

    @classmethod
    def sample_from(cls, ds, noise_gen: NoiseGenerator, sample_rate):
        sampled_dataset = cls()
        for query in range(len(ds.query_records)):
            sampled_records = []
            sampled_values = []
            for idx in range(len(ds.query_records[query])):
                if noise_gen.uniform(0, 1) < sample_rate:
                    sampled_records.append(ds.query_records[query][idx])
                    sampled_values.append(ds.query_values[query][idx])
            sampled_dataset.add_query_records(sampled_records, sampled_values)
        return sampled_dataset

    @classmethod
    def sample_explore(cls, ds, noise_gen: NoiseGenerator, k: int):
        sampled_users = set(noise_gen.choice(ds.num_users(), k,False))
        sampled_dataset = cls()
        for query in range(len(ds.query_records)):
            sampled_records = []
            sampled_values = []
            for idx in range(len(ds.query_records[query])):
                if ds.query_records[query][idx][0] in sampled_users:
                    sampled_records.append(ds.query_records[query][idx])
                    sampled_values.append(ds.query_values[query][idx])
            sampled_dataset.add_query_records(sampled_records, sampled_values)
        return sampled_dataset
