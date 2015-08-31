function [n_fails, n_passes] = check_f0_at_pps(packet)

npkts = length(packet);
n_fails = 0;
n_passes = 0;

for p=1:npkts
    pkt = packet{p};
    if p~=1
        if pkt.s~=s_last
            % its the first packet aligned with a new second
            if pkt.f~=0
                n_fails = n_fails+1;
            else
                n_passes= n_passes+1;
            end
        end
    end
    s_last = pkt.s;
end

end