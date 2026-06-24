#!/usr/bin/env python3
"""
新闻情绪深度分析模块
====================

功能：
1. 新闻情感分析（更准确的词库+上下文判断）
2. 主题分类（美联储、通胀、地缘、供需等）
3. 情绪趋势（对比近期情绪变化）
4. 市场情绪指标（恐惧/贪婪指数估算）
5. 新闻热度评分
"""

import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class NewsSentiment:
    """单条新闻情绪分析结果"""
    title: str
    description: str
    source: str
    pub_date: str
    sentiment_score: float = 0.0       # -1到+1
    sentiment_label: str = 'neutral'    # positive/negative/neutral
    topic_tags: List[str] = field(default_factory=list)
    impact_on_gold: float = 0.0         # 对黄金的直接影响判断
    importance: float = 0.0             # 重要性评分


@dataclass
class SentimentAnalysisResult:
    """新闻情绪综合分析结果"""
    total_news: int = 0
    positive_news: int = 0
    negative_news: int = 0
    neutral_news: int = 0
    
    overall_sentiment: float = 0.0      # 整体情绪评分 -1到+1
    sentiment_label: str = 'neutral'
    
    # 主题分布
    topic_distribution: Dict[str, int] = field(default_factory=dict)
    
    # 情绪分类统计
    sentiment_by_topic: Dict[str, float] = field(default_factory=dict)
    
    # 对黄金的综合影响
    gold_impact_score: float = 0.0      # -1到+1
    
    # 市场情绪估算
    fear_greed_index: float = 50.0      # 0（极度恐惧）到100（极度贪婪）
    
    # 新闻列表
    analyzed_news: List[NewsSentiment] = field(default_factory=list)


