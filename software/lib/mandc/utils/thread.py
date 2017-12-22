import logging
import sys

from functools import partial
from Queue import Empty, Queue
from threading import Lock, Thread, Timer
from time import sleep
from traceback import format_exception, format_exception_only

module_logger = logging.getLogger(__name__)

class Event(object):
	def __init__(self, func, *args, **kwargs):

		# Store function and arguments as partial
		self._partial = partial(func, *args, **kwargs)

	def do(self):
		return self._partial()

# Define a thread class that allows access to exceptions occuring within this thread to be accessible from within the calling
# thread
class ExceptingThread(Thread):
	def __init__(self, excq, parent_logger=module_logger, **kwargs):
		super(ExceptingThread, self).__init__(**kwargs)

		# Create queue to pass exceptions
		self._exception_queue = excq

		# Add a logger
		self.logger = logging.getLogger("{name}[{tid}]".format(name=".".join((parent_logger.name, self.__class__.__name__)),
		  tid=self.name))

	def run(self):

		try:
			# Just execute the parent class' run() method
			super(ExceptingThread, self).run()
		except:
			# Get last exception
			exc = sys.exc_info()

			# Log occurence
			exc_str = format_exception_only(*exc[:2])
			self.logger.error("Encountered an exception: {1}".format(self.name, exc_str))
			exc_lines = format_exception(*exc)
			self.logger.debug("Traceback follows:\n{1}".format(self.name, "".join(exc_lines)))

			# Add to queue
			self._exception_queue.put((self.name, exc))

# Define a thread class that can be stopped externally
class StoppableThread(Thread):
	def __init__(self, **kwargs):
		super(StoppableThread, self).__init__(**kwargs)

		# Set stop state and place under lock
		self._stopped = False
		self._stop_lock = Lock()

	def run(self):

		# Once-off tasks at thread start
		self.in_run_pre_loop()

		while True:

			# Tasks to do before each stop condition check, if return evaluates to True, exit loop
			if self.in_run_loop_pre_stop():
				break

			# Check if thread should terminate
			if self.stopped:
					break

			# Tasks to do after each stop condition check, if return evaluates to True, exit loop
			if self.in_run_loop_post_stop():
				break

		# Once-off tasks at thread stop
		self.in_run_post_loop()

	def in_run_pre_loop(self):
		# Override this method in decendent classes
		pass

	def in_run_loop_pre_stop(self):
		# Override this method in decendent classes. If the method return value evaluates to True, the thread loop will break
		pass

	def in_run_loop_post_stop(self):
		# Override this method in decendent classes. If the method return value evaluates to True, the thread loop will break
		pass

	def in_run_post_loop(self):
		# Override this method in decendent classes
		pass

	@property
	def stopped(self):
		with self._stop_lock:
			return self._stopped

	def stop(self):
		with self._stop_lock:
			self._stopped = True

# Define a thread class that allows access to exceptions occuring within this thread to be accessible from within the calling
# thread, but with external stop mechanism
class ExceptingStoppableThread(StoppableThread):
	def __init__(self, excq, parent_logger=module_logger, **kwargs):
		super(ExceptingStoppableThread, self).__init__(**kwargs)

		# Create queue to pass exceptions
		self._exception_queue = excq

		# Add a logger
		self.logger = logging.getLogger("{name}[{tid}]".format(name=".".join((parent_logger.name, self.__class__.__name__)),
		  tid=self.name))

	def run(self):

		try:
			# Just execute the parent class' run() method
			super(ExceptingStoppableThread, self).run()

		except:
			# Get last exception
			exc = sys.exc_info()

			# Log occurence
			exc_str = format_exception_only(*exc[:2])
			self.logger.error("Encountered an exception: {1}".format(self.name, exc_str))
			exc_lines = format_exception(*exc)
			self.logger.debug("Traceback follows:\n{1}".format(self.name, "".join(exc_lines)))

			# Add to queue
			self._exception_queue.put((self.name, exc))

			# Mark the thread as stopped
			self.stop()

class QueuedEventProcessor(ExceptingStoppableThread):
	def __init__(self, *args, **kwargs):
		super(QueuedEventProcessor, self).__init__(*args, **kwargs)

		# Create a queue
		self._event_queue = Queue()

	def enqueue(self, event):
		# If thread already stopped, do not accept any more events
		if self.stopped:
			raise RuntimeError("Cannot enqueue events after {cls} has been stopped.".format(cls=self.__class__.__name__))
		
		self._event_queue.put(event)

	def in_run_loop_pre_stop(self):

		try:
			# Process any waiting events
			event = self._event_queue.get_nowait()
			event.do()

		except Empty:
			# Nothing to do
			pass

	def in_run_loop_post_stop(self):

		# Wait a while
		sleep(0.001)

class EventScheduler(ExceptingStoppableThread):
	def __init__(self, event, processor, interval, num_repeat, *args, **kwargs):
		super(EventScheduler, self).__init__(*args, **kwargs)

		# This is the Event to schedule
		self._event = event

		# This is the QueuedEventProcessor
		self._processor = processor

		# Enqueue the Event every interval seconds
		self._interval = interval

		# Enqueue the Event in total num_repeat times, or indefinitely if < 0
		self._num_repeat = num_repeat

	def in_run_loop_pre_stop(self):
		# Sleep for the interval *before* checking stop condition (if sleeping after stop condition check, we allow ample
		# time for stop requests that can only be served after attempting to enqueue one more event)
		sleep(self._interval)

	def in_run_loop_post_stop(self):
		# If there are no repeats left, cause loop break; do this *after* checking stop condition
		if self._num_repeat == 0:
			return True

		# Enqueue event
		self._processor.enqueue(self._event)

		# Decrement repeats left if not indefinite
		if self._num_repeat > 0:
			self._num_repeat = self._num_repeat - 1
