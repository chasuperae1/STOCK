import pandas as pd
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data import GoldData
from core.strategy import TrendFollowingStrategy, MeanReversionStrategy, GridTradingStrategy, MultiFactorStrategy
from core.backtest import BackTester
from core.event import EventEngine


def run_strategy_backtest(strategy_name, strategy_class, data):
    print(f"\n{'='*60}")
    print(f"测试策略: {strategy_name}")
    print(f"{'='*60}")
    
    event_engine = EventEngine()
    strategy = strategy_class(event_engine)
    
    backtester = BackTester(initial_capital=100000.0, transaction_cost=0.001)
    result = backtester.run_backtest(strategy, data)
    
    print("\n回测统计:")
    stats = result.stats
    print(f"总交易次数: {stats['total_trades']}")
    print(f"盈利交易: {stats['winning_trades']}")
    print(f"亏损交易: {stats['losing_trades']}")
    print(f"胜率: {stats['win_rate']:.2%}")
    print(f"总盈亏: ${stats['total_pnl']:.2f}")
    print(f"平均盈利: ${stats['avg_win']:.2f}")
    print(f"平均亏损: ${stats['avg_loss']:.2f}")
    print(f"盈利因子: {stats['profit_factor']:.2f}")
    print(f"总收益率: {stats['total_return']:.2%}")
    print(f"最大回撤: {stats['max_drawdown']:.2%}")
    print(f"夏普比率: {stats['sharpe_ratio']:.2f}")
    
    print(f"\n初始资金: $100,000.00")
    print(f"最终权益: ${result.equity_curve['equity'].iloc[-1]:.2f}")
    
    return stats


def main():
    print("黄金量化交易策略回测演示")
    print("-" * 60)
    
    data_provider = GoldData()
    print("正在获取黄金数据...")
    gold_data = data_provider.fetch_gold_data("gold", start_date="2020-01-01", end_date="2024-01-01")
    
    print(f"数据获取完成，共 {len(gold_data)} 条记录")
    print(f"数据时间范围: {gold_data.index[0].strftime('%Y-%m-%d')} 至 {gold_data.index[-1].strftime('%Y-%m-%d')}")
    
    strategies = [
        ("趋势跟踪策略", TrendFollowingStrategy),
        ("均值回归策略", MeanReversionStrategy),
        ("网格交易策略", GridTradingStrategy),
        ("多因子策略", MultiFactorStrategy)
    ]
    
    results = []
    for name, strategy_class in strategies:
        stats = run_strategy_backtest(name, strategy_class, gold_data)
        results.append({
            'strategy': name,
            'total_return': stats['total_return'],
            'max_drawdown': stats['max_drawdown'],
            'sharpe_ratio': stats['sharpe_ratio'],
            'win_rate': stats['win_rate']
        })
    
    print("\n" + "="*60)
    print("策略对比结果")
    print("="*60)
    results_df = pd.DataFrame(results)
    results_df['total_return'] = results_df['total_return'].apply(lambda x: f"{x:.2%}")
    results_df['max_drawdown'] = results_df['max_drawdown'].apply(lambda x: f"{x:.2%}")
    results_df['sharpe_ratio'] = results_df['sharpe_ratio'].apply(lambda x: f"{x:.2f}")
    results_df['win_rate'] = results_df['win_rate'].apply(lambda x: f"{x:.2%}")
    
    print(results_df.to_string(index=False))


if __name__ == "__main__":
    main()