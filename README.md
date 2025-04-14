# XDP bench

Collection of scripts to benchmark XDP programs using
[TRex traffic generator](https://trex-tgn.cisco.com/)

## How to use

Install TRex to `/opt/trex`.

```sh
./install-trex.sh --insecure
```

Enable hugepages
```sh
./enable-hugepages.sh
```

Now, disable simultaneous multithreading (SMT), boost and C-states, and set
scaling governor to performance.

```sh
./disable-dynamic-cpu-features.sh
```

To configure TRex you can use `dpdk_setup_ports.py` interactively to select
which ports to use. It also automatically assign which cores to use, so make
sure to run it after `disable-dynamic-cpu-features.sh` as it disables SMT.

```sh
pushd /opt/trex/current
./dpdk_setup_ports.py -i --force-macs
popd
```

```sh
./run-bench
```

You can run the benchmark script in the same machine where TRex is running or
you can forward the ports to it and run the scrip locally:

```sh
ssh -L 4501:localhost:4501 -L 4500:localhost:4500 <trexserver>
```

```sh
./t-rex-64 -i -c 14
```
