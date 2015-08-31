function val = nth_valid(val_vec,n)

% returns vector of valid signals for the nth clock into each long pulse
% for example, hdr_valid is on for 8, but want the valid for word 1 (the
% 2nd in, n=2)

dur=duration(val_vec);
un_dur = unique(dur);

% check that there is one unique valid duration
if length(un_dur)~=1
    'inconsistent num of consec. valids in vector'
end

% check that n is less than or equal to the length of this duration
if n>un_dur
    'n outside of duration of valids in vector'
end

% then return first of each

df = diff(val_vec);

starts = find(df==1)+1;

val = zeros(size(val_vec));


for s=starts.';
    val(s+n-1)=1;    
end

