#include <errno.h>
#include <netdb.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/epoll.h>
#include <time.h>
#include <unistd.h>

#include "vdif.h"

void error(char *msg) {
	perror(msg);
	exit(1);
}

int main(int argc, char **argv) {
	// UDP socket for data receiption
	int sockfd;
	char *hostname;
	int portno;
	struct sockaddr_in server_addr;
	struct hostent *server;
	int optval;

	// epoll stuff
	#define MAX_EVENTS 10
	struct epoll_event ev, events[MAX_EVENTS];
	int nfds, epollfd;

	// VTP / VDIF data
	uint32_t npkt;
	uint32_t npkt_recv;
	vdif_r2dbe_vtp_t *vtp_pkt_buf;
	vdif_r2dbe_packet_t *vdif_pkt_buf;
	uint64_t psn_prev, psn_curr;
	ssize_t n_bytes_received;
	ssize_t n_bytes_expected;

	// Output
	char *outfile;
	FILE *fh;

	// Program flow
	int flag_verbose = 0;
	int ttl = 0;
	int ttl_left;
	time_t start;
	time_t current;
	int opt;

	// misc
	int ii;
	int rv;

	// Parse command-line arguments:
	//   1) first any optional arguments
	while ((opt = getopt(argc, argv, "vt:")) != -1) {
		switch(opt) {
			case 't':
				ttl = atoi(optarg);
				break;
			case 'v':
				flag_verbose++;
				break;
			default: // '?'
				error("ERROR parsing command line options");
		}
	}
	//   2) then obligatory positional arguments
	if (argc-optind < 4) {
		fprintf(stderr, "usage: %s [-v] [-t TTL] <hostname> <portno> <npkt> <outfile>\n", argv[0]);
		exit(1);
	}
	hostname = argv[optind];
	portno = atoi(argv[optind+1]);
	npkt = atoi(argv[optind+2]);
	outfile = argv[optind+3];

	// Allocate VTP buffer space
	vtp_pkt_buf = (vdif_r2dbe_vtp_t *)calloc(sizeof(vdif_r2dbe_vtp_t),npkt);

	// Open socket to receive data:
	//   1) get server by hostname
	server = gethostbyname(hostname);
	if (server == NULL) {
		error("ERROR get host by name");
	}
	//   2) open socket
	sockfd = socket(AF_INET, SOCK_DGRAM, 0);
	if (sockfd < 0) {
		error("ERROR opening socket");
	}
	//   3) set socket option to reuse address
	optval = 1;
	setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR, (const void *)&optval , sizeof(int));
	//   4) set server address parameters
	bzero((char *) &server_addr, sizeof(server_addr));
	server_addr.sin_family = AF_INET;
	bcopy((char *)server->h_addr, (char *)&server_addr.sin_addr, server->h_length);
	server_addr.sin_port = htons((unsigned short)portno);
	//    5) and bind
	if (bind(sockfd, (struct sockaddr *) &server_addr, sizeof(server_addr)) < 0) {
		error("ERROR on binding");
	}

	// Set up epoll
	epollfd = epoll_create1(0);
	if (epollfd == -1) {
		error("ERROR on epoll_create");
	}
	ev.events = EPOLLIN;
	ev.data.fd = sockfd;
	if (epoll_ctl(epollfd, EPOLL_CTL_ADD, sockfd, &ev) == -1) {
		error("ERROR on epoll_ctl");
	}

	// Main receive loop, just write VTP packets to buffer
	n_bytes_received = 0;
	n_bytes_expected = npkt*sizeof(vdif_r2dbe_vtp_t);
	start = time(NULL);
	ttl_left = ttl;
	while (n_bytes_received < n_bytes_expected) {

		// Update current time and check if TTL is over
		current = time(NULL);
		if (ttl > 0 && (current - start) > ttl) {
			fprintf(stdout,"warning: TTL elapsed\n");
			break;
		}

		nfds = epoll_wait(epollfd, events, MAX_EVENTS, ttl_left);
		if (nfds == -1) {
			error("ERROR on epoll_wait");
		}

		for (ii=0; ii<nfds; ii++) {
			// Receive bytes
			rv = recv(sockfd, (void *)vtp_pkt_buf+n_bytes_received, n_bytes_expected-n_bytes_received, 0);// MSG_DONTWAIT);

			// Check return value for possible error conditions
			if (rv < 0) {
				//if (errno != EAGAIN && errno != EWOULDBLOCK) {
					error("ERROR in recv");
				//}

				// Just no data yet, reiterate
				//continue;
			}

			// Increment total bytes received
			n_bytes_received += rv;
		}

	}

	// Close epoll file descriptor
	close(epollfd);

	// Done receiving data, close socket
	close(sockfd);

	// Count number of packets received
	npkt_recv = n_bytes_received / sizeof(vdif_r2dbe_vtp_t);
	if (npkt_recv > 0) {

		if (flag_verbose > 0) {
			fprintf(stdout,"received %d packets\n",npkt_recv);
		}

		// Warn if less than expected number of packets
		if (npkt_recv < npkt) {
			fprintf(stdout,"warning: only %d of %d requested packets received\n",npkt_recv,npkt);
		}

		// Allocate VDIF buffer space
		vdif_pkt_buf = (vdif_r2dbe_packet_t *)calloc((size_t)npkt_recv, sizeof(vdif_r2dbe_packet_t));
		if (vdif_pkt_buf == NULL) {
			error("ERROR on buffer memory allocation");
		}

		// Copy VDIF from VTP buffer to VDIF buffer
		psn_prev = 0;
		for (ii=0; ii<npkt_recv; ii++) {
			memcpy((void *)(vdif_pkt_buf+ii), (void *)&(vtp_pkt_buf+ii)->pkt, sizeof(vdif_r2dbe_vtp_t));
			psn_curr = (vdif_pkt_buf+ii)->header.edh_psn;
			if (psn_prev && psn_curr > psn_prev+1) {
				fprintf(stdout,"warning: PSN increment by more than 1, [n]=%lu, [n-1]=%lu (diff is %lu)\n",psn_curr,psn_prev,psn_curr-psn_prev);
			}
			if (flag_verbose > 2) {
				fprintf(stdout,"Received packet: ");
				print_header(&(vdif_pkt_buf+ii)->header);
				fprintf(stdout,"\n");
			}
			psn_prev = psn_curr;
		}

		// Initialize output file
		fh = fopen(outfile,"w+");
		if (fh == NULL) {
			error("ERROR opening outfile");
		}

		// Write data to file
		fwrite((void *)vdif_pkt_buf, sizeof(vdif_r2dbe_packet_t), npkt_recv, fh);

		// Close output file
		fclose(fh);

		// Free VDIF buffer memory
		free(vdif_pkt_buf);
	} else {
		fprintf(stdout,"warning: no packets received, no outfile '%s' written.\n",outfile);
	}

	// Free VTP buffer memory
	free(vtp_pkt_buf);

	return 0;
}

