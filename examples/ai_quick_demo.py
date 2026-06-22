import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai_api import EventAnalyzer, NewsAPIClient, SentimentAnalyzer


def main():
    print("🤖 AI事件驱动交易策略演示")
    print("=" * 50)
    
    print("\n1️⃣ 创建事件分析器")
    analyzer = EventAnalyzer()
    
    print("\n2️⃣ 分析今日事件")
    analysis = analyzer.analyze_todays_events()
    
    print(f"\n📊 黄金价格: ${analysis['current_price']:.2f}")
    print(f"\n📰 新闻情绪分析 ({analysis['news_count']} 条新闻):")
    print(f"  平均情绪分数: {analysis['avg_sentiment']:.2f}")
    
    sentiment_status = "BULLISH" if analysis['avg_sentiment'] > 0.2 else "BEARISH" if analysis['avg_sentiment'] < -0.2 else "NEUTRAL"
    print(f"  情绪状态: {sentiment_status}")
    
    print(f"\n📅 今日经济事件:")
    print(f"  高影响事件: {len(analysis['high_impact_events'])} 个")
    print(f"  中影响事件: {len(analysis['medium_impact_events'])} 个")
    
    print("\n  事件列表:")
    for event in analysis['high_impact_events'] + analysis['medium_impact_events']:
        print(f"    • [{event['impact'].upper()}] {event['title']} - {event['time']}")
    
    print(f"\n📝 今日新闻摘要:")
    for i, article in enumerate(analysis['news_details'], 1):
        print(f"    {i}. {article['title']}")
        print(f"       {article['description']}")
    
    print(f"\n🎯 综合分析:")
    if analysis['avg_sentiment'] > 0.2:
        print("✅ 建议: 考虑买入 (新闻情绪积极)")
    elif analysis['avg_sentiment'] < -0.2:
        print("❌ 建议: 考虑卖出 (新闻情绪消极)")
    else:
        print("⚡ 建议: 观望 (新闻情绪中性)")
    
    if len(analysis['high_impact_events']) > 0:
        print(f"⚠️  注意: 今日有 {len(analysis['high_impact_events'])} 个高影响事件，市场波动可能较大")


if __name__ == "__main__":
    main()