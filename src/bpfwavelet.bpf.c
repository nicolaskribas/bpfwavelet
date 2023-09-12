#include "vmlinux.h"
#include "bpfwavelet.h"
#include <bpf/bpf_helpers.h>

char __license[] SEC("license") = "GPL";

#define MAX_LEVELS 256

// array of lenght 1, because the timer must be inside a map
struct {
	__uint(type, BPF_MAP_TYPE_ARRAY);
	__uint(max_entries, 1);
	__type(key, __u32);
	__type(value, struct timer_wrapper);
} timer_map SEC(".maps");

struct {
	__uint(type, BPF_MAP_TYPE_RINGBUF);
	__uint(max_entries, 256 * 1024);
} rb SEC(".maps");

// this variables are set in the userspace code
__u64 alpha;
__u64 beta;
__u64 nsecs;
__u16 levels;

static const __u32 timer_key = 0;
static bool timer_was_init = false;
static __u64 pkt_count = 0;
static __u64 sample_idx = 0;
static __u64 w[MAX_LEVELS + 1] = { 0 };
static __u64 s[MAX_LEVELS + 1] = { 0 };

struct timer_wrapper {
	struct bpf_timer timer;
};

static int collect_process_sample(void *map, __u32 *key, struct timer_wrapper *wrap)
{
	__u16 j;
	__u64 x, k;
	struct event *e;

	bpf_timer_start(&wrap->timer, nsecs, 0);
	x = __sync_fetch_and_and(&pkt_count, 0); // atomically read then set to 0
	k = sample_idx;

	for (j = 0; j <= levels && j <= MAX_LEVELS; j++) {
		if (k % 2 == 0) {
			w[j] = x;
			break;
		}
		if (j != 0) { // dont calculate energy for lvl 0 (signal)
			s[j] += (w[j] - x) * (w[j] - x); // s_j <- s_j + (w_{j-1,0} - w_{j-1,1})^2

			if (j >= 2) { // compare with prev only lvl 2 onwards
				if (beta * s[j - 1] > 2 * alpha * s[j]) {
					e = bpf_ringbuf_reserve(&rb, sizeof(struct event), 0);
					if (!e) {
						return 0;
					}
					e->level = j - 1;
					bpf_ringbuf_submit(e, 0);
				}
			}
		}

		x += w[j]; // w_{j-1,0} + w_{j-1,1}
		k >>= 1;
	}

	sample_idx++;
	return 0;
}

SEC("xdp")
int xdp_pass(struct xdp_md *ctx)
{
	/* void *data = (void *)(long)ctx->data; */
	/* void *data_end = (void *)(long)ctx->data_end; */
	/* int pkt_sz = data_end - data; */

	struct timer_wrapper *wrap = bpf_map_lookup_elem(&timer_map, &timer_key);
	if (wrap) {
		if (!timer_was_init) {
			bpf_timer_init(&wrap->timer, &timer_map, 1);
			bpf_timer_set_callback(&wrap->timer, collect_process_sample);
			bpf_timer_start(&wrap->timer, nsecs, 0);
			timer_was_init = true;
		}
		__sync_add_and_fetch(&pkt_count, 1); // atomically increment by 1
	}

	return XDP_PASS;
}
