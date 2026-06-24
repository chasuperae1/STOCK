#!/usr/bin/env python3
"""
真实数据回测引擎
===============

**核心原则**：必须使用真实历史数据，严禁模拟数据

回测策略：
    1. 均线交叉策略（MA Crossover）
    2. RSI超买超卖策略
    3. MACD金叉死叉策略
    4. 布林带策略
    5. 金叉死叉策略

回测指标：
    - 总收益率
    - 年化收益率
    - 胜率
    - 盈亏比
    - 最大回撤
    - 夏普比率
    - 交易次数
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class BacktestResult:
    """回测结果数据类"""
    strategy_name: str
    total_return: float = 0.0
    annual_return: float = 0.0
    win_rate: float = 0.0
    profit_loss_ratio: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    final_value: float = 0.0
    is_real_data: bool = False
    data_source: str = ""
    data_start: str = ""
    data_end: str = ""
    trades: List[Dict] = field(default_factory=list)


class BacktestEngine:
    """
    回测引擎 - 基于真实历史数据
    
    严禁使用模拟数据！
    """
    
    def __init__(self, initial_capital: float = 100000.0):
        """
        初始化回测引擎
        
        参数:
            initial_capital: 初始资金
        """
        self.initial_capital = initial_capital
        self.is_real_data = False
        self.data_source = ""
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标
        
        参数:
            df: 包含 OHLCV 的数据框
            
        返回:
            添加了指标的数据框
        """
        df = df.copy()
        
        # 均线
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        df['rsi'] = df['rsi'].fillna(50)
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 布林带
        df['bb_mid'] = df['close'].rolling(20).mean()
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
        
        return df
    
    def _run_strategy(
        self,
        df: pd.DataFrame,
        signals: pd.Series
    ) -> BacktestResult:
        """
        运行策略回测
        
        参数:
            df: 价格数据
            signals: 买卖信号序列 (1=买入, -1=卖出, 0=持有)
            
        返回:
            BacktestResult
        """
        capital = self.initial_capital
        position = 0  # 持仓数量
        trades = []
        entry_price = 0
        entry_date = ""
        
        portfolio_values = []
        
        for i in range(len(df)):
            date = df['date'].iloc[i]
            close = df['close'].iloc[i]
            signal = signals.iloc[i]
            
            # 计算当前资产价值
            current_value = capital + position * close
            portfolio_values.append(current_value)
            
            # 执行交易
            if signal == 1 and position == 0:  # 买入
                shares = int(capital / close / 100) * 100  # 100股一手
                if shares > 0:
                    position = shares
                    capital -= shares * close
                    entry_price = close
                    entry_date = date
                    
            elif signal == -1 and position > 0:  # 卖出
                capital += position * close
                profit = (close - entry_price) * position
                profit_pct = (close - entry_price) / entry_price * 100
                
                trades.append({
                    'entry_date': entry_date,
                    'exit_date': date,
                    'entry_price': entry_price,
                    'exit_price': close,
                    'profit': profit,
                    'profit_pct': profit_pct,
                    'is_win': profit > 0
                })
                
                position = 0
                entry_price = 0
        
        # 最后清仓
        if position > 0:
            last_close = df['close'].iloc[-1]
            capital += position * close
            profit = (last_close - entry_price) * position
            profit_pct = (last_close - entry_price) / entry_price * 100
            
            trades.append({
                'entry_date': entry_date,
                'exit_date': df['date'].iloc[-1],
                'entry_price': entry_price,
                'exit_price': last_close,
                'profit': profit,
                'profit_pct': profit_pct,
                'is_win': profit > 0
            })
        
        final_value = capital
        total_return = (final_value / self.initial_capital - 1) * 100
        
        # 计算指标
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t['is_win'])
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # 盈亏比
        profits = [t['profit'] for t in trades if t['is_win']]
        losses = [-t['profit'] for t in trades if not t['is_win']]
        avg_profit = np.mean(profits) if profits else 0
        avg_loss = np.mean(losses) if losses else 1
        profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0
        
        # 最大回撤
        portfolio_array = np.array(portfolio_values)
        peak = np.maximum.accumulate(portfolio_array)
        drawdown = (peak - portfolio_array) / peak * 100
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
        
        # 年化收益率
        days = len(df)
        annual_return = ((1 + total_return / 100) ** (252 / days) - 1) * 100 if days > 0 else 0
        
        # 夏普比率 (简化版，无风险利率=2%)
        daily_returns = pd.Series(portfolio_values).pct_change().dropna()
        if len(daily_returns) > 1 and daily_returns.std() > 0:
            sharpe = (daily_returns.mean() * 252 - 0.02) / (daily_returns.std() * np.sqrt(252))
        else:
            sharpe = 0
        
        return BacktestResult(
            strategy_name="",
            total_return=total_return,
            annual_return=annual_return,
            win_rate=win_rate,
            profit_loss_ratio=profit_loss_ratio,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            final_value=final_value,
            is_real_data=self.is_real_data,
            data_source=self.data_source,
            trades=trades
        )
    
    def ma_crossover(self, df: pd.DataFrame, short: int = 5, long: int = 20) -> BacktestResult:
        """
        均线交叉策略
        
        规则：
            - 短期均线上穿长期均线 → 买入
            - 短期均线下穿长期均线 → 卖出
        """
        df = self._calculate_indicators(df)
        
        signals = pd.Series(0, index=df.index)
        
        short_ma = f'ma{short}'
        long_ma = f'ma{long}'
        
        for i in range(1, len(df)):
            # 金叉：上穿
            if df[short_ma].iloc[i] > df[long_ma].iloc[i] and \
               df[short_ma].iloc[i-1] <= df[long_ma].iloc[i-1]:
                signals.iloc[i] = 1
            # 死叉：下穿
            elif df[short_ma].iloc[i] < df[long_ma].iloc[i] and \
                 df[short_ma].iloc[i-1] >= df[long_ma].iloc[i-1]:
                signals.iloc[i] = -1
        
        result = self._run_strategy(df, signals)
        result.strategy_name = f"均线交叉({short}/{long})"
        return result
    
    def rsi_strategy(self, df: pd.DataFrame, oversold: int = 30, overbought: int = 70) -> BacktestResult:
        """
        RSI超买超卖策略
        
        规则：
            - RSI < 30 → 买入（超卖）
            - RSI > 70 → 卖出（超买）
        """
        df = self._calculate_indicators(df)
        
        signals = pd.Series(0, index=df.index)
        
        for i in range(1, len(df)):
            rsi = df['rsi'].iloc[i]
            
            if rsi < oversold:
                signals.iloc[i] = 1
            elif rsi > overbought:
                signals.iloc[i] = -1
        
        result = self._run_strategy(df, signals)
        result.strategy_name = f"RSI({oversold}/{overbought})"
        return result
    
    def macd_strategy(self, df: pd.DataFrame) -> BacktestResult:
        """
        MACD金叉死叉策略
        
        规则：
            - MACD上穿信号线 → 买入（金叉）
            - MACD下穿信号线 → 卖出（死叉）
        """
        df = self._calculate_indicators(df)
        
        signals = pd.Series(0, index=df.index)
        
        for i in range(1, len(df)):
            # 金叉
            if df['macd'].iloc[i] > df['macd_signal'].iloc[i] and \
               df['macd'].iloc[i-1] <= df['macd_signal'].iloc[i-1]:
                signals.iloc[i] = 1
            # 死叉
            elif df['macd'].iloc[i] < df['macd_signal'].iloc[i] and \
                 df['macd'].iloc[i-1] >= df['macd_signal'].iloc[i-1]:
                signals.iloc[i] = -1
        
        result = self._run_strategy(df, signals)
        result.strategy_name = "MACD金叉死叉"
        return result
    
    def bollinger_strategy(self, df: pd.DataFrame) -> BacktestResult:
        """
        布林带策略
        
        规则：
            - 价格跌破下轨 → 买入（超卖）
            - 价格突破上轨 → 卖出（超买）
        """
        df = self._calculate_indicators(df)
        
        signals = pd.Series(0, index=df.index)
        
        for i in range(1, len(df)):
            close = df['close'].iloc[i]
            upper = df['bb_upper'].iloc[i]
            lower = df['bb_lower'].iloc[i]
            
            if close < lower:
                signals.iloc[i] = 1
            elif close > upper:
                signals.iloc[i] = -1
        
        result = self._run_strategy(df, signals)
        result.strategy_name = "布林带策略"
        return result
    
    def golden_cross_strategy(self, df: pd.DataFrame) -> BacktestResult:
        """
        金叉死叉策略（MA5/MA20）
        
        规则：
            - MA5上穿MA20 → 买入（金叉）
            - MA5下穿MA20 → 卖出（死叉）
        """
        result = self.ma_crossover(df, short=5, long=20)
        result.strategy_name = "金叉死叉(5/20)"
        return result
    
    def run_all_strategies(self, df: pd.DataFrame) -> List[BacktestResult]:
        """
        运行所有策略并返回结果列表
        
        参数:
            df: 真实历史数据
            
        返回:
            策略结果列表
        """
        results = []
        
        strategies = [
            ('均线交叉(5/20)', lambda: self.ma_crossover(df, 5, 20)),
            ('均线交叉(10/20)', lambda: self.ma_crossover(df, 10, 20)),
            ('RSI(30/70)', lambda: self.rsi_strategy(df, 30, 70)),
            ('MACD金叉死叉', lambda: self.macd_strategy(df)),
            ('布林带策略', lambda: self.bollinger_strategy(df)),
            ('金叉死叉(5/20)', lambda: self.golden_cross_strategy(df)),
        ]
        
        for name, strategy_func in strategies:
            print(f"  运行策略: {name}...", end=" ")
            try:
                result = strategy_func()
                result.data_start = df['date'].iloc[0]
                result.data_end = df['date'].iloc[-1]
                results.append(result)
                print(f"✅ 收益{result.total_return:+.2f}%")
            except Exception as e:
                print(f"❌ 失败: {e}")
        
        return results
    
    def print_results(self, results: List[BacktestResult]):
        """
        打印回测结果
        """
        if not results:
            print("❌ 无回测结果")
            return
        
        print("\n" + "=" * 100)
        print(f"📊 回测结果汇总")
        print("=" * 100)
        
        if results[0].is_real_data:
            print(f"✅ 数据源: {results[0].data_source}（真实数据）")
        else:
            print(f"❌ 数据源: 模拟数据（禁止用于决策）")
        
        print(f"📅 数据区间: {results[0].data_start} ~ {results[0].data_end}")
        print(f"💰 初始资金: ¥{self.initial_capital:,.2f}")
        print()
        
        # 表头
        header = f"{'策略名称':<18} {'总收益':>8} {'年化收益':>8} {'胜率':>8} {'盈亏比':>8} {'最大回撤':>8} {'夏普比率':>8} {'交易次数':>8}"
        print(header)
        print("-" * 100)
        
        for r in results:
            line = f"{r.strategy_name:<18} {r.total_return:>+7.2f}% {r.annual_return:>+7.2f}% {r.win_rate:>7.2f}% {r.profit_loss_ratio:>8.2f} {r.max_drawdown:>7.2f}% {r.sharpe_ratio:>8.2f} {r.total_trades:>8d}"
            print(line)
        
        # 最佳策略
        best = max(results, key=lambda x: x.total_return)
        print(f"\n🏆 收益最高策略: {best.strategy_name} ({best.total_return:+.2f}%)")
        
        best_sharpe = max(results, key=lambda x: x.sharpe_ratio)
        print(f"📈 夏普比率最高: {best_sharpe.strategy_name} ({best_sharpe.sharpe_ratio:.2f})")
        
        print("=" * 100)


