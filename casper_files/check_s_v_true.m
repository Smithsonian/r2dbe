function [n_fails, n_passes] = check_s_v_true(packet)

npkts = length(packet);
n_fails = 0;
n_passes= 0;

for p=1:npkts
    pkt = packet{p};
    if pkt.s~=pkt.strue
        n_fails = n_fails+1;
    else
        n_passes= n_passes+1;
    end
end

end