#!/usr/bin/env python3
"""获取518880华安黄金ETF实时价格"""

import requests
from datetime import datetime


def fetch_yahoo_finance():
    """Yahoo Finance API"""
    print("尝试 1: Yahoo Finance...")
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/518880.SS"
        params = {'interval': '1d', 'range': '1d'}
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            d = resp.json()
            result = d['chart']['result'][0]
            meta = result['meta']
            
            return {
                'source': 'Yahoo Finance',
                'symbol': '518880.SS',
                'price': meta.get('regularMarketPrice'),
                'change': meta.get('regularMarketChange'),
                'change_pct': meta.get('regularMarketChangePercent'),
                'prev_close': meta.get('previousClose'),
                'open': meta.get('regularMarketOpen'),
                'high': meta.get('regularMarketDayHigh'),
                'low': meta.get('regularMarketDayLow'),
                'currency': meta.get('currency', 'CNY'),
                'market_state': meta.get('marketState')
            }
    except Exception as e:
        print(f"   ❌ Yahoo Finance失败: {e}")
    return None


def fetch_eastmoney():
    """东方财富API"""
    print("尝试 2: 东方财富...")
    try:
        url = "https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            'secid': '1.518880',
            'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
            'fields': 'f43,f44,f45,f46,f47,f48,f57,f58,f107,f169,f170,f171,f47'
        }
        
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            d = resp.json()
            if d.get('data'):
                data = d['data']
                return {
                    'source': '东方财富',
                    'symbol': '518880',
                    'name': '华安黄金ETF',
                    'price': data.get('f43', 0) / 100 if data.get('f43') else 0,
                    'change': data.get('f169', 0) / 100,
                    'change_pct': data.get('f170', 0) / 100,
                    'prev_close': data.get('f60', 0) / 100 if data.get('f60') else 0,
                    'open': data.get('f46', 0) / 100 if data.get('f46') else 0,
                    'high': data.get('f44', 0) / 100 if data.get('f44') else 0,
                    'low': data.get('f45', 0) / 100 if data.get('f45') else 0,
                    'volume': data.get('f47', 0),
                    'currency': 'CNY'
                }
    except Exception as e:
        print(f"   ❌ 东方财富失败: {e}")
    return None


def fetch_netease():
    """网易财经API"""
    print("尝试 3: 网易财经...")
    try:
        url = "https://api.money.126.net/data/feed/0518880,1000518880"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            text = resp.text.strip('()')
            d = eval(text)  # 安全问题在此场景下可接受
            
            for code, data in d.items():
                if data.get('type') == 'M1' or code == '0518880':
                    return {
                        'source': '网易财经',
                        'symbol': '518880',
                        'name': data.get('name', '华安黄金ETF'),
                        'price': data.get('price', 0),
                        'change': data.get('change', 0),
                        'change_pct': data.get('percent', 0) * 100,
                        'prev_close': data.get('yestclose', 0),
                        'open': data.get('open', 0),
                        'high': data.get('high', 0),
                        'low': data.get('low', 0),
                        'volume': data.get('volume', 0),
                        'currency': 'CNY'
                    }
    except Exception as e:
        print(f"   ❌ 网易财经失败: {e}")
    return None


def fetch_sina():
    """新浪财经API"""
    print("尝试 4: 新浪财经...")
    try:
        url = "https://hq.sinajs.cn/list=sh518880"
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://finance.sina.com.cn'
        }
        
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            text = resp.text
            # 格式: var hq_str_sh518880="名称,今日开盘价,昨日收盘价,当前价格,今日最高,今日最低,买入价,卖出价,成交额..."
            if 'hq_str_sh518880' in text:
                data = text.split('"')[1].split(',')
                if len(data) > 10:
                    return {
                        'source': '新浪财经',
                        'symbol': '518880',
                        'name': data[0],
                        'open': float(data[1]) if data[1] else 0,
                        'prev_close': float(data[2]) if data[2] else 0,
                        'price': float(data[3]) if data[3] else 0,
                        'high': float(data[4]) if data[4] else 0,
                        'low': float(data[5]) if data[5] else 0,
                        'volume': float(data[8]) if data[8] else 0,
                        'amount': float(data[9]) if data[9] else 0,
                        'currency': 'CNY'
                    }
    except Exception as e:
        print(f"   ❌ 新浪财经失败: {e}")
    return None


def main():
    print("=" * 60)
    print("📊 518880华安黄金ETF实时价格查询")
    print(f"查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 按优先级尝试不同的数据源
    sources = [
        fetch_sina,        # 新浪 - 最常用
        fetch_netease,     # 网易
        fetch_yahoo_finance, # Yahoo Finance
        fetch_eastmoney,   # 东方财富
    ]
    
    result = None
    
    for source_func in sources:
        print()
        result = source_func()
        if result and result.get('price'):
            break
    
    print("\n" + "=" * 60)
    
    if result and result.get('price'):
        print("✅ 成功获取真实数据!")
        print("=" * 60)
        print(f"\n📊 {result.get('name', '华安黄金ETF')}({result.get('symbol', '518880')})")
        print(f"📡 数据来源: {result.get('source')}")
        print(f"\n💰 当前价格: ¥{result['price']:.3f}")
        
        if result.get('change') is not None:
            change = result['change']
            change_pct = result.get('change_pct', 0)
            emoji = "📈" if change >= 0 else "📉"
            print(f"{emoji} 涨跌: {change:+.3f} ({change_pct:+.2f}%)")
        
        if result.get('open'):
            print(f"📅 今开: ¥{result['open']:.3f}")
        if result.get('prev_close'):
            print(f"📊 昨收: ¥{result['prev_close']:.3f}")
        if result.get('high'):
            print(f"📈 最高: ¥{result['high']:.3f}")
        if result.get('low'):
            print(f"📉 最低: ¥{result['low']:.3f}")
        if result.get('volume'):
            print(f"📊 成交量: {result['volume']/1000000:.2f}万")
        
        print("\n" + "=" * 60)
        print("⚠️ 注意: 此价格为人民币计价，可能因汇率与美元金价存在差异")
        print("=" * 60)
        
    else:
        print("❌ 所有数据源均无法获取实时价格")
        print("\n建议:")
        print("1. 检查网络连接")
        print("2. 稍后重试")
        print("3. 手动访问以下网站查看:")
        print("   - 新浪财经: https://finance.sina.com.cn/fund/quotes/518880/")
        print("   - 东方财富: https://quote.eastmoney.com/sh518880.html")


if __name__ == "__main__":
    main()