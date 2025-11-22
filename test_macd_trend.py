"""测试MACD趋势分析改进"""
import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置代理（如果需要）
if os.getenv('USE_PROXY', 'false').lower() == 'true':
    proxy_url = os.getenv('HTTP_PROXY', 'http://127.0.0.1:7890')
    os.environ['HTTP_PROXY'] = proxy_url
    os.environ['HTTPS_PROXY'] = proxy_url
    print(f"✓ 已设置代理: {proxy_url}")

from config import Config
from bot import OKXTrader
import json

def test_macd_trend():
    """测试MACD趋势分析功能"""
    print("="*60)
    print("测试MACD趋势分析功能")
    print("="*60)
    
    # 初始化交易器
    trader = OKXTrader(
        Config.OKX_API_KEY,
        Config.OKX_SECRET_KEY,
        Config.OKX_PASSPHRASE,
        Config.OKX_SIMULATED,
        use_proxy=Config.USE_PROXY,
        proxy_url=Config.HTTP_PROXY
    )
    
    # 测试不同时间周期
    timeframes = ['15m', '1H', '4H']
    
    for tf in timeframes:
        print(f"\n📊 测试{tf}周期...")
        data = trader.get_kline_data('BTC-USDT', tf, 100)
        
        if data:
            print(f"  ✓ 当前价格: ${data['current_price']:,.2f}")
            print(f"  ✓ MA(7/25/99): ${data['ma7']:,.0f} / ${data['ma25']:,.0f} / ${data['ma99']:,.0f}")
            print(f"  ✓ RSI: {data['rsi']:.1f}")
            
            # 重点测试MACD趋势
            print(f"\n  📈 MACD分析:")
            print(f"    - DIF: {data['macd']:+.1f}")
            print(f"    - DEA: {data['macd_signal']:+.1f}")
            print(f"    - 柱状图: {data['macd_hist']:+.1f}")
            print(f"    - **趋势**: {data.get('macd_trend', 'N/A')}")
            print(f"    - **强度**: {data.get('macd_strength', 0):.1%}")
            print(f"    - **动量**: {data.get('macd_momentum', 0):+.2f}")
            
            # 显示最近5根MACD柱
            macd_hist_list = data.get('macd_hist_list', [])
            if macd_hist_list:
                print(f"    - 最近5根MACD柱: {[f'{x:+.1f}' for x in macd_hist_list]}")
                
                # 分析变化趋势
                if len(macd_hist_list) > 1:
                    changes = [macd_hist_list[i] - macd_hist_list[i-1] 
                              for i in range(1, len(macd_hist_list))]
                    print(f"    - 变化趋势: {[f'{x:+.2f}' for x in changes]}")
                    
                    # 判断建议
                    if data.get('macd_trend') == 'BULLISH' and data.get('macd_strength', 0) > 0.6:
                        print(f"    💡 建议: 上涨趋势明确，可考虑买入")
                    elif data.get('macd_trend') == 'BEARISH' and data.get('macd_strength', 0) > 0.6:
                        print(f"    💡 建议: 下跌趋势明确，应考虑卖出或观望")
                    else:
                        print(f"    💡 建议: 趋势不明确，建议观望")
            
            print(f"\n  📊 其他指标:")
            print(f"    - 布林带: 上${data['bb_upper']:,.0f} 中${data['bb_middle']:,.0f} 下${data['bb_lower']:,.0f}")
            print(f"    - 成交量比率: {data['volume_ratio']:.2f}")
            print(f"    - 总体趋势: {data['trend']}")
        else:
            print(f"  ❌ 获取{tf}数据失败")
    
    print("\n" + "="*60)
    print("✓ 测试完成！")
    print("="*60)
    
    # 测试多时间周期数据
    print("\n测试多时间周期数据获取...")
    multi_data = trader.get_multi_timeframe_data('BTC-USDT')
    
    if multi_data:
        print("✓ 成功获取多时间周期数据")
        for tf, tf_data in multi_data['timeframes'].items():
            trend = tf_data.get('macd_trend', 'N/A')
            strength = tf_data.get('macd_strength', 0)
            print(f"  {tf}: MACD趋势={trend}, 强度={strength:.1%}")
    else:
        print("❌ 获取多时间周期数据失败")

if __name__ == "__main__":
    try:
        test_macd_trend()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
