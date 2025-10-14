# DP-S4S

This repo contains the code for "Sampling for Scale: Scalable Select-Join-Aggregate Query Processing under User-Level Differential Privacy".

## Installation

The prerequisites can be found in the [toml](pyproject.toml) file.

Other than the listed ones, the project also uses [IBM ILOG CPLEX Optimization Studio](https://www.ibm.com/support/pages/downloading-ibm-ilog-cplex-optimization-studio-2211) to solve LPs.
We recommend installing v22.1.1, which has a built-in python support.
Please copy the installed folder into `<project>/cplex/`, the docker will build the python wheel from `<project>/cplex/python/setup.py`.

For Mosek, a valid [license](https://www.mosek.com/products/academic-licenses/) is required. Please put it in `<project>/mosek.lic` so that the program can find it.

## Data

We use the same dataset as existing work [R2T](https://github.com/hkustDB/Race-to-the-Top), [PMSJA](https://github.com/hkustDB/PMSJA/tree/master), so the raw data can be similarly obtained.

We have preprocessed the raw data into join results under `info`. To reproduce them:
1. Run `./scripts/load_graph.py` or `load_tpch.py` to load the raw data into PostgreSQL
2. Run `./scripts/query_graph.py` or `query_tpch.py` to query PostgreSQL and write results into `info`.

## Run experiments

To run the mechanisms under a given set of parameters, use the following:

For scalar query:
```zsh
usage: main.py [-h] -i INPUT [-e EPSILON] [-d DELTA] [-b BETA]
               [-g GLOBAL_SENSITIVITY] [-c COLLABORATORS] [-w MAX_WEIGHT]
               [-s SAMPLE_RATE_INVERSE] -a
               {r2t,dp_s4s,se_blackbox,se_whitebox} [-r REPEATS]

DP-S4S.

options:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
                        Input file.txt
  -e EPSILON, --epsilon EPSILON
                        Epsilon
  -d DELTA, --delta DELTA
                        Delta
  -b BETA, --beta BETA  Beta
  -g GLOBAL_SENSITIVITY, --global_sensitivity GLOBAL_SENSITIVITY
                        Global sensitivity
  -c COLLABORATORS, --collaborators COLLABORATORS
                        Collaborators bound
  -w MAX_WEIGHT, --max_weight MAX_WEIGHT
                        Max weight of each record
  -s SAMPLE_RATE_INVERSE, --sample_rate_inverse SAMPLE_RATE_INVERSE
                        Sample rate inverse
  -a {r2t,dp_s4s,se_blackbox}, --algorithm {r2t,dp_s4s,se_blackbox}
                        Algorithm
  -r REPEATS, --repeats REPEATS
                        Number of repeats
```

For vector query:
```zsh
usage: main_mq.py [-h] -i INPUT [-e EPSILON] [-d DELTA] [-b BETA]
                  [-g GLOBAL_SENSITIVITY] [-c COLLABORATORS]
                  [-s SAMPLE_RATE_INVERSE] -a {pmsja,dp_s4s,se_pmsja}
                  [-r REPEATS]

DP-S4S.

options:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
                        Input folder, will glob all text files under the
                        folder
  -e EPSILON, --epsilon EPSILON
                        Epsilon
  -d DELTA, --delta DELTA
                        Delta
  -b BETA, --beta BETA  Beta
  -g GLOBAL_SENSITIVITY, --global_sensitivity GLOBAL_SENSITIVITY
                        Global sensitivity
  -c COLLABORATORS, --collaborators COLLABORATORS
                        Collaborators bound
  -s SAMPLE_RATE_INVERSE, --sample_rate_inverse SAMPLE_RATE_INVERSE
                        Sample rate inverse
  -a {pmsja,dp_s4s,se_pmsja}, --algorithm {pmsja,dp_s4s,se_pmsja}
                        Algorithm
  -r REPEATS, --repeats REPEATS
                        Number of repeats
```

## Docker image

Alternatively, a docker image was prepared for reproducing all the results in the experiments. To build the image, run
```zsh
docker build -t s4s .
```
under the project root. This will automatically install dependencies (but you still need to prepare `./cplex/` and `mosek.lic`)

Then the experiments can be run through calling `run.sh` for scalar query or `run_mq.sh` for vector query.