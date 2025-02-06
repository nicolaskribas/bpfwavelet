# XDP bench

Collection of scripts to benchmark XDP programs using
[TRex traffic generator](https://trex-tgn.cisco.com/)

## How to use

Install TRex to `/opt/trex`.

```sh
./install-trex.sh --insecure
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
