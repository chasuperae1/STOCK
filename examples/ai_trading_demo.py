import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from core.ai_strategy import AIEventDrivenStrategy, GameTheoryStrategy
from core.backtest import BackTester
from core.event import EventEngine


def generate_sample_data(days=500):
    dates = pd.date_range(start='2023-01-01', periods=days, freq='D')
    
    np.random.seed(42)
    base_returns = np.random.normal(0.0002, 0.01, days)
    
    event_days = np.random.choice(range(days), size=20, replace=False)
    for day in event_days:
        if np.random.random() > 0.5:
            base_returns[day] += 0.02
        else:
            base_returns[day] -= 0.02
    
    price = 2000
    prices = []
    for r in base_returns:
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
    print("🤖 AI事件驱动交易策略演示")
    print("=" * 50)
    
    print("\n1️⃣ 生成模拟数据")
    gold_data = generate_sample_data(500)
    print(f"数据范围: {gold_data.index[0].strftime('%Y-%m-%d')} 至 {gold_data.index[-1].strftime('%Y-%m-%d')}")
    print(f"数据条数: {len(gold_data)}")
    
    print("\n2️⃣ 创建AI事件驱动策略")
    event_engine = EventEngine()
    ai_strategy = AIEventDrivenStrategy(event_engine)
    
    print("\n3️⃣ 获取今日分析报告")
    ai_strategy.calculate_signal(gold_data)
    report = ai_strategy.get_analysis_report()
    
    print("\n📊 今日分析报告:")
    print(f"当前金价: ${report['current_price']:.2f}")
    print(f"\n📰 新闻情绪:")
    print(f"  状态: {report['sentiment_summary']['status'].upper()}")
    print(f"  分数: {report['sentiment_summary']['score']:.2f}")
    print(f"  描述: {report['sentiment_summary']['description']}")
    
    print(f"\n📅 今日事件:")
    print(f"  高影响事件: {report['event_summary']['high_impact_count']} 个")
    print(f"  中影响事件: {report['event_summary']['medium_impact_count']} 个")
    for i, event in enumerate(report['event_summary']['events'], 1):
        print(f"  {i}. {event}")
    
    print(f"\n📝 今日新闻 ({report['news_summary']['count']} 条):")
    for i, headline in enumerate(report['news_summary']['headlines'], 1):
        print(f"  {i}. {headline}")
    
    print("\n4️⃣ 运行AI策略回测")
    backtester = BackTester(initial_capital=100000.0, transaction_cost=0.001)
    result = backtester.run_backtest(ai_strategy, gold_data)
    
    print("\n📈 AI策略回测结果:")
    stats = result.stats
    print(f"""
├── 总交易次数: {stats['total_trades']}
├── 盈利交易: {stats['winning_trades']}
├── 亏损交易: {stats['losing_trades']}
├── 胜率: {stats['win_rate']:.2%}
├── 总收益率: {stats['total_return']:.2%}
├── 最大回撤: {stats['max_drawdown']:.2%}
├── 夏普比率: {stats['sharpe_ratio']:.2f}
└── 初始资金: $100,000 → 最终权益: ${result.equity_curve['equity'].iloc[-1]:.2f}
    """)
    
    print("\n5️⃣ 创建博弈论策略")
    game_theory_strategy = GameTheoryStrategy(event_engine)
    result2 = backtester.run_backtest(game_theory_strategy, gold_data)
    
    print("\n🎯 博弈论策略回测结果:")
    stats2 = result2.stats
    print(f"""
├── 总交易次数: {stats2['total_trades']}
├── 盈利交易: {stats2['winning_trades']}
├── 亏损交易: {stats2['losing_trades']}
├── 胜率: {stats2['win_rate']:.2%}
├── 总收益率: {stats2['total_return']:.2%}
├── 最大回撤: {stats2['max_drawdown']:.2%}
├── 夏普比率: {stats2['sharpe_ratio']:.2f}
└── 初始资金: $100,000 → 最终权益: ${result2.equity_curve['equity'].iloc[-1]:.2f}
    """)


if __name__ == "__main__":
    main()