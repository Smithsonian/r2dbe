import logging

# generic class for checks
class Check(object):

    def __init__(self, desc, attr):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.results = None
        self.desc = desc
        self.attr = attr

    def __str__(self):
        return "{0:<40s}: {1}".format(self.desc, self.results)

    def __call__(self, frame):
        pass

# generic class for counting checks
class CountingCheck(Check):

    def __init__(self, desc, attr):
        super(CountingCheck, self).__init__(desc, attr)
        self.cond_met_log_fmt = "condition met"
        self.results = 0

    def _condition(self, frame):
        return True

    def __call__(self, frame):
        if self._condition(frame):
            if self.cond_met_log_fmt:
                log_msg = self.cond_met_log_fmt.format(self)
                self.logger.debug(log_msg)
            self.results += 1

# Check to count when a frame val equals m
class CountEqualTo(CountingCheck):

    def __init__(self, desc, attr, m):
        super(CountEqualTo, self).__init__(desc, attr)
        self.cond_met_log_fmt = None
        self.m = m

    def _condition(self, frame):
        val = getattr(frame, self.attr)
        return val == self.m

# Check to count when a frame val is NOT equal to m
class CountNotEqualTo(CountingCheck):

    def __init__(self, desc, attr, m):
        super(CountNotEqualTo, self).__init__(desc, attr)
        self.cond_met_log_fmt = "{0.attr}={0.val} is NOT equal to {0.m}"
        self.m = m

    def _condition(self, frame):
        self.val = getattr(frame, self.attr)
        return not self.val == self.m

# Check to count when a frame val is out of range
class CountOutOfRange(CountingCheck):

    def __init__(self, desc, attr, start, stop):
        super(CountOutOfRange, self).__init__(desc, attr)
        self.cond_met_log_fmt = "{0.attr}={0.val} out-of-range [{0.start}: {0.stop}]"
        self.start = start
        self.stop = stop

    def _condition(self, frame):
        self.val = getattr(frame, self.attr)
        return not self.start <= self.val <= self.stop

# Check to count number of times frames are out of order
class CountNotIncrementingBy(CountingCheck):

    def __init__(self, desc, attr, m):
        super(CountNotIncrementingBy, self).__init__(desc, attr)
        self.cond_met_log_fmt = "{0.attr} incremented from {0.last_val} to {0.val} (diff. of {0.diff} not {0.m})"
        self.last_val = None
        self.diff = None
        self.m = m

    def _condition(self, frame):
        self.val = getattr(frame, self.attr)
        if self.last_val is None:
            self.last_val = self.val
            self.diff = 0
            return False
        else:
            self.diff = self.val - self.last_val
            return not self.diff == self.m

    def __call__(self, frame):
        super(CountNotIncrementingBy, self).__call__(frame)
        self.last_val = self.val

# generic class for listing checks
class ListingCheck(Check):

    def __init__(self, desc, attr):
        super(ListingCheck, self).__init__(desc, attr)
        self.new_val_log_fmt = "new {0.attr} found: {0.val}"
        self.results = []

    def __str__(self):
        results = ', '.join(repr(r) for r in self.results)
        return "{0:<40s}: {1}".format(self.desc, results)

    def __call__(self, frame):
        self.val = getattr(frame, self.attr)
        if self.val not in self.results:
            log_msg = self.new_val_log_fmt.format(self)
            self.logger.debug(log_msg)
            self.results.append(self.val)
