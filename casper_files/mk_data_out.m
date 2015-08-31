function [pkt] = mk_data_out(pkt,dt,db,d)


if mod(d,2)==1
    d = ceil(d/2);
    % data is from d0,1,2,3
    pkt.p0.d0(d) = bitand(bitshift(dt,-28),2^4-1) + 1j*bitand(bitshift(dt,-24),2^4-1);
    pkt.p1.d0(d) = bitand(bitshift(dt,-20),2^4-1) + 1j*bitand(bitshift(dt,-16),2^4-1);
    pkt.p0.d1(d) = bitand(bitshift(dt,-12),2^4-1) + 1j*bitand(bitshift(dt,-8),2^4-1);
    pkt.p1.d1(d) = bitand(bitshift(dt,-4),2^4-1) + 1j*bitand(dt,2^4-1);
    
    pkt.p0.d2(d) = bitand(bitshift(db,-28),2^4-1) + 1j*bitand(bitshift(db,-24),2^4-1);
    pkt.p1.d2(d) = bitand(bitshift(db,-20),2^4-1) + 1j*bitand(bitshift(db,-16),2^4-1);
    pkt.p0.d3(d) = bitand(bitshift(db,-12),2^4-1) + 1j*bitand(bitshift(db,-8),2^4-1);
    pkt.p1.d3(d) = bitand(bitshift(db,-4),2^4-1) + 1j*bitand(db,2^4-1);
    
else
    d = ceil(d/2);
    % data is from d4 d5 d6 d7
    pkt.p0.d4(d) = bitand(bitshift(dt,-28),2^4-1) + 1j*bitand(bitshift(dt,-24),2^4-1);
    pkt.p1.d4(d) = bitand(bitshift(dt,-20),2^4-1) + 1j*bitand(bitshift(dt,-16),2^4-1);
    pkt.p0.d5(d) = bitand(bitshift(dt,-12),2^4-1) + 1j*bitand(bitshift(dt,-8),2^4-1);
    pkt.p1.d5(d) = bitand(bitshift(dt,-4),2^4-1) + 1j*bitand(dt,2^4-1);
    
    pkt.p0.d6(d) = bitand(bitshift(db,-28),2^4-1) + 1j*bitand(bitshift(db,-24),2^4-1);
    pkt.p1.d6(d) = bitand(bitshift(db,-20),2^4-1) + 1j*bitand(bitshift(db,-16),2^4-1);
    pkt.p0.d7(d) = bitand(bitshift(db,-12),2^4-1) + 1j*bitand(bitshift(db,-8),2^4-1);
    pkt.p1.d7(d) = bitand(bitshift(db,-4),2^4-1) + 1j*bitand(db,2^4-1);
    
end


