import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from core.data import GoldData
from core.strategy import TrendFollowingStrategy, Signal
from core.backtest import BackTester
from core.event import EventEngine


def generate_sample_data(days=1000):
    """生成模拟黄金价格数据"""
    dates = pd.date_range(start='2020-01-01', periods=days, freq='D')
    
    np.random.seed(42)
    returns = np.random.normal(0.0002, 0.01, days)
    
    price = 1500
    prices = []
    for r in returns:
        price *= (1 + r)
        prices.append(price)
    
    data = pd.DataFrame({
        'open': prices,
        'high': [p * (1 + np.random.uniform(0, 0.01)) for p in prices],
        'low': [p * (1 - np.random.uniform(0, 0.01)) for p in prices],
        'close': prices,
        'volume': [np.random.randint(1000, 5000) for _ in range(days)]
    }, index=dates)
    
    return data


def main():
    print("黄金量化工具包 - 快速入门")
    print("-" * 50)
    
    print("\n1️⃣ 生成模拟数据")
    gold_data = generate_sample_data(1000)
    print(f"数据范围: {gold_data.index[0].strftime('%Y-%m-%d')} 至 {gold_data.index[-1].strftime('%Y-%m-%d')}")
    print(f"数据条数: {len(gold_data)}")
    print(f"价格范围: ${gold_data['close'].min():.2f} - ${gold_data['close'].max():.2f}")
    
    print("\n2️⃣ 创建策略")
    event_engine = EventEngine()
    strategy = TrendFollowingStrategy(event_engine)
    print(f"策略名称: {strategy.name}")
    print(f"策略参数: {strategy._params}")
    
    print("\n3️⃣ 运行回测")
    backtester = BackTester(initial_capital=100000.0, transaction_cost=0.001)
    result = backtester.run_backtest(strategy, gold_data)
    
    print("\n4️⃣ 回测结果")
    stats = result.stats
    print(f"""
📊 回测统计:
├── 总交易次数: {stats['total_trades']}
├── 盈利交易: {stats['winning_trades']}
├── 亏损交易: {stats['losing_trades']}
├── 胜率: {stats['win_rate']:.2%}
├── 总收益率: {stats['total_return']:.2%}
├── 最大回撤: {stats['max_drawdown']:.2%}
├── 夏普比率: {stats['sharpe_ratio']:.2f}
└── 盈利因子: {stats['profit_factor']:.2f}

💰 资金变化:
├── 初始资金: $100,000.00
└── 最终权益: ${result.equity_curve['equity'].iloc[-1]:.2f}
    """)
    
    print("\n5️⃣ 使用数据模块计算指标")
    data_provider = GoldData()
    data_with_indicators = data_provider.calculate_indicators(gold_data)
    print(f"计算的指标: {[col for col in data_with_indicators.columns if col not in ['open', 'high', 'low', 'close', 'volume']]}")
    
    print("\n✅ 工具包使用演示完成!")


if __name__ == "__main__":
    main()