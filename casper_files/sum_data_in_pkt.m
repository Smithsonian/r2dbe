function [sdata] = sum_data_in_pkt(packet)

npkts = length(packet);
sdata = zeros(1,npkts);

for p=1:npkts
    pkt = packet{p};
    sdata(p) = sum(pkt.d);
end

end