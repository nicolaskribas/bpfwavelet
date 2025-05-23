#include "bpfwavelet.h"
#include "bpfwavelet.skel.h"

#include <ctype.h> // isprint()
#include <linux/if_link.h> // XDP flags
#include <net/if.h> // if_nametoindex()
#include <signal.h> // signal()
#include <time.h>
#include <unistd.h> // getopt()

#define DEFAULT_ALPHA	 3
#define DEFAULT_BETA	 2
#define DEFAULT_INTERVAL 1000000000 // 1 second
#define DEFAULT_LEVELS	 17

static volatile bool verbose = false;
static int libbpf_print_fn(enum libbpf_print_level level, const char *format, va_list args)
{
	if (verbose || level == LIBBPF_WARN) {
		return vfprintf(stderr, format, args);
	}

	return 0;
}

static volatile bool exiting = false;
static void sig_handler(int sig)
{
	exiting = true;
}

static char *mode_name(__u32 mode_flag)
{
	switch (mode_flag) {
	case XDP_FLAGS_SKB_MODE:
		return "XDP_FLAGS_SKB_MODE";
		break;
	case XDP_FLAGS_DRV_MODE:
		return "XDP_FLAGS_DRV_MODE";
		break;
	case XDP_FLAGS_HW_MODE:
		return "XDP_FLAGS_HW_MODE";
		break;
	default:
		return "This should not happen";
		break;
	}
}

void usage(char *prog_name)
{
	fprintf(stderr,
		"usage: %s [options] <ifname>\n"
		"options:\n"
		"  -h  print help\n"
		"  -v  use verbose output\n"
		"  -g  generic mode (XDP_FLAGS_SKB_MODE)\n"
		"  -d  drv mode (XDP_FLAGS_DRV_MODE)\n"
		"  -o  offload mode (XDP_FLAGS_HW_MODE)\n"
		"  -r  reflects traffic back to the same interface (use XDP_TX instead of XDP_PASS)\n"
		"  -a <integer> set alpha value (defaults to %d)\n"
		"  -b <integer> set beta value (defaults to %d)\n"
		"  -t <integer> set the interval (in nanoseconds) between samples (defaults to %d)\n"
		"  -l <integer> set the number of decomposition levels (defaults to %d)\n",
		prog_name, DEFAULT_ALPHA, DEFAULT_BETA, DEFAULT_INTERVAL, DEFAULT_LEVELS);
}

static int handle_event(void *ctx, void *data, size_t data_sz)
{
	const struct event *e = data;
	struct timespec tp;

	clock_gettime(CLOCK_REALTIME, &tp);

	char buf[sizeof "2024-03-26T15:29:54.479-03:00"];
	size_t bufsize = sizeof buf;
	int off = 0;
	struct tm *local = localtime(&tp.tv_sec);
	off = strftime(buf, bufsize, "%FT%T", local);
	off += snprintf(buf + off, bufsize - off, ".%03ld", tp.tv_nsec / 1000000);
	off += snprintf(buf + off, bufsize - off, "%c%02ld:%02ld",
			local->tm_gmtoff >= 0 ? '+' : '-', labs(local->tm_gmtoff) / 3600,
			labs(local->tm_gmtoff) % 3600 / 60);

#ifdef DEBUG
	__u16 levels = *(__u16 *)ctx;
	if (e->is_debug) {
		printf("%s debug id %llu value %llu\n", buf, e->debug.id, e->debug.value);

		printf("w: ");
		for (int j = 0; j <= levels && j <= MAX_LEVELS; j++) {
			printf("%llu ", e->debug.w[j]);
		}
		printf("\ns: ");
		for (int j = 0; j <= levels && j <= MAX_LEVELS; j++) {
			printf("%llu ", e->debug.s[j]);
		}
		printf("\n");
		return 0;
	}
#endif /* DEBUG */

	printf("%s detected level %hu\n", buf, e->level);

	return 0;
}

