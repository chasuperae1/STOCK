from queue import Queue
from threading import Thread
from typing import Callable, Dict, List, Any


class Event:
    def __init__(self, event_type: str, data: Any = None):
        self.event_type = event_type
        self.data = data


class EventEngine:
    def __init__(self):
        self._queue = Queue()
        self._handlers: Dict[str, List[Callable]] = {}
        self._active = False
        self._thread = Thread(target=self._run)

    def _run(self):
        while self._active:
            try:
                event = self._queue.get(block=True, timeout=1)
                self._process(event)
            except:
                pass

    def _process(self, event: Event):
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"Error processing event {event.event_type}: {e}")

    def start(self):
        self._active = True
        self._thread.start()

    def stop(self):
        self._active = False
        if self._thread.is_alive():
            self._thread.join()

    def put(self, event: Event):
        self._queue.put(event)

    def register(self, event_type: str, handler: Callable):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    def unregister(self, event_type: str, handler: Callable):
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)


EVENT_TICK = "tick"
EVENT_ORDER = "order"
EVENT_TRADE = "trade"
EVENT_POSITION = "position"
EVENT_ACCOUNT = "account"
EVENT_LOG = "log"
EVENT_STRATEGY_SIGNAL = "strategy_signal"