#include "vmlinux.h"
#include "bpfwavelet.h"
#include <bpf/bpf_helpers.h>

char __license[] SEC("license") = "GPL";

#define MAX_LEVELS 29

struct {
	__uint(type, BPF_MAP_TYPE_HASH);
	__uint(max_entries, 1);
	__type(key, u16);
	__type(value, struct counter);
} flow SEC(".maps");

int alpha;
int beta;

struct counter {
	u64 pkt_count;
	u64 sample_idx;
	u64 w[MAX_LEVELS];
	u64 s[MAX_LEVELS - 1];
	struct bpf_timer timer;
};

static int calculate(void *map, int *key, struct counter *val)
{
	u8 j;
	u64 x, k;

	bpf_timer_start(&val->timer, 1000000000, 0);
	x = __sync_fetch_and_and(&val->pkt_count, 0); // atomically read then set to 0
	k = val->sample_idx;

	bpf_printk("count:%d", x);
	bpf_printk("i:%d", k);

	for (j = 0; j < MAX_LEVELS; j++) {
		if (k % 2 == 0) {
			val->w[j] = x;
		} else {
			if (j != 0) { // dont calculate energy for lvl 0 (signal)
				val->s[j - 1] += (val->w[j] - x) * (val->w[j] - x);

				if (j >= 2) { // compare with prev only lvl 2 onwards
					if (2 * alpha * val->s[j - 1] < beta * val->s[j - 2]) {
						bpf_printk("periodicity detected lvl %ld", j);
					}
				}
			}

			x = val->w[j] + x;
			k >>= 1;
		}
	}

	for (j = 1; j < MAX_LEVELS; j++) {
		bpf_printk(" [%d]:%ld", j, val->s[j - 1]);
	}

	val->sample_idx++;
	return 0;
}

SEC("xdp")
int xdp_pass(struct xdp_md *ctx)
{
	void *data = (void *)(long)ctx->data;
	void *data_end = (void *)(long)ctx->data_end;

	int pkt_sz = data_end - data;
	int idx = 0;

	struct counter empty_counter = { 0 };

	struct counter *fldt = bpf_map_lookup_elem(&flow, &idx);
	if (fldt) {
		__sync_add_and_fetch(&fldt->pkt_count, 1); // atomically increment by 1
	} else {
		// for initialization the timer must be already in a map
		// so we insert, retrive and then initialize
		bpf_map_update_elem(&flow, &idx, &empty_counter, BPF_NOEXIST);
		fldt = bpf_map_lookup_elem(&flow, &idx);
		if (fldt) {
			bpf_timer_init(&fldt->timer, &flow, 1);
			bpf_timer_set_callback(&fldt->timer, calculate);
			bpf_timer_start(&fldt->timer, 1000000000, 0);
		}
	}

	return XDP_PASS;
}
