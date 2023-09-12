# bpfwavelet: periodicity detection using discrete wavelet transform in BPF

# Building

## Dependencies

`make`, `clang`, `libelf` and `zlib` packages are needed to build. Make sure they are installed.

Also, this project depends on `libbpf` and `bpftool`. We do vendoring of both as git submodules in this repository.
So clone the repository like this:

```shell
git clone --recurse-submodules <url>
```

If you already cloned the repository you can initialize the submodules like this:

```shell
git submodule update --init --recursive
```

## Compiling

```shell
make bpfwavelet
```

# Usage

```
bpfwavelet [options] <ifname>
options:
  -h  print help
  -v  use verbose output
  -a  set alpha value
  -b  set beta value
  -t  set the interval (in nanoseconds) between samples
  -l  set the number of decomposition levels
```
