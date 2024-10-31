#include "vmlinux.h"
#include "bpfwavelet.h"
#include <bpf/bpf_helpers.h>

char __license[] SEC("license") = "GPL";

// array of length 1, because the timer must be inside a map
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
const volatile __u64 alpha;
const volatile __u64 beta;
const volatile __u64 nsecs;
const volatile __u16 levels;
const volatile bool reflect;

static const __u32 timer_key = 0;
static bool timer_was_init = false;
static __u64 pkt_count = 0;
static __u64 sample_idx = 0;
static __u64 w[MAX_LEVELS + 1] = { 0 }; // w[0] holds a sample
static __u64 s[MAX_LEVELS + 1] = { 0 };

struct timer_wrapper {
	struct bpf_timer timer;
};

static __always_inline void swap_src_dst_mac(void *data)
{
	unsigned short *p = data;
	unsigned short dst[3];

	dst[0] = p[0];
	dst[1] = p[1];
	dst[2] = p[2];
	p[0] = p[3];
	p[1] = p[4];
	p[2] = p[5];
	p[3] = dst[0];
	p[4] = dst[1];
	p[5] = dst[2];
}

static int collect_process_sample(void *map, __u32 *key, struct timer_wrapper *wrap)
{
	__u16 j;
	__u64 x, k;
	struct event *e;

	bpf_timer_start(&wrap->timer, nsecs, 0);
	x = __sync_fetch_and_and(&pkt_count, 0); // atomically read then set to 0
	k = sample_idx;

#ifdef DEBUG
	__u64 value = x;
#endif /* DEBUG */

	for (j = 0; j <= levels && j <= MAX_LEVELS; j++) {
		if (k % 2 == 0) {
			w[j] = x;
			break;
		}
		s[j] += (w[j] - x) * (w[j] - x); // s_j <- s_j + (w_{j-1,0} - w_{j-1,1})^2

		if (j >= 1) { // compare with prev only lvl 1 onwards
			if (beta * s[j - 1] > 2 * alpha * s[j]) {
				e = bpf_ringbuf_reserve(&rb, sizeof(*e), 0);
				if (e) {
#ifdef DEBUG
					e->is_debug = false;
#endif /* DEBUG */
					e->level = j;
					bpf_ringbuf_submit(e, 0);
				}
			}
		}

		x += w[j]; // w_{j-1,0} + w_{j-1,1}
		k >>= 1;
	}

#ifdef DEBUG
	e = bpf_ringbuf_reserve(&rb, sizeof(*e), 0);
	if (e) {
		e->is_debug = true;
		e->debug.id = sample_idx + 1;
		e->debug.value = value;
		for (j = 0; j <= levels && j <= MAX_LEVELS; j++) {
			e->debug.s[j] = s[j];
			e->debug.w[j] = w[j];
		}

		bpf_ringbuf_submit(e, 0);
	}
#endif /* DEBUG */

	sample_idx++;
	return 0;
}

SEC("xdp")
int bpfwavelet(struct xdp_md *ctx)
{
	void *data_end = (void *)(long)ctx->data_end;
	void *data = (void *)(long)ctx->data;
	struct ethhdr *eth = data;
	__u64 nh_off = sizeof(*eth);

	struct timer_wrapper *wrap = bpf_map_lookup_elem(&timer_map, &timer_key);
	if (wrap) {
		if (!timer_was_init) {
			bpf_timer_init(&wrap->timer, &timer_map, 1); // 1 = CLOCK_MONOTONIC
			bpf_timer_set_callback(&wrap->timer, collect_process_sample);
			bpf_timer_start(&wrap->timer, nsecs, 0);
			timer_was_init = true;
		}
		__sync_add_and_fetch(&pkt_count, 1); // atomically increment by 1
	}

	if (reflect) {
		if (data + nh_off > data_end)
			return XDP_ABORTED;

		swap_src_dst_mac(data);
		return XDP_TX;
	}

	return XDP_PASS;
}
