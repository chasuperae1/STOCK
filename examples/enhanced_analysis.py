#!/usr/bin/env python3
"""
黄金交易综合分析 - 增强版
新增: 技术指标、市场情绪、基本面数据、波动率等
"""

import requests
from datetime import datetime
import math


class EnhancedGoldAnalyzer:
    def __init__(self):
        self.NEWSDATA_API_KEY = "pub_a5a5a4284b084fdf82a37a88766f679f"
        self.real_time_price = None
        self.economic_events = []
        self.news = []
        self.sentiment_score = 0
        self.technical_indicators = {}
        self.market_data = {}
    
    def fetch_real_time_price(self):
        data = {}
        
        try:
            resp = requests.get("https://api.gold-api.com/price/XAU/USD", timeout=10)
            if resp.status_code == 200:
                d = resp.json()
                data['gold_api'] = {'price': d['price'], 'updated': d['updatedAt']}
        except:
            pass
        
        try:
            resp = requests.get("https://aurumrates.com/api/v1/spot", timeout=10)
            if resp.status_code == 200:
                d = resp.json()
                if d.get('status') == 'ok':
                    gold = d['data']['gold']
                    data['aurumrates'] = {
                        'price': gold['price'],
                        'change_pct': gold['change_pct'],
                        'prev_close': gold['prev_close']
                    }
        except:
            pass
        
        self.real_time_price = data
        return data
    
    def fetch_market_data(self):
        """获取市场相关数据：美元指数、VIX、债券收益率等"""
        market = {}
        
        try:
            resp = requests.get("https://cdn.jsdelivr.net/gh/fawazahmed0/currency-api@1/latest/currencies/usd.json", timeout=10)
            if resp.status_code == 200:
                market['dollar_index'] = {'source': 'currency-api'}
        except:
            pass
        
        try:
            resp = requests.get("https://api.stlouisfed.org/fred/series/observations?series_id=DGS10&api_key=demo&file_type=json&limit=1", timeout=10)
            if resp.status_code == 200:
                d = resp.json()
                if d.get('observations'):
                    market['treasury_10y'] = {
                        'yield': float(d['observations'][0]['value']),
                        'source': 'FRED'
                    }
        except:
            pass
        
        self.market_data = market
        return market
    
    def fetch_economic_calendar(self):
        events = []
        try:
            resp = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    for event in data[:20]:
                        events.append({
                            'title': event.get('title'),
                            'date': event.get('date'),
                            'impact': event.get('impact'),
                            'forecast': event.get('forecast'),
                            'previous': event.get('previous')
                        })
        except:
            pass
        
        self.economic_events = events
        return events
    
    def fetch_news(self):
        news = []
        seen_titles = set()
        
        try:
            url = "https://newsdata.io/api/1/news"
            params = {
                'apikey': self.NEWSDATA_API_KEY,
                'q': 'gold OR XAU OR precious metal OR gold price',
                'language': 'en',
                'category': 'business',
                'size': 8
            }
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                d = resp.json()
                if d.get('status') == 'success':
                    for item in d.get('results', []):
                        title = item.get('title', '')
                        if title in seen_titles:
                            continue
                        seen_titles.add(title)
                        news.append({
                            'title': title,
                            'description': item.get('description', ''),
                            'source': item.get('source_name', 'Unknown'),
                            'published_at': item.get('pubDate', '')
                        })
        except:
            pass
        
        self.news = news
        return news
    
    def calculate_technical_indicators(self):
        """计算技术指标"""
        indicators = {}
        
        if not self.real_time_price:
            self.fetch_real_time_price()
        
        prices = []
        if 'gold_api' in self.real_time_price:
            prices.append(self.real_time_price['gold_api']['price'])
        if 'aurumrates' in self.real_time_price:
            prices.append(self.real_time_price['aurumrates']['price'])
        
        if prices:
            current_price = sum(prices) / len(prices)
            prev_close = self.real_time_price['aurumrates'].get('prev_close', current_price)
            
            indicators['price'] = current_price
            indicators['change_pct'] = ((current_price - prev_close) / prev_close) * 100
            
            if indicators['change_pct'] < -1:
                indicators['trend_score'] = -0.5
            elif indicators['change_pct'] > 1:
                indicators['trend_score'] = 0.5
            elif indicators['change_pct'] < -0.5:
                indicators['trend_score'] = -0.25
            elif indicators['change_pct'] > 0.5:
                indicators['trend_score'] = 0.25
            else:
                indicators['trend_score'] = 0
            
            indicators['trend'] = '下跌' if indicators['change_pct'] < -0.5 else '上涨' if indicators['change_pct'] > 0.5 else '震荡'
        
        self.technical_indicators = indicators
        return indicators
    
    def analyze_sentiment(self):
        if not self.news:
            return 0
        
        positive_keywords = ['surge', 'rise', 'gain', 'bullish', 'high', 'rally', 'boost', 'record', 'jump', 'up', 'increase', 'strong', 'positive', 'upbeat', 'optimistic', 'soar', 'recovery', 'rebound']
        negative_keywords = ['fall', 'drop', 'decline', 'plunge', 'bearish', 'low', 'crash', 'slump', 'tumble', 'down', 'decrease', 'weak', 'negative', 'worried', 'pessimistic', 'plummet', 'slide']
        
        scores = []
        for article in self.news:
            text = (article.get('title', '') + ' ' + article.get('description', '')).lower()
            score = 0
            
            for kw in positive_keywords:
                if kw in text:
                    score += 0.15
            for kw in negative_keywords:
                if kw in text:
                    score -= 0.15
            
            scores.append(max(-1, min(1, score)))
        
        avg_score = sum(scores) / len(scores) if scores else 0
        self.sentiment_score = avg_score
        return avg_score
    
    def analyze_events(self):
        high_impact = [e for e in self.economic_events if e.get('impact') == 'High']
        medium_impact = [e for e in self.economic_events if e.get('impact') == 'Medium']
        
        event_score = 0
        event_details = []
        
        for event in high_impact:
            title = event.get('title', '').lower()
            event_details.append({
                'title': event.get('title'),
                'impact': 'High',
                'forecast': event.get('forecast'),
                'previous': event.get('previous')
            })
            
            if 'fed' in title or 'interest rate' in title:
                event_score += 0.3
            if 'cpi' in title or 'inflation' in title:
                event_score += 0.25
            if 'payroll' in title or 'unemployment' in title:
                event_score += 0.2
        
        for event in medium_impact[:3]:
            event_details.append({
                'title': event.get('title'),
                'impact': 'Medium'
            })
            event_score += 0.05
        
        return {
            'high_count': len(high_impact),
            'medium_count': len(medium_impact),
            'score': min(event_score, 1.0),
            'events': event_details
        }
    
    def analyze_fundamentals(self):
        """基本面分析：美元、利率、通胀等"""
        fundamentals = {
            'score': 0,
            'factors': []
        }
        
        if 'treasury_10y' in self.market_data:
            yield_val = self.market_data['treasury_10y']['yield']
            fundamentals['factors'].append(f"10年期美债收益率: {yield_val}%")
            if yield_val > 4.5:
                fundamentals['score'] -= 0.2
                fundamentals['factors'].append("→ 高利率不利于金价")
            elif yield_val < 3.5:
                fundamentals['score'] += 0.2
                fundamentals['factors'].append("→ 低利率有利于金价")
        
        fundamentals['score'] = max(-0.5, min(0.5, fundamentals['score']))
        return fundamentals
    
    def analyze_volatility(self):
        """波动率分析"""
        events = self.analyze_events()
        
        if events['high_count'] >= 2:
            return {
                'risk': '高',
                'score': -0.3,
                'reason': '多个高影响事件即将发布'
            }
        elif events['high_count'] == 1:
            return {
                'risk': '中',
                'score': -0.15,
                'reason': '有高影响事件'
            }
        else:
            return {
                'risk': '低',
                'score': 0,
                'reason': '事件影响有限'
            }
    
    def analyze_game_theory(self):
        """博弈论分析：羊群效应、逆向机会"""
        analysis = {}
        
        if self.sentiment_score > 0.4:
            analysis['herding_risk'] = '高'
            analysis['herding_score'] = -0.3
            analysis['herding_desc'] = '市场情绪过于乐观，可能存在羊群效应，谨慎追高'
        elif self.sentiment_score < -0.4:
            analysis['herding_risk'] = '高'
            analysis['herding_score'] = 0.3
            analysis['herding_desc'] = '市场情绪过于悲观，可能存在逆向买入机会'
        else:
            analysis['herding_risk'] = '低'
            analysis['herding_score'] = 0
            analysis['herding_desc'] = '市场情绪中性，无明显羊群效应'
        
        return analysis
    
    def get_comprehensive_score(self):
        """综合评分"""
        events = self.analyze_events()
        tech = self.calculate_technical_indicators()
        sentiment = self.analyze_sentiment()
        fundamentals = self.analyze_fundamentals()
        volatility = self.analyze_volatility()
        game = self.analyze_game_theory()
        
        weights = {
            'events': 0.25,
            'technical': 0.25,
            'sentiment': 0.15,
            'fundamentals': 0.15,
            'volatility': 0.10,
            'game_theory': 0.10
        }
        
        total_score = (
            events['score'] * weights['events'] +
            tech.get('trend_score', 0) * weights['technical'] +
            sentiment * weights['sentiment'] +
            fundamentals['score'] * weights['fundamentals'] +
            volatility['score'] * weights['volatility'] +
            game['herding_score'] * weights['game_theory']
        )
        
        return {
            'score': total_score,
            'breakdown': {
                'events': events['score'],
                'technical': tech.get('trend_score', 0),
                'sentiment': sentiment,
                'fundamentals': fundamentals['score'],
                'volatility': volatility['score'],
                'game_theory': game['herding_score']
            },
            'weights': weights
        }


