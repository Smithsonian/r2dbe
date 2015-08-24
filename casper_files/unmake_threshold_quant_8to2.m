% Decompose the given 32bit word into negative, positive and zero threshold
% values.
function [tn,tz,tp] = unmake_threshold_quant_8to2(w)
    tn = typecast(uint8(bitand(int64(w),int64(hex2dec('000000FF')))),'int8');
    tz = typecast(uint8(bitshift(bitand(int64(w),int64(hex2dec('0000FF00'))),-8)),'int8');
    tp = typecast(uint8(bitshift(bitand(int64(w),int64(hex2dec('00FF0000'))),-16)),'int8');
end