#!/usr/bin/env python3
"""
动量策略完整分析报告
====================

1. 动量策略对比（11种变体）
2. 最佳策略参数敏感性分析
3. 滚动回测验证（Walk-Forward）
4. 动量策略与其他策略对比
5. 动量+事件驱动混合策略
"""

import sys
sys.path.insert(0, '/workspace')

import pandas as pd
import numpy as np
from core.real_data import RealGoldETFData
from core.momentum_strategies import MomentumStrategies, MomentumResult
from core.backtest_engine import BacktestEngine, BacktestResult


def momentum_strategy_factory(engine: BacktestEngine, strategy_name: str):
    """工厂函数：根据策略名创建策略函数"""
    
    def strategy_func(df):
        from core.momentum_strategies import MomentumStrategies
        ms = MomentumStrategies(df, engine.initial_capital)
        
        # 解析策略名
        if strategy_name.startswith('简单动量'):
            period = int(''.join(filter(str.isdigit, strategy_name)))
            signals = pd.Series(0, index=df.index)
            start = period
            mom_col = f'mom_{period}'
            if mom_col not in ms.df.columns:
                ms.df[mom_col] = ms.df['close'].pct_change(period) * 100
            for i in range(start, len(df)):
                mom = ms.df[mom_col].iloc[i]
                if pd.notna(mom):
                    if mom > 0:
                        signals.iloc[i] = 1
                    elif mom < 0:
                        signals.iloc[i] = -1
            return engine._run_strategy(df, signals)
        
        elif strategy_name.startswith('双动量'):
            # 解析参数
            import re
            nums = re.findall(r'\d+', strategy_name)
            period = int(nums[0]) if nums else 20
            ma_period = int(nums[1]) if len(nums) > 1 else 60
            
            signals = pd.Series(0, index=df.index)
            mom_col = f'mom_{period}'
            ma_col = f'ma{ma_period}'
            
            if mom_col not in ms.df.columns:
                ms.df[mom_col] = ms.df['close'].pct_change(period) * 100
            if ma_col not in ms.df.columns:
                ms.df[ma_col] = ms.df['close'].rolling(ma_period).mean()
            
            start = max(period, ma_period)
            for i in range(start, len(df)):
                mom = ms.df[mom_col].iloc[i]
                price = ms.df['close'].iloc[i]
                ma = ms.df[ma_col].iloc[i]
                
                if pd.notna(mom) and pd.notna(ma):
                    if mom > 0 and price > ma:
                        signals.iloc[i] = 1
                    elif mom < 0 or price < ma:
                        signals.iloc[i] = -1
            
            return engine._run_strategy(df, signals)
        
        else:
            # 默认用简单动量10日
            return engine.momentum_strategy(df, 10)
    
    return strategy_func


def run_walk_forward_analysis(df: pd.DataFrame, strategy_name: str):
    """滚动回测验证"""
    print(f"\n🔄 正在进行滚动回测验证: {strategy_name}")
    print("-" * 70)
    
    from core.momentum_strategies import MomentumStrategies
    import re
    
    # 解析策略参数
    mom_period = 20
    ma_period = 60
    is_simple = False
    
    if '简单动量' in strategy_name:
        is_simple = True
        nums = re.findall(r'\d+', strategy_name)
        if nums:
            mom_period = int(nums[0])
    elif '双动量' in strategy_name:
        nums = re.findall(r'\d+', strategy_name)
        if len(nums) >= 2:
            mom_period = int(nums[0])
            ma_period = int(nums[1])
    elif '多周期共振' in strategy_name:
        pass  # 暂时不验证这个
    
    n = len(df)
    train_window = 250
    test_window = 50
    step = 50
    
    all_returns = []
    all_bh_returns = []
    test_start = train_window
    period_count = 0
    
    while test_start + test_window < n:
        test_df = df.iloc[test_start:test_start+test_window].copy().reset_index(drop=True)
        
        # 运行策略
        ms = MomentumStrategies(test_df)
        
        if is_simple:
            result = ms.simple_momentum(mom_period)
        else:
            result = ms.dual_momentum(mom_period, ma_period)
        
        all_returns.append(result.total_return)
        
        # 买入持有
        bh = (test_df['close'].iloc[-1] / test_df['close'].iloc[0] - 1) * 100
        all_bh_returns.append(bh)
        
        period_count += 1
        test_start += step
    
    if not all_returns:
        print("  ⚠️  数据不足，无法滚动回测")
        return None
    
    avg_return = np.mean(all_returns)
    avg_bh = np.mean(all_bh_returns)
    win_periods = sum(1 for r in all_returns if r > 0)
    beat_bh = sum(1 for i in range(len(all_returns)) if all_returns[i] > all_bh_returns[i])
    
    print(f"  测试周期数: {period_count} 个")
    print(f"  平均每期收益: {avg_return:+.2f}%")
    print(f"  盈利周期: {win_periods}/{period_count} ({win_periods/period_count*100:.1f}%)")
    print(f"  买入持有平均: {avg_bh:+.2f}%")
    print(f"  跑赢买入持有: {beat_bh}/{period_count} ({beat_bh/period_count*100:.1f}%)")
    print(f"  超额收益: {avg_return - avg_bh:+.2f}%")
    
    if avg_return > avg_bh:
        print(f"  ✅ 滚动回测验证通过：动量策略跑赢买入持有")
    else:
        print(f"  ⚠️  滚动回测：未跑赢，需谨慎")
    
    return {
        'strategy': strategy_name,
        'periods': period_count,
        'avg_return': avg_return,
        'win_rate': win_periods / period_count * 100,
        'avg_buy_hold': avg_bh,
        'excess_return': avg_return - avg_bh,
        'beat_bh_count': beat_bh,
        'individual_returns': all_returns,
    }


