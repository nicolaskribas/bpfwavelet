import sys
from collections.abc import Iterator
import pywt
import numpy as np

alpha = 3
beta = 2


def detect_with_online_calculated_s(s):
    detected = []
    for j in range(1, len(s)):
        if beta * s[j - 1] > 2 * alpha * s[j]:
            detected.append(j)
    return detected


def detect_with_offline_calculated_energy(e):
    detected = []
    for j in range(1, len(e)):
        if beta * e[j - 1] > alpha * e[j]:
            detected.append(j)
    return detected


def energy(d):
    return [np.sum(np.square(dj)) / len(dj) for dj in d]


def double_check(samples: list[int], _: list[int], s: list[int]):
    d = pywt.wavedec(samples, "haar")[:0:-1]
    e = energy(d)
    dwt_max_level = len(samples).bit_length() - 1

    print("sample", len(samples))
    print("can calculate", dwt_max_level, "decomposition levels")
    print()
    print("offline")
    print("energy:", e)
    print("detected:", detect_with_offline_calculated_energy(e))
    print()
    print("online s")
    print("s:", s[1 : dwt_max_level + 1])
    print("detected:", detect_with_online_calculated_s(s[1 : dwt_max_level + 1]))
    print("------------------------")


type Event = tuple[int, int, list[int], list[int]]


def parse_input() -> Iterator[Event]:
    try:
        while line := sys.stdin.readline():
            words = line.split()
            if words[1] == "detected":
                print("bpfwavelet detected", words[3])
            elif words[1] == "debug":
                idx = int(words[3])
                sample = int(words[5])
                w = [int(x) for x in sys.stdin.readline().split()[1:]]
                s = [int(x) for x in sys.stdin.readline().split()[1:]]
                yield (idx, sample, w, s)
            else:
                print("bug in parsing", file=sys.stderr)
                return
    except KeyboardInterrupt:
        return


def main():
    samples = []
    expected_idx = 1

    for idx, sample, w, s in parse_input():
        if idx != expected_idx:
            print("WARN: out of order index", file=sys.stderr)
        expected_idx = idx + 1

        samples.append(sample)
        double_check(samples, w, s)


if __name__ == "__main__":
    main()
