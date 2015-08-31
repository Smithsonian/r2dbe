close all; clc;

sim_time = 80000;

blank_sig = zeros(1,sim_time).'; % second is 8192, pkts 2048 long, so 4 pkts per second, 2.5 seconds in sim

pps.time = [];
pps.signals.values = blank_sig;


% starting inds
start_pps = 31;
start_reset = 10;
stop_reset  = 19;
start_sec_ref_ep = 50;
start_enable = 1401;

% determine periods involved
frame_len = 2048;
second = 6.5*frame_len; % fpga clocks per second
dur = 1; % on for 10 clocks

% create a vector of actual periods in the pps pulse
npulses = floor(length(blank_sig)/second)+1;
periods = second*ones(1,npulses); 

% create pps input signal, start at 30, end at 39
start_ind = start_pps;
stop_ind  = start_ind+dur-1;

for p = 1:length(periods)
    if stop_ind<length(blank_sig)
        pps.signals.values(start_ind:stop_ind) = 1;
    end
    start_ind = start_ind+periods(p);
    stop_ind  = start_ind+dur-1;
end

%% set little end
little_end.time = [];
little_end.signals.values = blank_sig;
% in practice we swap to little endian, but in sim its a pain to undo
%little_end.signals.values(100:end)=1;

s_at_0 = 10;
strue = s_at_0+cumsum(pps.signals.values); % true seconds since epoch vector

sec_ref_ep.time = [];
sec_ref_ep.signals.values = blank_sig;
sec_ref_ep.signals.values(start_sec_ref_ep:end)=s_at_0;

% now set reset signals AFTER first pps at time 30
reset.time = [];
reset.signals.values = blank_sig;
reset.signals.values(start_reset:stop_reset) = 1; % so ends up being on for 10 clocks, then back to 0

%% set enable signal
enable.time = [];
enable.signals.values = blank_sig;
enable.signals.values(start_enable:end)=1;

% find pulses that happen after enable signal is high
valid_pps = find(pps.signals.values==1 & enable.signals.values==1);


%% make data
xd.time = [];
xd.signals.values = blank_sig;

% set data values to something, data stream 16 times the length of ind data
% data set to single pulse with pps timing, so data0 at each pulse is a 1
data_matrix = repmat(blank_sig,1,16);
data_matrix(start_pps:second:end,1)=1;



