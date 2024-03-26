#ifndef __BPFWAVELET_H
#define __BPFWAVELET_H

#include <stdbool.h>
struct event {
	// true for detected periodicity, false if contains sample for debugging
	bool detection;
	union {
		short unsigned int level;
		struct {
			long long unsigned int id;
			long long unsigned int value;
		} sample;
	};
};

#endif /* __BPFWAVELET_H */
