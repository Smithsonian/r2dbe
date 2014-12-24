import sys, struct

stdin = sys.stdin
stdout = sys.stdout

# Read the PCAP file header first
pcap_hdr_bin = stdin.read(24)
if len(pcap_hdr_bin) != 24:
    raise RuntimeError("Error reading PCAP header!")

# Check for correct PCAP magic number
pcap_hdr = struct.unpack('IHHiIII', pcap_hdr_bin)
if pcap_hdr[0] != 0xa1b2c3d4:
    raise ValueError("Not a PCAP file? Bad magic number!")

# Loop until done
reading = True
while reading:

    # Read first PCAP packet header
    pcap_pkt_hdr_bin = stdin.read(16)
    if len(pcap_pkt_hdr_bin) == 0:
        reading = False
        continue
    elif len(pcap_pkt_hdr_bin) != 16:
        raise RuntimeError("Error reading file. Incomplete PCAP packet?")

    # Get length of the packet payload
    pcap_pkt_hdr = struct.unpack('IIII', pcap_pkt_hdr_bin)
    pkt_len = pcap_pkt_hdr[3]

    # Read the UDP packet
    udp_bin = stdin.read(pkt_len)
    if len(udp_bin) != pkt_len:
        raise RuntimeError("Error reading file. Incomplete PCAP packet?")

    # Strip out UDP header and PSN
    stdout.write(udp_bin[50:])
