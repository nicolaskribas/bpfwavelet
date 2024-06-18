#ifndef __BPFWAVELET_H
#define __BPFWAVELET_H

#define MAX_LEVELS 16

struct event {
#ifdef DEBUG
	unsigned char is_debug;
	union {
#endif /* DEBUG */

		short unsigned int level;

#ifdef DEBUG
		struct {
			long long unsigned int id;
			long long unsigned int value;
			long long unsigned int w[MAX_LEVELS + 1];
			long long unsigned int s[MAX_LEVELS + 1];
		} debug;
	};
#endif /* DEBUG */
};

#endif /* __BPFWAVELET_H */
