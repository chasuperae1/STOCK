#!/usr/bin/env python3
"""
事件驱动交易策略回测
====================

基于历史事件回测发现的规律，构建事件驱动交易策略

核心发现（来自500天历史数据）：
1. 超跌反弹：5日跌5%+后5日平均涨2.14%，胜率82.4% ⭐⭐⭐
2. 超涨回调：10日涨8%+后10日平均跌2.74%，胜率29.2%
3. 创60日新高后继续涨：后20日平均涨4.01%，胜率73.6%
4. MA5/MA20金叉后：后5日平均涨0.83%，胜率73.3%
5. 单日大涨3%+后容易回调：后3日平均跌2.33%
6. 周内效应：周三最好，周四最差

策略思路：
- 主要信号：超跌反弹买入 + 趋势突破买入
- 辅助信号：均线金叉确认
- 出场信号：止盈3% / 止损2% / 信号消失
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import sys

sys.path.insert(0, '/workspace')
from core.backtest_engine import BacktestResult


@dataclass
class SignalResult:
    """单次信号结果"""
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    return_pct: float
    hold_days: int
    signal_type: str
    exit_reason: str  # 止盈/止损/到期/信号消失


class EventDrivenStrategy:
    """
    事件驱动交易策略
    
    基于历史事件规律构建的多因子策略
    """
    
    def __init__(
        self,
        df: pd.DataFrame,
        initial_cash: float = 100000,
    ):
        self.df = df.copy()
        self.df['date'] = pd.to_datetime(self.df['date'])
        self.df = self.df.sort_values('date').reset_index(drop=True)
        
        self.initial_cash = initial_cash
        
        # 计算指标
        self._calculate_indicators()
    
    def _calculate_indicators(self):
        """预计算所有需要的指标"""
        df = self.df
        
        # 日收益率
        df['return_1d'] = df['close'].pct_change() * 100
        
        # 过去N日收益
        for n in [3, 5, 10, 20]:
            df[f'past_return_{n}d'] = (df['close'] / df['close'].shift(n) - 1) * 100
        
        # 未来N日收益（用于回测）
        for n in [3, 5, 10, 20]:
            df[f'fwd_return_{n}d'] = (df['close'].shift(-n) / df['close'] - 1) * 100
        
        # 均线
        for n in [5, 10, 20, 60]:
            df[f'ma{n}'] = df['close'].rolling(n).mean()
        
        # 均线差
        df['ma5_ma20_diff'] = df['ma5'] - df['ma20']
        df['ma10_ma20_diff'] = df['ma10'] - df['ma20']
        
        # 金叉死叉
        df['golden_cross_5_20'] = (
            (df['ma5_ma20_diff'].shift(1) < 0) & 
            (df['ma5_ma20_diff'] > 0)
        ).astype(int)
        
        df['death_cross_5_20'] = (
            (df['ma5_ma20_diff'].shift(1) > 0) & 
            (df['ma5_ma20_diff'] < 0)
        ).astype(int)
        
        # 20日/60日最高最低
        df['high_20d'] = df['close'].rolling(20).max()
        df['low_20d'] = df['close'].rolling(20).min()
        df['high_60d'] = df['close'].rolling(60).max()
        df['low_60d'] = df['close'].rolling(60).min()
        
        # 创新高/新低
        df['new_high_20d'] = (df['close'] >= df['high_20d'].shift(1)).astype(int)
        df['new_low_20d'] = (df['close'] <= df['low_20d'].shift(1)).astype(int)
        df['new_high_60d'] = (df['close'] >= df['high_60d'].shift(1)).astype(int)
        df['new_low_60d'] = (df['close'] <= df['low_60d'].shift(1)).astype(int)
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 布林带
        df['bb_mid'] = df['ma20']
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
    
    def check_oversold_signal(self, i: int) -> Tuple[bool, float, str]:
        """
        超跌反弹信号
        
        规则：
        - 5日跌5%+ → 弱信号（权重0.3）
        - 10日跌8%+ → 中信号（权重0.5）
        - 20日跌10%+ → 强信号（权重0.8）
        - 同时RSI < 30 → 加强（+0.2）
        - 价格触及布林带下轨 → 加强（+0.1）
        """
        df = self.df
        score = 0.0
        reasons = []
        
        # 5日跌5%+
        if df['past_return_5d'].iloc[i] <= -5:
            score += 0.3
            reasons.append(f'5日跌{df["past_return_5d"].iloc[i]:.1f}%')
        
        # 10日跌8%+
        if df['past_return_10d'].iloc[i] <= -8:
            score += 0.5
            reasons.append(f'10日跌{df["past_return_10d"].iloc[i]:.1f}%')
        
        # 20日跌10%+
        if df['past_return_20d'].iloc[i] <= -10:
            score += 0.8
            reasons.append(f'20日跌{df["past_return_20d"].iloc[i]:.1f}%')
        
        # RSI超卖
        if df['rsi'].iloc[i] < 30:
            score += 0.2
            reasons.append(f'RSI={df["rsi"].iloc[i]:.1f}(超卖)')
        
        # 触及布林带下轨
        if df['close'].iloc[i] <= df['bb_lower'].iloc[i] * 1.01:
            score += 0.1
            reasons.append('触及布林带下轨')
        
        # 单日大跌3%+
        if df['return_1d'].iloc[i] <= -3:
            score += 0.2
            reasons.append(f'单日跌{df["return_1d"].iloc[i]:.1f}%')
        
        threshold = 0.5  # 触发阈值
        signal = score >= threshold
        
        return signal, score, ' + '.join(reasons)
    
    def check_breakout_signal(self, i: int) -> Tuple[bool, float, str]:
        """
        突破买入信号（趋势延续）
        
        规则：
        - 创60日新高 → 强信号（0.6）
        - 创20日新高 + 均线多头 → 中信号（0.4）
        - MA5/MA20金叉 → 辅助信号（0.3）
        """
        df = self.df
        score = 0.0
        reasons = []
        
        # 创60日新高
        if df['new_high_60d'].iloc[i]:
            score += 0.6
            reasons.append('创60日新高')
        
        # 创20日新高 + 均线多头
        if df['new_high_20d'].iloc[i] and df['ma5'].iloc[i] > df['ma20'].iloc[i]:
            score += 0.4
            reasons.append('创20日新高+均线多头')
        
        # MA5/MA20金叉
        if df['golden_cross_5_20'].iloc[i]:
            score += 0.3
            reasons.append('MA5/MA20金叉')
        
        threshold = 0.5
        signal = score >= threshold
        
        return signal, score, ' + '.join(reasons)
    
    def check_overbought_signal(self, i: int) -> Tuple[bool, float, str]:
        """
        超涨回调信号（卖出/做空）
        
        规则：
        - 10日涨8%+ → 强信号（0.6）
        - 20日涨10%+ → 中信号（0.5）
        - 单日大涨3%+ → 辅助（0.2）
        - RSI > 70 → 加强（0.2）
        - 触及布林带上轨 → 加强（0.1）
        """
        df = self.df
        score = 0.0
        reasons = []
        
        if df['past_return_10d'].iloc[i] >= 8:
            score += 0.6
            reasons.append(f'10日涨{df["past_return_10d"].iloc[i]:.1f}%')
        
        if df['past_return_20d'].iloc[i] >= 10:
            score += 0.5
            reasons.append(f'20日涨{df["past_return_20d"].iloc[i]:.1f}%')
        
        if df['return_1d'].iloc[i] >= 3:
            score += 0.2
            reasons.append(f'单日涨{df["return_1d"].iloc[i]:.1f}%')
        
        if df['rsi'].iloc[i] > 70:
            score += 0.2
            reasons.append(f'RSI={df["rsi"].iloc[i]:.1f}(超买)')
        
        if df['close'].iloc[i] >= df['bb_upper'].iloc[i] * 0.99:
            score += 0.1
            reasons.append('触及布林带上轨')
        
        threshold = 0.5
        signal = score >= threshold
        
        return signal, score, ' + '.join(reasons)
    
    def _calc_perf_metrics(self, equity_series: pd.Series, initial_cash: float) -> dict:
        """计算性能指标"""
        returns = equity_series.pct_change().dropna()
        
        total_return = (equity_series.iloc[-1] / initial_cash - 1) * 100
        
        # 年化收益率
        days = len(equity_series)
        annual_return = (equity_series.iloc[-1] / initial_cash) ** (252 / max(days, 1)) - 1
        annual_return *= 100
        
        # 夏普比率
        if returns.std() > 0:
            sharpe = returns.mean() / returns.std() * np.sqrt(252)
        else:
            sharpe = 0
        
        # 最大回撤
        peak = equity_series.cummax()
        drawdown = (equity_series - peak) / peak
        max_drawdown = drawdown.min() * 100
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe': sharpe,
            'max_drawdown': max_drawdown,
        }
    
    def run_backtest(
        self,
        take_profit_pct: float = 3.0,
        stop_loss_pct: float = 2.0,
        max_hold_days: int = 10,
    ) -> dict:
        """
        运行事件驱动策略回测
        
        参数：
            take_profit_pct: 止盈比例（%）
            stop_loss_pct: 止损比例（%）
            max_hold_days: 最大持有天数
        """
        df = self.df
        n = len(df)
        
        cash = self.initial_cash
        position = 0  # 持股数量
        entry_price = 0
        entry_date = None
        entry_idx = 0
        signal_type = ''
        
        trades = []
        equity_curve = []
        
        for i in range(60, n):  # 前60天用来算指标
            date = df['date'].iloc[i].strftime('%Y-%m-%d')
            price = df['close'].iloc[i]
            
            # === 卖出逻辑 ===
            if position > 0:
                hold_days = i - entry_idx
                return_pct = (price / entry_price - 1) * 100
                
                exit_reason = ''
                should_exit = False
                
                # 止盈
                if return_pct >= take_profit_pct:
                    should_exit = True
                    exit_reason = '止盈'
                
                # 止损
                elif return_pct <= -stop_loss_pct:
                    should_exit = True
                    exit_reason = '止损'
                
                # 超涨信号出现 → 卖出
                else:
                    ob_signal, ob_score, ob_reason = self.check_overbought_signal(i)
                    if ob_signal and ob_score >= 0.7:
                        should_exit = True
                        exit_reason = f'超涨信号({ob_score:.1f})'
                
                # 最大持有天数
                if hold_days >= max_hold_days and not should_exit:
                    should_exit = True
                    exit_reason = '到期'
                
                if should_exit:
                    # 卖出
                    cash = position * price
                    actual_return = (price / entry_price - 1) * 100
                    
                    trades.append(SignalResult(
                        entry_date=entry_date,
                        entry_price=entry_price,
                        exit_date=date,
                        exit_price=price,
                        return_pct=actual_return,
                        hold_days=hold_days,
                        signal_type=signal_type,
                        exit_reason=exit_reason,
                    ))
                    
                    position = 0
                    entry_price = 0
            
            # === 买入逻辑 ===
            if position == 0:
                # 检查超跌反弹信号
                os_signal, os_score, os_reason = self.check_oversold_signal(i)
                
                # 检查突破信号
                bo_signal, bo_score, bo_reason = self.check_breakout_signal(i)
                
                buy_signal = False
                buy_score = 0
                buy_reason = ''
                buy_type = ''
                
                # 优先超跌反弹（胜率更高）
                if os_signal and os_score >= 0.6:
                    buy_signal = True
                    buy_score = os_score
                    buy_reason = f'超跌反弹: {os_reason}'
                    buy_type = '超跌反弹'
                
                # 其次突破信号
                elif bo_signal and bo_score >= 0.6:
                    # 确认趋势：MA5 > MA20
                    if df['ma5'].iloc[i] > df['ma20'].iloc[i]:
                        buy_signal = True
                        buy_score = bo_score
                        buy_reason = f'趋势突破: {bo_reason}'
                        buy_type = '趋势突破'
                
                if buy_signal:
                    # 全仓买入
                    position = int(cash / price * 100) / 100  # 100股整数倍
                    actual_cost = position * price
                    cash -= actual_cost
                    
                    entry_price = price
                    entry_date = date
                    entry_idx = i
                    signal_type = buy_type
            
            # 记录权益
            equity = cash + position * price
            equity_curve.append({
                'date': date,
                'equity': equity,
                'position': position > 0,
            })
        
        # 最后清仓
        if position > 0:
            cash = position * price
            position = 0
        
        # 计算结果
        equity_df = pd.DataFrame(equity_curve)
        equity_df['date'] = pd.to_datetime(equity_df['date'])
        
        final_value = cash
        total_return = (final_value / self.initial_cash - 1) * 100
        
        # 计算指标
        equity_series = pd.DataFrame(equity_curve).set_index('date')['equity']
        metrics = self._calc_perf_metrics(equity_series, self.initial_cash)
        
        # 交易统计
        win_trades = [t for t in trades if t.return_pct > 0]
        loss_trades = [t for t in trades if t.return_pct <= 0]
        
        # 按信号类型统计
        by_type = {}
        for t in trades:
            if t.signal_type not in by_type:
                by_type[t.signal_type] = {'count': 0, 'win': 0, 'avg_return': 0, 'total_return': 0}
            by_type[t.signal_type]['count'] += 1
            by_type[t.signal_type]['total_return'] += t.return_pct
            if t.return_pct > 0:
                by_type[t.signal_type]['win'] += 1
        
        for t_type, stats in by_type.items():
            stats['avg_return'] = stats['total_return'] / stats['count'] if stats['count'] > 0 else 0
            stats['win_rate'] = stats['win'] / stats['count'] * 100 if stats['count'] > 0 else 0
        
        return {
            'total_return': total_return,
            'total_trades': len(trades),
            'win_rate': len(win_trades) / len(trades) * 100 if trades else 0,
            'avg_return': np.mean([t.return_pct for t in trades]) if trades else 0,
            'max_return': max([t.return_pct for t in trades]) if trades else 0,
            'min_return': min([t.return_pct for t in trades]) if trades else 0,
            'avg_hold_days': np.mean([t.hold_days for t in trades]) if trades else 0,
            'trades': trades,
            'by_type': by_type,
            'equity_curve': equity_df,
            'final_value': final_value,
            'metrics': metrics,
        }
    
    def print_result(self, result: dict):
        """打印回测结果"""
        print("=" * 80)
        print("📊 事件驱动策略回测结果")
        print("=" * 80)
        print()
        
        print(f"💰 初始资金: ¥{self.initial_cash:,.0f}")
        print(f"💰 最终资金: ¥{result['final_value']:,.0f}")
        print(f"📈 总收益率: {result['total_return']:+.2f}%")
        print(f"📊 交易次数: {result['total_trades']} 次")
        print(f"🎯 胜率: {result['win_rate']:.1f}%")
        print(f"📊 平均每笔收益: {result['avg_return']:+.2f}%")
        print(f"📈 最大单笔盈利: {result['max_return']:+.2f}%")
        print(f"📉 最大单笔亏损: {result['min_return']:+.2f}%")
        print(f"⏱️  平均持有天数: {result['avg_hold_days']:.1f} 天")
        print()
        
        # 按信号类型统计
        if result['by_type']:
            print("📋 按信号类型统计:")
            print(f"  {'信号类型':<12} {'次数':>6} {'胜率':>8} {'平均收益':>10}")
            print("  " + "-" * 45)
            for t_type, stats in sorted(result['by_type'].items()):
                print(f"  {t_type:<12} {stats['count']:>5d} {stats['win_rate']:>7.1f}% {stats['avg_return']:>+9.2f}%")
            print()
        
        # 最近10笔交易
        if result['trades']:
            print("📝 最近10笔交易:")
            print(f"  {'买入日期':<12} {'卖出日期':<12} {'类型':<10} {'收益':>8} {'天数':>5} {'原因':<10}")
            print("  " + "-" * 65)
            for t in result['trades'][-10:]:
                icon = '🟢' if t.return_pct > 0 else '🔴'
                print(f"  {t.entry_date:<12} {t.exit_date:<12} {t.signal_type:<10} "
                      f"{t.return_pct:>+7.2f}% {t.hold_days:>4d} {t.exit_reason:<10} {icon}")
        
        # 买入持有对比
        print()
        buy_hold_return = (
            self.df['close'].iloc[-1] / self.df['close'].iloc[60] - 1
        ) * 100
        print(f"📊 买入持有收益: {buy_hold_return:+.2f}%")
        excess = result['total_return'] - buy_hold_return
        print(f"📈 超额收益: {excess:+.2f}% {'✅跑赢' if excess > 0 else '❌跑输'}")
        
        print()
        print("=" * 80)


# =============================================================================
# 快速测试
# =============================================================================

if __name__ == "__main__":
    from core.real_data import RealGoldETFData
    
    print("📊 正在获取数据...")
    data = RealGoldETFData('518880', 'sh')
    df = data.fetch_history(days=500)
    
    if df is None:
        print("❌ 无法获取数据")
        exit(1)
    
    print(f"✅ 获取到 {len(df)} 条数据")
    print()
    
    strategy = EventDrivenStrategy(df)
    result = strategy.run_backtest(
        take_profit_pct=3.0,
        stop_loss_pct=2.0,
        max_hold_days=10,
    )
    strategy.print_result(result)
