import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from .strategy import Signal
from .data import GoldData


class BackTestResult:
    def __init__(self):
        self.equity_curve = pd.DataFrame(columns=['datetime', 'equity', 'cash', 'position', 'pnl'])
        self.trades = []
        self.stats = {}

    def add_trade(self, entry_date, entry_price, exit_date, exit_price, position, pnl):
        self.trades.append({
            'entry_date': entry_date,
            'entry_price': entry_price,
            'exit_date': exit_date,
            'exit_price': exit_price,
            'position': position,
            'pnl': pnl
        })

    def calculate_stats(self):
        if len(self.trades) == 0:
            return {}

        trades_df = pd.DataFrame(self.trades)
        
        winning_trades = trades_df[trades_df['pnl'] > 0]
        losing_trades = trades_df[trades_df['pnl'] <= 0]
        
        total_return = self.equity_curve['equity'].iloc[-1] / self.equity_curve['equity'].iloc[0] - 1
        max_drawdown = self._calculate_max_drawdown(self.equity_curve['equity'])
        
        self.stats = {
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(self.trades),
            'total_pnl': trades_df['pnl'].sum(),
            'avg_win': winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0,
            'avg_loss': losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0,
            'profit_factor': abs(winning_trades['pnl'].sum() / losing_trades['pnl'].sum()) if len(losing_trades) > 0 else np.inf,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': self._calculate_sharpe_ratio(self.equity_curve['equity'])
        }
        return self.stats

    def _calculate_max_drawdown(self, equity: pd.Series) -> float:
        rolling_max = equity.cummax()
        drawdown = (equity - rolling_max) / rolling_max
        return abs(drawdown.min())

    def _calculate_sharpe_ratio(self, equity: pd.Series, risk_free_rate: float = 0.02) -> float:
        returns = equity.pct_change().dropna()
        if len(returns) == 0:
            return 0.0
        
        excess_returns = returns - risk_free_rate / 252
        return np.sqrt(252) * excess_returns.mean() / excess_returns.std()


class BackTester:
    def __init__(self, initial_capital: float = 100000.0, transaction_cost: float = 0.001):
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.data_provider = GoldData()
        self.result = None

    def run_backtest(self, strategy, data: pd.DataFrame) -> BackTestResult:
        self.result = BackTestResult()
        
        cash = self.initial_capital
        position = 0
        entry_price = 0.0
        equity = self.initial_capital
        
        self.result.equity_curve.loc[0] = [data.index[0], equity, cash, position, 0]
        
        for i in range(1, len(data)):
            current_data = data.iloc[:i+1]
            signal = strategy.calculate_signal(current_data)
            price = data['close'].iloc[i]
            
            if signal.signal_type == Signal.LONG and position <= 0:
                if position < 0:
                    cash += position * entry_price * (1 - self.transaction_cost)
                    position = 0
                
                position = cash / price * (1 - self.transaction_cost)
                entry_price = price
                cash = 0
            
            elif signal.signal_type == Signal.SHORT and position >= 0:
                if position > 0:
                    cash += position * entry_price * (1 - self.transaction_cost)
                    position = 0
                
                position = -cash / price * (1 - self.transaction_cost)
                entry_price = price
                cash = 0
            
            equity = cash + position * price
            pnl = equity - self.initial_capital
            
            self.result.equity_curve.loc[i] = [data.index[i], equity, cash, position, pnl]
            
            if position != 0 and signal.signal_type != Signal.HOLD and signal.signal_type != (1 if position > 0 else -1):
                exit_price = price
                trade_pnl = position * (exit_price - entry_price) * (1 - self.transaction_cost)
                self.result.add_trade(
                    entry_date=data.index[i-1],
                    entry_price=entry_price,
                    exit_date=data.index[i],
                    exit_price=exit_price,
                    position=position,
                    pnl=trade_pnl
                )
        
        self.result.equity_curve.set_index('datetime', inplace=True)
        self.result.calculate_stats()
        
        return self.result

    def optimize_parameters(self, strategy_class, data: pd.DataFrame, param_grid: Dict[str, List]) -> Dict:
        best_params = None
        best_result = None
        best_sharpe = -np.inf
        
        param_combinations = self._generate_param_combinations(param_grid)
        
        for params in param_combinations:
            strategy = strategy_class(None)
            strategy.set_params(**params)
            
            result = self.run_backtest(strategy, data)
            
            if result.stats['sharpe_ratio'] > best_sharpe:
                best_sharpe = result.stats['sharpe_ratio']
                best_params = params
                best_result = result
        
        return {
            'best_params': best_params,
            'best_result': best_result,
            'best_sharpe': best_sharpe
        }

    def _generate_param_combinations(self, param_grid: Dict[str, List]) -> List[Dict]:
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combinations = []
        
        from itertools import product
        for combo in product(*values):
            combinations.append(dict(zip(keys, combo)))
        
        return combinations