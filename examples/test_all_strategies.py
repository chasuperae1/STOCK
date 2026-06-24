#!/usr/bin/env python3
"""
测试所有策略 - 使用真实历史数据
"""
import sys
sys.path.insert(0, '/workspace')

from core.real_data import RealGoldETFData
from core.backtest_engine import BacktestEngine
from datetime import datetime


def main():
    print("=" * 100)
    print("📊 黄金ETF(518880)全策略回测对比")
    print("=" * 100)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 获取250天真实历史数据
    days = 250
    print(f"📊 正在获取 518880 历史K线数据 ({days}天)...")
    data = RealGoldETFData('518880', 'sh')
    df = data.fetch_history(days=days)
    
    if df is None:
        print("\n❌ 无法获取真实数据，回测终止")
        return
    
    print(f"\n✅ 数据获取成功")
    print(f"数据源: {data.data_source}")
    print(f"数据条数: {len(df)} 条")
    print(f"数据区间: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}")
    print()
    
    # 计算基础收益（买入持有）
    start_price = df['close'].iloc[0]
    end_price = df['close'].iloc[-1]
    buy_hold_return = (end_price / start_price - 1) * 100
    print(f"📈 买入持有收益: {buy_hold_return:+.2f}%")
    print()
    
    # 运行所有策略
    print("🚀 开始回测所有策略...")
    engine = BacktestEngine(initial_capital=100000)
    engine.is_real_data = data.is_real_data
    engine.data_source = data.data_source
    
    results = engine.run_all_strategies(df)
    
    # 打印结果
    engine.print_results(results)
    
    # 策略排名（按总收益）
    print("\n" + "=" * 100)
    print("🏆 策略收益排名")
    print("=" * 100)
    
    sorted_by_return = sorted(results, key=lambda x: x.total_return, reverse=True)
    for i, r in enumerate(sorted_by_return, 1):
        medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "  "))
        print(f"{medal} {i:2d}. {r.strategy_name:<18} 收益: {r.total_return:>+8.2f}%  夏普: {r.sharpe_ratio:>6.2f}  胜率: {r.win_rate:>6.2f}%")
    
    # 策略排名（按夏普比率）
    print("\n" + "=" * 100)
    print("📈 策略夏普比率排名")
    print("=" * 100)
    
    sorted_by_sharpe = sorted(results, key=lambda x: x.sharpe_ratio, reverse=True)
    for i, r in enumerate(sorted_by_sharpe, 1):
        medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "  "))
        print(f"{medal} {i:2d}. {r.strategy_name:<18} 夏普: {r.sharpe_ratio:>8.2f}  收益: {r.total_return:>+7.2f}%  最大回撤: {r.max_drawdown:>6.2f}%")
    
    # 对比买入持有
    print("\n" + "=" * 100)
    print("📊 策略 vs 买入持有")
    print("=" * 100)
    
    beat_count = sum(1 for r in results if r.total_return > buy_hold_return)
    print(f"买入持有收益: {buy_hold_return:+.2f}%")
    print(f"跑赢买入持有的策略数: {beat_count}/{len(results)} ({beat_count/len(results)*100:.1f}%)")
    print()
    
    print("跑赢的策略:")
    for r in sorted_by_return:
        if r.total_return > buy_hold_return:
            diff = r.total_return - buy_hold_return
            print(f"  ✅ {r.strategy_name:<18} {r.total_return:>+7.2f}% (超额{diff:+.2f}%)")
    
    print("\n" + "=" * 100)


if __name__ == "__main__":
    main()
