"""诊断买入失败问题"""
import os
import sys
from dotenv import load_dotenv
import traceback

# 加载环境变量
load_dotenv()

# 设置代理
if os.getenv('USE_PROXY', 'false').lower() == 'true':
    proxy_url = os.getenv('HTTP_PROXY', 'http://127.0.0.1:7890')
    os.environ['HTTP_PROXY'] = proxy_url
    os.environ['HTTPS_PROXY'] = proxy_url
    print(f"✓ 已设置代理: {proxy_url}")

from config import Config
from bot import OKXTrader

def diagnose_buy_issue():
    """诊断买入功能问题"""
    print("="*60)
    print("诊断买入功能")
    print("="*60)
    
    try:
        # 1. 检查配置
        print("\n1. 检查配置...")
        print(f"   API Key: {'*'*10}{Config.OKX_API_KEY[-4:]}")
        print(f"   模拟盘: {Config.OKX_SIMULATED}")
        print(f"   交易对: {Config.TRADING_SYMBOL}")
        
        # 2. 初始化交易器
        print("\n2. 初始化交易器...")
        trader = OKXTrader(
            Config.OKX_API_KEY,
            Config.OKX_SECRET_KEY,
            Config.OKX_PASSPHRASE,
            Config.OKX_SIMULATED,
            use_proxy=Config.USE_PROXY,
            proxy_url=Config.HTTP_PROXY
        )
        print("   ✓ 交易器初始化成功")
        
        # 3. 检查账户余额
        print("\n3. 检查账户余额...")
        balance = trader.get_balance()
        if balance['success']:
            print(f"   USDT: ${balance['usdt']:.2f}")
            print(f"   BTC: {balance['btc']:.8f}")
            
            if balance['usdt'] < 10:
                print("   ⚠️ USDT余额低于10，可能无法满足最小交易要求")
        else:
            print(f"   ❌ 获取余额失败: {balance.get('error')}")
            return
        
        # 4. 获取当前价格
        print("\n4. 获取当前价格...")
        price = trader.get_ticker(Config.TRADING_SYMBOL)
        if price:
            print(f"   BTC价格: ${price:,.2f}")
            min_trade_value = 0.00001 * price
            print(f"   最小交易量价值: ${min_trade_value:.2f}")
        else:
            print("   ❌ 无法获取价格")
            return
        
        # 5. 测试买入功能（极小额）
        if balance['usdt'] >= 10:
            print("\n5. 测试买入功能（小额测试）...")
            test_amount = 10.0  # 测试用10 USDT
            
            print(f"   测试金额: ${test_amount}")
            print(f"   预计买入: {test_amount/price:.8f} BTC")
            
            # 获取用户确认
            confirm = input("\n   是否执行测试买入？(y/n): ")
            if confirm.lower() == 'y':
                print("\n   执行买入...")
                
                # 直接测试buy_market函数
                try:
                    result = trader.buy_market(
                        Config.TRADING_SYMBOL,
                        test_amount,
                        "诊断测试买入"
                    )
                    
                    print("\n   返回结果:")
                    print(f"   成功: {result['success']}")
                    if result['success']:
                        print(f"   订单ID: {result.get('order_id')}")
                        print(f"   价格: ${result.get('price', 0):.2f}")
                        print(f"   数量: {result.get('amount', 0):.8f} BTC")
                        print("   ✅ 买入功能正常！")
                    else:
                        print(f"   错误: {result.get('error')}")
                        print("   ❌ 买入失败，请检查错误信息")
                        
                        # 额外诊断
                        if 'Insufficient balance' in str(result.get('error', '')):
                            print("\n   💡 提示: 余额不足，请充值USDT")
                        elif 'Parameter' in str(result.get('error', '')):
                            print("\n   💡 提示: 参数错误，可能是API格式问题")
                        elif 'Permission' in str(result.get('error', '')):
                            print("\n   💡 提示: 权限问题，请检查API权限设置")
                            print("      - 需要开启'交易'权限")
                            print("      - 模拟盘和实盘API不能混用")
                        
                except Exception as e:
                    print(f"\n   ❌ 执行出错: {e}")
                    print("\n   详细错误:")
                    traceback.print_exc()
                    
                    # 这就是之前的bug位置
                    if "name 'amount' is not defined" in str(e):
                        print("\n   💡 发现BUG: buy_market函数中使用了未定义的变量'amount'")
                        print("      这个BUG已经在最新版本中修复")
                        print("      请确保已应用修复：第527行 amount -> btc_amount")
            else:
                print("   跳过测试")
        else:
            print("\n5. ⚠️ USDT余额不足，无法测试买入")
        
        # 6. 检查日志目录
        print("\n6. 检查日志系统...")
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        if os.path.exists(log_dir):
            print(f"   日志目录: {log_dir}")
            log_files = os.listdir(log_dir)
            if log_files:
                print(f"   日志文件: {', '.join(log_files[-3:])}")  # 显示最近3个
            else:
                print("   ⚠️ 没有日志文件")
        else:
            print("   ⚠️ 日志目录不存在")
            os.makedirs(log_dir, exist_ok=True)
            print("   ✓ 已创建日志目录")
        
        print("\n" + "="*60)
        print("诊断完成！")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 诊断过程出错: {e}")
        print("\n详细错误信息:")
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_buy_issue()
