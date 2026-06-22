#!/usr/bin/env python3
"""
黄金交易综合分析：事件 + 情绪 + 技术 + 博弈
更新版：支持多种新闻源
"""

import requests
from datetime import datetime
import json
import time


class GoldAnalyzer:
    def __init__(self):
        self.real_time_price = None
        self.economic_events = []
        self.news = []
        self.sentiment_score = 0
    
    def fetch_real_time_price(self):
        data = {}
        
        try:
            resp = requests.get("https://xaus.com/api/v1/spot", timeout=10)
            if resp.status_code == 200:
                d = resp.json()
                data['spot'] = {
                    'price': d['spot_usd_oz'],
                    'updated': d['updated_at'],
                    'source': 'xaus.com (现货)'
                }
        except Exception as e:
            print(f"⚠️ xaus.com错误: {e}")
        
        try:
            resp = requests.get("https://aurumrates.com/api/v1/spot", timeout=10)
            if resp.status_code == 200:
                d = resp.json()
                if d.get('status') == 'ok':
                    gold = d['data']['gold']
                    data['futures'] = {
                        'price': gold['price'],
                        'change_pct': gold['change_pct'],
                        'change_abs': gold['change_abs'],
                        'prev_close': gold['prev_close'],
                        'source': 'aurumrates (期货GC=F)'
                    }
        except Exception as e:
            print(f"⚠️ aurumrates错误: {e}")
        
        self.real_time_price = data
        return data
    
    def fetch_economic_calendar(self):
        events = []
        try:
            resp = requests.get(
                "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    for event in data[:20]:
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
        
        self.economic_events = events
        return events
    
    def fetch_news(self):
        """尝试多个免费新闻源"""
        news = []
        
        sources = [
            self._fetch_news_yahoo,
            self._fetch_news_gdelt,
            self._fetch_news_crypto,
            self._fetch_news_feed
        ]
        
        for source_func in sources:
            try:
                result = source_func()
                news.extend(result)
                if len(news) >= 10:
                    break
            except Exception as e:
                print(f"⚠️ 新闻源错误: {e}")
        
        self.news = news[:10]
        return self.news
    
    def _fetch_news_yahoo(self):
        """Yahoo Finance新闻"""
        news = []
        try:
            resp = requests.get(
                "https://query1.finance.yahoo.com/v1/finance/search",
                params={
                    'q': 'gold price',
                    'quotesCount': 0,
                    'newsCount': 5,
                    'enableFuzzyQuery': True
                },
                headers={'User-Agent': 'Mozilla/5.0'},
                timeout=10
            )
            if resp.status_code == 200:
                d = resp.json()
                for item in d.get('news', []):
                    news.append({
                        'title': item.get('title'),
                        'publisher': item.get('publisher'),
                        'link': item.get('link'),
                        'provider': 'Yahoo Finance'
                    })
        except:
            pass
        return news
    
    def _fetch_news_gdelt(self):
        """GDELT新闻（带延迟）"""
        news = []
        try:
            time.sleep(6)
            resp = requests.get(
                "https://api.gdeltproject.org/api/v2/doc/doc",
                params={
                    'query': 'gold',
                    'mode': 'ArtList',
                    'maxrecords': 5,
                    'format': 'json',
                    'sort': 'datedesc'
                },
                timeout=15
            )
            if resp.status_code == 200:
                d = resp.json()
                for item in d.get('articles', []):
                    news.append({
                        'title': item.get('title'),
                        'provider': 'GDELT'
                    })
        except:
            pass
        return news
    
    def _fetch_news_crypto(self):
        """加密货币/黄金新闻聚合"""
        news = []
        try:
            resp = requests.get(
                "https://min-api.cryptocompare.com/data/v2/news/?lang=EN",
                timeout=10
            )
            if resp.status_code == 200:
                d = resp.json()
                for item in d.get('Data', []):
                    if 'gold' in item.get('title', '').lower():
                        news.append({
                            'title': item.get('title'),
                            'provider': 'CryptoCompare'
                        })
        except:
            pass
        return news
    
    def _fetch_news_feed(self):
        """备选新闻源"""
        news = []
        try:
            resp = requests.get(
                "https://newsdata.io/api/1/news",
                params={
                    'q': 'gold',
                    'language': 'en',
                    'category': 'business',
                    'pageSize': 5
                },
                timeout=10
            )
            if resp.status_code == 200:
                d = resp.json()
                if d.get('status') == 'success':
                    for item in d.get('results', []):
                        news.append({
                            'title': item.get('title'),
                            'provider': 'NewsData.io'
                        })
        except:
            pass
        return news
    
    def analyze_sentiment(self):
        if not self.news:
            return 0
        
        positive_keywords = ['surge', 'rise', 'gain', 'bullish', 'high', 'rally', 'boost', 'record', 'jump', 'up', 'increase', 'strong', 'positive', 'upbeat', 'optimistic', 'soar']
        negative_keywords = ['fall', 'drop', 'decline', 'plunge', 'bearish', 'low', 'crash', 'slump', 'tumble', 'down', 'decrease', 'weak', 'negative', 'worried', 'pessimistic', 'plummet']
        
        scores = []
        for article in self.news:
            title = article.get('title', '').lower()
            score = 0
            
            for kw in positive_keywords:
                if kw in title:
                    score += 0.2
            for kw in negative_keywords:
                if kw in title:
                    score -= 0.2
            
            scores.append(max(-1, min(1, score)))
        
        avg_score = sum(scores) / len(scores) if scores else 0
        self.sentiment_score = avg_score
        return avg_score
    
    def analyze_events(self):
        high_impact = [e for e in self.economic_events if e.get('impact') == 'High']
        medium_impact = [e for e in self.economic_events if e.get('impact') == 'Medium']
        
        event_score = 0
        
        for event in high_impact:
            title = event.get('title', '').lower()
            if 'fed' in title or 'interest rate' in title:
                event_score += 0.3
            if 'cpi' in title or 'inflation' in title:
                event_score += 0.25
            if 'payroll' in title or 'unemployment' in title:
                event_score += 0.2
        
        return {
            'high_count': len(high_impact),
            'medium_count': len(medium_impact),
            'events': high_impact + medium_impact[:5],
            'score': min(event_score, 1.0)
        }
    
    def analyze_technical(self):
        if not self.real_time_price:
            return None
        
        data = self.real_time_price
        price = data['futures']['price'] if 'futures' in data else data['spot']['price']
        change_pct = data['futures']['change_pct'] if 'futures' in data else 0
        
        tech_score = 0
        
        if change_pct < -1:
            tech_score -= 0.4
        elif change_pct > 1:
            tech_score += 0.4
        
        if change_pct < -0.5:
            tech_score -= 0.2
        elif change_pct > 0.5:
            tech_score += 0.2
        
        return {
            'price': price,
            'change_pct': change_pct,
            'score': tech_score,
            'trend': '下跌' if change_pct < -0.5 else '上涨' if change_pct > 0.5 else '震荡'
        }
    
    def analyze_game_theory(self):
        analysis = {}
        
        if self.sentiment_score > 0.3:
            analysis['herding_risk'] = '高'
            analysis['herding_score'] = -0.3
            analysis['herding_desc'] = '市场情绪过于乐观，可能存在羊群效应'
        elif self.sentiment_score < -0.3:
            analysis['herding_risk'] = '高'
            analysis['herding_score'] = 0.3
            analysis['herding_desc'] = '市场情绪过于悲观，可能存在逆向机会'
        else:
            analysis['herding_risk'] = '低'
            analysis['herding_score'] = 0
            analysis['herding_desc'] = '市场情绪中性，无明显羊群效应'
        
        events = self.analyze_events()
        if events['high_count'] >= 2:
            analysis['volatility_risk'] = '高'
            analysis['volatility_score'] = -0.2
            analysis['volatility_desc'] = '多个高影响事件，波动率可能上升'
        else:
            analysis['volatility_risk'] = '低'
            analysis['volatility_score'] = 0
            analysis['volatility_desc'] = '事件影响有限'
        
        analysis['total_score'] = analysis['herding_score'] + analysis['volatility_score']
        return analysis
    
    def get_comprehensive_score(self):
        event_analysis = self.analyze_events()
        tech_analysis = self.analyze_technical()
        sentiment = self.sentiment_score
        game_analysis = self.analyze_game_theory()
        
        weights = {
            'event': 0.25,
            'sentiment': 0.25,
            'technical': 0.30,
            'game_theory': 0.20
        }
        
        total_score = (
            event_analysis['score'] * weights['event'] +
            sentiment * weights['sentiment'] +
            (tech_analysis['score'] if tech_analysis else 0) * weights['technical'] +
            game_analysis['total_score'] * weights['game_theory']
        )
        
        return total_score


def main():
    print("=" * 70)
    print("📅 黄金综合分析: 事件 + 情绪 + 技术 + 博弈")
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 70)
    
    analyzer = GoldAnalyzer()
    
    print("\n【一】事件分析")
    print("-" * 70)
    analyzer.fetch_economic_calendar()
    events = analyzer.analyze_events()
    
    print(f"\n📅 今日事件统计:")
    print(f"  高影响事件: {events['high_count']} 个")
    print(f"  中影响事件: {events['medium_count']} 个")
    print(f"  事件影响评分: {events['score']:.2f}")
    
    print("\n📊 关键事件详情:")
    for event in events['events'][:5]:
        impact = event.get('impact')
        emoji = "🔴" if impact == 'High' else "🟡" if impact == 'Medium' else "🟢"
        print(f"\n  {emoji} [{impact}] {event.get('title')}")
        print(f"      时间: {event.get('date', '')} {event.get('time', '')}")
        if event.get('forecast'):
            print(f"      预期: {event['forecast']} | 前值: {event.get('previous', 'N/A')}")
    
    print("\n【二】情绪分析")
    print("-" * 70)
    
    news = analyzer.fetch_news()
    sentiment = analyzer.analyze_sentiment()
    
    print(f"\n📰 新闻数量: {len(news)} 条")
    print(f"📊 情绪综合评分: {sentiment:+.2f}")
    
    if sentiment > 0.2:
        print("   → 市场情绪: 🟢 看多")
    elif sentiment < -0.2:
        print("   → 市场情绪: 🔴 看空")
    else:
        print("   → 市场情绪: ⚡ 中性")
    
    if news:
        print("\n🎯 新闻摘要:")
        for i, article in enumerate(news[:5], 1):
            title = article.get('title', 'N/A')
            provider = article.get('provider', 'Unknown')
            print(f"  {i}. [{provider}] {title[:80]}...")
    else:
        print("\n⚠️  无法获取实时新闻（免费API限制）")
        print("   💡 建议: 注册NewsAPI/GNews等服务获取完整新闻")
    
    print("\n【三】技术分析")
    print("-" * 70)
    
    analyzer.fetch_real_time_price()
    tech = analyzer.analyze_technical()
    
    if tech:
        print(f"\n💰 当前价格: ${tech['price']:.2f}/oz")
        print(f"📈 当日涨跌: {tech['change_pct']:+.2f}%")
        print(f"📊 技术评分: {tech['score']:.2f}")
        print(f"🎯 趋势判断: {tech['trend']}")
    
    print("\n【四】博弈分析")
    print("-" * 70)
    
    game = analyzer.analyze_game_theory()
    
    print(f"\n🐑 羊群效应风险: {game['herding_risk']}")
    print(f"   评分: {game['herding_score']:.2f}")
    print(f"   分析: {game['herding_desc']}")
    
    print(f"\n📊 波动率风险: {game['volatility_risk']}")
    print(f"   评分: {game['volatility_score']:.2f}")
    print(f"   分析: {game['volatility_desc']}")
    
    print("\n【五】综合评分与建议")
    print("-" * 70)
    
    total_score = analyzer.get_comprehensive_score()
    print(f"\n🎯 综合评分: {total_score:+.2f}")
    
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
    
    print("\n📊 评分构成:")
    print(f"  • 事件因素: {events['score']:.2f} (权重25%)")
    print(f"  • 情绪因素: {sentiment:.2f} (权重25%)")
    print(f"  • 技术因素: {tech['score']:.2f} (权重30%)")
    print(f"  • 博弈因素: {game['total_score']:.2f} (权重20%)")
    
    print("\n" + "=" * 70)
    print("✅ 分析完成")
    print("=" * 70)


if __name__ == "__main__":
    main()