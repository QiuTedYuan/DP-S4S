from NoiseGen import NoiseGenerator

class UserRecordMap:
    def __init__(self):
        self.user_to_record = {}
        self.record_to_user = {}

    def add(self, user, record):
        if user not in self.user_to_record:
            self.user_to_record[user] = set()
        if record not in self.record_to_user:
            self.record_to_user[record] = set()
        self.user_to_record[user].add(record)
        self.record_to_user[record].add(user)

    def get_records(self, user):
        return self.user_to_record[user]

    def get_users(self, query):
        return self.record_to_user[query]

# a normalized dataset with normalized edges for vertices [0 ... num_vertices-1]
# downward sensitivity is the max contribution of a user
class Dataset:
    def __init__(self, edges, values):
        self.user_record_map = UserRecordMap()

        # normalize users to [0,...,n-1] and edges correspondingly
        user_cnt = 0
        id_mapping: dict = {}
        user_contribution: dict = {}
        user_edge_count: dict = {}


        for idx, edge in enumerate(edges):
            normal_edge = []
            for user in edge:
                if user in id_mapping:
                    user = id_mapping[user]
                else:
                    id_mapping[user] = user_cnt
                    user = user_cnt
                    user_cnt += 1
                normal_edge.append(user)
                user_contribution[user] = user_contribution.get(user, 0) + values[idx]
                user_edge_count[user] = user_edge_count.get(user, 0) + 1
                self.user_record_map.add(user, idx)
            edges[idx] = normal_edge

        self.num_vertices = user_cnt
        self.edges = edges
        self.values = values
        self.downward_sensitivity = max(user_contribution.values())
        self.result = sum(values)
        self.user_contribution = user_contribution
        self.user_edge_count = user_edge_count


    @classmethod
    def from_path(cls, path):
        edges = []
        values = []
        with open(path, 'rb') as f:
            for tup in f.readlines():
                entries = tup.split()
                value = float(entries[0])
                values.append(value)
                edges.append(entries[1:])
        return cls(edges, values)

    @classmethod
    def sample_and_normalize_from(cls, ds, noise_gen: NoiseGenerator, sample_rate: float, max_weight: float):
        samples = noise_gen.random_sample(len(ds.edges))
        edges = []
        values = []
        for idx in range(samples.shape[0]):
            if samples[idx] < sample_rate:
                edges.append(ds.edges[idx])
                values.append(ds.values[idx] / max_weight)
        return cls(edges, values)

    @classmethod
    def sample_from(cls, ds, noise_gen: NoiseGenerator, sample_rate: float):
        return cls.sample_and_normalize_from(ds, noise_gen, sample_rate, 1)

    @classmethod
    def sample_explore(cls, ds, noise_gen: NoiseGenerator, k: int):
        sampled_users = set(noise_gen.choice(ds.num_vertices, k,False))
        edges = []
        values = []
        for idx in range(len(ds.edges)):
            if ds.edges[idx][0] in sampled_users:
                edges.append(ds.edges[idx])
                values.append(ds.values[idx])
        return cls(edges, values)





