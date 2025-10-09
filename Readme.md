## Docker image

This project requires the IBM ILOG CPLEX Python API. Follow the IBM instructions to download and extract IBM ILOG CPLEX Optimization Studio, then set the Docker build argument `CPLEX_WHEEL` to the extracted wheel path (for example `third_party/cplex/python/3.10/x86-64_linux/cplex-22.1.1.0-cp310-cp310-linux_x86_64.whl`).

```bash
docker build \
  --build-arg CPLEX_WHEEL=third_party/cplex/python/3.10/x86-64_linux/cplex-22.1.1.0-cp310-cp310-linux_x86_64.whl \
  -t record-sampling .
```

Only the `dp_s4s` and `se_blackbox` algorithms sweep the sample-rate parameter. `r2t` runs once per dataset/query combination by default. Set `ENABLE_R2T=0` when invoking `scripts/run_algorithms_docker.sh` if you want to omit the `r2t` runs.
