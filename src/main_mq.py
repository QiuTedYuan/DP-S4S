import argparse
import time

import numpy as np

from DatasetMultipleQuery import DatasetMultipleQuery
from NoiseGen import NoiseGenerator
from PMSJA import QCQPSolver, pmsja, pmsja_renyi


def avg(arr):
    arr = sorted(arr)
    res = arr[int(len(arr)*0.2):int(len(arr)*0.8)]
    return sum(res) / len(res)

def l2_norm(x):
    return np.sqrt(np.sum(np.power(x, 2)))

def run(algorithm: str, data: DatasetMultipleQuery, epsilon: float, delta: float, beta: float,
        global_sensitivity: float, sample_rate: float, c_bound: int):

    errs = []
    times = []
    data_norm = l2_norm(data.query_results())

    for seed in range(10):
        print("iter", seed, "...")
        noise_gen = NoiseGenerator(seed)
        start = time.time()

        res = []
        if algorithm == 'pmsja':
            tau, res = pmsja(data, epsilon, delta, beta, noise_gen)
        elif algorithm == 'renyi':
            tau, res = pmsja_renyi(data, args.epsilon, args.delta, args.beta, noise_gen, sample_rate)
        else:
            assert False, "invalid algo"

        err = l2_norm(res - data.query_results()) / data_norm * 100
        tm = time.time() - start

        errs.append(err)
        times.append(tm)
        print(tm)
        print(res[0:3])
        print(err)

    return avg(errs), avg(times)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='DP-S4S.')
    parser.add_argument('-i', '--input', required=True, type=str, help='Input file')
    parser.add_argument('-e', '--epsilon', default=4.0, type=float, help='Epsilon')
    parser.add_argument('-d', '--delta', default=0.0000001, type=float, help='Delta')
    parser.add_argument('-b', '--beta', default=0.1, type=float, help='Beta')
    parser.add_argument('-g', '--global_sensitivity', default=1000000, type=float, help='Global sensitivity')
    parser.add_argument('-c', '--collaborators', default=1024, type=int, help='Collaborators bound')
    parser.add_argument('-s', '--sample_rate_inverse', default=10, type=float, help='Sample rate inverse')
    parser.add_argument('-a', '--algorithm', required=True, type=str,
                        choices=['pmsja', 'renyi'], help='Algorithm')

    args = parser.parse_args()


    dataset = DatasetMultipleQuery.from_prefix(args.input)
    print("Num Queries: ", dataset.num_queries())
    print("Data Sizes: ", [len(x) for x in dataset.query_records][0:3])
    print("Query Result: ", dataset.query_results()[0:3])
    print("Query Norm: ", l2_norm(dataset.query_results()))

    err, time = run(args.algorithm, dataset, args.epsilon, args.delta, args.beta, args.global_sensitivity,
                    1./args.sample_rate_inverse, args.collaborators)
    print("time", time)
    print("err", err)
