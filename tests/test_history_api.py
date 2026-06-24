#!/usr/bin/env python3
"""
验证518880历史K线数据API
测试新浪财经、东方财富等数据源的历史K线接口
"""

import requests
from datetime import datetime
import json


def test_sina_kline(code='sh518880', scale=240, ma='no', num=60):
    """
    测试新浪财经K线接口
    
    参数:
        code: 股票代码，如sh518880
        scale: K线周期，240=日线, 60=60分钟, 30=30分钟
        ma: 是否包含均线，no=不包含
        num: 获取K线数量
    
    接口文档:
        https://quotes.sina.cn/cn/api/jsonp_v2.php/=/CN_MarketDataService.getKLineData
    """
    print(f"\n{'='*60}")
    print(f"测试新浪财经K线接口")
    print(f"{'='*60}")
    print(f"代码: {code}")
    print(f"周期: {scale}分钟线")
    print(f"数量: {num}根")
    
    url = f"https://quotes.sina.cn/cn/api/jsonp_v2.php/=/CN_MarketDataService.getKLineData"
    params = {
        'symbol': code,
        'scale': scale,
        'ma': ma,
        'datalen': num
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        print(f"状态码: {resp.status_code}")
        
        if resp.status_code == 200:
            text = resp.text
            print(f"响应长度: {len(text)} 字符")
            
            # 解析JSONP格式
            if '(' in text and ')' in text:
                json_str = text[text.index('(')+1:text.rindex(')')]
                data = json.loads(json_str)
                
                if isinstance(data, list) and len(data) > 0:
                    print(f"✅ 获取成功！K线数量: {len(data)}")
                    print(f"\n数据样例 (最近3根):")
                    for item in data[-3:]:
                        print(f"  日期: {item.get('day', item.get('date', ''))}")
                        print(f"    开: {item.get('open')} 高: {item.get('high')}")
                        print(f"    低: {item.get('low')} 收: {item.get('close')}")
                        print(f"    成交量: {item.get('volume')}")
                    return data
                else:
                    print(f"❌ 数据格式错误或为空")
                    print(f"数据类型: {type(data)}")
                    if isinstance(data, list):
                        print(f"列表长度: {len(data)}")
            else:
                print(f"❌ 不是JSONP格式")
                print(f"前200字符: {text[:200]}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    return None


def test_eastmoney_kline(secid='1.518880', klt='101', fqt='1', end='20500101', lmt=60):
    """
    测试东方财富K线接口
    
    参数:
        secid: 股票ID，1.=沪市, 0.=深市
        klt: K线周期，101=日线, 102=周线, 103=月线
        fqt: 复权方式，1=前复权, 0=不复权
        end: 截止日期
        lmt: 获取数量
    
    接口文档:
        https://push2his.eastmoney.com/api/qt/stock/kline/get
    """
    print(f"\n{'='*60}")
    print(f"测试东方财富K线接口")
    print(f"{'='*60}")
    print(f"代码: {secid}")
    print(f"周期: 日线(klt=101)")
    print(f"数量: {lmt}根")
    
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        'secid': secid,
        'fields1': 'f1,f2,f3,f4,f5,f6',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
        'klt': klt,
        'fqt': fqt,
        'end': end,
        'lmt': lmt,
        'ut': 'fa5fd1943c7b386f172d6893dbfba10b'
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        print(f"状态码: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"响应状态: {data.get('rc')}")
            
            if data.get('data') and data['data'].get('klines'):
                klines = data['data']['klines']
                print(f"✅ 获取成功！K线数量: {len(klines)}")
                
                print(f"\n数据样例 (最近3根):")
                for kline in klines[-3:]:
                    parts = kline.split(',')
                    print(f"  日期: {parts[0]}")
                    print(f"    开: {parts[1]} 收: {parts[2]}")
                    print(f"    高: {parts[3]} 低: {parts[4]}")
                    print(f"    成交量: {parts[5]}")
                
                return klines
            else:
                print(f"❌ 无K线数据")
                print(f"返回数据: {json.dumps(data, ensure_ascii=False)[:500]}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    return None


def test_tencent_kline(code='sh518880', num=60):
    """
    测试腾讯财经K线接口
    """
    print(f"\n{'='*60}")
    print(f"测试腾讯财经K线接口")
    print(f"{'='*60}")
    
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    params = {
        'param': f'{code},day,,,{num},qfq'
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        print(f"状态码: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"响应状态: {data.get('code')}")
            
            if data.get('data'):
                stock_data = data['data'].get(code, {})
                klines = stock_data.get('qfqday') or stock_data.get('day', [])
                
                if klines:
                    print(f"✅ 获取成功！K线数量: {len(klines)}")
                    print(f"\n数据样例 (最近3根):")
                    for kline in klines[-3:]:
                        print(f"  日期: {kline[0]}")
                        print(f"    开: {kline[1]} 收: {kline[2]}")
                        print(f"    高: {kline[3]} 低: {kline[4]}")
                    return klines
                else:
                    print(f"❌ 无K线数据")
            else:
                print(f"❌ 无数据")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    return None


if __name__ == "__main__":
    print("=" * 60)
    print("🔍 518880 华安黄金ETF 历史K线API验证")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 测试1: 新浪财经
    sina_data = test_sina_kline('sh518880', scale=240, num=60)
    
    # 测试2: 东方财富
    eastmoney_data = test_eastmoney_kline('1.518880', lmt=60)
    
    # 测试3: 腾讯财经
    tencent_data = test_tencent_kline('sh518880', num=60)
    
    # 总结
    print(f"\n{'='*60}")
    print("📊 测试结果总结")
    print(f"{'='*60}")
    print(f"新浪财经: {'✅ 可用' if sina_data else '❌ 不可用'}")
    print(f"东方财富: {'✅ 可用' if eastmoney_data else '❌ 不可用'}")
    print(f"腾讯财经: {'✅ 可用' if tencent_data else '❌ 不可用'}")
    
    if sina_data or eastmoney_data or tencent_data:
        print(f"\n✅ 找到可用的历史数据API，可以建立回测系统！")
    else:
        print(f"\n❌ 所有API均不可用")
    
    print(f"\n{'='*60}")