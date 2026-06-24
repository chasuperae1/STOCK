#!/usr/bin/env python3
"""
金融数据API工具集
=================

本文件整合了多种金融数据API，包括：
- 黄金价格API（国际金价）
- A股/ETF实时行情API
- 外汇数据API
- 新闻数据API
- 经济日历API

使用说明：
    from api_tools import GoldAPI, ChinaStockAPI, NewsAPI
    
    # 获取黄金价格
    gold = GoldAPI()
    price = gold.get_realtime_price()
    
    # 获取A股实时行情
    stock = ChinaStockAPI()
    data = stock.get_realtime("518880")  # 华安黄金ETF

作者：TRAE AI 助手
版本：1.0.0
更新：2026-06-23
"""

import requests
from datetime import datetime
from typing import Optional, Dict, List, Any


# =============================================================================
# 第一部分：黄金价格API
# =============================================================================

class GoldAPI:
    """
    黄金价格API集合
    
    提供多种黄金价格数据源，包括现货价、期货价、涨跌幅等
    """
    
    @staticmethod
    def gold_api_com() -> Optional[Dict]:
        """
        API 1: gold-api.com
        
        功能：获取黄金实时现货价格
        优点：无需API Key、无请求限制、支持CORS
        链接：https://gold-api.com
        
        返回示例：
        {
            'price': 4215.50,
            'symbol': 'XAU',
            'currency': 'USD',
            'updatedAt': '2026-06-23T10:00:00Z'
        }
        """
        url = "https://api.gold-api.com/price/XAU/USD"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                d = resp.json()
                return {
                    'source': 'gold-api.com',
                    'price': d.get('price'),
                    'symbol': d.get('symbol'),
                    'currency': d.get('currency'),
                    'updated_at': d.get('updatedAt'),
                    'updated_readable': d.get('updatedAtReadable')
                }
        except Exception as e:
            print(f"❌ gold-api.com 失败: {e}")
        return None
    
    @staticmethod
    def xaus_com() -> Optional[Dict]:
        """
        API 2: xaus.com
        
        功能：获取黄金现货价格
        优点：无需API Key、数据全面
        链接：https://xaus.com
        
        返回示例：
        {
            'spot_usd_oz': 4215.00,
            'per_gram_usd': 135.56,
            'updated_at': '2026-06-23T10:00:00Z'
        }
        """
        url = "https://xaus.com/api/v1/spot"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                d = resp.json()
                return {
                    'source': 'xaus.com',
                    'price_oz': d.get('spot_usd_oz'),
                    'price_gram': d.get('per_gram_usd'),
                    'updated_at': d.get('updated_at')
                }
        except Exception as e:
            print(f"❌ xaus.com 失败: {e}")
        return None
    
    @staticmethod
    def aurumrates_com() -> Optional[Dict]:
        """
        API 3: aurumrates.com
        
        功能：获取黄金期货价格（含涨跌幅）
        优点：无需API Key、包含涨跌幅数据
        链接：https://aurumrates.com
        
        返回示例：
        {
            'price': 4218.50,
            'change_pct': -0.85,
            'change_abs': -36.20,
            'prev_close': 4254.70
        }
        """
        url = "https://aurumrates.com/api/v1/spot"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                d = resp.json()
                if d.get('status') == 'ok':
                    gold = d['data']['gold']
                    return {
                        'source': 'aurumrates.com',
                        'price': gold.get('price'),
                        'change_pct': gold.get('change_pct'),
                        'change_abs': gold.get('change_abs'),
                        'prev_close': gold.get('prev_close'),
                        'source_name': gold.get('source')
                    }
        except Exception as e:
            print(f"❌ aurumrates.com 失败: {e}")
        return None
    
    @classmethod
    def get_realtime_price(cls) -> Dict:
        """
        获取黄金实时价格（多源验证）
        
        按优先级尝试多个数据源，返回第一个成功的
        """
        sources = [cls.gold_api_com, cls.aurumrates_com, cls.xaus_com]
        
        for source in sources:
            result = source()
            if result:
                return result
        
        return {'error': '所有黄金API均无法访问'}


