import sys
from collections.abc import Iterator
import pywt
import numpy as np

alpha = 3
beta = 2


def detect_with_s(s):
    detected = []
    for j in range(1, len(s)):
        if beta * s[j - 1] > 2 * alpha * s[j]:
            detected.append(j)
    return detected


def detect_energy(e):
    detected = []
    for j in range(1, len(e)):
        if beta * e[j - 1] > alpha * e[j]:
            detected.append(j)
    return detected


def calculate_s(samples):
    a = [samples]
    for j in range(1, len(samples).bit_length()):
        aj = []
        for k in range(0, len(a[j - 1]) // 2):
            aj.append(a[j - 1][2 * k] + a[j - 1][2 * k + 1])
        a.append(aj)

    s = []
    for j in range(1, len(samples).bit_length()):
        acc = 0
        for k in range(0, len(a[j - 1]) // 2):
            acc += (a[j - 1][2 * k] - a[j - 1][2 * k + 1]) ** 2
        s.append(acc)
    return s


def energy(d):
    return [np.sum(np.square(dj)) / len(dj) for dj in d]


def double_check(samples: list[int], _: list[int], s: list[int]):
    d = pywt.wavedec(samples, "haar")[:0:-1]
    e = energy(d)
    dwt_max_level = len(samples).bit_length() - 1
    offline_s = calculate_s(samples)

    print(len(samples), "samples:", samples)
    print("can calculate", dwt_max_level, "decomposition levels")
    print()
    print("offline full dwt")
    print("energy:", e)
    print("detected:", detect_energy(e))
    print()
    print("offline with simplification")
    print("s:", offline_s)
    print("detected:", detect_with_s(offline_s))
    print()
    print("online (with simplification)")
    print("s:", s[0:dwt_max_level])
    print("detected:", detect_with_s(s[0:dwt_max_level]))
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
