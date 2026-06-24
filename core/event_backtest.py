#!/usr/bin/env python3
"""
历史事件回测引擎
================

研究历史上各种"事件"发生后，黄金价格的走势规律

功能：
1. 价格极端变动事件（大涨/大跌后怎么走）
2. 创新高/新低事件
3. 周内效应（周几涨得好/跌得多）
4. 月度效应（几月涨得好）
5. 均线交叉事件
6. 事件前后收益统计
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field


@dataclass
class EventAnalysisResult:
    """单种事件的分析结果"""
    event_name: str
    event_count: int = 0
    
    # 事件后N日收益统计
    forward_returns: Dict[int, Dict[str, float]] = field(default_factory=dict)
    # 事件前N日收益统计（看事件是否有预兆）
    backward_returns: Dict[int, Dict[str, float]] = field(default_factory=dict)
    
    # 胜率
    win_rates: Dict[int, float] = field(default_factory=dict)
    
    # 典型走势（平均路径）
    avg_path_before: List[float] = field(default_factory=list)
    avg_path_after: List[float] = field(default_factory=list)
    
    # 描述
    description: str = ''


@dataclass
class EventPoint:
    """事件点"""
    date: str
    index: int
    price: float
    event_type: str
    return_1d: float = 0.0  # 当日涨跌幅


class EventBacktester:
    """
    历史事件回测引擎
    
    在历史K线上标记各种事件，分析事件前后的价格走势
    """
    
    def __init__(self, df: pd.DataFrame):
        """
        参数：
            df: 历史K线数据，必须包含 date, open, high, low, close, volume
        """
        self.df = df.copy()
        self.df['date'] = pd.to_datetime(self.df['date'])
        self.df = self.df.sort_values('date').reset_index(drop=True)
        
        # 计算日收益率
        self.df['return_1d'] = self.df['close'].pct_change() * 100
        
        # 计算未来N日收益
        for n in [1, 3, 5, 10, 20]:
            self.df[f'fwd_return_{n}d'] = self.df['close'].shift(-n) / self.df['close'] - 1
            self.df[f'fwd_return_{n}d'] *= 100
        
        # 计算过去N日收益
        for n in [1, 3, 5, 10, 20]:
            self.df[f'past_return_{n}d'] = self.df['close'] / self.df['close'].shift(n) - 1
            self.df[f'past_return_{n}d'] *= 100
        
        # 日期特征
        self.df['weekday'] = self.df['date'].dt.weekday  # 0=周一, 6=周日
        self.df['month'] = self.df['date'].dt.month
        self.df['week_of_month'] = (self.df['date'].dt.day - 1) // 7 + 1
    
    def _calc_stats(self, values: np.ndarray) -> Dict[str, float]:
        """计算统计量"""
        values = values[~np.isnan(values)]
        if len(values) == 0:
            return {'mean': 0, 'median': 0, 'std': 0, 'min': 0, 'max': 0, 'count': 0}
        
        return {
            'mean': float(np.mean(values)),
            'median': float(np.median(values)),
            'std': float(np.std(values)),
            'min': float(np.min(values)),
            'max': float(np.max(values)),
            'count': len(values),
        }
    
    def analyze_price_extremes(
        self,
        threshold_pct: float = 2.0
    ) -> EventAnalysisResult:
        """
        分析价格极端变动事件
        
        参数：
            threshold_pct: 涨跌幅阈值（%），默认2%
        """
        result = EventAnalysisResult(
            event_name=f'单日涨跌{threshold_pct}%以上',
            description=f'统计单日涨跌幅超过{threshold_pct}%的日子，之后几天的表现'
        )
        
        # 大涨事件
        big_up_mask = self.df['return_1d'] >= threshold_pct
        big_up_indices = self.df[big_up_mask].index.tolist()
        
        # 大跌事件
        big_down_mask = self.df['return_1d'] <= -threshold_pct
        big_down_indices = self.df[big_down_mask].index.tolist()
        
        print(f"  大涨{threshold_pct}%以上: {len(big_up_indices)} 次")
        print(f"  大跌{threshold_pct}%以上: {len(big_down_indices)} 次")
        
        # 分别分析大涨和大跌后的表现
        for name, indices in [
            (f'大涨{threshold_pct}%+', big_up_indices),
            (f'大跌{threshold_pct}%+', big_down_indices),
        ]:
            if not indices:
                continue
            
            print(f"\n  --- {name}后表现 ---")
            
            for n in [1, 3, 5, 10, 20]:
                col = f'fwd_return_{n}d'
                if col in self.df.columns:
                    returns = self.df.loc[indices, col].values
                    stats = self._calc_stats(returns)
                    win_rate = (returns > 0).sum() / len(returns) * 100 if len(returns) > 0 else 0
                    
                    print(f"    后{n}日: 平均{stats['mean']:+.2f}% | 胜率{win_rate:.1f}% "
                          f"| 最大{stats['max']:+.2f}% | 最小{stats['min']:+.2f}%")
        
        # 综合结果
        all_extreme_indices = big_up_indices + big_down_indices
        result.event_count = len(all_extreme_indices)
        
        if all_extreme_indices:
            for n in [1, 3, 5, 10, 20]:
                col = f'fwd_return_{n}d'
                if col in self.df.columns:
                    returns = self.df.loc[all_extreme_indices, col].values
                    result.forward_returns[n] = self._calc_stats(returns)
                    result.win_rates[n] = (returns > 0).sum() / len(returns) * 100 if len(returns) > 0 else 0
        
        return result
    
    def analyze_new_highs_lows(self, lookback: int = 60) -> EventAnalysisResult:
        """
        分析创新高/新低事件
        
        参数：
            lookback: 回看多少天的新高/新低
        """
        result = EventAnalysisResult(
            event_name=f'{lookback}日新高/新低',
            description=f'价格创{lookback}日新高或新低后的表现'
        )
        
        # 计算rolling最高/最低
        self.df['rolling_high'] = self.df['close'].rolling(lookback).max()
        self.df['rolling_low'] = self.df['close'].rolling(lookback).min()
        
        # 创新高
        new_high_mask = self.df['close'] >= self.df['rolling_high'].shift(1)
        new_high_indices = self.df[new_high_mask].index.tolist()
        
        # 创新低
        new_low_mask = self.df['close'] <= self.df['rolling_low'].shift(1)
        new_low_indices = self.df[new_low_mask].index.tolist()
        
        print(f"  创{lookback}日新高: {len(new_high_indices)} 次")
        print(f"  创{lookback}日新低: {len(new_low_indices)} 次")
        
        # 分析创新高后的表现
        for name, indices in [
            (f'创{lookback}日新高后', new_high_indices),
            (f'创{lookback}日新低后', new_low_indices),
        ]:
            if not indices:
                continue
            
            print(f"\n  --- {name}表现 ---")
            
            for n in [1, 3, 5, 10, 20]:
                col = f'fwd_return_{n}d'
                if col in self.df.columns:
                    returns = self.df.loc[indices, col].values
                    stats = self._calc_stats(returns)
                    win_rate = (returns > 0).sum() / len(returns) * 100 if len(returns) > 0 else 0
                    
                    print(f"    后{n}日: 平均{stats['mean']:+.2f}% | 胜率{win_rate:.1f}% "
                          f"| 最大{stats['max']:+.2f}% | 最小{stats['min']:+.2f}%")
        
        result.event_count = len(new_high_indices) + len(new_low_indices)
        
        return result
    
    def analyze_weekday_effect(self) -> EventAnalysisResult:
        """
        分析周内效应（周几表现最好/最差）
        """
        result = EventAnalysisResult(
            event_name='周内效应',
            description='一周中每天的平均表现'
        )
        
        weekday_names = ['周一', '周二', '周三', '周四', '周五']
        
        print(f"  {'星期':<6} {'平均涨幅':>10} {'胜率':>8} {'次数':>6} {'最大涨幅':>10} {'最大跌幅':>10}")
        print("  " + "-" * 60)
        
        for wd in range(5):  # 0-4, 周一到周五
            wd_data = self.df[self.df['weekday'] == wd]
            returns = wd_data['return_1d'].dropna()
            
            if len(returns) == 0:
                continue
            
            avg_ret = returns.mean()
            win_rate = (returns > 0).sum() / len(returns) * 100
            max_up = returns.max()
            max_down = returns.min()
            
            print(f"  {weekday_names[wd]:<6} {avg_ret:>+9.3f}% {win_rate:>7.1f}% {len(returns):>5d} "
                  f"{max_up:>+9.2f}% {max_down:>+9.2f}%")
        
        # 找最好和最差的
        weekday_perf = {}
        for wd in range(5):
            returns = self.df[self.df['weekday'] == wd]['return_1d'].dropna()
            if len(returns) > 0:
                weekday_perf[wd] = returns.mean()
        
        if weekday_perf:
            best_wd = max(weekday_perf, key=weekday_perf.get)
            worst_wd = min(weekday_perf, key=weekday_perf.get)
            
            print(f"\n  💡 表现最好: {weekday_names[best_wd]} ({weekday_perf[best_wd]:+.3f}%)")
            print(f"  💡 表现最差: {weekday_names[worst_wd]} ({weekday_perf[worst_wd]:+.3f}%)")
        
        result.event_count = len(self.df)
        return result
    
    def analyze_monthly_effect(self) -> EventAnalysisResult:
        """
        分析月度效应（几月表现最好/最差）
        """
        result = EventAnalysisResult(
            event_name='月度效应',
            description='每个月的平均表现'
        )
        
        month_names = ['1月', '2月', '3月', '4月', '5月', '6月', 
                       '7月', '8月', '9月', '10月', '11月', '12月']
        
        print(f"  {'月份':<6} {'平均涨幅':>10} {'胜率':>8} {'次数':>6} {'最大涨幅':>10} {'最大跌幅':>10}")
        print("  " + "-" * 60)
        
        monthly_perf = {}
        
        for m in range(1, 13):
            m_data = self.df[self.df['month'] == m]
            returns = m_data['return_1d'].dropna()
            
            if len(returns) == 0:
                continue
            
            avg_ret = returns.mean()
            win_rate = (returns > 0).sum() / len(returns) * 100
            max_up = returns.max()
            max_down = returns.min()
            
            monthly_perf[m] = avg_ret
            
            print(f"  {month_names[m-1]:<6} {avg_ret:>+9.3f}% {win_rate:>7.1f}% {len(returns):>5d} "
                  f"{max_up:>+9.2f}% {max_down:>+9.2f}%")
        
        if monthly_perf:
            best_m = max(monthly_perf, key=monthly_perf.get)
            worst_m = min(monthly_perf, key=monthly_perf.get)
            
            print(f"\n  💡 表现最好: {month_names[best_m-1]} ({monthly_perf[best_m]:+.3f}%)")
            print(f"  💡 表现最差: {month_names[worst_m-1]} ({monthly_perf[worst_m]:+.3f}%)")
        
        result.event_count = len(self.df)
        return result
    
    def analyze_ma_crossover(self, short: int = 5, long: int = 20) -> EventAnalysisResult:
        """
        分析均线交叉事件后的表现
        """
        result = EventAnalysisResult(
            event_name=f'MA{short}/MA{long}金叉死叉',
            description=f'MA{short}上穿/下穿MA{long}后的表现'
        )
        
        # 计算均线
        self.df[f'ma{short}'] = self.df['close'].rolling(short).mean()
        self.df[f'ma{long}'] = self.df['close'].rolling(long).mean()
        
        # 均线差
        self.df['ma_diff'] = self.df[f'ma{short}'] - self.df[f'ma{long}']
        
        # 金叉：前一天ma_diff < 0，今天 > 0
        golden_cross = (self.df['ma_diff'].shift(1) < 0) & (self.df['ma_diff'] > 0)
        golden_indices = self.df[golden_cross].index.tolist()
        
        # 死叉：前一天ma_diff > 0，今天 < 0
        death_cross = (self.df['ma_diff'].shift(1) > 0) & (self.df['ma_diff'] < 0)
        death_indices = self.df[death_cross].index.tolist()
        
        print(f"  金叉次数: {len(golden_indices)} 次")
        print(f"  死叉次数: {len(death_indices)} 次")
        
        for name, indices in [
            ('金叉后', golden_indices),
            ('死叉后', death_indices),
        ]:
            if not indices:
                continue
            
            print(f"\n  --- {name}表现 ---")
            
            for n in [5, 10, 20, 30]:
                col = f'fwd_return_{n}d'
                if col in self.df.columns:
                    returns = self.df.loc[indices, col].values
                    stats = self._calc_stats(returns)
                    win_rate = (returns > 0).sum() / len(returns) * 100 if len(returns) > 0 else 0
                    
                    print(f"    后{n}日: 平均{stats['mean']:+.2f}% | 胜率{win_rate:.1f}% "
                          f"| 最大{stats['max']:+.2f}% | 最小{stats['min']:+.2f}%")
        
        result.event_count = len(golden_indices) + len(death_indices)
        return result
    
    def analyze_overreaction_reversal(
        self,
        lookback: int = 5,
        threshold_pct: float = 3.0
    ) -> EventAnalysisResult:
        """
        分析超跌反弹/超涨回调
        
        思路：过去N天涨/跌太多了，接下来会不会反转？
        """
        result = EventAnalysisResult(
            event_name=f'{lookback}日涨跌{threshold_pct}%后的反转效应',
            description=f'过去{lookback}日累计涨跌{threshold_pct}%后，是否会反转'
        )
        
        past_col = f'past_return_{lookback}d'
        
        # 超涨（过去N天涨太多）
        overbought = self.df[past_col] >= threshold_pct
        overbought_indices = self.df[overbought].index.tolist()
        
        # 超跌（过去N天跌太多）
        oversold = self.df[past_col] <= -threshold_pct
        oversold_indices = self.df[oversold].index.tolist()
        
        print(f"  超涨（{lookback}日涨{threshold_pct}%+）: {len(overbought_indices)} 次")
        print(f"  超跌（{lookback}日跌{threshold_pct}%+）: {len(oversold_indices)} 次")
        
        for name, indices in [
            ('超涨后（看是否回调）', overbought_indices),
            ('超跌后（看是否反弹）', oversold_indices),
        ]:
            if not indices:
                continue
            
            print(f"\n  --- {name} ---")
            
            for n in [3, 5, 10, 15]:
                col = f'fwd_return_{n}d'
                if col in self.df.columns:
                    returns = self.df.loc[indices, col].values
                    stats = self._calc_stats(returns)
                    win_rate = (returns > 0).sum() / len(returns) * 100 if len(returns) > 0 else 0
                    
                    # 判断是延续还是反转
                    if name.startswith('超涨'):
                        reversal = '延续' if stats['mean'] > 0 else '反转'
                    else:
                        reversal = '延续' if stats['mean'] < 0 else '反转'
                    
                    print(f"    后{n}日: 平均{stats['mean']:+.2f}% | 胜率{win_rate:.1f}% | {reversal}")
        
        result.event_count = len(overbought_indices) + len(oversold_indices)
        return result
    
    def run_all_analysis(self):
        """运行所有事件分析"""
        print("=" * 80)
        print("📊 历史事件回测分析报告")
        print("=" * 80)
        print(f"📅 数据区间: {self.df['date'].iloc[0].strftime('%Y-%m-%d')} ~ {self.df['date'].iloc[-1].strftime('%Y-%m-%d')}")
        print(f"📈 数据条数: {len(self.df)} 天")
        print(f"💰 起始价格: ¥{self.df['close'].iloc[0]:.3f}")
        print(f"💰 结束价格: ¥{self.df['close'].iloc[-1]:.3f}")
        total_return = (self.df['close'].iloc[-1] / self.df['close'].iloc[0] - 1) * 100
        print(f"📈 买入持有: {total_return:+.2f}%")
        print(f"📊 日均波动: {self.df['return_1d'].std():.2f}%")
        print()
        
        # 1. 周内效应
        print("=" * 80)
        print("【一】周内效应（周几表现最好？）")
        print("=" * 80)
        self.analyze_weekday_effect()
        print()
        
        # 2. 月度效应
        print("=" * 80)
        print("【二】月度效应（几月表现最好？）")
        print("=" * 80)
        self.analyze_monthly_effect()
        print()
        
        # 3. 单日极端涨跌
        print("=" * 80)
        print("【三】单日极端涨跌后的表现")
        print("=" * 80)
        for threshold in [2.0, 3.0]:
            print(f"\n--- 阈值 {threshold}% ---")
            self.analyze_price_extremes(threshold)
        print()
        
        # 4. 超跌反弹/超涨回调
        print("=" * 80)
        print("【四】超跌反弹 / 超涨回调（反转效应）")
        print("=" * 80)
        for lookback, threshold in [(5, 5), (10, 8), (20, 10)]:
            print(f"\n--- {lookback}日累计涨跌{threshold}% ---")
            self.analyze_overreaction_reversal(lookback, threshold)
        print()
        
        # 5. 创新高/新低
        print("=" * 80)
        print("【五】创新高/新低后的表现")
        print("=" * 80)
        for lookback in [20, 60, 120]:
            print(f"\n--- {lookback}日新高新低 ---")
            self.analyze_new_highs_lows(lookback)
        print()
        
        # 6. 均线交叉
        print("=" * 80)
        print("【六】均线交叉后的表现")
        print("=" * 80)
        for short, long in [(5, 20), (10, 20), (20, 60)]:
            print(f"\n--- MA{short}/MA{long} ---")
            self.analyze_ma_crossover(short, long)
        print()
        
        print("=" * 80)
        print("✅ 分析完成")
        print("=" * 80)


# =============================================================================
# 快速测试
# =============================================================================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '/workspace')
    from core.real_data import RealGoldETFData
    
    print("📊 正在获取数据...")
    data = RealGoldETFData('518880', 'sh')
    df = data.fetch_history(days=500)
    
    if df is None:
        print("❌ 无法获取数据")
        exit(1)
    
    print(f"✅ 获取到 {len(df)} 条数据")
    print()
    
    backtester = EventBacktester(df)
    backtester.run_all_analysis()
