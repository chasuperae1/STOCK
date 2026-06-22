#!/usr/bin/env python3
"""
真实数据黄金交易分析 - 修正版
使用实时API数据，不依赖过时的历史数据
"""

import requests
from datetime import datetime
import json


def get_real_time_data():
    """获取真实实时金价数据"""
    data = {}
    
    # xaus.com - 实时金价
    try:
        resp = requests.get("https://xaus.com/api/v1/spot", timeout=10)
        if resp.status_code == 200:
            d = resp.json()
            data['xaus'] = {
                'price': d['spot_usd_oz'],
                'per_gram': d['per_gram_usd'],
                'updated': d['updated_at'],
                'source': d.get('price_source', 'xaus.com')
            }
    except Exception as e:
        print(f"⚠️ xaus.com错误: {e}")
    
    # aurumrates.com - 含涨跌数据
    try:
        resp = requests.get("https://aurumrates.com/api/v1/spot", timeout=10)
        if resp.status_code == 200:
            d = resp.json()
            if d.get('status') == 'ok':
                gold = d['data']['gold']
                data['aurumrates'] = {
                    'price': gold['price'],
                    'change_pct': gold['change_pct'],
                    'change_abs': gold['change_abs'],
                    'prev_close': gold['prev_close'],
                    'source': gold['source']
                }
    except Exception as e:
        print(f"⚠️ aurumrates.com错误: {e}")
    
    return data


def get_economic_calendar():
    """获取真实经济日历"""
    events = []
    try:
        resp = requests.get(
            "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                for event in data[:15]:
                    events.append({
                        'title': event.get('title'),
                        'date': event.get('date'),
                        'time': event.get('time'),
                        'impact': event.get('impact'),
                        'forecast': event.get('forecast'),
                        'previous': event.get('previous'),
                        'currency': event.get('country', 'USD')
                    })
    except Exception as e:
        print(f"⚠️ 经济日历错误: {e}")
    return events


def get_gold_news():
    """获取真实黄金新闻"""
    news = []
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                'q': 'gold price OR XAU',
                'language': 'zh',
                'sortBy': 'publishedAt',
                'pageSize': 5
            },
            timeout=15
        )
        if resp.status_code == 200:
            d = resp.json()
            news = d.get('articles', [])
    except Exception as e:
        pass
    
    if not news:
        try:
            resp = requests.get(
                "https://api.gdeltproject.org/api/v2/doc/doc",
                params={
                    'query': '(gold OR XAU) AND sourcelang:eng',
                    'mode': 'ArtList',
                    'maxrecords': 5,
                    'format': 'json',
                    'sort': 'datedesc'
                },
                timeout=15
            )
            if resp.status_code == 200:
                d = resp.json()
                news = d.get('articles', [])[:5]
        except Exception as e:
            pass
    
    return news


def analyze_trend(data):
    """基于实时数据分析趋势"""
    trend = {}
    
    if 'aurumrates' in data:
        change = data['aurumrates']['change_pct']
        
        if change < -1:
            trend['short_term'] = '下跌'
            trend['short_term_score'] = change / 10
        elif change > 1:
            trend['short_term'] = '上涨'
            trend['short_term_score'] = change / 10
        else:
            trend['short_term'] = '震荡'
            trend['short_term_score'] = 0
        
        trend['change_pct'] = change
        trend['change_abs'] = data['aurumrates']['change_abs']
    
    return trend


def main():
    print("=" * 70)
    print("📅 真实数据 - 黄金交易分析 (修正版)")
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 70)
    
    # 获取实时数据
    print("\n" + "=" * 70)
    print("【第一步】实时金价数据")
    print("=" * 70)
    
    data = get_real_time_data()
    
    prices = []
    print("\n💰 当前黄金价格:")
    if 'xaus' in data:
        print(f"  • xaus.com: ${data['xaus']['price']:.2f}/oz")
        print(f"    更新: {data['xaus']['updated']}")
        prices.append(data['xaus']['price'])
    
    if 'aurumrates' in data:
        d = data['aurumrates']
        print(f"  • aurumrates: ${d['price']:.2f}/oz")
        print(f"    涨跌: {d['change_pct']:+.2f}% (${d['change_abs']:+.2f})")
        print(f"    前收: ${d['prev_close']:.2f}")
        prices.append(d['price'])
    
    if prices:
        avg_price = sum(prices) / len(prices)
        print(f"\n  📊 平均价格: ${avg_price:.2f}/oz")
        print(f"  📊 每克价格: ${avg_price/31.1035:.2f}/g")
    else:
        print("  ❌ 无法获取金价")
        return
    
    # 趋势分析
    print("\n" + "=" * 70)
    print("【第二步】趋势分析")
    print("=" * 70)
    
    trend = analyze_trend(data)
    print(f"\n📈 短期趋势: {trend.get('short_term', '未知')}")
    if 'change_pct' in trend:
        print(f"📊 当日涨跌: {trend['change_pct']:+.2f}% (${trend['change_abs']:+.2f})")
    
    if trend.get('short_term') == '下跌':
        print("\n⚠️  您说得对！价格确实在下跌！")
        print("   当前跌幅: {:.2f}%".format(abs(trend['change_pct'])))
        if abs(trend['change_pct']) > 1:
            print("   💡 建议: 关注支撑位，等待企稳信号")
        else:
            print("   💡 建议: 小幅下跌，可观察后续走势")
    elif trend.get('short_term') == '上涨':
        print("\n📈 价格正在上涨")
    else:
        print("\n⚡ 价格震荡整理")
    
    # 经济日历
    print("\n" + "=" * 70)
    print("【第三步】经济日历")
    print("=" * 70)
    
    events = get_economic_calendar()
    if events:
        print("\n📅 今日关键事件:")
        for event in events[:5]:
            impact = event.get('impact')
            emoji = "🔴" if impact == 'High' else "🟡" if impact == 'Medium' else "🟢"
            print(f"  {emoji} [{impact}] {event.get('title')}")
            if event.get('forecast'):
                print(f"      预期: {event['forecast']} | 前值: {event.get('previous', 'N/A')}")
    
    # 新闻分析
    print("\n" + "=" * 70)
    print("【第四步】黄金新闻")
    print("=" * 70)
    
    news = get_gold_news()
    if news:
        print("\n📰 最新新闻:")
        for i, article in enumerate(news[:5], 1):
            title = article.get('title', article.get('url', 'N/A'))
            print(f"  {i}. {title[:100]}...")
    
    # 综合建议
    print("\n" + "=" * 70)
    print("【第五步】综合交易建议")
    print("=" * 70)
    
    score = 0
    if 'change_pct' in trend:
        score = trend['change_pct'] / 5
    
    print(f"\n🎯 综合评分: {score:+.2f}")
    print(f"💰 当前价格: ${avg_price:.2f}/oz")
    
    if score < -0.3:
        recommendation = "🔴 卖出/观望"
    elif score > 0.3:
        recommendation = "🟢 买入"
    else:
        recommendation = "⚡ 观望/轻仓"
    
    print(f"\n建议: {recommendation}")
    
    print("\n" + "=" * 70)
    print("✅ 分析完成")
    print("=" * 70)


if __name__ == "__main__":
    main()