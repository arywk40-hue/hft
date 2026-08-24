"""Reproducible batch-size-one latency measurements."""
from __future__ import annotations
import platform, time, numpy as np

def benchmark(callable_, *, warmup: int = 1000, iterations: int = 10000) -> dict[str, float | int | str]:
    for _ in range(warmup): callable_()
    samples=np.empty(iterations,dtype=np.int64)
    for i in range(iterations):
        start=time.perf_counter_ns(); callable_(); samples[i]=time.perf_counter_ns()-start
    return {"warmup_iterations":warmup,"timed_iterations":iterations,"p50_ns":float(np.percentile(samples,50)),"p95_ns":float(np.percentile(samples,95)),"p99_ns":float(np.percentile(samples,99)),"mean_ns":float(samples.mean()),"std_ns":float(samples.std()),"python":platform.python_version(),"os":platform.platform(),"numpy":np.__version__}
