#include "vmlinux.h"
#include "bpfwavelet.h"
#include <bpf/bpf_helpers.h>

char __license[] SEC("license") = "GPL";

#define MAX_LEVELS 256

// array of lenght 1, because the time must be inside a map
struct {
	__uint(type, BPF_MAP_TYPE_ARRAY);
	__uint(max_entries, 1);
	__type(key, u32);
	__type(value, struct counter);
} flow SEC(".maps");

// this variables are set in the userspace code
__u64 alpha;
__u64 beta;
__u64 nsecs;
__u8 levels;

static bool timer_was_init = false;
static u64 pkt_count = 0;
static u64 sample_idx = 0;
static u64 w[MAX_LEVELS] = { 0 };
static u64 s[MAX_LEVELS - 1] = { 0 };

struct counter {
	struct bpf_timer timer;
};

static int calculate(void *map, int *key, struct counter *val)
{
	u8 j;
	u64 x, k;

	bpf_timer_start(&val->timer, nsecs, 0);
	x = __sync_fetch_and_and(&pkt_count, 0); // atomically read then set to 0
	k = sample_idx;

	bpf_printk("count:%d", x);
	bpf_printk("i:%d", k);

	for (j = 0; j < levels; j++) {
		if (k % 2 == 0) {
			w[j] = x;
			break;
		} else {
			bpf_printk("caclulating with %ld %ld", w[j], x);
			if (j != 0) { // dont calculate energy for lvl 0 (signal)
				s[j - 1] += (w[j] - x) * (w[j] - x);

				if (j >= 2) { // compare with prev only lvl 2 onwards
					if (2 * alpha * s[j - 1] < beta * s[j - 2]) {
						bpf_printk("periodicity detected lvl %ld", j);
					}
				}
			}

			x += w[j];
			bpf_printk("result x %ld", x);
			k >>= 1;
		}
	}

	for (j = 1; j < levels; j++) {
		bpf_printk(" [%d]:%ld", j, s[j - 1]);
	}

	sample_idx++;
	return 0;
}

SEC("xdp")
int xdp_pass(struct xdp_md *ctx)
{
	void *data = (void *)(long)ctx->data;
	void *data_end = (void *)(long)ctx->data_end;

	int pkt_sz = data_end - data;

	int key = 0;
	struct counter *fldt = bpf_map_lookup_elem(&flow, &key);
	if (fldt) {
		if (!timer_was_init) {
			bpf_timer_init(&fldt->timer, &flow, 1);
			bpf_timer_set_callback(&fldt->timer, calculate);
			bpf_timer_start(&fldt->timer, nsecs, 0);
			timer_was_init = true;
		}
		__sync_add_and_fetch(&pkt_count, 1); // atomically increment by 1
	}

	return XDP_PASS;
}
