#!/usr/bin/env python3
"""
2年周期完整回测分析报告
======================

使用过去2年（约500个交易日）的真实历史数据
进行完整的策略回测和滚动回测分析
"""

import sys
sys.path.insert(0, '/workspace')

from core.real_data import RealGoldETFData
from core.backtest_engine import BacktestEngine
from core.walk_forward import WalkForwardTester
from datetime import datetime


def main():
    print("=" * 120)
    print("📊 黄金ETF(518880) 2年策略回测分析报告")
    print("=" * 120)
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 获取500天数据（约2年）
    days = 500
    print(f"📊 正在获取 {days} 天历史数据...")
    data = RealGoldETFData('518880', 'sh')
    df = data.fetch_history(days=days)
    
    if df is None:
        print("\n❌ 无法获取真实数据")
        return
    
    print(f"\n✅ 数据获取成功")
    print(f"  数据源: {data.data_source}")
    print(f"  数据条数: {len(df)} 条")
    print(f"  起始日期: {df['date'].iloc[0]}")
    print(f"  结束日期: {df['date'].iloc[-1]}")
    
    # 基础收益
    start_price = df['close'].iloc[0]
    end_price = df['close'].iloc[-1]
    buy_hold_return = (end_price / start_price - 1) * 100
    print(f"  起始价格: ¥{start_price:.3f}")
    print(f"  结束价格: ¥{end_price:.3f}")
    print(f"  买入持有收益: {buy_hold_return:+.2f}%")
    
    # 分段看行情
    mid_idx = len(df) // 2
    first_half_return = (df['close'].iloc[mid_idx] / df['close'].iloc[0] - 1) * 100
    second_half_return = (df['close'].iloc[-1] / df['close'].iloc[mid_idx] - 1) * 100
    print(f"  前半段收益: {first_half_return:+.2f}% ({df['date'].iloc[0]} ~ {df['date'].iloc[mid_idx]})")
    print(f"  后半段收益: {second_half_return:+.2f}% ({df['date'].iloc[mid_idx]} ~ {df['date'].iloc[-1]})")
    print()
    
    # =========================================================================
    # 第一部分：普通回测（全样本内）
    # =========================================================================
    print("=" * 120)
    print("📊 第一部分：普通回测（全样本内）")
    print("=" * 120)
    
    engine = BacktestEngine(initial_capital=100000)
    engine.is_real_data = data.is_real_data
    engine.data_source = data.data_source
    
    normal_results = engine.run_all_strategies(df)
    normal_dict = {r.strategy_name: r.total_return for r in normal_results}
    
    engine.print_results(normal_results)
    
    # =========================================================================
    # 第二部分：滚动回测
    # =========================================================================
    print("\n" + "=" * 120)
    print("🔬 第二部分：滚动回测（训练120天 + 测试30天，步长30天）")
    print("=" * 120)
    print("💡 数据量更大，滚动窗口更多，结果更可靠")
    print()
    
    tester = WalkForwardTester(
        train_days=120,
        test_days=30,
        step_days=30,
        initial_capital=100000
    )
    
    wf_results = tester.test_all_strategies(df, is_real_data=data.is_real_data)
    
    tester.print_results(wf_results)
    
    # =========================================================================
    # 第三部分：策略选择测试
    # =========================================================================
    print("\n" + "=" * 120)
    print("🎯 第三部分：策略选择测试（模拟真实场景）")
    print("=" * 120)
    
    for top_n in [1, 2, 3]:
        result = tester.strategy_selection_test(df, is_real_data=data.is_real_data, top_n=top_n)
        
        print(f"\n--- 选前{top_n}名策略 ---")
        print(f"  测试总收益: {result['total_return']:+.2f}%")
        print(f"  买入持有:   {result['buy_hold_return']:+.2f}%")
        print(f"  超额收益:   {result['excess_return']:+.2f}%")
        print(f"  窗口胜率:   {result['win_rate']:.2f}%")
        print(f"  测试窗口数: {result['num_windows']}")
    
    # =========================================================================
    # 第四部分：过拟合对比
    # =========================================================================
    print("\n" + "=" * 120)
    print("⚠️  第四部分：过拟合对比（普通回测 vs 滚动回测）")
    print("=" * 120)
    
    print(f"\n{'策略名称':<18} {'普通回测':>10} {'滚动回测':>10} {'收益差':>10} {'过拟合风险':>12}")
    print("-" * 70)
    
    decay_list = []
    for r in wf_results:
        normal_ret = normal_dict.get(r.strategy_name, 0)
        decay = normal_ret - r.total_return
        risk = "🔴 严重" if decay > 10 else ("🟡 中等" if decay > 5 else "🟢 轻微")
        decay_list.append((r.strategy_name, normal_ret, r.total_return, decay, risk))
        print(f"{r.strategy_name:<18} {normal_ret:>+9.2f}% {r.total_return:>+9.2f}% {decay:>+9.2f}% {risk:>12}")
    
    # =========================================================================
    # 第五部分：按年度分段回测
    # =========================================================================
    print("\n" + "=" * 120)
    print("📅 第五部分：分年度策略表现（看策略在不同行情下的适应性）")
    print("=" * 120)
    
    # 按年份分段
    df['year'] = df['date'].str[:4]
    years = sorted(df['year'].unique())
    
    print(f"\n{'策略名称':<18}", end="")
    for y in years:
        print(f" {y}年({y[-2:]}):>10", end="")
    print(f" {'2年综合':>10}")
    print("-" * (20 + len(years) * 12 + 12))
    
    # 选几个代表性策略
    key_strategies = [
        '均线交叉(5/20)',
        'MACD金叉死叉',
        'RSI(30/70)',
        '海龟交易(20/10)',
        '动量策略(20日)',
        '多因子综合',
        '布林带策略',
        'KDJ金叉死叉',
    ]
    
    for strat_name in key_strategies:
        print(f"{strat_name:<18}", end="")
        for year in years:
            year_df = df[df['year'] == year].reset_index(drop=True)
            if len(year_df) < 30:
                print(f" {'N/A':>9}", end="")
                continue
            
            # 跑这个策略
            func = tester._get_strategy_func(engine, strat_name)
            if func is None:
                print(f" {'N/A':>9}", end="")
                continue
            
            try:
                result = func(year_df)
                print(f" {result.total_return:>+9.2f}%", end="")
            except Exception:
                print(f" {'ERR':>9}", end="")
        
        # 2年综合
        normal_ret = normal_dict.get(strat_name, 0)
        print(f" {normal_ret:>+9.2f}%")
    
    # 买入持有
    print(f"{'买入持有':<18}", end="")
    for year in years:
        year_df = df[df['year'] == year].reset_index(drop=True)
        if len(year_df) < 30:
            print(f" {'N/A':>9}", end="")
            continue
        yr_return = (year_df['close'].iloc[-1] / year_df['close'].iloc[0] - 1) * 100
        print(f" {yr_return:>+9.2f}%", end="")
    print(f" {buy_hold_return:>+9.2f}%")
    
    # =========================================================================
    # 第六部分：最终结论
    # =========================================================================
    print("\n" + "=" * 120)
    print("📝 第六部分：最终结论与建议")
    print("=" * 120)
    
    # 找出滚动回测中表现最好的
    wf_sorted = sorted(wf_results, key=lambda x: x.total_return, reverse=True)
    
    print(f"\n🏆 滚动回测收益TOP3:")
    for i, r in enumerate(wf_sorted[:3], 1):
        print(f"  {i}. {r.strategy_name}")
        print(f"     滚动收益: {r.total_return:+.2f}% | 窗口胜率: {r.win_rate:.2f}% | 性能衰减: {r.performance_decay:+.2f}%")
    
    # 找出低衰减且正收益的
    good_strategies = [r for r in wf_results if r.total_return > 0 and r.performance_decay < 5]
    print(f"\n✅ 相对可靠策略（正收益 + 低衰减）:")
    if good_strategies:
        for i, r in enumerate(sorted(good_strategies, key=lambda x: x.total_return, reverse=True), 1):
            print(f"  {i}. {r.strategy_name}")
            print(f"     滚动收益: {r.total_return:+.2f}% | 衰减: {r.performance_decay:+.2f}% | 窗口胜率: {r.win_rate:.2f}%")
    else:
        print("  ⚠️  没有找到同时满足条件的策略")
    
    print(f"\n📌 核心发现:")
    print(f"  1. 2年买入持有收益: {buy_hold_return:+.2f}%")
    print(f"  2. 普通回测中排名靠前的策略，在滚动回测中往往排名下降")
    print(f"  3. 不同年份市场环境不同，策略表现差异很大（适应性差）")
    print(f"  4. 单一策略很难在所有行情下都赚钱")
    
    print(f"\n💡 实战建议:")
    print(f"  • 判断大趋势比找技术信号更重要（基本面>技术面）")
    print(f"  • 不要靠单一策略，多策略组合分散风险")
    print(f"  • 严格止损，单笔亏损控制在2%以内")
    print(f"  • 震荡市用均值回归，趋势市用趋势跟踪")
    print(f"  • 定期评估策略有效性，失效了及时调整")
    
    print("\n" + "=" * 120)
    print("⚠️ 风险提示：本分析仅供学习研究，不构成投资建议")
    print("=" * 120)


if __name__ == "__main__":
    main()
