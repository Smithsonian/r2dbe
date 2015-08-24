% Compose the threshold 32bit word for the given positive, negative and
% zero values.
function [th] = make_threshold_quant_8to2(tp,tz,tn)
    bits_tn = uint64(bitcmp(uint8(abs(tn)-1)));
    bits_tz = bitshift(uint64(tz),8);
    bits_tp = bitshift(uint64(tp),16);
    th = bitor(bits_tn,bits_tz);
    th = bitor(th,bits_tp);
    th = bitor(uint64(hex2dec('80000000')),uint64(th));
end