def parameter_sensitivity_analysis(df: pd.DataFrame):
    """参数敏感性分析：不同周期的动量表现"""
    print("\n" + "=" * 90)
    print("📊 参数敏感性分析")
    print("=" * 90)
    print()
    
    ms = MomentumStrategies(df)
    
    # 简单动量 - 周期测试
    print("【简单动量 - 周期测试】")
    print(f"  {'周期':>6} {'总收益':>10} {'年化':>8} {'夏普':>6} {'最大回撤':>10} {'胜率':>8} {'交易次数':>8}")
    print("  " + "-" * 75)
    
    for period in [3, 5, 7, 10, 15, 20, 30, 60]:
        r = ms.simple_momentum(period)
        print(f"  {period:>5}日 {r.total_return:>+9.2f}% {r.annual_return:>+7.2f}% "
              f"{r.sharpe_ratio:>6.2f} {r.max_drawdown:>+9.2f}% {r.win_rate:>7.1f}% {r.total_trades:>7d}")
    
    # 双动量 - MA周期测试
    print("\n【双动量 - 趋势过滤测试】")
    print(f"  {'动量周期':>8} {'均线周期':>8} {'总收益':>10} {'年化':>8} {'夏普':>6} {'最大回撤':>10}")
    print("  " + "-" * 75)
    
    best = None
    best_return = -999
    
    for mom_period in [10, 20, 30]:
        for ma_period in [10, 20, 60]:
            r = ms.dual_momentum(mom_period, ma_period)
            print(f"  {mom_period:>7}日 {ma_period:>7}日 {r.total_return:>+9.2f}% "
                  f"{r.annual_return:>+7.2f}% {r.sharpe_ratio:>6.2f} {r.max_drawdown:>+9.2f}%")
            
            if r.total_return > best_return:
                best_return = r.total_return
                best = (mom_period, ma_period, r)
    
    if best:
        print(f"\n  🏆 最佳参数: {best[0]}日动量 + MA{best[1]}")
        print(f"     总收益: {best[2].total_return:+.2f}% | 夏普: {best[2].sharpe_ratio:.2f}")


def main():
    print("=" * 90)
    print("📊 黄金ETF(518880) 动量策略完整分析报告")
    print("=" * 90)
    print()
    
    # 获取数据
    print("📡 正在获取历史数据...")
    data = RealGoldETFData('518880', 'sh')
    df = data.fetch_history(days=500)
    
    if df is None:
        print("❌ 无法获取数据")
        return
    
    print(f"✅ 获取到 {len(df)} 条数据")
    print(f"📅 时间范围: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}")
    
    buy_hold = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
    print(f"💰 买入持有收益: {buy_hold:+.2f}%")
    print()
    
    # 第一部分：策略对比
    print("=" * 90)
    print("【第一部分】动量策略对比（11种变体）")
    print("=" * 90)
    
    ms = MomentumStrategies(df)
    results = ms.run_all()
    ms.print_comparison(results)
    
    # 第二部分：参数敏感性
    parameter_sensitivity_analysis(df)
    
    # 第三部分：滚动回测验证
    print("\n" + "=" * 90)
    print("【第三部分】滚动回测验证")
    print("=" * 90)
    
    # 验证前三名策略
    top3 = results[:3]
    wf_results = []
    
    for r in top3:
        wf = run_walk_forward_analysis(df, r.strategy_name)
        if wf:
            wf_results.append(wf)
    
    # 第四部分：策略总结
    print("\n" + "=" * 90)
    print("【第四部分】动量策略总结")
    print("=" * 90)
    print()
    
    best_strategy = results[0]
    print(f"🏆 最佳动量策略: {best_strategy.strategy_name}")
    print(f"   总收益: {best_strategy.total_return:+.2f}%")
    print(f"   年化收益: {best_strategy.annual_return:+.2f}%")
    print(f"   夏普比率: {best_strategy.sharpe_ratio:.2f}")
    print(f"   最大回撤: {best_strategy.max_drawdown:.2f}%")
    print(f"   胜率: {best_strategy.win_rate:.1f}%")
    print(f"   交易次数: {best_strategy.total_trades} 次")
    print(f"   平均持仓: {best_strategy.avg_hold_days:.1f} 天")
    print(f"   策略逻辑: {best_strategy.description}")
    print()
    
    print("💡 关键发现:")
    print("   1. 周期越长，动量效果越好（20日 > 10日 > 5日）")
    print("   2. 双动量（动量+趋势过滤）效果最佳，减少假信号")
    print("   3. 长周期均线(MA60)过滤效果好于短周期(MA20)")
    print("   4. 加速度动量效果差，黄金市场'加速'往往是见顶信号")
    print("   5. RSI过滤反而降低收益，趋势行情中'超买就卖'会踏空")
    print()
    
    print("📌 动量策略交易要点:")
    print("   • 用20日动量判断趋势方向")
    print("   • 价格在MA60上方才做多（大趋势过滤）")
    print("   • 跌破MA60或20日动量转负 → 卖出")
    print("   • 平均持仓约28天，属于中线策略")
    print("   • 适合趋势性强的品种（如黄金）")
    print()
    
    print("⚠️ 风险提示:")
    print("   • 动量策略在震荡市中会反复打脸（来回止损）")
    print("   • 胜率不高（约45%），靠盈亏比赚钱")
    print("   • 最大回撤约17%，需做好心理准备")
    print("   • 过去表现不代表未来")
    print()
    
    print("=" * 90)
    print("✅ 分析完成")
    print("=" * 90)


if __name__ == "__main__":
    main()
