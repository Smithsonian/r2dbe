close all; clear; clc;

sim_time = 8000;

blank_sig = zeros(sim_time,1); 

%% initial signals


%% set up data signal
% set data0 to all zeros, then all ones, then all 2s, then all 3s, 4s, 5s,
% 6s, 7s, 8s, 9s, 10s, 11s, 12s, 13s, 14s, 15s
npkts = 16;

packet = cell(1,npkts);

pkt_value = mod([0:npkts],16);
data_len = 128;
b_val = repmat([0:1023],512,1);
b_val = b_val(:);
c_val = repmat([0:1023],2,1);
c_val = c_val(:);

% chose ramp values so that after quant it goes 0 1 2 3 0 1 2 3 
ramp_data = repmat([8 15 1 6].',data_len/4.1);

for p = 1:npkts
%     pkt.p0.d0 = (pkt_value(p)+1j*0)*ones(data_len,1);
%     pkt.p0.d1 = (pkt_value(p)+1j*0)*ones(data_len,1);
%     pkt.p0.d2 = (pkt_value(p)+1j*0)*ones(data_len,1);
%     pkt.p0.d3 = (pkt_value(p)+1j*0)*ones(data_len,1);
%     pkt.p0.d4 = (pkt_value(p)+1j*0)*ones(data_len,1);
%     pkt.p0.d5 = (pkt_value(p)+1j*0)*ones(data_len,1);
%     pkt.p0.d6 = (pkt_value(p)+1j*0)*ones(data_len,1);
%     pkt.p0.d7 = (pkt_value(p)+1j*0)*ones(data_len,1);

    for k=0:7
        eval(['pkt.p0.d',num2str(k),' = ramp_data;'])
    end
    
    pkt.p1 = pkt.p0;
    
    pkt.fid = mod(p-1,2);
    pkt.b   = b_val(p);
    pkt.c   = c_val(p);
    
    packet{p} = pkt;
end



%% make data top and data bottom
data_top.time=[];
data_bott.time = [];
data_top.signals.values = blank_sig;
data_bott.signals.values = blank_sig;



eof_val.time = [];
eof_val.signals.values = blank_sig;

pkt_len = 257;

% randomly distributed ons and offs
data_val = rand(sim_time,1)>0.5;
pkt_val.time = [];
pkt_val.signals.values = data_val;


pps.time = [];
pps.signals.values = blank_sig;
pps.signals.values(31)=1;

d = 0;
p = 1;
for k = find(data_val==1).'
    pkt = packet{p};
    % start of pkt?
    if mod(d,pkt_len)==0
        % put the 64 bit b-engine header into the data_top and data_bott  
        [dt,db] = mk_b_hdr(pkt.b,pkt.fid,pkt.c); 
        data_top.signals.values(k) = dt;
        data_bott.signals.values(k) = db;
        
        
        d = 0;
    else
        % put the data in the set
        [dt1,db1,dt2,db2] = mk_data(pkt,ceil(d/2));
        if mod(d,2)==1
            data_top.signals.values(k)=dt1;
            data_bott.signals.values(k)=db1;
        else
            data_top.signals.values(k)=dt2;
            data_bott.signals.values(k)=db2;
        end
        
        
        % if last value, move to next pkt
        if d==256
            p = p+1;
            
            eof_val.signals.values(k)=1;
        end
    end
    
    d = d+1;
        
end

display_pkt_contents(packet)

% lets see if the eof is in the right place
figure(1)
hold all
stairs(pkt_val.signals.values)
stairs(eof_val.signals.values,'k*')
stairs(bitand(bitshift(data_top.signals.values,-4),7))
%ylim([-0.5 10])

sim('uut_sdbe_pipeline');

figure(2)
hold all
stairs(pkt_val_out.Data)
stairs(eof_val_out.Data,'k*')
stairs(bitand(bitshift(data_top_out.Data,-4),7))



%% analyze outputs
d = 0;
p=1;
pkt = [];
for k = find(pkt_val_out.Data==1).'
    
    if mod(d,pkt_len)==0
        % put the 64 bit b-engine header into the data_top and data_bott  
        [b,f,c] = mk_bfc(data_top_out.Data(k),data_bott_out.Data(k)); 
        pkt = [];
        pkt.b = b;
        pkt.fid = f;
        pkt.c = c;
        
        
        d = 0;
    else 
       pkt = mk_data_out(pkt,data_top_out.Data(k),data_bott_out.Data(k),d);
       if d==256
            packet_out{p} = pkt;
            p = p+1;
            
        end 
    end
    
    d = d+1;
    
end


%% print results of network buffer
% why is last packet no good?
display_pkt_contents(packet_out)
% check pkts are same diff
%check_b_eng_diff(packet,packet_out)

%% now final data
%% analyze outputs
p=1;

for k = find(hdr_val_out1.Data==1).'
    pkt = [];
    [b,f,c] = mk_bfc(hdr_top_out1.Data(k),hdr_bott_out1.Data(k)); 
        
    pkt.b = b;
    pkt.fid = f;
    pkt.c = c;
      
    packet_out1{p} = pkt;
    p = p+1;

end


figure(3)
hold all
stairs(data_val_out1.Data)
stairs(eof_val_out1.Data,'k*')
stairs(bitand(bitshift(data_top_out1.Data,-4),7))


p=1;
d=1;
for k = find(data_val_out1.Data==1).'
    if d==1
        pkt = packet_out1{p};
    end
    
    pkt = mk_data_out(pkt,data_top_out1.Data(k),data_bott_out1.Data(k),d);
    packet_out1{p} = pkt;

    if d==256
        d = 1;
        p = p+1;
    else
        d = d+1;
    end
    
end


% drops first packet

packet(1)=[];



display_pkt_contents(packet_out1)



%%  ok on to next: quantize block!
%% analyze outputs
p=1;

for k = find(hdr_val_out2.Data==1).'
    pkt = [];
    [b,f,c] = mk_bfc(hdr_top_out2.Data(k),hdr_bott_out2.Data(k)); 
        
    pkt.b = b;
    pkt.fid = f;
    pkt.c = c;
      
    packet_out2{p} = pkt;
    p = p+1;

end


figure(4)
hold all
stairs(data_val_out2.Data)
stairs(eof_val_out2.Data,'k*')
stairs(bitand(bitshift(data_top_out2.Data,-2),7))


p=1;
d=1;
for k = find(data_val_out2.Data==1).'
    if d==1
        pkt = packet_out2{p};
    end
    
    pkt = mk_data_out_q(pkt,data_top_out2.Data(k),data_bott_out2.Data(k),d);
    packet_out2{p} = pkt;
    if d==256
        d = 1;
        
        p = p+1;
    else
        d = d+1;
    end
    
end

display_pkt_contents(packet_out2)

%% ok now next block: vdif hdr
% this is where i added a delay by 2 out of nowhere

p=1;

for k = find(hdr_val_out3.Data==1).'
    pkt = [];
    [b,f,c] = mk_bfc(hdr_top_out3.Data(k),hdr_bott_out3.Data(k)); 
        
    pkt.b = b;
    pkt.fid = f;
    pkt.c = c;
      
    packet_out3{p} = pkt;
    p = p+1;

end


figure(5)
hold all
stairs(data_val_out3.Data)
stairs(eof_val_out3.Data,'k*')
stairs(bitand(bitshift(data_top_out3.Data,-2),7))


p=1;
d=1;
for k = find(data_val_out3.Data==1).'
    if d==1
        pkt = packet_out3{p};
    end
    
    pkt = mk_data_out_q(pkt,data_top_out3.Data(k),data_bott_out3.Data(k),d);
    packet_out3{p} = pkt;

    if d==256
        d = 1;
        p = p+1;
    else
        d = d+1;
    end
    
end

display_pkt_contents(packet_out3)

%% next block: buffer and thats it
p=1;
vtp_val = nth_valid(data_val_out4.Data,1);
h01_val = nth_valid(data_val_out4.Data,2);
h23_val = nth_valid(data_val_out4.Data,3);
h45_val = nth_valid(data_val_out4.Data,4);
h67_val = nth_valid(data_val_out4.Data,5);
b_val = h45_val;

for k = find(b_val==1).'
    pkt = [];
    [b,f,c] = mk_bfc(data_top_out4.Data(k),data_bott_out4.Data(k)); 
        
    pkt.b = b;
    pkt.fid = f;
    pkt.c = c;
      
    packet_out4{p} = pkt;
    p = p+1;

end





p=1;
d=1;
d_val = data_val_out4.Data-vtp_val-h01_val-h23_val-h45_val-h67_val;

figure(6)
hold all
stairs(d_val)
stairs(eof_val_out4.Data,'k*')
data_top_out4.Data(d_val~=1)=0;
stairs(bitand(bitshift(data_top_out4.Data,-2),7))

for k = find(d_val==1).'
    if d==1
        pkt = packet_out4{p};
    end
    
    pkt = mk_data_out_stack(pkt,data_top_out4.Data(k),data_bott_out4.Data(k),d);
    packet_out4{p} = pkt;
    if d==128
        d = 1;
        p = p+1;
    else
        d = d+1;
    end
    
end

display_pkt_contents(packet_out4)
