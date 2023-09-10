#include "bpfwavelet.h"
#include "bpfwavelet.skel.h"
#include <bpf/libbpf.h>
#include <linux/if_link.h>

#include <net/if.h>
#include <signal.h>

#include <unistd.h>

static int libbpf_print_fn(enum libbpf_print_level level, const char *format, va_list args)
{
	return vfprintf(stderr, format, args);
}

static volatile bool exiting = false;
static void sig_handler(int sig)
{
	exiting = true;
}

int main(int argc, char **argv)
{
	struct bpfwavelet_bpf *skel;
	int err;
	int ifindex;
	int prog_fd;
	bool attached = false;

	if (argc > 2) {
		fprintf(stderr, "Too many arguments supplied.\n");
		return 1;
	} else if (argc == 1) {
		fprintf(stderr, "Expecting ifname as argument.\n");
		return 1;
	}

	libbpf_set_print(libbpf_print_fn);

	signal(SIGINT, sig_handler);
	signal(SIGTERM, sig_handler);

	ifindex = if_nametoindex(argv[1]);
	if (ifindex == 0) {
		fprintf(stderr, "No interface found with given name. %s\n", strerror(errno));
		return 1;
	}

	skel = bpfwavelet_bpf__open_and_load();
	if (skel == NULL) {
		fprintf(stderr, "Failed to open or load BPF program. %s\n", strerror(errno));
		goto cleanup;
	}

	skel->bss->beta = 3;
	skel->bss->alpha = 2;

	prog_fd = bpf_program__fd(skel->progs.xdp_pass);
	err = bpf_xdp_attach(ifindex, prog_fd, XDP_FLAGS_SKB_MODE, NULL);
	if (err) {
		fprintf(stderr, "Failed to attach: %d\n", err);
		goto cleanup;
	}
	attached = true;

	fprintf(stderr, "Started!\n");

	while (!exiting) {
		fprintf(stderr, ".");
		sleep(1);
	}

cleanup:
	if (attached)
		bpf_xdp_detach(ifindex, 0, NULL);
	bpfwavelet_bpf__destroy(skel);
}
