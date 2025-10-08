import argparse
import faulthandler
import time

import numpy as np

from DatasetMultipleQuery import DatasetMultipleQuery
from NoiseGen import NoiseGenerator
from PMSJA import QCQPSolver, pmsja, pmsja_renyi


def l2_norm(x):
    return np.sqrt(np.sum(np.power(x, 2)))

parser = argparse.ArgumentParser(description='Sample-based R2T.')
parser.add_argument('-i', '--input', required=True, type=str, help='Input file')
parser.add_argument('-e', '--epsilon', default=4.0, type=float, help='Epsilon')
parser.add_argument('-d', '--delta', default=0.00000001, type=float, help='Delta')
parser.add_argument('-b', '--beta', default=0.1, type=float, help='Beta')
parser.add_argument('-g', '--global_sensitivity', default=1000000, type=float, help='Global sensitivity')
parser.add_argument('-w', '--max_weight', default=1, type=float, help='Max weight of each record')
args = parser.parse_args()

faulthandler.enable()

dataset = DatasetMultipleQuery.from_prefix(args.input)

solver = QCQPSolver(dataset)
# print("Data Size: ", len(dataset.edges))
# print("Query Result: ", dataset.query_results())
sample_rate = 0.05


for seed in range(5):
    noise_gen = NoiseGenerator(seed)
    start = time.time()
    tau, noisy_result = pmsja(dataset, args.epsilon, args.delta, args.beta, noise_gen)
    print(noisy_result )
    print("Time")
    print(time.time()-start)
    # print("Query Result")
    # print(dataset.query_results())
    # print("Noised Result")
    # print(noisy_result)
    print("pmsja", tau,  l2_norm(noisy_result - dataset.query_results()) / l2_norm(dataset.query_results()), time.time() - start, 's')

    start = time.time()
    tau, noisy_result = pmsja_renyi(dataset, args.epsilon, args.delta, args.beta, noise_gen, sample_rate)
    print("renyi", tau, l2_norm(noisy_result - dataset.query_results()) / l2_norm(dataset.query_results()), time.time() - start, 's')
