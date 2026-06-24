#!/usr/bin/env python3
"""
动量策略加强版 (Momentum Strategies Pro)
========================================

专门为黄金ETF设计的动量策略集合，包含7种变体：

1. 简单动量策略 (Simple Momentum)
2. 双动量策略 (Dual Momentum) - 绝对动量 + 趋势过滤
3. 多周期动量共振 (Multi-Period Resonance)
4. 加速度动量 (Acceleration Momentum)
5. 波动率调整动量 (Volatility-Adjusted)
6. 动量+RSI过滤 (Momentum + RSI Filter)
7. MACD动量策略 (MACD Momentum)

核心思想：黄金是趋势性很强的品种，"涨了还会涨，跌了还会跌"
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from core.backtest_engine import BacktestResult, BacktestEngine


@dataclass
class MomentumResult:
    """动量策略回测结果"""
    strategy_name: str
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_hold_days: float
    description: str = ''


class MomentumStrategies:
    """
    动量策略集合
    
    专为黄金ETF(518880)优化的动量策略
    """
    
    def __init__(self, df: pd.DataFrame, initial_cash: float = 100000):
        self.df = df.copy()
        self.df['date'] = pd.to_datetime(self.df['date'])
        self.df = self.df.sort_values('date').reset_index(drop=True)
        self.initial_cash = initial_cash
        
        # 预计算指标
        self._calculate_all_indicators()
    
    def _calculate_all_indicators(self):
        """预计算所有需要的指标"""
        df = self.df
        close = df['close']
        
        # 各周期涨跌幅
        for n in [3, 5, 10, 15, 20, 30, 60]:
            df[f'mom_{n}'] = close.pct_change(n) * 100
        
        # 均线
        for n in [5, 10, 20, 60]:
            df[f'ma{n}'] = close.rolling(n).mean()
        
        # 波动率（20日标准差）
        df['volatility_20'] = close.pct_change().rolling(20).std() * 100
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta.where(delta < 0, 0))
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df['rsi'] = 100 - (100 / (1 + rs))
        df['rsi'] = df['rsi'].fillna(50)
        
        # MACD
        exp12 = close.ewm(span=12, adjust=False).mean()
        exp26 = close.ewm(span=26, adjust=False).mean()
        df['macd_dif'] = exp12 - exp26
        df['macd_dea'] = df['macd_dif'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd_dif'] - df['macd_dea']
        
        # MACD动量（柱的变化）
        df['macd_hist_change'] = df['macd_hist'].diff()
        
        # ATR（真实波幅）
        high = df['high']
        low = df['low']
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
        df['atr_14'] = tr.rolling(14).mean()
        
        self.df = df
    
    def _run_strategy(self, signals: pd.Series, name: str, desc: str = '') -> MomentumResult:
        """运行策略并返回结果"""
        # 使用BacktestEngine运行回测
        engine = BacktestEngine(self.initial_cash)
        result = engine._run_strategy(self.df, signals)
        result.strategy_name = name
        
        # 统计交易次数
        total_trades = 0
        if hasattr(result, 'trades') and result.trades:
            total_trades = len(result.trades)
        
        avg_hold = len(self.df) / max(total_trades, 1)
        
        return MomentumResult(
            strategy_name=name,
            total_return=result.total_return,
            annual_return=result.annual_return,
            sharpe_ratio=result.sharpe_ratio if hasattr(result, 'sharpe_ratio') else 0,
            max_drawdown=result.max_drawdown if hasattr(result, 'max_drawdown') else 0,
            win_rate=result.win_rate,
            profit_factor=result.profit_loss_ratio if hasattr(result, 'profit_loss_ratio') else 0,
            total_trades=total_trades,
            avg_hold_days=avg_hold,
            description=desc,
        )
    
    def _count_trades(self, signals: pd.Series) -> int:
        """统计交易次数"""
        count = 0
        prev = 0
        for sig in signals:
            if sig != 0 and prev == 0:
                count += 1
            prev = sig
        return count
    
    # =====================================================================
    # 策略1：简单动量策略
    # =====================================================================
    def simple_momentum(self, period: int = 10) -> MomentumResult:
        """
        简单动量策略
        
        规则：
        - 过去N日涨幅 > 0 → 买入（趋势向上）
        - 过去N日涨幅 < 0 → 卖出（趋势向下）
        
        核心思想：涨了还会涨，跌了还会跌
        """
        df = self.df
        signals = pd.Series(0, index=df.index)
        mom_col = f'mom_{period}'
        
        # 动态计算（如果没有的话）
        if mom_col not in df.columns:
            df[mom_col] = df['close'].pct_change(period) * 100
        
        for i in range(period, len(df)):
            mom = df[mom_col].iloc[i]
            if pd.notna(mom):
                if mom > 0:
                    signals.iloc[i] = 1
                elif mom < 0:
                    signals.iloc[i] = -1
        
        return self._run_strategy(
            signals,
            f'简单动量({period}日)',
            f'过去{period}日涨跌幅为正就买入'
        )
    
    # =====================================================================
    # 策略2：双动量策略（绝对动量 + 趋势过滤）
    # =====================================================================
    def dual_momentum(self, period: int = 10, ma_period: int = 20) -> MomentumResult:
        """
        双动量策略 (Dual Momentum)
        
        规则：
        - 买入条件（同时满足）：
          1. 过去N日涨幅 > 0（绝对动量为正）
          2. 价格在MA20以上（趋势向上）
        - 卖出条件（满足任一）：
          1. 过去N日涨幅 < 0
          2. 价格跌破MA20
        
        核心思想：双保险，只有动量和趋势都看涨才买入
        """
        df = self.df
        signals = pd.Series(0, index=df.index)
        mom_col = f'mom_{period}'
        ma_col = f'ma{ma_period}'
        
        # 动态计算
        if mom_col not in df.columns:
            df[mom_col] = df['close'].pct_change(period) * 100
        if ma_col not in df.columns:
            df[ma_col] = df['close'].rolling(ma_period).mean()
        
        start = max(period, ma_period)
        
        for i in range(start, len(df)):
            mom = df[mom_col].iloc[i]
            price = df['close'].iloc[i]
            ma = df[ma_col].iloc[i]
            
            if pd.notna(mom) and pd.notna(ma):
                # 买入：动量为正 + 价格在均线上方
                if mom > 0 and price > ma:
                    signals.iloc[i] = 1
                # 卖出：动量为负 或 价格跌破均线
                elif mom < 0 or price < ma:
                    signals.iloc[i] = -1
        
        return self._run_strategy(
            signals,
            f'双动量({period}日+MA{ma_period})',
            f'动量+趋势双确认，减少假信号'
        )
    
    # =====================================================================
    # 策略3：多周期动量共振
    # =====================================================================
    def multi_period_resonance(
        self,
        periods: List[int] = None,
        min_positive: int = 3
    ) -> MomentumResult:
        """
        多周期动量共振策略
        
        规则：
        - 多个周期（5/10/20日）的动量同时为正 → 买入（共振）
        - 多个周期的动量同时为负 → 卖出
        - 其他情况：观望
        
        核心思想：多个周期共振的趋势更可靠
        """
        if periods is None:
            periods = [5, 10, 20, 30]
        
        df = self.df
        signals = pd.Series(0, index=df.index)
        
        start = max(periods)
        
        for i in range(start, len(df)):
            positive_count = 0
            negative_count = 0
            
            for p in periods:
                mom = df[f'mom_{p}'].iloc[i]
                if pd.notna(mom):
                    if mom > 0:
                        positive_count += 1
                    elif mom < 0:
                        negative_count += 1
            
            # 多数周期看涨 → 买入
            if positive_count >= min_positive:
                signals.iloc[i] = 1
            # 多数周期看跌 → 卖出
            elif negative_count >= min_positive:
                signals.iloc[i] = -1
        
        return self._run_strategy(
            signals,
            f'多周期共振({len(periods)}周期)',
            f'{len(periods)}个周期中至少{min_positive}个看涨才买入'
        )
    
    # =====================================================================
    # 策略4：加速度动量
    # =====================================================================
    def acceleration_momentum(self, fast_period: int = 5, slow_period: int = 20) -> MomentumResult:
        """
        加速度动量策略
        
        规则：
        - 短期动量 > 长期动量（加速度向上）→ 买入
        - 短期动量 < 长期动量（加速度向下）→ 卖出
        
        核心思想：不仅要看涨，还要看涨得越来越快
        加速上涨的行情最肥美
        """
        df = self.df
        signals = pd.Series(0, index=df.index)
        
        start = slow_period
        
        for i in range(start, len(df)):
            mom_fast = df[f'mom_{fast_period}'].iloc[i]
            mom_slow = df[f'mom_{slow_period}'].iloc[i]
            
            if pd.notna(mom_fast) and pd.notna(mom_slow):
                # 加速度向上：短期动量 > 长期动量
                if mom_fast > mom_slow and mom_slow > 0:
                    signals.iloc[i] = 1
                # 加速度向下：短期动量 < 长期动量
                elif mom_fast < mom_slow:
                    signals.iloc[i] = -1
        
        return self._run_strategy(
            signals,
            f'加速度动量({fast_period}/{slow_period})',
            '短期动量超过长期动量 → 加速上涨'
        )
    
    # =====================================================================
    # 策略5：波动率调整动量
    # =====================================================================
    def volatility_adjusted(
        self,
        period: int = 10,
        vol_period: int = 20,
        threshold: float = 0.5
    ) -> MomentumResult:
        """
        波动率调整动量策略
        
        规则：
        - 动量 / 波动率 > 阈值 → 买入（风险调整后收益高）
        - 动量 / 波动率 < -阈值 → 卖出
        - 中间：观望
        
        核心思想：同样的涨幅，波动率低的更健康、更可持续
        类似夏普比率的思路
        """
        df = self.df
        signals = pd.Series(0, index=df.index)
        
        start = max(period, vol_period)
        
        for i in range(start, len(df)):
            mom = df[f'mom_{period}'].iloc[i]
            vol = df['volatility_20'].iloc[i]
            
            if pd.notna(mom) and pd.notna(vol) and vol > 0:
                # 风险调整后动量
                risk_adjusted_mom = mom / (vol * np.sqrt(period / 252))
                
                if risk_adjusted_mom > threshold:
                    signals.iloc[i] = 1
                elif risk_adjusted_mom < -threshold:
                    signals.iloc[i] = -1
        
        return self._run_strategy(
            signals,
            f'波动率调整({period}日)',
            '考虑风险调整后的动量，更稳健'
        )
    
    # =====================================================================
    # 策略6：动量 + RSI过滤
    # =====================================================================
    def momentum_with_rsi_filter(
        self,
        period: int = 10,
        rsi_oversold: int = 30,
        rsi_overbought: int = 70
    ) -> MomentumResult:
        """
        动量 + RSI过滤策略
        
        规则：
        - 买入：动量为正 且 RSI < 70（没超买，还有空间）
        - 卖出：动量为负 或 RSI > 70（超买了，小心回调）
        
        核心思想：动量告诉我们方向，RSI告诉我们位置
        不要在超买区域追高
        """
        df = self.df
        signals = pd.Series(0, index=df.index)
        
        start = max(period, 14)
        
        for i in range(start, len(df)):
            mom = df[f'mom_{period}'].iloc[i]
            rsi = df['rsi'].iloc[i]
            
            if pd.notna(mom) and pd.notna(rsi):
                # 买入：动量向上 + 没超买
                if mom > 0 and rsi < rsi_overbought:
                    signals.iloc[i] = 1
                # 卖出：动量向下 或 超买
                elif mom < 0 or rsi > rsi_overbought:
                    signals.iloc[i] = -1
        
        return self._run_strategy(
            signals,
            f'动量+RSI过滤({period}日)',
            '避免在超买区域追高，提高胜率'
        )
    
    # =====================================================================
    # 策略7：MACD动量策略
    # =====================================================================
    def macd_momentum(self) -> MomentumResult:
        """
        MACD动量策略
        
        规则：
        - 买入：MACD柱 > 0 且 柱在变大（动量增强）
        - 卖出：MACD柱 < 0 或 柱在变小（动量减弱）
        
        核心思想：用MACD柱的大小和变化来衡量动量
        MACD柱变大 = 上涨动能增强
        """
        df = self.df
        signals = pd.Series(0, index=df.index)
        
        for i in range(26, len(df)):
            hist = df['macd_hist'].iloc[i]
            hist_change = df['macd_hist_change'].iloc[i]
            
            if pd.notna(hist) and pd.notna(hist_change):
                # 买入：MACD柱正 且 还在变大（动能增强）
                if hist > 0 and hist_change > 0:
                    signals.iloc[i] = 1
                # 卖出：MACD柱负 或 在变小
                elif hist < 0 or hist_change < 0:
                    signals.iloc[i] = -1
        
        return self._run_strategy(
            signals,
            'MACD动量',
            'MACD柱的大小和变化判断动能'
        )
    
    # =====================================================================
    # 运行所有策略
    # =====================================================================
    def run_all(self) -> List[MomentumResult]:
        """运行所有动量策略"""
        results = []
        
        # 1. 简单动量（不同周期）
        for period in [5, 10, 20]:
            results.append(self.simple_momentum(period))
        
        # 2. 双动量
        results.append(self.dual_momentum(10, 20))
        results.append(self.dual_momentum(20, 60))
        
        # 3. 多周期共振
        results.append(self.multi_period_resonance([5, 10, 20], 2))
        results.append(self.multi_period_resonance([5, 10, 20, 30], 3))
        
        # 4. 加速度动量
        results.append(self.acceleration_momentum(5, 20))
        
        # 5. 波动率调整
        results.append(self.volatility_adjusted(10))
        
        # 6. 动量+RSI过滤
        results.append(self.momentum_with_rsi_filter(10))
        
        # 7. MACD动量
        results.append(self.macd_momentum())
        
        return results
    
    def print_comparison(self, results: List[MomentumResult]):
        """打印策略对比表"""
        buy_hold_return = (
            self.df['close'].iloc[-1] / self.df['close'].iloc[0] - 1
        ) * 100
        
        # 按总收益排序
        results.sort(key=lambda x: x.total_return, reverse=True)
        
        print("=" * 100)
        print("📊 动量策略对比（按总收益排序）")
        print("=" * 100)
        print()
        print(f"  {'策略名称':<25} {'总收益':>10} {'年化':>8} {'夏普':>6} {'最大回撤':>10} "
              f"{'胜率':>8} {'交易次数':>8} {'平均持仓':>8}")
        print("  " + "-" * 95)
        
        rank = 1
        for r in results:
            icon = "🏆" if rank == 1 else ("🥈" if rank == 2 else ("🥉" if rank == 3 else "  "))
            print(f"  {icon} {r.strategy_name:<22} {r.total_return:>+9.2f}% "
                  f"{r.annual_return:>+7.2f}% {r.sharpe_ratio:>6.2f} "
                  f"{r.max_drawdown:>+9.2f}% {r.win_rate:>7.1f}% "
                  f"{r.total_trades:>7d} {r.avg_hold_days:>7.1f}天")
            rank += 1
        
        print()
        print(f"  💰 买入持有: {buy_hold_return:+.2f}%")
        print()
        
        # 统计跑赢的策略
        beat_count = sum(1 for r in results if r.total_return > buy_hold_return)
        print(f"  📈 跑赢买入持有: {beat_count}/{len(results)} 个策略")
        print()
        
        # 最佳策略详情
        best = results[0]
        print("=" * 100)
        print(f"🏆 最佳策略: {best.strategy_name}")
        print("=" * 100)
        print(f"  总收益: {best.total_return:+.2f}%")
        print(f"  年化收益: {best.annual_return:+.2f}%")
        print(f"  夏普比率: {best.sharpe_ratio:.2f}")
        print(f"  最大回撤: {best.max_drawdown:.2f}%")
        print(f"  胜率: {best.win_rate:.1f}%")
        print(f"  交易次数: {best.total_trades} 次")
        print(f"  平均持仓: {best.avg_hold_days:.1f} 天")
        print(f"  策略描述: {best.description}")
        print()


# =====================================================================
# 快速测试
# =====================================================================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '/workspace')
    from core.real_data import RealGoldETFData
    
    print("📊 正在获取历史数据...")
    data = RealGoldETFData('518880', 'sh')
    df = data.fetch_history(days=500)
    
    if df is None:
        print("❌ 无法获取数据")
        exit(1)
    
    print(f"✅ 获取到 {len(df)} 条数据")
    print(f"📅 时间范围: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}")
    print()
    
    strategies = MomentumStrategies(df)
    results = strategies.run_all()
    strategies.print_comparison(results)
