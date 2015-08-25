close all; clc;

blank_sig = zeros(1,40000).'; % second is 8192, pkts 2048 long, so 4 pkts per second, 2.5 seconds in sim

pps.time = [];
pps.signals.values = blank_sig;

start_pps = 30;

% determine periods involved
frame_len = 2048;
second = 6*frame_len; % fpga clocks per second
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

%% set enable signal
enable.time = [];
enable.signals.values = blank_sig;
enable.signals.values(401:end)=1;

%% frame in, starts on next pps valid after enable on
frame_in.time = [];
frame_in.signals.values = blank_sig;

% find pulses that happen after enable signal is high
valid_pps = find(pps.signals.values==1 & enable.signals.values==1);

% start frame in signal on first pps after enable high, every 2048

frame_in.signals.values(valid_pps(1):frame_len:end)=1;



%% sec ref ep is constant + cumsum of pps signal, regardless of enable
secs_ref_ep_in.time = [];
secs_ref_ep_in.signals.values = blank_sig+cumsum(pps.signals.values);
secs_ref_ep_in.signals.values(frame_in.signals.values~=1)=0;

%% fnum is 0 every pps, but increments every frame_in (tied to enable)
fnum_in.time = [];
fnum_in.signals.values = blank_sig;
fn=0;
for k=find(frame_in.signals.values==1).';
    fn = fn+1;
    if pps.signals.values(k)==1;
        fn = 0;
    end
    fnum_in.signals.values(k) = fn;
end



%% make data
% 16 pieces of data per clock cycle
% initalize data0-data15 values
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

%% plot initial values, should look like output of hdr block
figure
hold all
stairs(pps.signals.values/3,'k:')
x = find(pps.signals.values==1);
for k=1:length(x)
    text(x(k),1/3,'pps')
end
stairs(fnum_in.signals.values,'color',[0.5 0 0.5])
x = find(frame_in.signals.values==1);
for k=1:length(x)
    text(x(k),fnum_in.signals.values(x(k)),['f=',num2str(fnum_in.signals.values(x(k)))],'color',[.5 0 .5])
end

stairs(secs_ref_ep_in.signals.values,'color',[0 0.5 0])
for k=1:length(x)
    text(x(k),secs_ref_ep_in.signals.values(x(k))-.2,['s=',num2str(secs_ref_ep_in.signals.values(x(k)))],'color',[0 0.5 0])
end

stairs(frame_in.signals.values/2)
legend('pps out','frame num','secs since ref','start of frame')
xlim([0 40000])
title('Input Data')



figure
hold all
stairs(pps.signals.values+1,'k')
for k=0:15
    eval(['x=data',num2str(k),';'])
    stairs(x.signals.values-k*1)
end
set(gca,'YTick',[-15 -14:2:0 1])
set(gca,'YTickLabel',{'data15','data14','data12','data10','data8','data6','data4','data2','data0','pps'})






%% set breakpoint, run simulation

% get data
x = [];
for k=0:15
    eval(['x = [x data_out',num2str(k),'.Data];'])
end
data_stream_out = reshape(x.',1,length(data_out0.Data)*16);


dt = 1/16;
ti = [0:length(data_stream)-1]*dt;
to = [0:length(data_stream_out)-1]*dt;
tpi= [0:length(blank_sig)-1];
tpo= [0:length(sync_out.Data)-1];
figure
hold all
stairs(ti,data_stream/2,'b')
stairs(to,data_stream_out,'r')
stairs(tpi,pps.signals.values/2,'k:')
stairs(tpo,sync_out.Data,'k:')
ylim([-1 2])
legend('input data','output data','pps in','pps out')
title('vdif: serialize hdr block input and output data timing, no latency ')
xlim([12313 12321])
xlabel('fpga clocks (16 data samples each clock)')


%% now analyze output values
% plot and check valid signals

% check hdr_val always equal to the same number
un_hval = unique(duration(hdr_valid_out.Data));
% check vtp val always equal to same number
un_vval = unique(duration(vtp_valid.Data));

nos = 0;
for k=find(frame_out.Data==1).'
    if hdr_valid_out.Data(k)==0 || vtp_valid.Data(k)==0 || data_valid_out.Data(k)==0
        nos=nos+1;
    end
end


figure
hold all
stairs(data_valid_out.Data*2)
stairs(hdr_valid_out.Data*1.5,'color',[0 0.5 0])
stairs(vtp_valid.Data*1,'m')
stairs(frame_out.Data/2,'r')
legend('data out valid','hdr valid','vtp valid','frame out')
xlim([12315 12330])
ylim([-.5 2.5])
grid on
set(gca,'XTick',12315:12330)
set(gca,'XTickLabels',{'12315','12316','12317','12318','12319','12320','12321','12322','12323','12324','12325','12326','12327','12328','12329','12330'})

title({['Output valid signals'],['Unique hdr valid duration: ',num2str(un_hval)],['Unique vtp valid duration: ',num2str(un_vval)],['Number of times frame out valid but something else isnt: ',num2str(nos)]})


% find w0 valid, w1 valid
w0_val = nth_valid(hdr_valid_out.Data,1);
w1_val = nth_valid(hdr_valid_out.Data,2);

figure
hold all
stairs(hdr_valid_out.Data*2)
stairs(w0_val*1.5,'c')
stairs(w1_val*1,'g')
ylim([0 2.5])
grid on
title('Did I select w0 and w1 valids right?')



% now plot output signals as you did the input, but using their separate
% valid signals
secs_ref_ep.Data(w0_val==0)=0;
fnum.Data(w1_val==0)=0;

figure
hold all
stairs(sync_out.Data/3,'k:')
x = find(sync_out.Data==1);
for k=1:length(x)
    text(x(k),1/3,'pps')
end

stairs(fnum.Data,'color',[0.5 0 0.5])
x = find(w1_val==1);
for k=1:length(x)
    text(x(k),fnum.Data(x(k)),['f=',num2str(fnum.Data(x(k)))],'color',[.5 0 .5])
end

stairs(secs_ref_ep.Data,'color',[0 0.5 0])
x = find(w0_val==1);
for k=1:length(x)
    text(x(k),secs_ref_ep.Data(x(k))-.2,['s=',num2str(secs_ref_ep.Data(x(k)))],'color',[.5 0 .5])
end

stairs(frame_out.Data/2)
legend('pps out','frame num','secs since ref','start of frame')
xlim([0 40000])
title('Output Data')


% ()