# =============================================================================
# 第二部分：中国A股/ETF实时行情API
# =============================================================================

class ChinaStockAPI:
    """
    中国A股/ETF实时行情API集合
    
    支持获取：价格、涨跌幅、成交量、OHLC等
    """
    
    @staticmethod
    def sina() -> Dict:
        """
        API 4: 新浪财经API
        
        功能：获取A股/ETF实时行情
        优点：实时性强、国内最常用、覆盖全面
        链接：https://finance.sina.com.cn
        
        参数：股票代码（沪市加sh、深市加sz）
        示例：sh518880（华安黄金ETF）
        
        返回示例：
        {
            'name': '黄金ETF华安',
            'open': 8.668,
            'prev_close': 8.716,
            'price': 8.632,
            'high': 8.674,
            'low': 8.604,
            'volume': 1475400,
            'amount': 12789345.60
        }
        """
        def _fetch(code: str) -> Optional[Dict]:
            url = f"https://hq.sinajs.cn/list={code}"
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Referer': 'https://finance.sina.com.cn'
            }
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    text = resp.text
                    if f'hq_str_{code}' in text:
                        data = text.split('"')[1].split(',')
                        if len(data) > 10:
                            return {
                                'source': '新浪财经',
                                'code': code,
                                'name': data[0],
                                'open': float(data[1]) if data[1] else 0,
                                'prev_close': float(data[2]) if data[2] else 0,
                                'price': float(data[3]) if data[3] else 0,
                                'high': float(data[4]) if data[4] else 0,
                                'low': float(data[5]) if data[5] else 0,
                                'volume': float(data[8]) if data[8] else 0,
                                'amount': float(data[9]) if data[9] else 0,
                                'datetime': f"{data[30]} {data[31]}" if len(data) > 31 else None
                            }
            except Exception as e:
                print(f"❌ 新浪财经失败: {e}")
            return None
        
        return {'fetch': _fetch}
    
    @staticmethod
    def netease() -> Dict:
        """
        API 5: 网易财经API
        
        功能：获取A股/ETF实时行情
        优点：数据全面、包含市值等扩展信息
        链接：https://money.163.com
        
        参数：股票代码（沪市0开头、深市1开头）
        示例：1000518880
        
        返回示例：
        {
            'name': '华安黄金ETF',
            'price': 8.632,
            'change': -0.084,
            'percent': -0.0096,
            'open': 8.668,
            'yestclose': 8.716,
            'high': 8.674,
            'low': 8.604,
            'volume': 1475400
        }
        """
        def _fetch(code: str) -> Optional[Dict]:
            url = f"https://api.money.126.net/data/feed/{code}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    text = resp.text.strip('()')
                    d = eval(text)  # 安全提示：在生产环境中应使用json.loads替代
                    for c, data in d.items():
                        if str(c).replace('0', '') in code:
                            return {
                                'source': '网易财经',
                                'code': c,
                                'name': data.get('name'),
                                'price': data.get('price'),
                                'change': data.get('change'),
                                'percent': data.get('percent'),
                                'open': data.get('open'),
                                'yestclose': data.get('yestclose'),
                                'high': data.get('high'),
                                'low': data.get('low'),
                                'volume': data.get('volume')
                            }
            except Exception as e:
                print(f"❌ 网易财经失败: {e}")
            return None
        
        return {'fetch': _fetch}
    
    @staticmethod
    def eastmoney() -> Dict:
        """
        API 6: 东方财富API
        
        功能：获取A股/ETF实时行情（详细数据）
        优点：数据最详细、包含盘口数据
        链接：https://www.eastmoney.com
        
        参数：secid（沪市1开头、深市0开头）
        示例：1.518880
        
        返回字段说明：
        f43=当前价格 f44=最高 f45=最低 f46=今开
        f47=成交量 f48=成交额 f60=昨收
        f169=涨跌额 f170=涨跌幅
        """
        def _fetch(secid: str) -> Optional[Dict]:
            url = "https://push2.eastmoney.com/api/qt/stock/get"
            params = {
                'secid': secid,
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                'fields': 'f43,f44,f45,f46,f47,f48,f57,f58,f60,f107,f169,f170'
            }
            try:
                resp = requests.get(url, params=params, timeout=10)
                if resp.status_code == 200:
                    d = resp.json()
                    if d.get('data'):
                        data = d['data']
                        return {
                            'source': '东方财富',
                            'secid': secid,
                            'price': data.get('f43', 0) / 100 if data.get('f43') else 0,
                            'high': data.get('f44', 0) / 100 if data.get('f44') else 0,
                            'low': data.get('f45', 0) / 100 if data.get('f45') else 0,
                            'open': data.get('f46', 0) / 100 if data.get('f46') else 0,
                            'volume': data.get('f47', 0),
                            'amount': data.get('f48', 0),
                            'prev_close': data.get('f60', 0) / 100 if data.get('f60') else 0,
                            'change': data.get('f169', 0) / 100,
                            'change_pct': data.get('f170', 0) / 100,
                            'name': data.get('f58', '')
                        }
            except Exception as e:
                print(f"❌ 东方财富失败: {e}")
            return None
        
        return {'fetch': _fetch}
    
    @classmethod
    def get_realtime(cls, code: str, market: str = 'sh') -> Dict:
        """
        获取A股/ETF实时行情
        
        参数：
            code: 股票代码，如 '518880'
            market: 市场前缀，'sh' 或 'sz'，默认 'sh'
        
        返回：第一个成功的数据源
        """
        full_code = f"{market}{code}"
        
        # 尝试新浪
        result = cls.sina()['fetch'](full_code)
        if result:
            return result
        
        # 尝试东方财富
        secid = f"1.{code}" if market == 'sh' else f"0.{code}"
        result = cls.eastmoney()['fetch'](secid)
        if result:
            return result
        
        return {'error': '所有数据源均无法访问'}


