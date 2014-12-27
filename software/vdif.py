from struct import pack, unpack
from datetime import datetime, timedelta, tzinfo
from numpy import int32, uint32, array, zeros


class UTC(tzinfo):
    """ UTC tzinfo """

    def utcoffset(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return timedelta(0)


class VDIFFrameHeader(object):

    def __init__(self, sample_rate=4096e6):
        self.sample_rate = sample_rate

        # word 0
        self.invalid_data = False
        self.legacy_mode = False
        self.secs_since_epoch = 0

        # word 1
        self.ref_epoch = 0
        self.data_frame = 0

        # word 2
        self.vdif_vers = 0
        self.log2_chans = 0
        self.frame_length = 0

        # word 3
        self.complex = False
        self.bits_per_sample = 0
        self.thread_id = 0
        self.station_id = 0

        # words 4-7
        self.eud_vers = 0
        self.eud = [0, 0, 0, 0]
        self.psn = 0
        self.offset_samp = 0;

    @classmethod
    def from_bin(cls, bin_hdr):

        # create our instance
        inst = cls()

        # parse bin data
        words = list(unpack('<4I', bin_hdr[0:16]))

        # word 0
        inst.invalid_data = bool((words[0] >> 31) & 0x1)
        inst.legacy_mode = bool((words[0] >> 30) & 0x1)
        inst.secs_since_epoch = words[0] & 0x3fffffff

        # word 1
        inst.ref_epoch = (words[1] >> 24) & 0x3f
        inst.data_frame = words[1] & 0xffffff

        # word 2
        inst.vdif_vers = (words[2] >> 29) & 0x7
        inst.log2_chans = (words[2] >> 24) & 0x1f
        inst.frame_length = words[2] & 0xffffff

        # word 3
        inst.complex = bool((words[3] >> 31) & 0x1)
        inst.bits_per_sample = 1 + ((words[3] >> 26) & 0x1f)
        inst.thread_id = (words[3] >> 16) & 0x3ff
        inst.station_id = words[3] & 0xffff

        if not inst.legacy_mode:

            # parse extended user data
            words.extend(unpack('<I', bin_hdr[16:20]))
            words.extend(unpack('<i', bin_hdr[20:24]))
            words.extend(unpack('<2I', bin_hdr[24:32]))

            # words 4-7
            inst.eud_vers = (words[4] >> 24) & 0xff
            inst.eud[0] = words[4] & 0xffffff
            inst.eud[1:4] = words[5:8]
            inst.psn = words[6]+2**32*words[7]
            inst.offset_samp = words[5];


        return inst

    def to_bin(self):

        words = []

        # word 0
        words.append(
            ((self.invalid_data & 0x1) << 31) + 
            ((self.legacy_mode & 0x1) << 30) +
            (self.secs_since_epoch & 0x3fffffff)
            )

        # word 1
        words.append(
            ((self.ref_epoch & 0x3f) << 24) + 
            (self.data_frame & 0xffffff)
            )

        # word 2
        words.append(
            ((self.vdif_vers & 0x7) << 29) + 
            ((self.log2_chans & 0x1f) << 24) + 
            (self.frame_length & 0xffffff)
            )

        # word 3
        words.append(
            ((self.complex & 0x1) << 31) + 
            (((self.bits_per_sample-1) & 0x1f) << 26) + 
            ((self.thread_id & 0x3ff) << 16) + 
            (self.station_id & 0xffff)
            )

        if not self.legacy_mode:

            # words 4-7
            words.append(
                ((self.eud_vers & 0xff) << 24) + 
                (self.eud[0] & 0xffffff)
                )
            words.append(self.eud[1] & 0xffffffff)
            words.append(self.eud[2] & 0xffffffff)
            words.append(self.eud[3] & 0xffffffff)

        return pack('<{0}I'.format(len(words)), *words)

    def __str__(self):
        return self.to_bin()

    def datetime(self, end=False):

        # find out how many words per frame
        header_size = 2 if self.legacy_mode else 4
        data_words = 2 * (self.frame_length - header_size)

        # now how many time samples per frame
        samp_per_word = 32 / self.bits_per_sample
        tsamp_per_word = samp_per_word / (int(self.complex) + 1)
        tsamp_per_frame = tsamp_per_word * data_words

        # now how many usecs per frame
        usecs_per_frame = 1e6 * (tsamp_per_frame / self.sample_rate)

        # get the date
        date = datetime(year = 2000 + self.ref_epoch/2,
                        month = 1 + (self.ref_epoch & 1) * 6,
                        day = 1, tzinfo=UTC())

        # get the seconds from the start of the day
        secs = timedelta(seconds = self.secs_since_epoch)

        # get the microseconds from the second
        off = usecs_per_frame if end else 0.0
        usecs = timedelta(microseconds = usecs_per_frame * self.data_frame + off)

        return date + secs + usecs


class VDIFFrame(VDIFFrameHeader):

    def __init__(self):
        super(VDIFFrame, self).__init__()
        self.data = array([], int32)

    @classmethod
    def from_bin(cls, bin_frame):

        # create our instance
        inst = super(VDIFFrame, cls).from_bin(bin_frame)

        # find where the data starts and ends in binary frame
        data_start = 16 if inst.legacy_mode else 32
        data_stop = inst.frame_length * 8
        data_size = data_stop - data_start
        data_words = data_size / 4

        # create empty data buffer
        samp_per_word = 32 / inst.bits_per_sample
        inst.data = zeros(samp_per_word * data_words, int32)

        # unpack data into array
        words = array(unpack('<{0}I'.format(data_words), bin_frame[data_start:data_stop]), uint32)

        # interpret the data given our bits-per-sample
        samp_max = 2**inst.bits_per_sample - 1
        for samp_n in range(samp_per_word):

            # get sample data from words
            shift_by = inst.bits_per_sample * samp_n
            inst.data[samp_n::samp_per_word] = (words >> shift_by) & samp_max

        # we need to reinterpret as offset binary
        inst.data = inst.data - 2**(inst.bits_per_sample-1)

        return inst

    def to_bin(self):

        # get the header string first
        out_str = VDIFFrameHeader.to_bin(self)

        # find where the data starts and ends in binary frame
        data_start = 16 if self.legacy_mode else 32
        data_stop = self.frame_length * 8
        data_size = data_stop - data_start
        data_words = data_size / 4

        # reinterpet data given our bits-per-sample
        samp_max = 2**self.bits_per_sample - 1
        samp_per_word = 32 / self.bits_per_sample
        for word_n in range(data_words):
            word = 0

            for samp_n in range(samp_per_word):
                samp = int(self.data[word_n * samp_per_word + samp_n])

                # reinterpret sample as offset-binary
                samp = (samp + 2**(self.bits_per_sample-1)) & samp_max

                # add the sample data to the word
                shift_by = self.bits_per_sample * samp_n
                word = word + (samp << shift_by)

            out_str += pack('<I', word)

        return out_str

    def __str__(self):
        return self.to_bin()