def main():
    print("=" * 75)
    print("📅 黄金综合分析 - 增强版")
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 75)
    
    analyzer = EnhancedGoldAnalyzer()
    
    print("\n【一】实时金价")
    print("-" * 75)
    data = analyzer.fetch_real_time_price()
    
    if 'gold_api' in data:
        print(f"💰 gold-api.com: ${data['gold_api']['price']:.2f}/oz")
    if 'aurumrates' in data:
        d = data['aurumrates']
        print(f"💰 aurumrates: ${d['price']:.2f}/oz ({d['change_pct']:+.2f}%)")
    
    print("\n【二】技术分析")
    print("-" * 75)
    tech = analyzer.calculate_technical_indicators()
    print(f"\n📊 当前价格: ${tech.get('price', 'N/A'):.2f}/oz")
    print(f"📈 涨跌幅度: {tech.get('change_pct', 'N/A'):+.2f}%")
    print(f"🎯 趋势判断: {tech.get('trend', 'N/A')}")
    print(f"📈 技术评分: {tech.get('trend_score', 'N/A'):.2f}")
    
    print("\n【三】事件分析")
    print("-" * 75)
    analyzer.fetch_economic_calendar()
    events = analyzer.analyze_events()
    
    print(f"\n📅 今日事件统计:")
    print(f"  🔴 高影响: {events['high_count']} 个")
    print(f"  🟡 中影响: {events['medium_count']} 个")
    print(f"  📊 事件评分: {events['score']:.2f}")
    
    print("\n📋 关键事件详情:")
    for event in events['events'][:5]:
        emoji = "🔴" if event['impact'] == 'High' else "🟡"
        print(f"\n  {emoji} [{event['impact']}] {event['title']}")
        if 'forecast' in event:
            print(f"      预期: {event['forecast']} | 前值: {event.get('previous', 'N/A')}")
    
    print("\n【四】市场情绪")
    print("-" * 75)
    news = analyzer.fetch_news()
    sentiment = analyzer.analyze_sentiment()
    
    print(f"\n📰 新闻数量: {len(news)} 条")
    print(f"📊 情绪评分: {sentiment:+.2f}")
    
    if sentiment > 0.2:
        print("   → 市场情绪: 🟢 看多")
    elif sentiment < -0.2:
        print("   → 市场情绪: 🔴 看空")
    else:
        print("   → 市场情绪: ⚡ 中性")
    
    print("\n【五】基本面分析")
    print("-" * 75)
    analyzer.fetch_market_data()
    fundamentals = analyzer.analyze_fundamentals()
    
    print(f"\n📊 基本面评分: {fundamentals['score']:.2f}")
    print("\n💰 影响因素:")
    for factor in fundamentals['factors']:
        print(f"  • {factor}")
    
    print("\n【六】波动率分析")
    print("-" * 75)
    volatility = analyzer.analyze_volatility()
    print(f"\n⚠️  波动率风险: {volatility['risk']}")
    print(f"   原因: {volatility['reason']}")
    print(f"   评分影响: {volatility['score']:.2f}")
    
    print("\n【七】博弈分析")
    print("-" * 75)
    game = analyzer.analyze_game_theory()
    print(f"\n🐑 羊群效应风险: {game['herding_risk']}")
    print(f"   分析: {game['herding_desc']}")
    
    print("\n【八】综合评分与建议")
    print("-" * 75)
    result = analyzer.get_comprehensive_score()
    
    print(f"\n🎯 综合评分: {result['score']:+.2f}")
    
    print("\n📊 评分构成:")
    breakdown = result['breakdown']
    weights = result['weights']
    for key, score in breakdown.items():
        print(f"  • {key}: {score:.2f} (权重: {weights[key]*100:.0f}%)")
    
    total_score = result['score']
    if total_score > 0.3:
        recommendation = "🟢 买入/做多"
        confidence = "高"
    elif total_score < -0.3:
        recommendation = "🔴 卖出/做空"
        confidence = "高"
    elif total_score > 0:
        recommendation = "🟡 谨慎看多"
        confidence = "中等"
    elif total_score < 0:
        recommendation = "🟡 谨慎看空"
        confidence = "中等"
    else:
        recommendation = "⚡ 观望/轻仓"
        confidence = "低"
    
    print(f"\n📋 交易建议: {recommendation}")
    print(f"💯 置信度: {confidence}")
    
    print("\n💡 操作提示:")
    if events['high_count'] >= 2:
        print("   • 今日高影响事件较多，建议等待数据发布后再决策")
    if tech.get('trend') == '下跌':
        print("   • 当前趋势向下，关注支撑位")
    elif tech.get('trend') == '上涨':
        print("   • 当前趋势向上，关注阻力位")
    else:
        print("   • 当前震荡整理，等待方向明确")
    
    print("\n" + "=" * 75)
    print("✅ 分析完成")
    print("=" * 75)


if __name__ == "__main__":
    main()