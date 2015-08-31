function [pkt] = mk_data_out_stack(pkt,dt,db,d)


    % data is from d0,1,2,3
    pkt.p0.d0(d) = bitand(bitshift(dt,-30),2^2-1) + 1j*bitand(bitshift(dt,-28),2^2-1);
    pkt.p1.d0(d) = bitand(bitshift(dt,-26),2^2-1) + 1j*bitand(bitshift(dt,-24),2^2-1);
    pkt.p0.d1(d) = bitand(bitshift(dt,-22),2^2-1) + 1j*bitand(bitshift(dt,-20),2^2-1);
    pkt.p1.d1(d) = bitand(bitshift(dt,-18),2^2-1) + 1j*bitand(bitshift(dt,-16),2^2-1);
    
    pkt.p0.d2(d) = bitand(bitshift(dt,-14),2^2-1) + 1j*bitand(bitshift(dt,-12),2^2-1);
    pkt.p1.d2(d) = bitand(bitshift(dt,-10),2^2-1) + 1j*bitand(bitshift(dt,-8),2^2-1);
    pkt.p0.d3(d) = bitand(bitshift(dt,-6),2^2-1) + 1j*bitand(bitshift(dt,-4),2^2-1);
    pkt.p1.d3(d) = bitand(bitshift(dt,-2),2^2-1) + 1j*bitand(dt,2^4-1);

    % data is from d0,1,2,3
    pkt.p0.d4(d) = bitand(bitshift(db,-30),2^2-1) + 1j*bitand(bitshift(db,-28),2^2-1);
    pkt.p1.d4(d) = bitand(bitshift(db,-26),2^2-1) + 1j*bitand(bitshift(db,-24),2^2-1);
    pkt.p0.d5(d) = bitand(bitshift(db,-22),2^2-1) + 1j*bitand(bitshift(db,-20),2^2-1);
    pkt.p1.d5(d) = bitand(bitshift(db,-18),2^2-1) + 1j*bitand(bitshift(db,-16),2^2-1);
    
    pkt.p0.d6(d) = bitand(bitshift(db,-14),2^2-1) + 1j*bitand(bitshift(db,-12),2^2-1);
    pkt.p1.d6(d) = bitand(bitshift(db,-10),2^2-1) + 1j*bitand(bitshift(db,-8),2^2-1);
    pkt.p0.d7(d) = bitand(bitshift(db,-6),2^2-1) + 1j*bitand(bitshift(db,-4),2^2-1);
    pkt.p1.d7(d) = bitand(bitshift(db,-2),2^2-1) + 1j*bitand(db,2^2-1);
end


