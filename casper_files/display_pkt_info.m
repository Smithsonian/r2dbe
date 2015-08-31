function [nsecs,npkts] = display_pkt_info(packet)

npkts = length(packet);
nsecs = 0;
for p=1:npkts
    pkt = packet{p};
    if pkt.f==0
        nsecs = nsecs+1;
    end
end

S1 = sprintf('Pkt info:');
S2 = sprintf('    total pkts tx: %d', npkts);
S3 = sprintf('    total seconds: %d', nsecs);
disp(S1)
disp(S2)
disp(S3)
end