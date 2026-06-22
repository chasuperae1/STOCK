import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from core.ai_api import EventAnalyzer
from core.ai_strategy import AIEventDrivenStrategy, GameTheoryStrategy
from core.data import GoldData
from core.event import EventEngine
from core.backtest import BackTester


def get_tomorrow_trading_plan():
    print("=" * 60)
    print("📅 明日（明天）黄金交易研究分析")
    print("=" * 60)
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n" + "=" * 60)
    print("【第一步】基本面分析")
    print("=" * 60)
    
    analyzer = EventAnalyzer()
    analysis = analyzer.analyze_todays_events()
    
    print(f"\n💰 当前金价: ${analysis['current_price']:.2f}")
    
    print(f"\n📰 新闻情绪分析:")
    print(f"  情绪分数: {analysis['avg_sentiment']:.2f}")
    sentiment_status = "看多" if analysis['avg_sentiment'] > 0.2 else "看空" if analysis['avg_sentiment'] < -0.2 else "中性"
    print(f"  情绪状态: {sentiment_status}")
    
    print(f"\n📅 经济日历事件:")
    high_events = analysis['high_impact_events']
    medium_events = analysis['medium_impact_events']
    
    print(f"  高影响事件: {len(high_events)} 个")
    for event in high_events:
        print(f"    ⚠️  {event['title']} - {event['time']}")
        print(f"       预期: {event['forecast']} | 前值: {event['previous']}")
    
    print(f"  中影响事件: {len(medium_events)} 个")
    for event in medium_events:
        print(f"    • {event['title']} - {event['time']}")
    
    print(f"\n📝 重要新闻:")
    for i, article in enumerate(analysis['news_details'][:5], 1):
        print(f"  {i}. {article['title']}")
    
    print("\n" + "=" * 60)
    print("【第二步】技术面分析")
    print("=" * 60)
    
    print("\n正在获取历史数据进行分析...")
    data_provider = GoldData()
    
    try:
        gold_data = data_provider.fetch_gold_data("gold", start_date="2024-01-01")
        
        if len(gold_data) > 0:
            print(f"  ✅ 数据获取成功: {len(gold_data)} 条记录")
            
            data_with_indicators = data_provider.calculate_indicators(gold_data)
            latest = data_with_indicators.iloc[-1]
            prev = data_with_indicators.iloc[-2]
            
            print(f"\n📊 当前技术指标:")
            print(f"  收盘价: ${latest['close']:.2f}")
            print(f"  MA20: ${latest['ma20']:.2f} (趋势: {'上升' if latest['ma20'] > prev['ma20'] else '下降'})")
            print(f"  MA60: ${latest['ma60']:.2f}")
            print(f"  MA200: ${latest['ma200']:.2f}")
            print(f"  RSI(14): {latest['rsi']:.2f} ({'超买' if latest['rsi'] > 70 else '超卖' if latest['rsi'] < 30 else '中性'})")
            print(f"  MACD: {latest['macd']:.2f}")
            print(f"  信号线: {latest['signal']:.2f}")
            print(f"  MACD柱: {latest['hist']:.2f}")
            print(f"  ATR(14): ${latest['atr']:.2f} (波动率)")
            
            print(f"\n📈 价格区间:")
            print(f"  布林带上轨: ${latest['bb_upper']:.2f}")
            print(f"  布林带中轨: ${latest['bb_middle']:.2f}")
            print(f"  布林带下轨: ${latest['bb_lower']:.2f}")
            
            print(f"\n📊 近期表现:")
            for days in [5, 10, 20]:
                if len(gold_data) > days:
                    change = (gold_data['close'].iloc[-1] / gold_data['close'].iloc[-days-1] - 1) * 100
                    print(f"  {days}日涨跌幅: {change:+.2f}%")
        else:
            print("  ⚠️ 数据获取失败，使用模拟数据进行技术分析")
            gold_data = generate_mock_data()
            gold_data = data_provider.calculate_indicators(gold_data)
            latest = gold_data.iloc[-1]
            print(f"  模拟数据收盘价: ${latest['close']:.2f}")
            print(f"  MA20: ${latest['ma20']:.2f}")
            print(f"  MA60: ${latest['ma60']:.2f}")
            print(f"  RSI(14): {latest['rsi']:.2f}")
    except Exception as e:
        print(f"  ⚠️ 数据获取错误: {e}")
        print("  使用模拟数据进行分析")
    
    print("\n" + "=" * 60)
    print("【第三步】博弈论分析")
    print("=" * 60)
    
    print("\n🎯 市场情绪博弈分析:")
    
    sentiment_score = analysis['avg_sentiment']
    event_count = len(high_events)
    
    print(f"\n  羊群效应检测:")
    if event_count >= 2:
        print(f"    ⚠️  今日有{event_count}个高影响事件，市场可能出现跟风行为")
        print(f"    建议: 警惕短期波动，等待方向明确")
    else:
        print(f"    ✅ 市场情绪相对稳定")
    
    print(f"\n  逆向机会分析:")
    if abs(sentiment_score) > 0.3:
        print(f"    ⚠️  市场情绪极端（分数: {sentiment_score:.2f}）")
        print(f"    建议: 考虑逆向操作的可能性")
    else:
        print(f"    ✅ 市场情绪适中（分数: {sentiment_score:.2f}）")
        print(f"    建议: 跟随主流趋势")
    
    print("\n" + "=" * 60)
    print("【第四步】综合交易建议")
    print("=" * 60)
    
    print("\n🎯 AI综合评分:")
    
    scores = {
        'sentiment': sentiment_score,
        'event_impact': min(event_count * 0.3, 1.0),
        'technical': 0.0
    }
    
    if len(gold_data) > 60:
        ma_score = 0.3 if latest['ma20'] > latest['ma60'] else -0.3
        rsi_score = 0.4 if latest['rsi'] < 30 else -0.4 if latest['rsi'] > 70 else 0
        scores['technical'] = ma_score + rsi_score
    
    total_score = (
        scores['sentiment'] * 0.4 +
        scores['event_impact'] * 0.2 +
        scores['technical'] * 0.4
    )
    
    print(f"  新闻情绪: {scores['sentiment']:.2f} (权重40%)")
    print(f"  事件影响: {scores['event_impact']:.2f} (权重20%)")
    print(f"  技术面:   {scores['technical']:.2f} (权重40%)")
    print(f"  ─────────────────")
    print(f"  综合评分: {total_score:.2f}")
    
    print(f"\n📋 明日交易策略:")
    
    if total_score > 0.3:
        print("  ┌─────────────────────────────────────┐")
        print("  │ 🟢 建议: 买入/做多                    │")
        print("  │                                       │")
        print(f"  │ 理由: 综合评分为正({total_score:.2f})   │")
        print("  │                                       │")
        if len(gold_data) > 60:
            entry = latest['close']
            target1 = entry * 1.01
            target2 = entry * 1.02
            stop_loss = entry * 0.99
            print(f"  │ 入场价: ${entry:.2f}                  │")
            print(f"  │ 目标1:  ${target1:.2f} (+1%)          │")
            print(f"  │ 目标2:  ${target2:.2f} (+2%)          │")
            print(f"  │ 止损:   ${stop_loss:.2f} (-1%)         │")
        print("  └─────────────────────────────────────┘")
    elif total_score < -0.3:
        print("  ┌─────────────────────────────────────┐")
        print("  │ 🔴 建议: 卖出/做空                    │")
        print("  │                                       │")
        print(f"  │ 理由: 综合评分为负({total_score:.2f})   │")
        print("  │                                       │")
        if len(gold_data) > 60:
            entry = latest['close']
            target1 = entry * 0.99
            target2 = entry * 0.98
            stop_loss = entry * 1.01
            print(f"  │ 入场价: ${entry:.2f}                  │")
            print(f"  │ 目标1:  ${target1:.2f} (-1%)          │")
            print(f"  │ 目标2:  ${target2:.2f} (-2%)          │")
            print(f"  │ 止损:   ${stop_loss:.2f} (+1%)         │")
        print("  └─────────────────────────────────────┘")
    else:
        print("  ┌─────────────────────────────────────┐")
        print("  │ ⚡ 建议: 观望/轻仓                   │")
        print("  │                                       │")
        print(f"  │ 理由: 综合评分中性({total_score:.2f})   │")
        print("  │                                       │")
        print("  │ 策略: 等待明确信号，规避高影响事件    │")
        print("  └─────────────────────────────────────┘")
    
    print(f"\n⚠️  风险提示:")
    print(f"  • 黄金市场波动较大，请严格控制仓位")
    print(f"  • 今日有{event_count}个高影响事件，建议关注实时消息")
    print(f"  • 建议止损不超过总资金的2%")
    print(f"  • 本分析仅供参考，不构成投资建议")
    
    print("\n" + "=" * 60)
    print("📊 报告生成完成")
    print("=" * 60)


def generate_mock_data():
    dates = pd.date_range(start='2024-01-01', periods=200, freq='D')
    np.random.seed(42)
    price = 2000
    prices = []
    for _ in range(200):
        price *= (1 + np.random.normal(0.0002, 0.01))
        prices.append(price)
    return pd.DataFrame({
        'open': prices,
        'high': [p * 1.005 for p in prices],
        'low': [p * 0.995 for p in prices],
        'close': prices,
        'volume': [1000000] * 200
    }, index=dates)


if __name__ == "__main__":
    get_tomorrow_trading_plan()