# =============================================================================
# 快速测试
# =============================================================================

if __name__ == "__main__":
    from core.real_data import RealGoldETFData
    from datetime import datetime
    
    print("=" * 100)
    print("📊 真实数据回测系统测试")
    print("=" * 100)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 获取真实数据
    data = RealGoldETFData('518880', 'sh')
    df = data.fetch_history(days=120)
    
    if df is None:
        print("\n❌ 无法获取真实数据，回测终止")
        exit(1)
    
    print(f"\n✅ 数据获取成功")
    print(f"数据源: {data.data_source}")
    print(f"数据条数: {len(df)} 条")
    print()
    
    # 运行回测
    print("开始回测...")
    engine = BacktestEngine(initial_capital=100000)
    engine.is_real_data = data.is_real_data
    engine.data_source = data.data_source
    
    results = engine.run_all_strategies(df)
    
    # 打印结果
    engine.print_results(results)
    
    # 最佳策略详情
    best = max(results, key=lambda x: x.total_return)
    print(f"\n📋 最佳策略详情: {best.strategy_name}")
    print("-" * 50)
    print(f"交易明细（最近5笔）:")
    
    for i, trade in enumerate(best.trades[-5:], 1):
        status = "🟢" if trade['is_win'] else "🔴"
        print(f"{i}. {trade['entry_date']} → {trade['exit_date']}")
        print(f"   {trade['entry_price']:.3f} → {trade['exit_price']:.3f}")
        print(f"   盈亏: ¥{trade['profit']:,.2f} ({trade['profit_pct']:+.2f}%) {status}")
    
    print("\n" + "=" * 100)