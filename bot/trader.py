"""OKX交易执行器"""
import okx.Account as Account
import okx.MarketData as MarketData
import okx.Trade as Trade
from typing import Dict, Optional, List
import time
import pandas as pd
import urllib3
from functools import wraps
import os

# 禁用SSL警告（仅用于测试，生产环境不建议）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def retry_on_error(max_retries=3, delay=2):
    """API调用重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"  ⚠️ {func.__name__}失败 (尝试{attempt + 1}/{max_retries}): {str(e)[:50]}")
                        print(f"  等待{delay}秒后重试...")
                        time.sleep(delay)
                    else:
                        print(f"  ❌ {func.__name__}重试{max_retries}次后仍失败: {e}")
                        raise
        return wrapper
    return decorator


class OKXTrader:
    """OKX交易执行器"""
    
    def __init__(self, api_key: str, secret_key: str, passphrase: str, simulated: bool = True, use_proxy: bool = False, proxy_url: str = None):
        """
        初始化
        :param api_key: API Key
        :param secret_key: Secret Key
        :param passphrase: Passphrase
        :param simulated: 是否使用模拟盘
        :param use_proxy: 是否使用代理
        :param proxy_url: 代理地址
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.simulated = simulated
        
        # 设置代理（通过环境变量）
        if use_proxy and proxy_url:
            os.environ['HTTP_PROXY'] = proxy_url
            os.environ['HTTPS_PROXY'] = proxy_url
            print(f"✓ 已配置代理: {proxy_url}")
        
        # 初始化API客户端
        flag = '1' if simulated else '0'  # 1=模拟盘, 0=实盘
        
        self.account_api = Account.AccountAPI(api_key, secret_key, passphrase, False, flag)
        self.market_api = MarketData.MarketAPI(api_key, secret_key, passphrase, False, flag)
        self.trade_api = Trade.TradeAPI(api_key, secret_key, passphrase, False, flag)
    
    @retry_on_error(max_retries=3, delay=2)
    def get_balance(self) -> Dict:
        """获取账户余额"""
        result = self.account_api.get_account_balance()
        
        if result['code'] != '0':
            return {'success': False, 'error': result['msg']}
        
        balances = {}
        for item in result['data']:
            for detail in item.get('details', []):
                ccy = detail.get('ccy')
                available = float(detail.get('availBal', 0))
                balances[ccy] = available
        
        return {
            'success': True,
            'usdt': balances.get('USDT', 0),
            'btc': balances.get('BTC', 0)
        }
    
    @retry_on_error(max_retries=3, delay=2)
    def get_spot_avg_cost(self, symbol: str = 'BTC-USDT', current_balance: float = 0) -> Dict:
        """
        获取现货持仓的平均成本价（从成交记录计算）
        OKX API: GET /api/v5/trade/fills-history (获取3个月内成交记录)
        :param symbol: 交易对，如 BTC-USDT
        :param current_balance: 当前BTC余额
        :return: 平均成本价字典
        """
        try:
            if current_balance <= 0.00000001:
                return {
                    'success': True,
                    'has_position': False,
                    'amount': 0,
                    'avg_price': 0
                }
            
            # 获取最近的成交记录（最多100条，约3个月）
            result = self.trade_api.get_fills_history(instType='SPOT', instId=symbol, limit='100')
            
            if result['code'] != '0':
                return {'success': False, 'error': result['msg']}
            
            fills = result.get('data', [])
            
            if not fills:
                return {
                    'success': True,
                    'has_position': False,
                    'amount': current_balance,
                    'avg_price': 0
                }
            
            # 从旧到新正序处理，用FIFO原则模拟持仓变化
            # 逻辑：维护一个持仓队列，BUY追加，SELL从头部扣除
            fills_reversed = list(reversed(fills))  # 从旧到新排序
            position_queue = []  # [(amount, price), ...] 先进先出
            buy_count = 0
            
            for fill in fills_reversed:
                side = fill.get('side')
                fill_sz = float(fill.get('fillSz', 0))
                fill_px = float(fill.get('fillPx', 0))
                
                if side == 'buy':
                    # 买入：加入持仓队列
                    position_queue.append({'amount': fill_sz, 'price': fill_px})
                    buy_count += 1
                elif side == 'sell':
                    # 卖出：从队列头部扣除（先进先出）
                    remaining_to_sell = fill_sz
                    while remaining_to_sell > 0.00000001 and position_queue:
                        first_position = position_queue[0]
                        if first_position['amount'] <= remaining_to_sell:
                            # 这笔买入全部卖出
                            remaining_to_sell -= first_position['amount']
                            position_queue.pop(0)
                        else:
                            # 部分卖出
                            first_position['amount'] -= remaining_to_sell
                            remaining_to_sell = 0
            
            # 计算队列中剩余持仓的加权平均成本
            total_cost = sum(pos['amount'] * pos['price'] for pos in position_queue)
            total_accounted = sum(pos['amount'] for pos in position_queue)
            if total_accounted > 0:
                avg_cost = total_cost / total_accounted
                return {
                    'success': True,
                    'has_position': True,
                    'amount': current_balance,
                    'avg_price': avg_cost,
                    'total_accounted': total_accounted,  # FIFO计算出的持仓数量
                    'fills_count': buy_count,  # 总买入笔数
                    'position_pieces': len(position_queue)  # 剩余持仓分几笔买入
                }
            else:
                return {
                    'success': True,
                    'has_position': False,
                    'amount': current_balance,
                    'avg_price': 0
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @retry_on_error(max_retries=3, delay=2)
    def get_ticker(self, symbol: str = 'BTC-USDT') -> Optional[float]:
        """
        获取实时价格
        :param symbol: 交易对
        :return: 价格
        """
        try:
            result = self.market_api.get_ticker(instId=symbol)
            
            if result['code'] != '0' or not result['data']:
                return None
            
            last_price = float(result['data'][0]['last'])
            return last_price
        
        except Exception as e:
            print(f"获取价格失败: {e}")
            return None
    
    @retry_on_error(max_retries=3, delay=2)
    def get_multi_timeframe_data(self, symbol: str = 'BTC-USDT') -> Optional[Dict]:
        """
        获取多时间周期K线数据
        :param symbol: 交易对
        :return: 多时间周期数据
        """
        try:
            result = {
                'symbol': symbol,
                'timeframes': {}
            }
            
            # 获取两个时间周期的数据（针对短期交易优化）
            timeframes = [
                ('15m', 30),  # 15分钟, 30根(约7.5小时)
                ('1H', 24),   # 1小时, 24根(1天)
            ]
            
            for bar, limit in timeframes:
                # 获取K线数据
                data = self.get_kline_data(symbol, bar, limit)
                if data:
                    result['timeframes'][bar] = data
            
            # 如果所有时间周期都失败，返回None
            if not result['timeframes']:
                return None
            
            # 使用15分钟的当前价格作为主价格
            if '15m' in result['timeframes']:
                result['current_price'] = result['timeframes']['15m']['current_price']
            elif '1H' in result['timeframes']:
                result['current_price'] = result['timeframes']['1H']['current_price']
            else:
                result['current_price'] = list(result['timeframes'].values())[0]['current_price']
            
            return result
            
        except Exception as e:
            print(f"获取多时间周期数据失败: {e}")
            return None
    
    def get_kline_data(self, symbol: str = 'BTC-USDT', bar: str = '15m', limit: int = 100) -> Optional[Dict]:
        """
        获取K线数据
        :param symbol: 交易对
        :param bar: K线周期 (1m/5m/15m/30m/1H/4H/1D)
        :param limit: 获取数量
        :return: K线原始数据
        """
        try:
            # 获取K线数据
            result = self.market_api.get_candlesticks(
                instId=symbol,
                bar=bar,
                limit=str(limit)
            )
            
            if result['code'] != '0' or not result['data']:
                return None
            
            # 解析K线数据
            # OKX返回格式：[时间戳, 开盘价, 最高价, 最低价, 收盘价, 成交量, 成交额(Quote货币), 成交量(Base货币), confirm]
            klines = result['data']
            
            # 转换为DataFrame便于计算（处理可能的9列数据）
            df = pd.DataFrame(klines)
            # 只取需要的列
            df = df.iloc[:, :8]  # 取前8列
            df.columns = [
                'timestamp', 'open', 'high', 'low', 'close', 
                'volume', 'volCcy', 'volCcyQuote'
            ]
            
            # 转换数据类型
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            # 按时间排序（从旧到新）
            df = df.sort_values('timestamp')
            
            # 直接返回K线数据，不计算技术指标
            return {
                'current_price': df['close'].iloc[-1],
                'bar_period': bar,
                'data_count': len(df),
                # K线原始数据（全部返回，让AI自己选择需要的部分）
                'recent_klines': [
                    {
                        'timestamp': int(row['timestamp']),
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': float(row['volume'])
                    }
                    for _, row in df.iterrows()
                ]
            }
            
        except Exception as e:
            print(f"获取K线数据失败: {e}")
            return None
    
    
    @retry_on_error(max_retries=3, delay=2)
    def buy_market(self, symbol: str, usdt_amount: float, reason: str = '') -> Dict:
        """
        市价买入
        :param symbol: 交易对，如 BTC-USDT
        :param usdt_amount: 使用的USDT金额（直接传入USDT，更精准）
        :param reason: 交易原因
        :return: 交易结果
        """
        try:
            # 获取当前价格（用于日志显示）
            current_price = self.get_ticker(symbol)
            if not current_price:
                return {
                    'success': False,
                    'error': '无法获取当前价格',
                    'reason': reason
                }
            
            print(f"  调用OKX API下单...")
            print(f"  参数: symbol={symbol}, usdt_amount={usdt_amount:.2f}, tdMode=cash")
            
            result = self.trade_api.place_order(
                instId=symbol,
                tdMode='cash',  # 现货交易
                side='buy',
                ordType='market',  # 市价单
                sz=str(usdt_amount),  # 市价买单传USDT金额
                tgtCcy='quote_ccy'  # 指定sz单位为报价货币（USDT）
            )
            
            print(f"  API返回: code={result.get('code')}, msg={result.get('msg')}")
            
            if result['code'] != '0':
                print(f"  ❌ 订单失败详情: {result}")
                return {
                    'success': False,
                    'error': f"OKX: {result.get('msg')} (code: {result.get('code')})",
                    'reason': reason
                }
            
            order_id = result['data'][0]['ordId']
            
            # 等待订单成交
            time.sleep(1)
            
            # 查询订单详情
            order_info = self.get_order_info(symbol, order_id)
            
            # 计算实际买入的BTC数量
            btc_amount = order_info.get('filled_amount', usdt_amount / current_price)
            
            return {
                'success': True,
                'action': 'BUY',
                'order_id': order_id,
                'price': order_info.get('avg_price', current_price),
                'amount': btc_amount,
                'reason': reason
            }
        
        except Exception as e:
            # 打印详细错误信息用于调试
            print(f"  ❌ buy_market异常: {e}")
            import traceback
            print(f"  错误堆栈:\n{traceback.format_exc()}")
            
            return {
                'success': False,
                'error': str(e),
                'reason': reason
            }
    
    @retry_on_error(max_retries=3, delay=2)
    def sell_market(self, symbol: str, amount: float, reason: str = '') -> Dict:
        """
        市价卖出
        :param symbol: 交易对
        :param amount: BTC数量
        :param reason: 交易原因
        :return: 交易结果
        """
        try:
            # OKX要求：BTC数量精度最多8位小数，去掉尾部的0
            # 使用Decimal确保精确格式化
            from decimal import Decimal, ROUND_DOWN
            
            # 转换为Decimal并量化到8位小数
            amount_decimal = Decimal(str(amount)).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
            # 转为字符串并去掉尾部的0
            formatted_amount = format(amount_decimal, 'f').rstrip('0').rstrip('.')
            
            print(f"  调用OKX API卖出...")
            print(f"  原始数量: {amount}")
            print(f"  格式化后: {formatted_amount}")
            print(f"  参数: symbol={symbol}, tdMode=cash, side=sell")
            
            result = self.trade_api.place_order(
                instId=symbol,
                tdMode='cash',
                side='sell',
                ordType='market',
                sz=formatted_amount,
                tgtCcy='base_ccy'  # 指定sz单位为基础货币（BTC）
            )
            
            print(f"  API返回: code={result.get('code')}, msg={result.get('msg')}")
            
            if result['code'] == '0':
                # 成功
                order_id = result['data'][0]['ordId']
                # 查询订单详情获取实际成交价格和数量
                order_detail = self.trade_api.get_order(instId=symbol, ordId=order_id)
                
                if order_detail['code'] == '0' and order_detail['data']:
                    fill_price = float(order_detail['data'][0]['fillPx']) if order_detail['data'][0]['fillPx'] else 0
                    fill_size = float(order_detail['data'][0]['fillSz']) if order_detail['data'][0]['fillSz'] else amount
                    
                    return {
                        'success': True,
                        'order_id': order_id,
                        'price': fill_price if fill_price > 0 else None,
                        'amount': fill_size,
                        'reason': reason
                    }
            
            # 失败 - 打印详细错误
            error_detail = result.get('data', [{}])[0] if result.get('data') else {}
            print(f"  ❌ OKX API错误详情:")
            print(f"     code: {result.get('code')}")
            print(f"     msg: {result.get('msg')}")
            if error_detail:
                print(f"     sCode: {error_detail.get('sCode')}")
                print(f"     sMsg: {error_detail.get('sMsg')}")
            
            return {
                'success': False,
                'error': f"OKX: {result['msg']} (code: {result['code']})",
                'reason': reason
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'reason': reason
            }
    
    def get_order_info(self, symbol: str, order_id: str) -> Dict:
        """获取订单信息"""
        try:
            result = self.trade_api.get_order(instId=symbol, ordId=order_id)
            
            if result['code'] != '0' or not result['data']:
                return {}
            
            order = result['data'][0]
            return {
                'avg_price': float(order.get('avgPx', 0)),
                'filled_amount': float(order.get('accFillSz', 0)),
                'status': order.get('state', '')
            }
        
        except Exception as e:
            print(f"获取订单信息失败: {e}")
            return {}
