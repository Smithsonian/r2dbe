% Test
%close all
%clear all
%clc

x = in_8bit.signals.values(6:end-5);
th = th_new.signals.values(1);
[tn,tz,tp] = unmake_threshold_quant_8to2(th);
nx = zeros(4,1);
nx(1) = sum(x <= tn);
nx(2) = sum(x > tn & x < tz) + ceil(sum(x == tz)/2);
nx(3) = sum(x < tp & x > tz) + floor(sum(x == tz)/2);
nx(4) = sum(x >= tp);

y = out_new_2bit.signals.values(6:end-5);
ny = zeros(4,1);
ny(1) = sum(y==0);
ny(2) = sum(y==1);
ny(3) = sum(y==2);
ny(4) = sum(y==3);
