#!/usr/bin/env python3
"""
滚动回测引擎（Walk-Forward Testing）
====================================

核心思想：用过去数据训练/选策略，用未来数据验证
避免过拟合，更接近真实交易表现

回测方式：
    - 训练窗口：用于选择最优策略/参数
    - 测试窗口：用选出来的策略做交易，记录真实收益
    - 滚动向前：每次滑动一个测试窗口的长度
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from .backtest_engine import BacktestEngine, BacktestResult


@dataclass
class WalkForwardResult:
    """滚动回测结果"""
    strategy_name: str
    total_return: float = 0.0          # 滚动回测总收益
    annual_return: float = 0.0         # 年化收益
    win_rate: float = 0.0              # 测试窗口胜率
    avg_test_return: float = 0.0       # 平均每个测试窗口收益
    best_train_return: float = 0.0     # 训练窗口最佳收益
    performance_decay: float = 0.0     # 性能衰减（训练-测试）
    num_windows: int = 0               # 测试窗口数量
    winning_windows: int = 0           # 盈利窗口数
    train_returns: List[float] = field(default_factory=list)
    test_returns: List[float] = field(default_factory=list)
    is_real_data: bool = False


class WalkForwardTester:
    """
    滚动回测验证器
    
    用于检测策略是否过拟合
    """
    
    def __init__(
        self,
        train_days: int = 80,      # 训练窗口天数
        test_days: int = 20,       # 测试窗口天数
        step_days: int = 20,       # 步长（每次滚动多少天）
        initial_capital: float = 100000.0
    ):
        self.train_days = train_days
        self.test_days = test_days
        self.step_days = step_days
        self.initial_capital = initial_capital
    
    def _get_strategy_func(self, engine: BacktestEngine, name: str):
        """根据策略名获取策略函数"""
        strategies = {
            '均线交叉(5/20)': lambda df: engine.ma_crossover(df, 5, 20),
            '均线交叉(10/20)': lambda df: engine.ma_crossover(df, 10, 20),
            '均线交叉(20/60)': lambda df: engine.ma_crossover(df, 20, 60),
            'RSI(30/70)': lambda df: engine.rsi_strategy(df, 30, 70),
            'MACD金叉死叉': lambda df: engine.macd_strategy(df),
            '布林带策略': lambda df: engine.bollinger_strategy(df),
            '布林带均值回归': lambda df: engine.bollinger_reversion(df),
            '双均线趋势过滤': lambda df: engine.dual_ma_trend_filter(df),
            '海龟交易(20/10)': lambda df: engine.turtle_strategy(df),
            '动量策略(10日)': lambda df: engine.momentum_strategy(df, 10),
            '动量策略(20日)': lambda df: engine.momentum_strategy(df, 20),
            'KDJ金叉死叉': lambda df: engine.kdj_strategy(df),
            '威廉指标': lambda df: engine.willr_strategy(df),
            '多因子综合': lambda df: engine.multi_factor_strategy(df),
            '多策略投票组合': lambda df: engine.ensemble_voting_strategy(df),
        }
        return strategies.get(name)
    
    def test_single_strategy(
        self,
        df: pd.DataFrame,
        strategy_name: str,
        is_real_data: bool = False
    ) -> WalkForwardResult:
        """
        对单个策略进行滚动回测
        
        注意：这里不是选策略，而是测试同一个策略在滚动窗口中的表现
        看策略的表现是否稳定，是否在训练期好、测试期就崩了
        """
        engine = BacktestEngine(self.initial_capital)
        engine.is_real_data = is_real_data
        engine.data_source = "滚动回测"
        
        strategy_func = self._get_strategy_func(engine, strategy_name)
        if strategy_func is None:
            raise ValueError(f"未知策略: {strategy_name}")
        
        train_returns = []
        test_returns = []
        
        total_days = len(df)
        window_size = self.train_days + self.test_days
        
        # 计算可以滚动多少轮
        start_idx = 0
        while start_idx + window_size <= total_days:
            train_end = start_idx + self.train_days
            test_end = train_end + self.test_days
            
            train_df = df.iloc[start_idx:train_end].reset_index(drop=True)
            test_df = df.iloc[train_end:test_end].reset_index(drop=True)
            
            # 训练期表现
            try:
                train_result = strategy_func(train_df)
                train_returns.append(train_result.total_return)
            except Exception:
                train_returns.append(0.0)
            
            # 测试期表现（这才是真实的！）
            try:
                test_result = strategy_func(test_df)
                test_returns.append(test_result.total_return)
            except Exception:
                test_returns.append(0.0)
            
            start_idx += self.step_days
        
        # 计算统计结果
        num_windows = len(test_returns)
        winning_windows = sum(1 for r in test_returns if r > 0)
        
        avg_train = np.mean(train_returns) if train_returns else 0
        avg_test = np.mean(test_returns) if test_returns else 0
        
        # 总收益（用复利计算）
        total_return = 0
        if test_returns:
            cumulative = 1.0
            for r in test_returns:
                cumulative *= (1 + r / 100)
            total_return = (cumulative - 1) * 100
        
        # 年化收益
        total_test_days = num_windows * self.test_days
        annual_return = 0
        if total_test_days > 0:
            annual_return = ((1 + total_return / 100) ** (252 / total_test_days) - 1) * 100
        
        # 性能衰减 = 训练期平均收益 - 测试期平均收益
        # 衰减越大，说明过拟合越严重
        performance_decay = avg_train - avg_test
        
        win_rate = (winning_windows / num_windows * 100) if num_windows > 0 else 0
        
        return WalkForwardResult(
            strategy_name=strategy_name,
            total_return=total_return,
            annual_return=annual_return,
            win_rate=win_rate,
            avg_test_return=avg_test,
            best_train_return=max(train_returns) if train_returns else 0,
            performance_decay=performance_decay,
            num_windows=num_windows,
            winning_windows=winning_windows,
            train_returns=train_returns,
            test_returns=test_returns,
            is_real_data=is_real_data
        )
    
    def test_all_strategies(
        self,
        df: pd.DataFrame,
        is_real_data: bool = False
    ) -> List[WalkForwardResult]:
        """测试所有策略"""
        strategy_names = [
            '均线交叉(5/20)',
            '均线交叉(10/20)',
            '均线交叉(20/60)',
            'RSI(30/70)',
            'MACD金叉死叉',
            '布林带策略',
            '布林带均值回归',
            '双均线趋势过滤',
            '海龟交易(20/10)',
            '动量策略(10日)',
            '动量策略(20日)',
            'KDJ金叉死叉',
            '威廉指标',
            '多因子综合',
            '多策略投票组合',
        ]
        
        results = []
        for name in strategy_names:
            print(f"  滚动回测: {name}...", end=" ")
            try:
                result = self.test_single_strategy(df, name, is_real_data)
                results.append(result)
                print(f"✅ 测试收益{result.total_return:+.2f}% (衰减{result.performance_decay:+.2f}%)")
            except Exception as e:
                print(f"❌ 失败: {e}")
        
        return results
    
    def strategy_selection_test(
        self,
        df: pd.DataFrame,
        is_real_data: bool = False,
        top_n: int = 3
    ) -> Dict:
        """
        策略选择测试（更真实的场景）
        
        每轮在训练期选表现最好的top_n个策略，然后在测试期用这些策略
        模拟真实情况：我们总是会选"过去表现好"的策略
        """
        engine = BacktestEngine(self.initial_capital)
        engine.is_real_data = is_real_data
        
        strategy_names = [
            '均线交叉(5/20)',
            '均线交叉(10/20)',
            'RSI(30/70)',
            'MACD金叉死叉',
            '海龟交易(20/10)',
            '动量策略(10日)',
            '动量策略(20日)',
            '多因子综合',
        ]
        
        all_test_returns = []
        selection_log = []  # 记录每轮选了什么策略
        
        total_days = len(df)
        window_size = self.train_days + self.test_days
        
        start_idx = 0
        while start_idx + window_size <= total_days:
            train_end = start_idx + self.train_days
            test_end = train_end + self.test_days
            
            train_df = df.iloc[start_idx:train_end].reset_index(drop=True)
            test_df = df.iloc[train_end:test_end].reset_index(drop=True)
            
            # 训练期：评估所有策略，选最好的
            train_perfs = {}
            for name in strategy_names:
                func = self._get_strategy_func(engine, name)
                if func is None:
                    continue
                try:
                    result = func(train_df)
                    train_perfs[name] = result.total_return
                except Exception:
                    train_perfs[name] = -999
            
            # 选前top_n个最好的策略
            sorted_strategies = sorted(train_perfs.items(), key=lambda x: x[1], reverse=True)
            selected = [name for name, _ in sorted_strategies[:top_n]]
            
            # 测试期：用选出来的策略，平均收益
            test_returns = []
            for name in selected:
                func = self._get_strategy_func(engine, name)
                if func is None:
                    continue
                try:
                    result = func(test_df)
                    test_returns.append(result.total_return)
                except Exception:
                    test_returns.append(0)
            
            avg_test_return = np.mean(test_returns) if test_returns else 0
            all_test_returns.append(avg_test_return)
            
            selection_log.append({
                'train_start': df['date'].iloc[start_idx],
                'train_end': df['date'].iloc[train_end - 1],
                'test_start': df['date'].iloc[train_end],
                'test_end': df['date'].iloc[test_end - 1],
                'selected_strategies': selected,
                'best_train_return': sorted_strategies[0][1],
                'avg_test_return': avg_test_return,
            })
            
            start_idx += self.step_days
        
        # 计算总收益
        cumulative = 1.0
        for r in all_test_returns:
            cumulative *= (1 + r / 100)
        total_return = (cumulative - 1) * 100
        
        # 买入持有基准
        buy_hold_returns = []
        start_idx = 0
        while start_idx + window_size <= total_days:
            train_end = start_idx + self.train_days
            test_end = train_end + self.test_days
            test_df = df.iloc[train_end:test_end]
            bh_return = (test_df['close'].iloc[-1] / test_df['close'].iloc[0] - 1) * 100
            buy_hold_returns.append(bh_return)
            start_idx += self.step_days
        
        bh_cumulative = 1.0
        for r in buy_hold_returns:
            bh_cumulative *= (1 + r / 100)
        bh_total = (bh_cumulative - 1) * 100
        
        winning_windows = sum(1 for r in all_test_returns if r > 0)
        win_rate = (winning_windows / len(all_test_returns) * 100) if all_test_returns else 0
        
        return {
            'top_n': top_n,
            'total_return': total_return,
            'buy_hold_return': bh_total,
            'excess_return': total_return - bh_total,
            'win_rate': win_rate,
            'num_windows': len(all_test_returns),
            'avg_test_return': np.mean(all_test_returns) if all_test_returns else 0,
            'all_test_returns': all_test_returns,
            'buy_hold_returns': buy_hold_returns,
            'selection_log': selection_log,
        }
    
    def print_results(self, results: List[WalkForwardResult]):
        """打印滚动回测结果"""
        if not results:
            print("❌ 无结果")
            return
        
        print("\n" + "=" * 110)
        print(f"🔬 滚动回测结果（训练{self.train_days}天 + 测试{self.test_days}天，步长{self.step_days}天）")
        print("=" * 110)
        
        header = (
            f"{'策略名称':<18} "
            f"{'测试总收益':>10} "
            f"{'年化收益':>10} "
            f"{'窗口胜率':>10} "
            f"{'平均测试收益':>12} "
            f"{'平均训练收益':>12} "
            f"{'性能衰减':>10} "
            f"{'窗口数':>6}"
        )
        print(header)
        print("-" * 110)
        
        for r in results:
            decay_color = "🔴" if r.performance_decay > 5 else ("🟡" if r.performance_decay > 2 else "🟢")
            line = (
                f"{r.strategy_name:<18} "
                f"{r.total_return:>+9.2f}% "
                f"{r.annual_return:>+9.2f}% "
                f"{r.win_rate:>9.2f}% "
                f"{r.avg_test_return:>+11.2f}% "
                f"{np.mean(r.train_returns) if r.train_returns else 0:>+11.2f}% "
                f"{decay_color}{r.performance_decay:>+8.2f}% "
                f"{r.num_windows:>5d}"
            )
            print(line)
        
        # 排名
        print("\n" + "=" * 110)
        print("🏆 测试收益排名（越靠前越真实有效）")
        print("=" * 110)
        
        sorted_by_test = sorted(results, key=lambda x: x.total_return, reverse=True)
        for i, r in enumerate(sorted_by_test, 1):
            medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "  "))
            print(f"{medal} {i:2d}. {r.strategy_name:<18} 测试收益: {r.total_return:>+8.2f}%  衰减: {r.performance_decay:>+7.2f}%  窗口胜率: {r.win_rate:>6.2f}%")
        
        # 过拟合警示
        print("\n" + "=" * 110)
        print("⚠️  过拟合检测（性能衰减越大，过拟合越严重）")
        print("=" * 110)
        
        sorted_by_decay = sorted(results, key=lambda x: x.performance_decay, reverse=True)
        for i, r in enumerate(sorted_by_decay[:5], 1):
            risk = "🔴 高风险" if r.performance_decay > 5 else ("🟡 中风险" if r.performance_decay > 2 else "🟢 低风险")
            print(f"  {i}. {r.strategy_name:<18} 衰减: {r.performance_decay:>+7.2f}%  {risk}")
        
        # 真正有效的策略（测试收益>0 且 衰减<5%）
        print("\n" + "=" * 110)
        print("✅ 推荐关注策略（测试盈利 + 低衰减）")
        print("=" * 110)
        
        good_strategies = [r for r in results if r.total_return > 0 and r.performance_decay < 5]
        if good_strategies:
            for i, r in enumerate(sorted(good_strategies, key=lambda x: x.total_return, reverse=True), 1):
                print(f"  {i}. {r.strategy_name:<18} 测试收益: {r.total_return:>+7.2f}%  衰减: {r.performance_decay:>+6.2f}%  窗口胜率: {r.win_rate:>6.2f}%")
        else:
            print("  ❌ 没有找到同时满足条件的策略，需谨慎！")
        
        print("=" * 110)


# =============================================================================
# 快速测试
# =============================================================================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '/workspace')
    from core.real_data import RealGoldETFData
    from datetime import datetime
    
    print("=" * 110)
    print("🔬 滚动回测验证系统 - 检测策略是否过拟合")
    print("=" * 110)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 获取数据
    days = 250
    print(f"📊 正在获取 518880 历史K线数据 ({days}天)...")
    data = RealGoldETFData('518880', 'sh')
    df = data.fetch_history(days=days)
    
    if df is None:
        print("\n❌ 无法获取真实数据")
        exit(1)
    
    print(f"\n✅ 数据获取成功")
    print(f"数据源: {data.data_source}")
    print(f"数据条数: {len(df)} 条")
    print()
    
    # 滚动回测
    print("🚀 开始滚动回测...")
    tester = WalkForwardTester(
        train_days=80,
        test_days=20,
        step_days=20,
        initial_capital=100000
    )
    
    results = tester.test_all_strategies(df, is_real_data=data.is_real_data)
    
    tester.print_results(results)
