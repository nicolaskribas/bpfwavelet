# bpfwavelet: Periodicity detection using discrete wavelet transform in eBPF

## Building

### Dependencies

`make`, `clang`, `libelf` and `zlib` packages are needed to build. Make sure
they are installed.

Also, this project depends on `libbpf` and `bpftool`. We do vendoring of both as
git submodules in this repository. Clone the repository like this:

```shell
git clone --recurse-submodules https://github.com/nicolaskribas/bpfwavelet.git
```

If you already cloned the repository you can initialize the submodules like
this:

```shell
git submodule update --init --recursive
```

### Compiling

```shell
make bpfwavelet
```

## Usage

```text
bpfwavelet [options] <ifname>
options:
  -h  print help
  -v  use verbose output
  -g  generic mode (XDP_FLAGS_SKB_MODE)
  -d  drv mode (XDP_FLAGS_DRV_MODE)
  -o  offload mode (XDP_FLAGS_HW_MODE)
  -r  reflects traffic back to the same interface (use XDP_TX instead of XDP_PASS)
  -a <integer> set alpha value (defaults to 3)
  -b <integer> set beta value (defaults to 2)
  -t <integer> set the interval (in nanoseconds) between samples (defaults to 1000000000)
  -l <integer> set the number of decomposition levels (defaults to 17)
```
