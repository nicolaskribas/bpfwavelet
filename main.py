import sys

sys.path.append("/opt/trex/current/trex_client/interactive")

import trex_stl_lib.api as trex
import trex.examples.stl.ndr_bench as ndr


class FileLogger(trex.Logger):
    def __init__(self, log_file_name: str, verbose="info"):
        super(FileLogger, self).__init__(verbose)
        self.log = open(log_file_name, "a")

    def _write(self, msg, newline):
        if newline:
            self.log.write(msg)
        else:
            self.log.write(msg)

    def _flush(self):
        self.log.flush()


client = trex.STLClient(verbose_level="info", logger=None)
client.connect()
client.reset()

profile = trex.STLProfile.load_py("traffic_profile.py")
if profile is None:
    exit(1)

streams = profile.get_streams()
client.add_streams(streams)

config = ndr.NdrBenchConfig(
    ports=[],
    title="Title",
    cores=client.get_server_system_info()["dp_core_count_per_port"],  # just for logging
    iteration_duration=20,
    q_full_resolution=2,
    first_run_duration=20,
    pdr=0.1,
    pdr_error=1,
    ndr_results=1,
    max_iterations=10,
    max_latency=0,
    lat_tolerance=0,
    verbose=True,
    bi_dir=False,
    plugin_file=None,
    tunables={},
    opt_binary_search=False,
    opt_binary_search_percentage=5,
    total_cores=client.get_server_system_info()["dp_core_count"],  # just for logging
    kwargs={},  # this is not used
)

bench = ndr.NdrBench(stl_client=client, config=config)
bench.find_ndr()
client.disconnect()

bench.results.print_final()
