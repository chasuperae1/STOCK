import pandas as pd
import numpy as np
from typing import Dict, List, Any
from .strategy import Signal


class Position:
    def __init__(self, symbol: str, quantity: float = 0.0, avg_cost: float = 0.0):
        self.symbol = symbol
        self.quantity = quantity
        self.avg_cost = avg_cost

    @property
    def market_value(self) -> float:
        return self.quantity * self.avg_cost

    def update(self, quantity: float, price: float):
        total_cost = self.quantity * self.avg_cost + quantity * price
        self.quantity += quantity
        if self.quantity != 0:
            self.avg_cost = total_cost / self.quantity
        else:
            self.avg_cost = 0.0


class Portfolio:
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.transaction_cost = 0.001

    @property
    def total_equity(self) -> float:
        return self.cash + self.total_position_value

    @property
    def total_position_value(self) -> float:
        return sum(pos.market_value for pos in self.positions.values())

    def get_position(self, symbol: str) -> Position:
        return self.positions.get(symbol, Position(symbol))

    def execute_order(self, symbol: str, signal: Signal, price: float):
        if signal.signal_type == Signal.HOLD:
            return

        position = self.positions.get(symbol, Position(symbol))
        
        if signal.signal_type == Signal.LONG:
            if position.quantity < 0:
                self.cash += position.quantity * price * (1 - self.transaction_cost)
                position.quantity = 0
                position.avg_cost = 0.0
            
            max_quantity = self.cash / price * (1 - self.transaction_cost)
            position.update(max_quantity, price)
            self.cash -= max_quantity * price
        
        elif signal.signal_type == Signal.SHORT:
            if position.quantity > 0:
                self.cash += position.quantity * price * (1 - self.transaction_cost)
                position.quantity = 0
                position.avg_cost = 0.0
            
            max_quantity = self.cash / price * (1 - self.transaction_cost)
            position.update(-max_quantity, price)
            self.cash += max_quantity * price * (1 - self.transaction_cost)
        
        self.positions[symbol] = position

    def update_market_values(self, prices: Dict[str, float]):
        for symbol, position in self.positions.items():
            if symbol in prices:
                pass

    def get_summary(self) -> Dict[str, Any]:
        positions_info = {}
        for symbol, pos in self.positions.items():
            positions_info[symbol] = {
                'quantity': pos.quantity,
                'avg_cost': pos.avg_cost,
                'market_value': pos.market_value
            }
        
        return {
            'cash': self.cash,
            'total_equity': self.total_equity,
            'total_position_value': self.total_position_value,
            'positions': positions_info
        }


class RiskManager:
    def __init__(self, max_position_size: float = 0.1, max_drawdown: float = 0.2):
        self.max_position_size = max_position_size
        self.max_drawdown = max_drawdown
        self.initial_equity = 0.0
        self.highest_equity = 0.0

    def setup(self, initial_equity: float):
        self.initial_equity = initial_equity
        self.highest_equity = initial_equity

    def check_risk(self, portfolio: Portfolio, signal: Signal) -> bool:
        current_equity = portfolio.total_equity
        self.highest_equity = max(self.highest_equity, current_equity)
        
        drawdown = (self.highest_equity - current_equity) / self.highest_equity
        
        if drawdown > self.max_drawdown:
            return False
        
        return True

    def get_position_size(self, portfolio: Portfolio, price: float) -> float:
        max_value = portfolio.total_equity * self.max_position_size
        return max_value / price