# bpfwavelet: Periodicity detection using discrete wavelet transform in eBPF

In this repository you will find the source code for bpfwavelet, as well as
sources for our experiments and analysis.

Under the directory [src/](src/) is the source code for the eBPF program. See
the [README.md](src/README.md) for more information on building and running it.

In the directory [bench/](bench/) you will find scripts using in the benchmarks
for bpfwavelet. We implemented a non-drop rate benchmark using the TRex traffic
generator. See the [README.md](bench/README.md) on how to reproduce our
benchmark.

Following we have [bench-analysis/](bench-analysis/) with python notebooks used
to analise and visualize the results of the benchmark.

In [validade/](validade/) is located packet captures to demonstrate use cases of
bpfwavelet as well as the script used to

In [check/](check/) there is scripts used for checking the correctness of our
implementation. We compared results of our algorithm implemented in eBPF with
one implementation in python that uses a known wavelet library.
