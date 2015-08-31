function v = make_valid(per,dur,ind_start,blank_vec)

% makes a column vector of valids
% signal length L, starting at ind_start, duration dur, period per

v = blank_vec;

for d = 1:dur
    v(ind_start+d-1:per:end)=1;
end