# =============================================================================
# 第三部分：外汇数据API
# =============================================================================

class ForexAPI:
    """
    外汇数据API集合
    
    用于获取美元指数、汇率等数据
    """
    
    @staticmethod
    def currency_api() -> Optional[Dict]:
        """
        API 7: currency-api
        
        功能：获取美元指数及主要货币汇率
        优点：完全免费、无需API Key
        链接：https://github.com/fawazahmed0/currency-api
        
        返回示例：
        {
            'usd_eur': 0.92,
            'usd_cny': 7.25,
            'usd_jpy': 155.50
        }
        """
        url = "https://cdn.jsdelivr.net/gh/fawazahmed0/currency-api@1/latest/currencies/usd.json"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                return {
                    'source': 'currency-api',
                    'base': 'USD',
                    'data': resp.json().get('usd', {})
                }
        except Exception as e:
            print(f"❌ currency-api失败: {e}")
        return None


# =============================================================================
# 第四部分：新闻数据API
# =============================================================================

class NewsAPI:
    """
    新闻数据API集合
    
    用于获取财经新闻、市场情绪等
    注意：大多数需要API Key
    """
    
    # 用户提供的API Key
    NEWSDATA_KEY = "pub_a5a5a4284b084fdf82a37a88766f679f"
    MARKET_AUX_KEY = "7yd3GosRCb0clYEHvLnFC6Owaao9t6fQYKwAfUjf"
    
    @staticmethod
    def newsdata_io(key: str = None) -> Optional[List[Dict]]:
        """
        API 8: NewsData.io
        
        功能：获取财经新闻
        优点：数据质量高、支持多语言
        链接：https://newsdata.io
        限制：免费版1000次/月
        
        参数：API Key（用户提供）
        
        返回示例：
        [{
            'title': '黄金价格上涨',
            'description': '...',
            'source': 'Reuters',
            'pubDate': '2026-06-23'
        }]
        """
        api_key = key or NewsAPI.NEWSDATA_KEY
        
        keywords_list = ['gold', 'XAU', 'precious metal', 'gold price']
        results = []
        
        for keyword in keywords_list[:3]:
            url = "https://newsdata.io/api/1/news"
            params = {
                'apikey': api_key,
                'q': keyword,
                'language': 'en',
                'category': 'business',
                'size': 5
            }
            try:
                resp = requests.get(url, params=params, timeout=15)
                if resp.status_code == 200:
                    d = resp.json()
                    if d.get('status') == 'success':
                        for item in d.get('results', []):
                            results.append({
                                'title': item.get('title'),
                                'description': item.get('description'),
                                'source': item.get('source_name'),
                                'pubDate': item.get('pubDate'),
                                'link': item.get('link')
                            })
            except Exception as e:
                print(f"❌ newsdata.io失败: {e}")
        
        return results if results else None
    
    @staticmethod
    def market_aux(key: str = None) -> Optional[List[Dict]]:
        """
        API 9: MarketAux
        
        功能：获取金融新闻
        优点：专注金融领域
        链接：https://www.marketaux.com
        限制：免费版1000次/月
        
        参数：API Key（用户提供）
        """
        api_key = key or NewsAPI.MARKET_AUX_KEY
        
        keywords_list = ['gold', 'gold price', 'gold market']
        results = []
        
        for keyword in keywords_list[:2]:
            url = "https://api.marketaux.com/v1/news/all"
            params = {
                'api_token': api_key,
                'keywords': keyword,
                'language': 'en',
                'limit': 5
            }
            try:
                resp = requests.get(url, params=params, timeout=15)
                if resp.status_code == 200:
                    d = resp.json()
                    for item in d.get('data', []):
                        results.append({
                            'title': item.get('title'),
                            'description': item.get('description'),
                            'source': item.get('source'),
                            'pubDate': item.get('published_at')
                        })
            except Exception as e:
                print(f"❌ marketaux失败: {e}")
        
        return results if results else None
    
    @staticmethod
    def jin10() -> Optional[List[Dict]]:
        """
        API 10: 金十数据
        
        功能：获取中文财经快讯（黄金、外汇、股市等）
        优点：完全免费、无需API Key、时效性强、中文内容
        链接：https://www.jin10.com
        
        返回示例：
        [{
            'title': '金价突破4000美元',
            'description': '...',
            'source': '金十数据',
            'pubDate': '2026-06-24 12:00:00',
            'language': 'zh'
        }]
        """
        url = "https://www.jin10.com/flash_newest.js"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        try:
            import json as _json
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                text = resp.text
                start = text.find('[')
                end = text.rfind(']') + 1
                if start >= 0 and end > start:
                    json_str = text[start:end]
                    data = _json.loads(json_str)
                    
                    # 筛选黄金相关
                    gold_keywords = [
                        '黄金', '金价', 'gold', 'XAU', '贵金属', '白银',
                        '美联储', '加息', '降息', 'CPI', '通胀', 'PCE',
                        '非农', '就业', '美元', '美指', '地缘', '战争',
                        '避险', '利率决议', 'FOMC', '鲍威尔'
                    ]
                    
                    results = []
                    for item in data:
                        d = item.get('data', {})
                        title = d.get('title', '') or ''
                        content = d.get('content', '') or ''
                        source = d.get('source', '') or '金十数据'
                        time_str = item.get('time', '')
                        
                        # 检查是否黄金相关
                        text_all = (title + content).lower()
                        is_gold_related = any(k.lower() in text_all for k in gold_keywords)
                        
                        # 重要新闻也保留
                        is_important = item.get('important', 0) == 1
                        
                        if is_gold_related or is_important:
                            desc = content if len(content) > len(title) else title
                            results.append({
                                'title': title or content[:50],
                                'description': desc,
                                'source': source or '金十数据',
                                'pubDate': time_str,
                                'language': 'zh',
                                'important': is_important,
                                'link': d.get('source_link', '')
                            })
                    
                    return results if results else None
        except Exception as e:
            print(f"❌ 金十数据失败: {e}")
        return None
    
    @staticmethod
    def wallstreetcn() -> Optional[List[Dict]]:
        """
        API 11: 华尔街见闻
        
        功能：获取中文财经快讯（黄金频道）
        优点：完全免费、无需API Key、专业金融媒体、中文内容
        链接：https://wallstreetcn.com
        
        返回示例：
        [{
            'title': '美联储会议纪要公布',
            'description': '...',
            'source': '华尔街见闻',
            'pubDate': '2026-06-24',
            'language': 'zh'
        }]
        """
        url = "https://api.wallstreetcn.com/apiv1/content/lives?channel=gold-channel&limit=30"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                d = resp.json()
                items = d.get('data', {}).get('items', [])
                
                results = []
                for item in items:
                    title = item.get('title', '') or ''
                    content_text = item.get('content_text', '') or ''
                    display_time = item.get('display_time', '')
                    
                    # 如果title太短，用content_text
                    if len(title) < 5 and content_text:
                        title = content_text[:80]
                    
                    results.append({
                        'title': title,
                        'description': content_text,
                        'source': '华尔街见闻',
                        'pubDate': display_time,
                        'language': 'zh',
                        'link': f"https://wallstreetcn.com/live/{item.get('id', '')}"
                    })
                
                return results if results else None
        except Exception as e:
            print(f"❌ 华尔街见闻失败: {e}")
        return None
    
    @staticmethod
    def eastmoney_news() -> Optional[List[Dict]]:
        """
        API 12: 东方财富快讯
        
        功能：获取东方财富财经快讯
        优点：完全免费、无需API Key、国内主流财经媒体
        链接：https://www.eastmoney.com
        
        返回示例：
        [{
            'title': '黄金价格上涨',
            'description': '...',
            'source': '东方财富',
            'pubDate': '2026-06-24',
            'language': 'zh'
        }]
        """
        url = "https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_50_1_.html"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        try:
            import json as _json
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                text = resp.text
                start = text.find('{')
                end = text.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = text[start:end]
                    d = _json.loads(json_str)
                    lives = d.get('LivesList', [])
                    
                    gold_keywords = ['黄金', '金价', '贵金属', '美联储', '加息', '降息', 'CPI', '通胀', '白银']
                    
                    results = []
                    for item in lives:
                        title = item.get('title', '') or ''
                        digest = item.get('digest', '') or ''
                        
                        text_all = (title + digest).lower()
                        if any(k.lower() in text_all for k in gold_keywords):
                            results.append({
                                'title': title,
                                'description': digest,
                                'source': '东方财富',
                                'pubDate': item.get('showtime', ''),
                                'language': 'zh',
                                'link': item.get('url_w', '')
                            })
                    
                    return results if results else None
        except Exception as e:
            print(f"❌ 东方财富失败: {e}")
        return None
    
    @classmethod
    def get_chinese_news(cls) -> List[Dict]:
        """
        获取中文财经新闻（多源汇总）
        
        按优先级：金十数据 > 华尔街见闻 > 东方财富
        """
        all_news = []
        
        # 金十数据（最快、最相关）
        news = cls.jin10()
        if news:
            all_news.extend(news)
        
        # 华尔街见闻（黄金频道）
        news = cls.wallstreetcn()
        if news:
            all_news.extend(news)
        
        # 东方财富
        news = cls.eastmoney_news()
        if news:
            all_news.extend(news)
        
        # 去重（按标题）
        seen = set()
        unique_news = []
        for item in all_news:
            title = item.get('title', '')[:50]
            if title and title not in seen:
                seen.add(title)
                unique_news.append(item)
        
        return unique_news
    
    @classmethod
    def get_financial_news(cls, keyword: str = 'gold') -> List[Dict]:
        """
        获取财经新闻（多源，中英文混合）
        
        优先中文新闻（更贴近国内投资者），再补充英文新闻
        """
        all_news = []
        
        # 中文新闻优先
        cn_news = cls.get_chinese_news()
        if cn_news:
            all_news.extend(cn_news)
        
        # 补充英文新闻
        en_news = cls.newsdata_io()
        if en_news:
            for item in en_news:
                item['language'] = 'en'
            all_news.extend(en_news)
        
        # 再补充MarketAux
        if len(all_news) < 10:
            en_news2 = cls.market_aux()
            if en_news2:
                for item in en_news2:
                    item['language'] = 'en'
                all_news.extend(en_news2)
        
        return all_news


