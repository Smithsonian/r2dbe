function d = duration(vec)

% a function that outputs the duration of different pulses in vector vec

df = diff(vec);

starts = find(df==1)+1;
stops  = find(df==-1)+1;

% if we start during a pulse, discard
if stops(1)<starts(1)
    stops(1)=[];
end

% if we end during a pulse, then the last start is greater than last stop
if starts(end)>stops(end)
    starts(end)=[];
end


d = stops-starts;

end