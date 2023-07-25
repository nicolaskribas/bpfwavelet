#include <errno.h>
#include <unistd.h>
#include <signal.h>
#include <net/if.h>

#include "wavelets.h"
#include <wavelets.skel.h>
#include <bpf/libbpf.h>
#include <linux/if_link.h>

static volatile sig_atomic_t exiting = 0;

static void sig_int(int signo)
{
	exiting = 1;
}

static int libbpf_print_fn(enum libbpf_print_level level, const char *format, va_list args)
{
	return vfprintf(stderr, format, args);
}

int main(int argc, char **argv)
{
	int err;
	int prog_fd;
	unsigned int ifindex;
	struct wavelets_bpf *skel;

	// enable debug printing for the libbpf functions
	libbpf_set_print(libbpf_print_fn);

	if (argc > 2) {
		fprintf(stderr, "Too many arguments supplied.\n");
		return 1;
	} else if (argc == 1) {
		fprintf(stderr, "Expecting ifname as argument.\n");
		return 1;
	}

	ifindex = if_nametoindex(argv[1]);
	if (ifindex == 0) {
		fprintf(stderr, "No interface found with given name. %s\n", strerror(errno));
		return 1;
	}

	skel = wavelets_bpf__open_and_load();
	if (skel == NULL) {
		fprintf(stderr, "Failed to open or load BPF program. %s\n", strerror(errno));
		return 1;
	}
	
	prog_fd = bpf_program__fd(skel->progs.xdp_pass);

	err = bpf_xdp_attach(ifindex, prog_fd, 0, NULL);
	if (err) {
		fprintf(stderr, "Failed to attach: %d\n", err);
		goto cleanup;
	}

	if (signal(SIGINT, sig_int) == SIG_ERR) {
		fprintf(stderr, "Can't set signal handler. %s\n", strerror(errno));
		goto cleanup;
	}

	printf("Started!\n");

	while (!exiting) {
		fprintf(stderr, ".");
		sleep(1);
	}

	wavelets_bpf__detach(skel);

cleanup:
	wavelets_bpf__destroy(skel);
}
