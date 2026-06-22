from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd
from .event import Event, EVENT_STRATEGY_SIGNAL
from .data import GoldData


class Signal:
    LONG = 1
    SHORT = -1
    HOLD = 0

    def __init__(self, signal_type: int, price: float = 0.0, confidence: float = 0.0):
        self.signal_type = signal_type
        self.price = price
        self.confidence = confidence
        self.timestamp = pd.Timestamp.now()

    def __repr__(self):
        types = {self.LONG: "LONG", self.SHORT: "SHORT", self.HOLD: "HOLD"}
        return f"Signal({types[self.signal_type]}, price={self.price:.2f}, confidence={self.confidence:.2f})"


class BaseStrategy(ABC):
    def __init__(self, event_engine):
        self.event_engine = event_engine
        self.data_provider = GoldData()
        self.name = self.__class__.__name__
        self._params: Dict[str, Any] = {}

    @abstractmethod
    def calculate_signal(self, data: pd.DataFrame) -> Signal:
        pass

    def set_params(self, **kwargs):
        self._params.update(kwargs)

    def get_param(self, key: str, default: Any = None) -> Any:
        return self._params.get(key, default)

    def emit_signal(self, signal: Signal):
        event = Event(EVENT_STRATEGY_SIGNAL, {
            "strategy": self.name,
            "signal": signal
        })
        self.event_engine.put(event)

    def on_tick(self, event: Event):
        data = event.data
        signal = self.calculate_signal(data)
        self.emit_signal(signal)


class TrendFollowingStrategy(BaseStrategy):
    def __init__(self, event_engine):
        super().__init__(event_engine)
        self.set_params(
            short_window=20,
            long_window=60,
            confirmation_threshold=0.01
        )

    def calculate_signal(self, data: pd.DataFrame) -> Signal:
        short_window = self.get_param("short_window")
        long_window = self.get_param("long_window")
        threshold = self.get_param("confirmation_threshold")

        if len(data) < long_window:
            return Signal(Signal.HOLD)

        data = data.copy()
        data['ma_short'] = data['close'].rolling(short_window).mean()
        data['ma_long'] = data['close'].rolling(long_window).mean()
        
        latest = data.iloc[-1]
        prev = data.iloc[-2]

        if prev['ma_short'] <= prev['ma_long'] and latest['ma_short'] > latest['ma_long']:
            diff = (latest['ma_short'] - latest['ma_long']) / latest['ma_long']
            if diff >= threshold:
                return Signal(Signal.LONG, price=latest['close'], confidence=min(diff * 10, 1.0))
        
        elif prev['ma_short'] >= prev['ma_long'] and latest['ma_short'] < latest['ma_long']:
            diff = (latest['ma_long'] - latest['ma_short']) / latest['ma_long']
            if diff >= threshold:
                return Signal(Signal.SHORT, price=latest['close'], confidence=min(diff * 10, 1.0))

        return Signal(Signal.HOLD)


class MeanReversionStrategy(BaseStrategy):
    def __init__(self, event_engine):
        super().__init__(event_engine)
        self.set_params(
            window=20,
            std_dev=2.0,
            revert_threshold=0.5
        )

    def calculate_signal(self, data: pd.DataFrame) -> Signal:
        window = self.get_param("window")
        std_dev = self.get_param("std_dev")
        revert_threshold = self.get_param("revert_threshold")

        if len(data) < window:
            return Signal(Signal.HOLD)

        data = data.copy()
        data['mean'] = data['close'].rolling(window).mean()
        data['std'] = data['close'].rolling(window).std()
        data['z_score'] = (data['close'] - data['mean']) / data['std']

        latest = data.iloc[-1]
        z_score = latest['z_score']

        if z_score > std_dev:
            confidence = min((z_score - std_dev) / 2, 1.0)
            return Signal(Signal.SHORT, price=latest['close'], confidence=confidence)
        elif z_score < -std_dev:
            confidence = min((-z_score - std_dev) / 2, 1.0)
            return Signal(Signal.LONG, price=latest['close'], confidence=confidence)

        return Signal(Signal.HOLD)


class GridTradingStrategy(BaseStrategy):
    def __init__(self, event_engine):
        super().__init__(event_engine)
        self.set_params(
            grid_count=10,
            grid_range=0.10,
            position_limit=10
        )
        self.current_position = 0
        self.grid_levels = []

    def calculate_signal(self, data: pd.DataFrame) -> Signal:
        if len(data) < 2:
            return Signal(Signal.HOLD)

        price = data['close'].iloc[-1]
        grid_count = self.get_param("grid_count")
        grid_range = self.get_param("grid_range")
        position_limit = self.get_param("position_limit")

        if not self.grid_levels:
            recent_high = data['high'].max()
            recent_low = data['low'].min()
            price_range = recent_high - recent_low
            grid_size = price_range * grid_range / grid_count
            
            self.grid_levels = [
                recent_low + i * grid_size
                for i in range(grid_count + 1)
            ]

        grid_index = None
        for i in range(len(self.grid_levels) - 1):
            if self.grid_levels[i] <= price < self.grid_levels[i + 1]:
                grid_index = i
                break

        if grid_index is None:
            return Signal(Signal.HOLD)

        target_position = grid_index - grid_count // 2

        if target_position > self.current_position and self.current_position < position_limit:
            self.current_position += 1
            return Signal(Signal.LONG, price=price, confidence=0.8)
        elif target_position < self.current_position and self.current_position > -position_limit:
            self.current_position -= 1
            return Signal(Signal.SHORT, price=price, confidence=0.8)

        return Signal(Signal.HOLD)


class MultiFactorStrategy(BaseStrategy):
    def __init__(self, event_engine):
        super().__init__(event_engine)
        self.set_params(
            rsi_overbought=70,
            rsi_oversold=30,
            macd_signal_threshold=0,
            ma_trend_weight=0.3,
            rsi_weight=0.3,
            macd_weight=0.4
        )

    def calculate_signal(self, data: pd.DataFrame) -> Signal:
        if len(data) < 60:
            return Signal(Signal.HOLD)

        data = self.data_provider.calculate_indicators(data)
        latest = data.iloc[-1]

        ma_trend = 0
        if latest['ma20'] > latest['ma60']:
            ma_trend = 1
        elif latest['ma20'] < latest['ma60']:
            ma_trend = -1

        rsi_signal = 0
        if latest['rsi'] > self.get_param("rsi_overbought"):
            rsi_signal = -1
        elif latest['rsi'] < self.get_param("rsi_oversold"):
            rsi_signal = 1

        macd_signal = 0
        if latest['macd'] > latest['signal'] + self.get_param("macd_signal_threshold"):
            macd_signal = 1
        elif latest['macd'] < latest['signal'] - self.get_param("macd_signal_threshold"):
            macd_signal = -1

        combined_score = (
            ma_trend * self.get_param("ma_trend_weight") +
            rsi_signal * self.get_param("rsi_weight") +
            macd_signal * self.get_param("macd_weight")
        )

        if combined_score > 0.3:
            return Signal(Signal.LONG, price=latest['close'], confidence=min(combined_score, 1.0))
        elif combined_score < -0.3:
            return Signal(Signal.SHORT, price=latest['close'], confidence=min(-combined_score, 1.0))

        return Signal(Signal.HOLD)