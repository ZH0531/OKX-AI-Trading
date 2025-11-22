"""AI炒币机器人主程序"""
import os
# ⚠️ 重要：必须在导入任何网络库之前设置代理环境变量
# python-okx库底层使用requests，需要提前设置环境变量
from dotenv import load_dotenv
load_dotenv()  # 先加载.env文件

# 设置代理（必须在导入okx之前！）
if os.getenv('USE_PROXY', 'false').lower() == 'true':
    proxy_url = os.getenv('HTTP_PROXY', 'http://127.0.0.1:7890')
    os.environ['HTTP_PROXY'] = proxy_url
    os.environ['HTTPS_PROXY'] = proxy_url
    os.environ['http_proxy'] = proxy_url  # 小写也要设置
    os.environ['https_proxy'] = proxy_url
    print(f"✓ 已设置全局代理: {proxy_url}")

import time
import sys
import json
from datetime import datetime, timedelta
from config import Config
from bot import OKXTrader, TradingStrategy, Database
from bot.logger import get_logger


class TradingBot:
    """交易机器人"""
    
    @staticmethod
    def calculate_next_check_time(kline_interval_minutes=15):
        """
        计算下一次检查时间（在K线刚成型时）
        
        Args:
            kline_interval_minutes: K线周期（分钟）
            
        Returns:
            等待秒数
        """
        now = datetime.now()
        current_minute = now.minute
        
        # 计算当前所在K线的开始分钟
        kline_start_minute = (current_minute // kline_interval_minutes) * kline_interval_minutes
        
        # 计算下一根K线的开始时间（即当前K线的结束时间）
        next_kline_minute = kline_start_minute + kline_interval_minutes
        
        # 如果超过60分钟，需要进入下一小时
        if next_kline_minute >= 60:
            target_time = now.replace(minute=next_kline_minute - 60, second=0, microsecond=0) + timedelta(hours=1)
        else:
            target_time = now.replace(minute=next_kline_minute, second=0, microsecond=0)
        
        # 如果目标时间已过，计算下一个K线的开始时间
        if target_time <= now:
            target_time += timedelta(minutes=kline_interval_minutes)
        
        wait_seconds = (target_time - now).total_seconds()
        return int(max(wait_seconds, 10))  # 至少等10秒
    
    def __init__(self):
        # 验证配置
        errors = Config.validate_config()
        if errors:
            print("❌ 配置错误:")
            for error in errors:
                print(f"  - {error}")
            print("\n请检查 .env 文件")
            sys.exit(1)
        
        # 打印配置
        Config.print_config()
        
        # 初始化组件
        print("\n正在初始化...")
        self.trader = OKXTrader(
            Config.OKX_API_KEY,
            Config.OKX_SECRET_KEY,
            Config.OKX_PASSPHRASE,
            Config.OKX_SIMULATED,
            use_proxy=Config.USE_PROXY,
            proxy_url=Config.HTTP_PROXY
        )
        
        from bot.ai_analyzer import AIAnalyzer
        self.ai = AIAnalyzer(
            Config.DEEPSEEK_API_KEY,
            Config.DEEPSEEK_BASE_URL
        )
        
        # 策略初始化时不设置固定值
        self.strategy = TradingStrategy()
        
        self.db = Database(Config.DATABASE_PATH)
        
        # 初始化日志
        self.logger = get_logger()
        
        self.running = False
        print("✓ 初始化完成\n")
        self.logger.log_info("交易机器人启动")
    
    def check_balance(self) -> bool:
        """检查余额"""
        balance = self.trader.get_balance()
        
        if not balance['success']:
            print(f"❌ 获取余额失败: {balance.get('error')}")
            return False
        
        print(f"账户余额:")
        print(f"  USDT: ${balance['usdt']:,.2f}")
        print(f"  BTC: {balance['btc']:.6f}")
        return True
    
    def run_once(self):
        """执行一次交易循环"""
        # 1. 获取多时间周期K线数据
        market_data = self.trader.get_multi_timeframe_data(Config.TRADING_SYMBOL)
        
        if not market_data:
            print("❌ 获取市场数据失败")
            price = self.trader.get_ticker(Config.TRADING_SYMBOL)
            if price is None:
                print("❌ 获取价格失败")
                return
            market_data = {'current_price': price, 'timeframes': {}}
        else:
            price = market_data['current_price']
        
        # 2. 获取余额
        balance = self.trader.get_balance()
        if not balance['success']:
            print(f"❌ 获取余额失败: {balance.get('error')}")
            return
        
        usdt = balance['usdt']
        btc = balance['btc']
        total_value = btc * price + usdt
        
        # 3. 获取最近交易记录
        recent_trades = self.db.get_recent_trades(5)
        
        # 5. 准备持仓信息（优先从OKX API获取，包含准确的成本价）
        # 优先从OKX API获取现货平均成本价（从成交记录计算）
        avg_price_source = '未知'
        position_data = self.trader.get_spot_avg_cost(Config.TRADING_SYMBOL, btc)
        
        if position_data['success'] and position_data.get('avg_price', 0) > 0:
            # 从成交记录成功计算出平均成本价
            avg_price = position_data.get('avg_price')
            fills_count = position_data.get('fills_count', 0)
            avg_price_source = f'OKX成交记录({fills_count}笔BUY)'
        else:
            # API没有持仓数据，尝试其他方式获取成本价
            avg_price = self.strategy.last_buy_price
            if avg_price:
                avg_price_source = '本地记录'
            elif recent_trades:
                # 从最近交易记录中找最后一次BUY的价格
                for trade in recent_trades:
                    if trade.get('action') == 'BUY':
                        avg_price = trade.get('price')
                        avg_price_source = '数据库'
                        break
            
            if not avg_price:
                avg_price = price  # 实在找不到就用当前价
                avg_price_source = '当前价(未知)'
        
        current_position = {
            'has_position': btc >= 0.00001,  # 大于等于最小交易量才算有持仓
            'amount': btc,  # 实际余额
            'avg_price': avg_price
        }
        
        # 6. AI决策分析（使用对话历史保持上下文）
        
        performance_stats = self.db.get_recent_performance(20)
        recent_decisions = self.db.get_recent_ai_decisions(10)  # 获取最近10条AI决策记录
        
        analysis = self.ai.analyze_market(
            price, btc, usdt,
            market_data=market_data,
            current_position=current_position,
            recent_trades=recent_trades,
            performance_stats=performance_stats,
            recent_decisions=recent_decisions  # 传入最近10条决策作为上下文
        )
        
        if not analysis['success']:
            error_msg = f"AI分析失败: {analysis.get('error')}"
            print(f"\n❌ {error_msg}")
            self.logger.log_error(error_msg)
            return
        
        # 记录AI决策到日志（包括HOLD）
        self.logger.log_ai_decision(analysis, price, {'usdt': usdt, 'btc': btc})
        
        # 记录状态（将AI建议以JSON字符串形式保存，方便前端结构化展示）
        ai_status_payload = {
            "action": analysis.get("action"),
            "confidence": analysis.get("confidence"),
            "risk_level": analysis.get("risk_level"),
            "reason": analysis.get("reason"),
            "suggested_amount": analysis.get("suggested_amount"),
        }
        
        # 获取AI推理过程
        ai_reasoning = analysis.get("reasoning", "")
        
        self.db.add_status(
            price,
            usdt,
            btc,
            total_value,
            json.dumps(ai_status_payload, ensure_ascii=False),
            ai_reasoning  # 保存推理过程
        )
        
        # 6. 执行交易（使用AI建议的参数，根据配置的最低信心阈值）
        if analysis['action'] == 'BUY':
            if analysis['confidence'] < Config.AI_MIN_CONFIDENCE:
                msg = f"⚠️ AI建议BUY但信心不足({analysis['confidence']}% < {Config.AI_MIN_CONFIDENCE}%)，跳过"
                print(msg)
                self.logger.log_warning(msg)
                return
            
            # 获取AI建议的USDT金额（兼容旧格式suggested_amount）
            if 'suggested_usdt' not in analysis:
                # 兼容旧格式：如果AI输出的是suggested_amount（BTC），转换为USDT
                if 'suggested_amount' in analysis:
                    suggested_usdt = analysis['suggested_amount'] * price
                    msg = f"⚠️ AI使用旧格式(suggested_amount={analysis['suggested_amount']:.8f} BTC)，已转换为${suggested_usdt:.2f} USDT"
                    print(msg)
                    self.logger.log_warning(msg)
                else:
                    msg = "❌ AI建议买入但没有提供交易参数（需要suggested_usdt或suggested_amount）"
                    print(msg)
                    self.logger.log_error(msg)
                    return
            else:
                suggested_usdt = analysis['suggested_usdt']
            
            # 计算最大可用USDT（保留5%余量用于滑点和手续费）
            max_usdt_available = usdt * 0.95
            
            # 根据余额限制计算实际交易金额
            actual_usdt = min(suggested_usdt, max_usdt_available)
            
            # 检查是否满足OKX最小交易量（0.00001 BTC）对应的USDT金额
            min_btc = 0.00001
            min_usdt_value = min_btc * price  # 约0.9-1 USDT（随BTC价格浮动）
            if actual_usdt < min_usdt_value:
                msg = f"⚠️ 交易金额太小(${actual_usdt:.2f} < ${min_usdt_value})，跳过买入"
                print(msg)
                self.logger.log_warning(msg)
                return
            
            # 检查余额是否充足
            if usdt < actual_usdt:
                msg = f"⚠️ USDT余额不足: 需要${actual_usdt:.2f}, 实际${usdt:.2f}，跳过买入"
                print(msg)
                self.logger.log_warning(msg)
                return
            
            # 打印交易前的详细信息
            print(f"\n💰 准备买入:")
            print(f"  AI建议金额: ${suggested_usdt:.2f}")
            print(f"  实际买入金额: ${actual_usdt:.2f}")
            print(f"  当前BTC价格: ${price:,.2f}")
            print(f"  预计买入BTC: {actual_usdt / price:.8f}")
            print(f"  当前USDT余额: ${usdt:.2f}")
            
            try:
                result = self.trader.buy_market(
                    Config.TRADING_SYMBOL,
                    actual_usdt,
                    analysis['reason']
                )
            except Exception as e:
                # 捕获并记录买入异常
                error_msg = f"买入执行异常: {e}"
                print(f"\n❌ {error_msg}")
                self.logger.log_error(error_msg)
                return
            
            if result['success']:
                # 记录交易日志
                self.logger.log_trade('BUY', result['price'], result['amount'], 'SUCCESS')
                
                # 记录到数据库
                balance_after = self.trader.get_balance()
                self.db.add_trade(
                    'BUY',
                    result['price'],
                    result['amount'],
                    result['reason'],
                    0,
                    balance_after.get('usdt', 0),
                    balance_after.get('btc', 0)
                )
                
                # 记录买入价格（用于后续计算盈亏）
                self.strategy.set_position(
                    price=result['price'],
                    amount=result['amount']  # 使用实际成交的BTC数量
                )
            else:
                error_msg = f"买入失败: {result.get('error')}"
                print(f"\n❌ {error_msg}")
                self.logger.log_error(error_msg)
        
        elif analysis['action'] == 'SELL':
            if analysis['confidence'] < Config.AI_MIN_CONFIDENCE:
                msg = f"⚠️ AI建议SELL但信心不足({analysis['confidence']}% < {Config.AI_MIN_CONFIDENCE}%)，跳过"
                print(msg)
                self.logger.log_warning(msg)
                return
            
            # 获取AI建议的交易量（必须存在）
            if 'suggested_amount' not in analysis:
                return
            
            suggested_amount = analysis['suggested_amount']
            actual_amount = min(suggested_amount, btc)
            
            # 检查OKX最小交易量（0.00001 BTC）
            min_btc_amount = 0.00001
            
            if actual_amount < min_btc_amount:
                return
            
            result = self.trader.sell_market(
                Config.TRADING_SYMBOL,
                actual_amount,
                analysis['reason']
            )
            
            if result['success']:
                # 计算实际利润（优先从OKX API获取平均成本价）
                avg_cost_data = self.trader.get_spot_avg_cost(Config.TRADING_SYMBOL, btc)
                avg_cost = 0
                
                if avg_cost_data['success'] and avg_cost_data.get('avg_price', 0) > 0:
                    # 从OKX API获取到的平均成本价（最准确）
                    avg_cost = avg_cost_data['avg_price']
                elif self.strategy.last_buy_price:
                    # 退而求其次，使用内存中的最后买入价
                    avg_cost = self.strategy.last_buy_price
                
                profit = (price - avg_cost) * actual_amount if avg_cost > 0 else 0
                
                # 记录交易日志
                self.logger.log_trade('SELL', result['price'], result['amount'], 'SUCCESS')
                self.logger.log_info(f"盈亏: ${profit:+,.2f} (成本: ${avg_cost:,.2f})")
                
                balance_after = self.trader.get_balance()
                self.db.add_trade(
                    'SELL',
                    result['price'],
                    result['amount'],
                    result['reason'],
                    profit,
                    balance_after.get('usdt', 0),
                    balance_after.get('btc', 0)
                )
                
                self.strategy.clear_position()
            else:
                error_msg = f"卖出失败: {result.get('error')}"
                print(f"\n❌ {error_msg}")
                self.logger.log_error(error_msg)
    
    def run(self):
        """运行机器人"""
        print("🚀 AI炒币机器人启动!")
        
        # 检查余额
        if not self.check_balance():
            return
        
        print(f"\n机器人将在每根15分钟K线刚成型时检查市场（准点：00/15/30/45分）")
        print("按 Ctrl+C 停止\n")
        
        self.running = True
        
        try:
            while self.running:
                try:
                    self.run_once()
                except Exception as e:
                    error_msg = f"执行出错: {e}"
                    print(f"\n❌ {error_msg}")
                    self.logger.log_error(error_msg)
                    import traceback
                    traceback.print_exc()
                
                # 计算下一次检查时间（15分钟K线刚成型时）
                wait_seconds = self.calculate_next_check_time(
                    kline_interval_minutes=15
                )
                time.sleep(wait_seconds)
        
        except KeyboardInterrupt:
            print("\n\n⏹️  停止运行...")
            self.logger.log_info("用户手动停止机器人")
            self.running = False
        
        # 打印统计
        stats = self.db.get_statistics()
        stats_msg = f"""
交易统计:
  总交易次数: {stats['total_trades']}
  买入次数: {stats['buy_count']}
  卖出次数: {stats['sell_count']}
  总盈亏: ${stats['total_profit']:,.2f}
  平均盈亏: ${stats['avg_profit']:,.2f}
"""
        print("\n" + "="*60)
        print(stats_msg)
        print("="*60)
        self.logger.log_info(stats_msg)


def main():
    """主函数"""
    bot = TradingBot()
    bot.run()


if __name__ == "__main__":
    main()
