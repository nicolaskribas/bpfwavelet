import argparse
from os import path

import trex_stl_lib.api as trex
from trex_stl_lib.api import IP, UDP, Ether


class STLS1(object):
    def create_stream(self, pkt_len):
        # Create base packet and pad it to size
        size = pkt_len - 4  # HW will add 4 bytes Ethernet FCS

        base_pkt = Ether() / IP() / UDP()
        pad = "x" * max(0, size - len(base_pkt))

        streams = trex.STLProfile(
            [
                trex.STLStream(
                    packet=trex.STLPktBuilder(pkt=base_pkt / pad),
                    mode=trex.STLTXCont(pps=1),
                ),
                trex.STLStream(
                    packet=trex.STLPktBuilder(pkt=base_pkt / pad),
                    mode=trex.STLTXCont(pps=1000),
                    flow_stats=trex.STLFlowLatencyStats(pg_id=1),
                ),
            ]
        )

        return streams

    def get_streams(self, direction, tunables, **kwargs):
        parser = argparse.ArgumentParser(
            description="Argparser for {}".format(path.basename(__file__)),
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        parser.add_argument(
            "--size",
            type=int,
            default=64,
            help="The packets size in the regular stream",
        )
        args = parser.parse_args(tunables)
        return self.create_stream(pkt_len=args.size)


# dynamic load - used for TRex console or simulator
def register():
    return STLS1()