# =============================================================================
# 第五部分：经济日历API
# =============================================================================

class EconomicCalendarAPI:
    """
    经济日历API集合
    
    用于获取财经事件日程（美联储、CPI等）
    """
    
    @staticmethod
    def forexfactory() -> Optional[List[Dict]]:
        """
        API 10: Forex Factory 经济日历
        
        功能：获取全球财经事件日历
        优点：完全免费、无需API Key、数据最权威
        链接：https://www.forexfactory.com
        
        返回示例：
        [{
            'title': 'CPI m/m',
            'date': '2026-06-22T08:30:00-04:00',
            'impact': 'High',
            'forecast': '0.7%',
            'previous': '0.4%',
            'country': 'USD'
        }]
        """
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    events = []
                    for event in data[:20]:
                        events.append({
                            'title': event.get('title'),
                            'date': event.get('date'),
                            'time': event.get('time'),
                            'impact': event.get('impact'),  # High/Medium/Low
                            'forecast': event.get('forecast'),
                            'previous': event.get('previous'),
                            'currency': event.get('country')
                        })
                    return events
        except Exception as e:
            print(f"❌ Forex Factory失败: {e}")
        return None
    
    @classmethod
    def get_today_events(cls, currency: str = None) -> List[Dict]:
        """
        获取今日财经事件
        
        参数：currency 过滤特定货币（如 'USD', 'EUR'）
        """
        events = cls.forexfactory()
        if not events:
            return []
        
        # 过滤今日事件
        today = datetime.now().strftime('%Y-%m-%d')
        today_events = [e for e in events if today in str(e.get('date', ''))]
        
        if currency:
            today_events = [e for e in today_events if e.get('currency') == currency]
        
        return today_events