class NewsSentimentAnalyzer:
    """
    新闻情绪深度分析器
    
    基于关键词和语义的情感分析，专门针对黄金市场优化
    """
    
    def __init__(self):
        # 正面情绪词库（利多黄金）
        self.positive_words = {
            # 上涨类
            'surge': 0.8, 'soar': 0.8, 'rally': 0.7, 'gain': 0.6,
            'rise': 0.5, 'increase': 0.4, 'climb': 0.5, 'jump': 0.6,
            'advance': 0.4, 'up': 0.3, 'higher': 0.4, 'growth': 0.4,
            
            # 看好类
            'bullish': 0.9, 'optimistic': 0.7, 'positive': 0.6,
            'strong': 0.5, 'outperform': 0.7, 'upgrade': 0.6,
            'buy': 0.6, 'long': 0.5, 'support': 0.4,
            
            # 避险类（对黄金是正面）
            'safe haven': 0.8, 'risk off': 0.7, 'fear': 0.6,
            'uncertainty': 0.5, 'volatility': 0.4, 'crisis': 0.7,
            'tension': 0.5, 'worried': 0.5, 'concern': 0.3,
            
            # 通胀类（利多黄金）
            'inflation': 0.5, 'hot': 0.4, 'rising prices': 0.6,
            'rate cut': 0.7, 'dovish': 0.6, 'easing': 0.5,
        }
        
        # 负面情绪词库（利空黄金）
        self.negative_words = {
            # 下跌类
            'plunge': -0.8, 'crash': -0.9, 'slump': -0.7, 'drop': -0.5,
            'fall': -0.5, 'decline': -0.4, 'decrease': -0.4, 'tumble': -0.7,
            'dip': -0.3, 'down': -0.3, 'lower': -0.4, 'loss': -0.5,
            
            # 看空类
            'bearish': -0.9, 'pessimistic': -0.7, 'negative': -0.6,
            'weak': -0.5, 'underperform': -0.7, 'downgrade': -0.6,
            'sell': -0.6, 'short': -0.5, 'resistance': -0.3,
            
            # 风险偏好类（利空黄金）
            'risk on': -0.7, 'optimism': -0.4, 'confidence': -0.3,
            'rally in stocks': -0.6, 'stock market up': -0.5,
            
            # 加息类（利空黄金）
            'rate hike': -0.7, 'hawkish': -0.6, 'tightening': -0.5,
            'fed hike': -0.7, 'higher rates': -0.6,
        }
        
        # 否定词（会翻转情绪）
        self.negation_words = [
            'not', 'no', 'never', "don't", "doesn't", "didn't",
            'isn\'t', 'aren\'t', 'won\'t', 'wouldn\'t',
            'fail to', 'lack of', 'without',
        ]
        
        # 加强词（会放大情绪）
        self.intensifiers = {
            'very': 1.3, 'extremely': 1.5, 'significantly': 1.4,
            'sharply': 1.4, 'dramatically': 1.5, 'slightly': 0.7,
            'modestly': 0.8, 'moderately': 0.9,
        }
        
        # 主题关键词
        self.topic_keywords = {
            'fed_policy': ['fed', 'fomc', 'powell', 'rate decision', 'interest rate', 'rate cut', 'rate hike', 'monetary policy', 'federal reserve'],
            'inflation': ['cpi', 'inflation', 'pce', 'ppi', 'consumer price', 'price index', 'rising prices'],
            'geopolitical': ['war', 'conflict', 'military', 'attack', 'sanction', 'tariff', 'tension', 'geopolitical', 'crisis', 'election'],
            'dollar': ['dollar', 'usd', 'dollar index', 'greenback'],
            'supply_demand': ['supply', 'demand', 'production', 'consumption', 'import', 'export', 'etf', 'holding'],
            'employment': ['nonfarm', 'nfp', 'employment', 'unemployment', 'job', 'labor'],
            'growth': ['gdp', 'growth', 'recession', 'economic', 'recovery'],
        }
        
        # 重要性词（提升新闻权重）
        self.importance_words = [
            'breaking', 'urgent', 'important', 'key', 'major',
            'fomc meeting', 'fed meeting', 'cpi data', 'nonfarm payrolls',
            'powell speech', 'fed chair',
        ]
    
    def analyze_news(self, news_list: List[Dict]) -> SentimentAnalysisResult:
        """
        分析一批新闻的情绪
        
        参数：
            news_list: 新闻列表，每条包含title/description/source/pubDate
        
        返回：
            SentimentAnalysisResult
        """
        result = SentimentAnalysisResult()
        
        if not news_list:
            return result
        
        result.total_news = len(news_list)
        
        total_sentiment = 0.0
        total_weight = 0.0
        total_gold_impact = 0.0
        
        topic_sentiment_sum = {}
        topic_sentiment_count = {}
        
        for news in news_list:
            analysis = self._analyze_single_news(news)
            result.analyzed_news.append(analysis)
            
            # 统计正负中性
            if analysis.sentiment_score > 0.15:
                result.positive_news += 1
            elif analysis.sentiment_score < -0.15:
                result.negative_news += 1
            else:
                result.neutral_news += 1
            
            # 加权累计
            weight = analysis.importance + 0.5  # 基础权重0.5 + 重要性
            total_sentiment += analysis.sentiment_score * weight
            total_gold_impact += analysis.impact_on_gold * weight
            total_weight += weight
            
            # 主题统计
            for topic in analysis.topic_tags:
                result.topic_distribution[topic] = result.topic_distribution.get(topic, 0) + 1
                
                if topic not in topic_sentiment_sum:
                    topic_sentiment_sum[topic] = 0.0
                    topic_sentiment_count[topic] = 0
                topic_sentiment_sum[topic] += analysis.sentiment_score * weight
                topic_sentiment_count[topic] += weight
        
        # 计算整体情绪
        if total_weight > 0:
            result.overall_sentiment = total_sentiment / total_weight
            result.gold_impact_score = total_gold_impact / total_weight
        
        # 情绪标签
        if result.overall_sentiment > 0.2:
            result.sentiment_label = 'positive'
        elif result.overall_sentiment < -0.2:
            result.sentiment_label = 'negative'
        else:
            result.sentiment_label = 'neutral'
        
        # 各主题情绪
        for topic, sum_val in topic_sentiment_sum.items():
            count = topic_sentiment_count.get(topic, 1)
            result.sentiment_by_topic[topic] = sum_val / count
        
        # 恐惧贪婪指数估算
        # 情绪越正面（对黄金），说明市场越恐惧（避险情绪）
        result.fear_greed_index = 50 - result.gold_impact_score * 40
        result.fear_greed_index = max(0, min(100, result.fear_greed_index))
        
        return result
    
    def _analyze_single_news(self, news: Dict) -> NewsSentiment:
        """分析单条新闻"""
        title = news.get('title', '') or ''
        description = news.get('description', '') or ''
        source = news.get('source', '') or ''
        pub_date = news.get('pubDate', '') or news.get('published_at', '') or ''
        
        text = f"{title}. {description}".lower()
        
        # 1. 计算情绪分数
        sentiment_score = self._calculate_sentiment(text)
        
        # 2. 主题分类
        topics = self._classify_topics(text)
        
        # 3. 对黄金的直接影响
        gold_impact = self._calculate_gold_impact(text, sentiment_score, topics)
        
        # 4. 重要性评分
        importance = self._calculate_importance(text, topics)
        
        # 情绪标签
        if sentiment_score > 0.15:
            label = 'positive'
        elif sentiment_score < -0.15:
            label = 'negative'
        else:
            label = 'neutral'
        
        return NewsSentiment(
            title=title,
            description=description,
            source=source,
            pub_date=pub_date,
            sentiment_score=sentiment_score,
            sentiment_label=label,
            topic_tags=topics,
            impact_on_gold=gold_impact,
            importance=importance,
        )
    
    def _calculate_sentiment(self, text: str) -> float:
        """
        计算情绪分数（-1到+1）
        
        考虑：
        - 正面/负面词的数量和强度
        - 否定词翻转
        - 加强词放大
        """
        words = text.split()
        total_score = 0.0
        word_count = 0
        
        i = 0
        while i < len(words):
            word = words[i]
            clean_word = word.strip('.,!?;:()[]{}"\'')
            
            # 检查多词短语
            found_phrase = False
            for phrase_len in [3, 2]:
                if i + phrase_len <= len(words):
                    phrase = ' '.join(words[i:i + phrase_len])
                    clean_phrase = phrase.strip('.,!?;:()[]{}"\'')
                    
                    if clean_phrase in self.positive_words:
                        score = self.positive_words[clean_phrase]
                        score = self._apply_modifiers(words, i, phrase_len, score)
                        total_score += score
                        word_count += 1
                        i += phrase_len
                        found_phrase = True
                        break
                    
                    if clean_phrase in self.negative_words:
                        score = self.negative_words[clean_phrase]
                        score = self._apply_modifiers(words, i, phrase_len, score)
                        total_score += score
                        word_count += 1
                        i += phrase_len
                        found_phrase = True
                        break
            
            if found_phrase:
                continue
            
            # 单词匹配
            if clean_word in self.positive_words:
                score = self.positive_words[clean_word]
                score = self._apply_modifiers(words, i, 1, score)
                total_score += score
                word_count += 1
            elif clean_word in self.negative_words:
                score = self.negative_words[clean_word]
                score = self._apply_modifiers(words, i, 1, score)
                total_score += score
                word_count += 1
            
            i += 1
        
        if word_count == 0:
            return 0.0
        
        # 归一化到-1到+1
        avg_score = total_score / word_count
        return max(-1.0, min(1.0, avg_score))
    
    def _apply_modifiers(self, words: List[str], index: int, length: int, score: float) -> float:
        """应用修饰词（否定词、加强词）"""
        result = score
        
        # 检查前面3个词内的否定词和加强词
        start = max(0, index - 3)
        for j in range(start, index):
            w = words[j].strip('.,!?;:()[]{}"\'').lower()
            
            if w in self.negation_words:
                result = -result  # 翻转
            elif w in self.intensifiers:
                result *= self.intensifiers[w]
        
        return result
    
    def _classify_topics(self, text: str) -> List[str]:
        """给新闻打主题标签"""
        topics = []
        
        for topic, keywords in self.topic_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    topics.append(topic)
                    break
        
        return topics
    
    def _calculate_gold_impact(
        self,
        text: str,
        sentiment_score: float,
        topics: List[str]
    ) -> float:
        """
        计算对黄金价格的影响（-1到+1）
        
        注意：情绪是正面的，不一定利多黄金。
        比如"股市大涨"是正面情绪，但利空黄金（资金从避险资产流出）
        """
        impact = sentiment_score
        
        # 根据主题调整
        for topic in topics:
            if topic == 'fed_policy':
                # 美联储政策对黄金影响大，权重加倍
                impact *= 1.5
            elif topic == 'inflation':
                # 通胀数据，权重加倍
                impact *= 1.5
            elif topic == 'geopolitical':
                # 地缘政治，权重加倍
                impact *= 1.4
            elif topic == 'dollar':
                # 美元走强通常利空黄金，但情绪词可能是正面的
                # 需要单独判断
                if 'strong' in text and ('dollar' in text or 'usd' in text):
                    impact -= 0.3  # 美元强，黄金弱
                if 'weak' in text and ('dollar' in text or 'usd' in text):
                    impact += 0.3  # 美元弱，黄金强
        
        # 黄金相关词汇直接影响
        if any(w in text for w in ['gold', 'xau', 'precious metal']):
            impact *= 1.3  # 直接提到黄金，置信度更高
        
        return max(-1.0, min(1.0, impact))
    
    def _calculate_importance(self, text: str, topics: List[str]) -> float:
        """计算新闻重要性（0到1）"""
        importance = 0.0
        
        # 重要性词汇
        for word in self.importance_words:
            if word in text:
                importance += 0.2
        
        # 重要主题
        important_topics = ['fed_policy', 'inflation', 'geopolitical', 'employment']
        for topic in topics:
            if topic in important_topics:
                importance += 0.15
        
        # 直接提到黄金
        if any(w in text for w in ['gold', 'xau', 'gold price']):
            importance += 0.1
        
        return min(1.0, importance)
    
    def print_analysis(self, result: SentimentAnalysisResult):
        """打印情绪分析结果"""
        print("\n" + "=" * 80)
        print("📰 新闻情绪深度分析")
        print("=" * 80)
        
        print(f"\n📊 总体统计:")
        print(f"   新闻总数: {result.total_news}")
        print(f"   正面: {result.positive_news} | 中性: {result.neutral_news} | 负面: {result.negative_news}")
        
        label_cn = {
            'positive': '🟢 偏多情绪',
            'negative': '🔴 偏空情绪',
            'neutral': '⚡ 中性情绪'
        }.get(result.sentiment_label, '中性')
        
        print(f"   整体情绪: {label_cn} ({result.overall_sentiment:+.2f})")
        print(f"   对黄金影响: {result.gold_impact_score:+.2f}")
        
        # 恐惧贪婪指数
        if result.fear_greed_index < 25:
            fg_label = "🔴 极度恐惧"
        elif result.fear_greed_index < 45:
            fg_label = "🟡 恐惧"
        elif result.fear_greed_index < 55:
            fg_label = "⚡ 中性"
        elif result.fear_greed_index < 75:
            fg_label = "🟢 贪婪"
        else:
            fg_label = "🟢 极度贪婪"
        
        print(f"   市场情绪(恐惧/贪婪): {result.fear_greed_index:.0f} - {fg_label}")
        
        # 主题分布
        if result.topic_distribution:
            print(f"\n🏷️  主题分布:")
            sorted_topics = sorted(result.topic_distribution.items(), key=lambda x: x[1], reverse=True)
            topic_cn = {
                'fed_policy': '美联储政策',
                'inflation': '通胀数据',
                'geopolitical': '地缘政治',
                'dollar': '美元指数',
                'supply_demand': '供需关系',
                'employment': '就业数据',
                'growth': '经济增长',
            }
            for topic, count in sorted_topics:
                topic_name = topic_cn.get(topic, topic)
                sent = result.sentiment_by_topic.get(topic, 0)
                print(f"   {topic_name}: {count}条 (情绪{sent:+.2f})")
        
        # 重点新闻
        important_news = sorted(
            result.analyzed_news,
            key=lambda x: x.importance + abs(x.impact_on_gold),
            reverse=True
        )[:5]
        
        if important_news:
            print(f"\n📝 重要新闻TOP5:")
            for i, news in enumerate(important_news, 1):
                direction = "🟢" if news.impact_on_gold > 0.1 else ("🔴" if news.impact_on_gold < -0.1 else "⚡")
                topics_str = ",".join(news.topic_tags[:2]) if news.topic_tags else "其他"
                print(f"   {i}. {direction} [{news.source}] {news.title[:60]}")
                print(f"      情绪: {news.sentiment_score:+.2f} | 黄金影响: {news.impact_on_gold:+.2f} | 重要性: {news.importance:.2f} | 主题: {topics_str}")
        
        print("=" * 80)


# =============================================================================
# 快速测试
# =============================================================================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '/workspace')
    from core.api_tools import NewsAPI
    
    print("=" * 80)
    print("🧪 新闻情绪深度分析测试")
    print("=" * 80)
    print()
    
    print("📰 正在获取财经新闻...")
    news = NewsAPI.get_financial_news()
    print(f"   获取到 {len(news)} 条新闻")
    print()
    
    analyzer = NewsSentimentAnalyzer()
    result = analyzer.analyze_news(news)
    
    analyzer.print_analysis(result)
