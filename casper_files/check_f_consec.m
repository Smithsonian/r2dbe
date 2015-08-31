function [n_fails, n_passes] = check_f_consec(packet)

npkts = length(packet);
n_fails = 0;
n_passes = 0;

for p=1:npkts
    pkt = packet{p};
    if p~=1
        if pkt.s~=s_last
            % its the first packet aligned with a new second
            f_last = -1;
        end
        if pkt.f-f_last~=1
            n_fails = n_fails+1;
        else
            n_passes = n_passes+1;
        end
    end
    
    s_last = pkt.s;
    f_last = pkt.f;
end

end