int main(int argc, char **argv)
{
	setlinebuf(stdout);

#ifdef DEBUG
	fprintf(stderr, "bpfwavelet was compiled with debug code\n");
#endif /* DEBUG */

	struct bpfwavelet_bpf *skel;
	struct ring_buffer *rb = NULL;
	int err;
	int detach_err;
	int read;
	int ifindex;
	int prog_fd;
	bool attached = false;
	int c;
	__u32 attach_mode = 0;
	__u64 alpha = DEFAULT_ALPHA;
	__u64 beta = DEFAULT_BETA;
	__u64 interval = DEFAULT_INTERVAL;
	__u16 levels = DEFAULT_LEVELS;
	bool reflect = false;

	while ((c = getopt(argc, argv, ":vhgdora:b:t:l:")) != -1) {
		switch (c) {
		case 'v':
			verbose = true;
			break;
		case 'h':
			usage(argv[0]);
			return 0;
			break;
		case 'g':
			attach_mode = XDP_FLAGS_SKB_MODE;
			break;
		case 'd':
			attach_mode = XDP_FLAGS_DRV_MODE;
			break;
		case 'o':
			attach_mode = XDP_FLAGS_HW_MODE;
			break;
		case 'r':
			reflect = true;
			break;
		case 'a':
			read = sscanf(optarg, "%llu", &alpha);
			if (read != 1) {
				fprintf(stderr, "error: could not parse argument for '-a'\n");
				usage(argv[0]);
				return 1;
			}
			break;
		case 'b':
			read = sscanf(optarg, "%llu", &beta);
			if (read != 1) {
				fprintf(stderr, "error: could not parse argument for '-b'\n");
				usage(argv[0]);
				return 1;
			}
			break;
		case 't':
			read = sscanf(optarg, "%llu", &interval);
			if (read != 1) {
				fprintf(stderr, "error: could not parse argument for '-t'\n");
				usage(argv[0]);
				return 1;
			}
			break;
		case 'l':
			read = sscanf(optarg, "%hu", &levels);
			if (read != 1) {
				fprintf(stderr, "error: could not parse argument for '-l'\n");
				usage(argv[0]);
				return 1;
			}
			break;
		case ':':
			fprintf(stderr, "error: option '-%c' needs an argument\n", optopt);
			usage(argv[0]);
			return 1;
			break;
		case '?':
			if (isprint(optopt)) {
				fprintf(stderr, "error: unrecognized option '-%c'\n", optopt);
			} else {
				fprintf(stderr, "error: unrecognized option caractere '\\x%x'\n",
					optopt);
			}
			usage(argv[0]);
			return 1;
			break;
		default:
			return 1;
			break;
		}
	}

	if (optind >= argc) {
		fprintf(stderr, "error: no ifname supplied\n");
		usage(argv[0]);
		return 1;
	} else if (optind != argc - 1) { // is last argument
		fprintf(stderr, "error: too many arguments supplied\n");
		usage(argv[0]);
		return 1;
	} else if ((attach_mode & XDP_FLAGS_MODES) == 0) {
		fprintf(stderr, "error: xdp mode not specified\n");
		usage(argv[0]);
		return 1;
	}

	ifindex = if_nametoindex(argv[optind]);
	if (ifindex == 0) {
		fprintf(stderr, "error: no interface named '%s' found. %s\n", argv[optind],
			strerror(errno));
		return 1;
	}

	libbpf_set_print(libbpf_print_fn);

	signal(SIGINT, sig_handler);
	signal(SIGTERM, sig_handler);

	skel = bpfwavelet_bpf__open();
	if (skel == NULL) {
		err = -1;
		fprintf(stderr, "error: failed to open or load BPF program. %s\n", strerror(errno));
		goto cleanup;
	}
	skel->rodata->alpha = alpha;
	skel->rodata->beta = beta;
	skel->rodata->nsecs = interval;
	skel->rodata->levels = levels;
	skel->rodata->reflect = reflect;
	err = bpfwavelet_bpf__load(skel);
	if (err) {
		fprintf(stderr, "error: failed to load and verify BPF skeleton\n");
		goto cleanup;
	}

	rb = ring_buffer__new(bpf_map__fd(skel->maps.rb), handle_event, &levels, NULL);
	if (!rb) {
		err = -1;
		fprintf(stderr, "failed to create ring buffer\n");
		goto cleanup;
	}

	if (verbose) {
		fprintf(stderr, "attaching with mode %s\n", mode_name(attach_mode));
	}

	prog_fd = bpf_program__fd(skel->progs.bpfwavelet);
	err = bpf_xdp_attach(ifindex, prog_fd, attach_mode | XDP_FLAGS_UPDATE_IF_NOEXIST, NULL);
	if (err) {
		fprintf(stderr, "error: failed to attach BPF program: %d\n", err);
		goto cleanup;
	}
	attached = true;

	if (verbose) {
		fprintf(stderr, "runing with alpha=%llu  beta=%llu  interval=%llu  levels=%u\n",
			alpha, beta, interval, levels);
	}

	while (!exiting) {
		if (verbose)
			fprintf(stderr, ".");
		err = ring_buffer__poll(rb, 100);
		/* Ctrl-C will cause -EINTR */
		if (err == -EINTR) {
			err = 0;
			break;
		}
		if (err < 0) {
			fprintf(stderr, "error polling ring buffer: %d\n", err);
			break;
		}
	}

cleanup:
	if (attached) {
		detach_err = bpf_xdp_attach(ifindex, -1, attach_mode, NULL);
		if (detach_err < 0) {
			fprintf(stderr, "error detaching %d", detach_err);
		}
	}

	ring_buffer__free(rb);
	bpfwavelet_bpf__destroy(skel);
	return err < 0 ? -err : 0;
}