data_stream = reshape(data_matrix.',16*length(blank_sig),1);


% distribute data_stream into the 16 matlab variables
for k=0:15
    xd.signals.values = data_matrix(:,k+1);
    eval(['data',num2str(k),'=xd;'])
end

% figure 1: plot of parallel input data streams and input pps
figure(1)
hold all
stairs(pps.signals.values+1,'k')
for k=0:15
    eval(['x=data',num2str(k),';'])
    stairs(x.signals.values-k*1)
end
set(gca,'YTick',[-15 -14:2:0 1])
set(gca,'YTickLabel',{'data15','data14','data12','data10','data8','data6','data4','data2','data0','pps'})

%%
% figure 8: plot starting conditions by clock
tpi= [0:length(pps.signals.values)-1]+1;
figure(8)
hold all


stairs(tpi,strue,'k:')
text(0,max(strue),'true time')

text(valid_pps(1),2,'system enabled on this pps')

stairs(tpi,enable.signals.values,'g')
stairs(tpi,reset.signals.values,'b')
stairs(tpi,pps.signals.values,'k')
stairs(tpi,sec_ref_ep.signals.values,'r')

title('Starting conditions')
xlabel('FPGA clocks')
xlim([0 sim_time])

xlim([0 15000])

text(start_enable,2.5,'enable signal set by r2dbe_start','interpreter','none')
xlim([0 2000])

text(0,4.5,['r2dbe_start calcs secs from ref ep as ',num2str(s_at_0)],'interpreter','none')
text(start_reset,4,'reset signal set high then low by r2dbe_start','interpreter','none')
text(start_pps,3.5,['first pps at ',num2str(start_pps)])
text(start_sec_ref_ep,3,'sec_ref_ep constant set by r2dbe_start','interpreter','none')
xlim([0 100])




%% run simulation
sim('uut_vdif')


% get data_valid from tx_valid

% from start of tx_valid
% 1: vtp val
% 2: hdr val
% 3
% 4
% 5
% 6: data valid
% 7
% ...
% 1029

vtp_val = nth_valid(tx_val.Data,1);

hdr_start = nth_valid(tx_val.Data,2);
hind_val = find(hdr_start==1);
hdr_val = make_valid(frame_len,4,hind_val(1),zeros(size(tx_val.Data)));

data_start = nth_valid(tx_val.Data,6);
dind_val = find(data_start==1);
data_val = make_valid(frame_len,frame_len/2,dind_val(1),zeros(size(tx_val.Data)));

w0_valid = nth_valid(hdr_val,1);
w1_valid = nth_valid(hdr_val,1);

% calculate latency
total_latency = dind_val(1)-valid_pps(1);
strue_latent = [s_at_0*ones(total_latency-5,1); strue];


%% now analyze output values
% plot and check valid signals
% get data


x = [];
for k=0:31
    % load data from sim variable
    eval(['d = data_out_final',num2str(k),'.Data;'])
    % mask data that isnt valid (else hdr data split into all data streams)
    d = d.*data_val;
    % append this one stream of data to matrix
    x = [x d];
end
% serialize data in time order
data_stream_out_final = reshape(x.',1,length(data_out_final0.Data)*32);




% plot valid signals
% figure 2: plot the output valid signals
figure(2)
hold all
stairs(tx_val.Data*3,'k')
stairs(data_val*2)
stairs(hdr_val*1.5,'color',[0 0.5 0])
stairs(vtp_val*1,'m')
stairs(w0_valid*0.5,'k')
stairs(w1_valid*0.5,'k*')
stairs(end_of_frame.Data/2,'r')
legend('tx_val','data out valid','hdr valid','vtp valid','w0_val','w1_val','end_of_frame','Location','northwest')
%xlim([12315 12330])
ylim([-.5 2.5])
grid on
%set(gca,'XTick',12315:12330)
%set(gca,'XTickLabel',{'12315','12316','12317','12318','12319','12320','12321','12322','12323','12324','12325','12326','12327','12328','12329','12330'})

title({['Output valid signals']})


% now plot output signals as you did the input, but using their separate
% valid signals

% set non-valid parts of signal to 0, w0 and w1 valid on 1st clock of
% hdr_valid signal, as they are stacked into 1 64 bit word

secs_ref_ep_final.Data(w0_valid==0)=0;
fnum_final.Data(w1_valid==0)=0;

% figure 3: otuput frame num, secs since ref ep, 
figure(3)
hold all

stairs(fnum_final.Data,'color',[0.5 0 0.5])
x = find(w1_valid==1);
for k=1:length(x)
    text(x(k),fnum_final.Data(x(k)),['f=',num2str(fnum_final.Data(x(k)))],'color',[.5 0 .5])
end

stairs(secs_ref_ep_final.Data,'color',[0 0.5 0])
for k=1:length(x)
    text(x(k),secs_ref_ep_final.Data(x(k))-.5,['s=',num2str(secs_ref_ep_final.Data(x(k)))],'color',[0 0.5 0])
end

stairs(strue_latent,'k:')

legend('frame num','secs since ref','secs since ref (true)','Location','northwest')
xlim([0 sim_time])
title('Output timing and data')


% figure 4: input data + pps, output data + 1st data val (no pps)


dt1 = 1/16;
dt2 = 1/32;
ti = [0:length(data_stream)-1]*dt1;
to = [0:length(data_stream_out_final)-1]*dt2;
tpi= [0:length(pps.signals.values)-1];
tpo= [0:length(data_val)-1];

% figure 4: input data + pps, output data + 1st data val of pkt (no pps)
figure(4)
hold all
stairs(ti,data_stream,'b')
stairs(to,data_stream_out_final,'r')
stairs(tpi,pps.signals.values,'k:')
stairs(tpo,data_val,'k')
% stairs(tpo,data_valid_out_final.Data*2,'k')
ylim([-1 2])
legend('Input data','Output data','pps in','data_val','Location','northwest')
title('vdif: total pipeline ')
%xlim([12317 12323])
xlabel('fpga clocks (32 data samples each clock)')
ylim([-0.5 2.5])
% xlim([12321-2 12321+2])
% xlim([13346-2 13346+2])


% ()
%% gather packets into group for testing

n_pkts = sum(vtp_val);
packet = cell(n_pkts);
pkt_start = find(vtp_val==1);

for p = 1:n_pkts
    v_ind = pkt_start(p);
    s_ind = v_ind+1;
    f_ind = s_ind;
    d_ind_start = s_ind+4;
    d_ind_stop  = d_ind_start+frame_len/2-1;
    if length(data_out_final0.Data)<d_ind_stop
        d_ind_stop = length(data_out_final0.Data);
    end
    pkt.s = secs_ref_ep_final.Data(s_ind);
    pkt.f = fnum_final.Data(f_ind);
    pkt.strue = strue_latent(d_ind_start);
    
    x = [];
    for k=0:31
        % load data from sim variable
        eval(['d = data_out_final',num2str(k),'.Data(d_ind_start:d_ind_stop);'])
        x = [x d];
    end
    pkt.d = x(:);
    
    packet{p} = pkt;
    
    
end



%% checks
clc
%display_pkt_contents(packet)
[nsecs, npkts] = display_pkt_info(packet);

disp('Check F=0 at second boundary...')
[nf, np] = check_f0_at_pps(packet);
if nf~=0
    S = sprintf('    FAIL: Num pkts for which frame 0 not at first pkt of pps: %d',nf);
else
    S = sprintf('    PASS: Every time s increments, f = 0');
end
disp(S)

disp('Check F continuous (adjusted at second boundary)...')
[nf, np] = check_f_consec(packet);
if nf~=0
    S = sprintf('    FAIL: Num pkts for which f not cont''s (adj. at pps): %d',nf);
else
    S = sprintf('    PASS: frame number F continuous across all packets');
end
disp(S)

disp('Check fmax is unique...')
[unique_fmax, nf, np] = check_unique_fmax(packet);
if nf~=0
    S = sprintf('    FAIL: fmax changes, unique fmax vals: %d',unique_fmax);
else
    if nsecs<3
        S = sprintf('    Longer sim needed...');
    else
        S = sprintf('    PASS: fmax is unique during simulation time (%d)',unique_fmax);
    end
end
disp(S)

disp('Check at second boundary first data value in pkt is 1...')
[nf,np] = check_d0_at_pps(packet);
if nf~=0
    S = sprintf('    FAIL: Num pkts for which 1st data point in pkt at pps not 1: %d',nf);
else
    S = sprintf('    PASS: first data value is 1 on all second boundaries');
end
disp(S)

disp('Sum of data in each pkt...')
[sdata] = sum_data_in_pkt(packet);
Sa = sprintf('    sum of data: ');
Sb = sprintf('%d',sdata);
S = strcat(Sa,Sb);
disp(S)

disp('Check seconds since epoch aligned with real time...')
[nf,np] = check_s_v_true(packet);
if nf~=0
    S = sprintf('    FAIL: Num pkts for time stamp is not equal to correct time (sec): %d',nf);
else
    S = sprintf('    PASS: Second counter correct with real time');
end
disp(S)