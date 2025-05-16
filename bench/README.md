# XDP bench

Collection of scripts to benchmark XDP programs using
[TRex traffic generator](https://trex-tgn.cisco.com/)

## Dependencies

- **Python**: You need to install
  [uv package manager](https://docs.astral.sh/uv/) to manage Python dependencies
  and Python itself.

- **TRex**: We provide a [script](install-trex.sh) to install TRex.

## Setting up the traffic generator

1. Install TRex to `/opt/trex`

   ```sh
   ./install-trex.sh --insecure
   ```

   `--insecure` tells curl **not** to verify server's TLS certificate. Needed
   because TRex servers has problems with certificates.

   See `./install-trex.sh --help` for more usage options.

2. Enable hugepages

   ```sh
   ./enable-hugepages.sh
   ```

3. Disable dynamic CPU features

   Now, disable simultaneous multithreading (SMT), boost and C-states, and set
   scaling governor to performance.

   ```sh
   ./disable-dynamic-cpu-features.sh
   ```

4. Configure TRex

   To configure TRex you can use `dpdk_setup_ports.py` interactively to select
   which ports to use. It also automatically assign which cores to use, so make
   sure to run it after disabling SMT.

   ```sh
   cd /opt/trex/current
   ./dpdk_setup_ports.py -i --force-macs
   ```

   You can find more information on configuring TRex in its
   [official documentation](https://trex-tgn.cisco.com/trex/doc/trex_manual.html)
   under section “3. First time running.”

## Setting up the device under test

Well, this is particular to your use case. But a good practice is to disable
dynamic CPU feature:

```sh
./disable-dynamic-cpu-features.sh
```

## Running

1. Start TRex

   ```sh
   cd /opt/trex/current
   ./t-rex-64 -i -c numberofcores
   ```

2. Run the benchmark

   ```sh
   uv run main.py
   ```

   See `uv run main.py --help` for documentation and available options.

> [!TIP]
> You can run the benchmark script locally and make it control a TRex server
> started remotely.
>
> For this you have to, first, forward the ports used for controlling the TRex
> server, that is ports 4500 and 4501:
>
> ```sh
> ssh -L 4500:localhost:4500 -L 4501:localhost:4501 user@trexserver
> ```
>
> Then you can run the benchmark script normally.
