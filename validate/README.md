# Validating

## Scripts

`bpfwavelet_pcap` wraps bpfwavelet and passes the pcap it receives from stdin
through it.

We used `isolate-heartbleed` to filter the relevant packets from
`Wednesday-workingHours.pcap`, generating the file `captures/heartbleed.pcap`.

`run` uses `bpfwavelet_pcap` to analyze each capture in `captures/` and outputs
to `results/`

## Captures

In `validate/` there is `Wednesday-workingHours.pcap` with 13G and
`cobalt-strike.pcap` 11M.

`isolate-heartbleed` transforms `Wednesday-workingHours.pcap` into
`captures/heartbleed.pcap`

Other files in `captures/` are `captures/cobalt-strike.pcap`,
`captures/trickbot-a.pcap`, and `captures/trickbot-b.pcap`. They are exact
copies of traffic from the datasets.

```text
09721b1e3203d78aeb282f0012e2f6d0959c65e8c1a9399e43912c640bfbc7e1  captures/cobalt-strike.pcap
fcbe7d4671580b060c6ed953c4dfd207fceea0be95d3b6d52acfe6db3a4f6134  captures/trickbot-b.pcap
5b92c31bc68255d98cc8f0d116234863b7f95863ada7cb322f1484d638ca7f63  captures/trickbot-a.pcap
```

```text
09721b1e3203d78aeb282f0012e2f6d0959c65e8c1a9399e43912c640bfbc7e1  datasets/2021-05-13-Hancitor-traffic-with-Ficker-Stealer-and-Cobalt-Strike/2021-05-13-Hancitor-traffic-with-Ficker-Stealer-and-Cobalt-Strike.pcap
fcbe7d4671580b060c6ed953c4dfd207fceea0be95d3b6d52acfe6db3a4f6134  datasets/2019-12-26-IcedID-infection-with-Trickbot-gtag-tin233/2019-12-26-IcedID-infection-with-Trickbot-gtag-tin233.pcap
5b92c31bc68255d98cc8f0d116234863b7f95863ada7cb322f1484d638ca7f63  datasets/2019-10-31-IcedID-infection-with-Trickbot/2019-10-31-IcedID-infection-with-Trickbot.pcap
```

## Logs and results

`results/` have the raw output of bpfwavelet.

## Analysis and plotting

`analysis.ipynb`
