function [unique_fmax, nf, np] = check_unique_fmax(packet)

npkts = length(packet);

fmax = [];

for p=1:npkts
    pkt = packet{p};
    if p~=1
        if pkt.s~=s_last
            % its the first packet aligned with a new second, change f_last
            fmax = [fmax f_last];  % append the last frame number to fmax array
        end
    end
    s_last = pkt.s;
    f_last = pkt.f;
end

unique_fmax = unique(fmax);


% uh oh, there are packets of different lengths
nf = sum(fmax~=max(unique_fmax));
np = length(fmax)-nf;

end