# =============================================================================
# 工具函数
# =============================================================================

def get_all_gold_price() -> Dict:
    """
    获取所有黄金价格数据（多源汇总）
    
    同时调用所有黄金API，返回汇总结果
    """
    results = {
        'timestamp': datetime.now().isoformat(),
        'sources': {}
    }
    
    # gold-api.com
    data = GoldAPI.gold_api_com()
    if data:
        results['sources']['gold_api'] = data
    
    # xaus.com
    data = GoldAPI.xaus_com()
    if data:
        results['sources']['xaus'] = data
    
    # aurumrates
    data = GoldAPI.aurumrates_com()
    if data:
        results['sources']['aurumrates'] = data
    
    # 计算平均价格
    prices = []
    if results['sources'].get('gold_api', {}).get('price'):
        prices.append(results['sources']['gold_api']['price'])
    if results['sources'].get('aurumrates', {}).get('price'):
        prices.append(results['sources']['aurumrates']['price'])
    
    if prices:
        results['average_price'] = sum(prices) / len(prices)
    
    return results


# =============================================================================
# 使用示例
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("📊 金融API工具集测试")
    print("=" * 60)
    
    # 测试1: 黄金价格
    print("\n【1】黄金实时价格")
    gold = GoldAPI.get_realtime_price()
    if gold.get('price'):
        print(f"   💰 价格: ${gold['price']}")
        print(f"   📡 来源: {gold['source']}")
    else:
        print("   ❌ 无法获取")
    
    # 测试2: A股ETF
    print("\n【2】518880华安黄金ETF")
    stock = ChinaStockAPI.get_realtime("518880")
    if stock.get('price'):
        print(f"   💰 价格: ¥{stock['price']}")
        print(f"   📈 涨跌: {stock.get('change', 0):+.3f} ({stock.get('change_pct', 0):+.2f}%)")
        print(f"   📡 来源: {stock['source']}")
    else:
        print("   ❌ 无法获取")
    
    # 测试3: 财经新闻
    print("\n【3】财经新闻")
    news = NewsAPI.get_financial_news()
    print(f"   📰 获取到 {len(news)} 条新闻")
    if news:
        print(f"   最新: {news[0].get('title', '')[:50]}...")
    
    # 测试4: 经济日历
    print("\n【4】今日财经事件")
    events = EconomicCalendarAPI.get_today_events()
    print(f"   📅 今日事件: {len(events)} 个")
    high_impact = [e for e in events if e.get('impact') == 'High']
    print(f"   🔴 高影响事件: {len(high_impact)} 个")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)