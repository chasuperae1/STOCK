#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金持仓追踪模块
追踪用户持有的基金，每日分析时自动获取最新净值和涨跌情况
"""

import requests
import re
import json
from datetime import datetime
from typing import Dict, List, Optional


# 用户持仓基金列表
USER_FUNDS = [
    {
        'code': '023638',
        'name': '国泰A股电网设备ETF联接A',
        'type': '指数型-股票',
        'risk': '高风险',
        'manager': '国泰基金',
        'fund_manager': '朱碧莹',
        'benchmark': '恒生A股电网设备指数收益率×95%+银行活期存款利率(税后)×5%',
        'strategy': '被动跟踪恒生A股电网设备指数，聚焦电网设备产业链',
        'top_holdings': [
            {'name': '亨通光电', 'weight': 9.78},
            {'name': '思源电气', 'weight': 9.74},
            {'name': '国电南瑞', 'weight': 9.48},
            {'name': '特变电工', 'weight': 9.43},
            {'name': '中天科技', 'weight': 8.24},
            {'name': '中国西电', 'weight': 3.54},
            {'name': '宏发股份', 'weight': 3.25},
            {'name': '东方电缆', 'weight': 2.52},
            {'name': '精达股份', 'weight': 2.44},
            {'name': '四方股份', 'weight': 2.17},
        ],
        'sector': '电网设备/特高压/新能源',
        'notes': '受益于电网投资加速、特高压建设、新能源并网需求',
    },
    {
        'code': '110027',
        'name': '易方达安心回报债券A',
        'type': '债券型（二级债基）',
        'risk': '中低风险(R2)',
        'manager': '易方达基金',
        'fund_manager': '张清华',
        'benchmark': '中债-优选投资级信用债财富指数收益率×85%+沪深300指数收益率×15%',
        'strategy': '固收为主(≥80%)，权益增强(≤20%)，追求长期稳定增值',
        'top_holdings': [
            {'name': '烽火通信', 'weight': 1.89},
            {'name': '芯原股份', 'weight': 1.19},
            {'name': '新易盛', 'weight': 1.15},
            {'name': '杰瑞股份', 'weight': 1.04},
            {'name': '中际旭创', 'weight': 1.00},
            {'name': '三环集团', 'weight': 0.94},
            {'name': '寒武纪', 'weight': 0.91},
            {'name': '扬农化工', 'weight': 0.85},
            {'name': '卫星化学', 'weight': 0.82},
            {'name': '北汽蓝谷', 'weight': 0.76},
        ],
        'top_bonds': [
            {'name': '25农发31', 'weight': 3.58},
            {'name': '25北京银行永续债01', 'weight': 3.30},
            {'name': '24兴业银行永续债01', 'weight': 2.65},
            {'name': '24北京银行永续债01', 'weight': 2.62},
            {'name': '24浦发银行二级资本债01A', 'weight': 2.47},
        ],
        'sector': '固收+/信用债/银行永续债',
        'notes': '老牌二级债基，成立14年累计收益356%，张清华管理12年+',
    },
    {
        'code': '001513',
        'name': '易方达信息产业混合A',
        'type': '混合型（偏股）',
        'risk': '中高风险(R4)',
        'manager': '易方达基金',
        'fund_manager': '郑希',
        'benchmark': '中证TMT产业主题指数收益率×85%+中债-总全价(总值)指数收益率×15%',
        'strategy': '股票60%-95%，信息产业≥80%，聚焦TMT/半导体/光通信/AI',
        'top_holdings': [
            {'name': '新易盛', 'weight': 8.69},
            {'name': '中际旭创', 'weight': 8.38},
            {'name': '源杰科技', 'weight': 7.48},
            {'name': '宁德时代', 'weight': 4.53},
            {'name': '鼎泰高科', 'weight': 4.17},
            {'name': '东山精密', 'weight': 3.70},
            {'name': '亨通光电', 'weight': 3.10},
            {'name': '长飞光纤', 'weight': 2.93},
            {'name': '光库科技', 'weight': 2.82},
            {'name': '中天科技', 'weight': 2.70},
        ],
        'sector': 'TMT/光通信/AI算力/半导体',
        'notes': '郑希管理近10年，成立以来收益992%，重仓光模块/AI算力产业链',
    },
    {
        'code': '017730',
        'name': '嘉实全球产业升级股票发起式(QDII)A',
        'type': 'QDII-股票',
        'risk': '中高风险',
        'manager': '嘉实基金',
        'fund_manager': '陈俊杰',
        'benchmark': 'MSCI全球指数收益率×75%+沪深300指数收益率×20%+银行活期存款利率(税后)×5%',
        'strategy': '全球配置，聚焦产业升级，美股科技+A股成长',
        'top_holdings': [
            {'name': '博通(AVGO)', 'weight': 5.37},
            {'name': '美光科技(MU)', 'weight': 4.85},
            {'name': '迈威尔科技(MRVL)', 'weight': 4.37},
            {'name': '源杰科技(688498)', 'weight': 4.25},
            {'name': '英伟达(NVDA)', 'weight': 3.79},
            {'name': '台积电(TSM)', 'weight': 3.50},
            {'name': '科磊(KLAC)', 'weight': 2.80},
            {'name': '应用材料(AMAT)', 'weight': 2.60},
            {'name': '阿斯麦(ASML)', 'weight': 2.50},
            {'name': '拉姆研究(LRCX)', 'weight': 2.30},
        ],
        'sector': '全球半导体/AI算力/美股科技',
        'notes': 'QDII基金，全球配置美股科技巨头+国内半导体，今年以来+90.75%',
    },
    {
        'code': '008887',
        'name': '华夏国证半导体芯片ETF联接A',
        'type': '指数型-股票',
        'risk': '中高风险',
        'manager': '华夏基金',
        'fund_manager': '赵宗庭',
        'benchmark': '国证半导体芯片指数收益率×95%+人民币活期存款税后利率×5%',
        'strategy': '被动跟踪国证半导体芯片指数，覆盖芯片设计/制造/封测全产业链',
        'top_holdings': [
            {'name': '海光信息', 'weight': 0.26},
            {'name': '北方华创', 'weight': 0.24},
            {'name': '中芯国际', 'weight': 0.22},
            {'name': '兆易创新', 'weight': 0.21},
            {'name': '澜起科技', 'weight': 0.19},
            {'name': '中微公司', 'weight': 0.19},
            {'name': '寒武纪', 'weight': 0.19},
            {'name': '豪威集团', 'weight': 0.11},
            {'name': '芯原股份', 'weight': 0.09},
            {'name': '拓荆科技', 'weight': 0.09},
        ],
        'sector': '半导体/芯片/国产替代',
        'notes': '跟踪国证半导体芯片指数，覆盖A股芯片全产业链，今年以来+60.39%',
    },
]


class FundTracker:
    """基金持仓追踪器"""
    
    def __init__(self):
        self.funds = USER_FUNDS
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def fetch_fund_nav(self, fund_code: str) -> Optional[Dict]:
        """获取基金最新净值"""
        try:
            # 使用天天基金API获取净值
            url = f'http://fundgz.1234567.com.cn/js/{fund_code}.js'
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                # 解析jsonp格式: jsonpgz({"fundcode":"023638",...});
                match = re.search(r'jsonpgz\((.*?)\)', resp.text)
                if match:
                    data = json.loads(match.group(1))
                    return {
                        'code': data.get('fundcode', fund_code),
                        'name': data.get('name', ''),
                        'nav': float(data.get('gsz', 0)),  # 估算净值
                        'nav_date': data.get('gztime', ''),
                        'change_pct': float(data.get('gszzl', 0)),  # 估算涨跌幅
                    }
        except Exception as e:
            print(f"  ❌ 获取{fund_code}净值失败: {e}")
        
        return None
    
    def fetch_all_funds(self) -> List[Dict]:
        """获取所有持仓基金最新数据"""
        results = []
        for fund in self.funds:
            nav_data = self.fetch_fund_nav(fund['code'])
            if nav_data:
                fund_info = {**fund, **nav_data}
                results.append(fund_info)
            else:
                results.append(fund)
        return results
    
    def generate_fund_report(self, funds_data: List[Dict]) -> str:
        """生成基金持仓分析报告"""
        report = []
        report.append("=" * 90)
        report.append("📦 基金持仓追踪")
        report.append("=" * 90)
        report.append("")
        
        # 汇总
        up_count = sum(1 for f in funds_data if f.get('change_pct', 0) > 0)
        down_count = sum(1 for f in funds_data if f.get('change_pct', 0) < 0)
        avg_change = sum(f.get('change_pct', 0) for f in funds_data) / len(funds_data) if funds_data else 0
        
        report.append(f"📊 持仓概览:")
        report.append(f"   持仓基金: {len(funds_data)}只")
        report.append(f"   今日上涨: {up_count}只 | 下跌: {down_count}只")
        report.append(f"   平均涨跌: {avg_change:+.2f}%")
        report.append("")
        
        # 各基金详情
        report.append("📝 各基金详情:")
        report.append("")
        
        for i, fund in enumerate(funds_data, 1):
            change = fund.get('change_pct', 0)
            emoji = '🟢' if change > 0 else ('🔴' if change < 0 else '⚡')
            
            report.append(f"   {i}. {emoji} {fund['name']} ({fund['code']})")
            report.append(f"      类型: {fund['type']} | 风险: {fund['risk']}")
            if fund.get('nav'):
                report.append(f"      净值: {fund['nav']:.4f} | 涨跌: {change:+.2f}%")
            report.append(f"      板块: {fund['sector']}")
            report.append(f"      基金经理: {fund['fund_manager']}")
            report.append("")
        
        # 板块分布
        report.append("🏷️ 板块分布:")
        sectors = {}
        for fund in funds_data:
            sector = fund.get('sector', '未知')
            for s in sector.split('/'):
                s = s.strip()
                if s:
                    sectors[s] = sectors.get(s, 0) + 1
        
        for sector, count in sorted(sectors.items(), key=lambda x: -x[1]):
            report.append(f"   • {sector}: {count}只基金覆盖")
        report.append("")
        
        # 风险提示
        report.append("💡 持仓分析建议:")
        report.append("")
        
        # 分析集中度
        tech_count = sum(1 for f in funds_data if any(k in f.get('sector', '') for k in ['半导体', '芯片', 'TMT', '信息产业', 'AI']))
        if tech_count >= 3:
            report.append(f"   ⚠️ 科技板块集中度高（{tech_count}只），注意行业系统性风险")
        
        bond_count = sum(1 for f in funds_data if '债' in f.get('type', ''))
        if bond_count >= 1:
            report.append(f"   ✅ 有{bond_count}只债券基金作为防御配置")
        
        qdii_count = sum(1 for f in funds_data if 'QDII' in f.get('type', ''))
        if qdii_count >= 1:
            report.append(f"   ✅ 有{qdii_count}只QDII基金实现全球配置")
        
        report.append("")
        report.append("   📌 重要提示:")
        report.append("   • 基金净值数据来自天天基金，仅供参考")
        report.append("   • 基金投资有风险，过往业绩不代表未来表现")
        report.append("   • 建议定期审视持仓，根据市场环境调整配置")
        report.append("")
        
        return '\n'.join(report)


def main():
    """主函数：测试基金追踪"""
    print("=" * 90)
    print("📦 基金持仓追踪系统")
    print("=" * 90)
    print()
    
    tracker = FundTracker()
    
    # 获取所有基金数据
    print("📡 获取基金最新净值...")
    funds_data = tracker.fetch_all_funds()
    print(f"✅ 获取到 {len(funds_data)} 只基金数据")
    print()
    
    # 生成报告
    report = tracker.generate_fund_report(funds_data)
    print(report)
    
    return funds_data


if __name__ == '__main__':
    main()
