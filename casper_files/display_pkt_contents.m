function display_pkt_contents(packet_out)

npkts = length(packet_out);
for p=1:npkts
    S = sprintf('Pkt: %d',p);
    disp(S)
    po = packet_out{p};
    S = sprintf('    result b,f,c: %d,%d,%d',po.b,po.fid,po.c);
    disp(S)
    
    
    for ph = 0:1
        for data = 0:7
            x = po;
            eval(['dat = x.p',num2str(ph),'.d',num2str(data),';'])
            S = sprintf(['    unique p%d d%d:'],ph,data);
            disp(S)
            S = sprintf('          %d',unique(dat));
            disp(S)
        end
    end
    
    x = [];
    y = [];
    xe = [];
    ye = [];
    L = 8;
    for k = 0:7
        eval(['d = packet_out{1}.p0.d',num2str(k),'(1:L);'])
        d = d(:);
        x = [x real(d)];
        eval(['d = packet_out{1}.p1.d',num2str(k),'(1:L);'])
        d = d(:);
        y = [y real(d)];
        eval(['d = packet_out{1}.p0.d',num2str(k),'(end-L+1:end);'])
        d = d(:);
        xe = [xe real(d)];
        eval(['d = packet_out{1}.p1.d',num2str(k),'(end-L+1:end);'])
        d = d(:);
        ye = [ye real(d)];
        
    end
    
    p0 = x
    p0end = xe
    p1 = y
    p1end = ye
end

