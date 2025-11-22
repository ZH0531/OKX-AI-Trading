"""DeepSeek AI分析器"""
import requests
from typing import Dict
import json


class AIAnalyzer:
    """DeepSeek AI分析器"""
    
    def __init__(self, api_key: str, base_url: str = 'https://api.deepseek.com'):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def analyze_market(self, current_price: float, btc_balance: float, 
                      usdt_balance: float, market_data: dict = None, 
                      current_position: dict = None, recent_trades: list = None,
                      performance_stats: dict = None, recent_decisions: list = None) -> Dict:
        """
        分析市场并给出交易建议
        :param current_price: 当前BTC价格
        :param btc_balance: BTC余额
        :param usdt_balance: USDT余额
        :param market_data: 多时间周期K线数据
        :param current_position: 当前持仓信息
        :param recent_trades: 最近交易记录
        :param performance_stats: 历史表现统计
        :param recent_decisions: 最近的AI决策记录（将作为messages上下文）
        :return: 分析结果
        """
        
        # 构建当前状态提示词（不包含历史决策，因为已经在messages里）
        prompt = self._build_prompt(current_price, btc_balance, usdt_balance, 
                                    market_data, current_position, recent_trades, performance_stats)
        
        try:
            # 构建完整的messages（system + 最近决策历史 + 当前请求）
            messages = [
                {
                    'role': 'system',
                    'content': self._build_system_prompt()
                }
            ]
            
            # 添加最近的AI决策作为上下文（转换为user/assistant消息对）
            if recent_decisions and len(recent_decisions) > 0:
                for decision in reversed(recent_decisions):  # 按时间顺序
                    # 用户消息：市场状态
                    user_msg = f"价格${decision.get('price', 0):,.2f}"
                    messages.append({
                        'role': 'user',
                        'content': user_msg
                    })
                    
                    # AI回复：决策（只保留content，不包含reasoning_content）
                    action = decision.get('action', 'HOLD')
                    confidence = decision.get('confidence', 0)
                    reason = decision.get('reason', '')[:100]  # 截取前100字符
                    assistant_msg = f"{action} (信心{confidence}%): {reason}"
                    messages.append({
                        'role': 'assistant',
                        'content': assistant_msg
                    })
            
            # 添加当前请求
            messages.append({
                'role': 'user',
                'content': prompt
            })
            
            # 根据DEBUG_MODE控制是否打印完整提示词
            from config import Config
            if Config.DEBUG_MODE:
                print("\n" + "="*80)
                print("📤 发送给AI的完整提示词")
                print("="*80)
                
                # 打印系统提示词
                if messages[0]['role'] == 'system':
                    print("\n【系统提示词 (System Prompt)】:")
                    print("-" * 80)
                    print(messages[0]['content'])
                    print("-" * 80)
                
                # 打印用户提示词（最后一条消息）
                print("\n【用户提示词 (User Prompt)】:")
                print("-" * 80)
                print(messages[-1]['content'])
                print("-" * 80)
                print("\n")
            
            # 使用 deepseek-reasoner 模型获取推理过程
            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers=self.headers,
                json={
                    'model': 'deepseek-reasoner',  # 使用Reasoner模型
                    'messages': messages,
                    'max_tokens': 8000,  # Reasoner需要更多token（默认32K，最大64K）
                    'response_format': {'type': 'json_object'}  # 强制JSON输出
                },
                timeout=90  # Reasoner推理需要更长时间
            )
            
            if response.status_code != 200:
                error_body = ""
                try:
                    error_body = response.text[:300]
                except Exception:
                    pass
                return {
                    'success': False,
                    'error': f'API请求失败: {response.status_code}',
                    'details': error_body
                }
            
            result = response.json()
            message = result['choices'][0]['message']
            
            # 提取决策内容和推理过程
            content = message.get('content', '')
            reasoning_content = message.get('reasoning_content', '')  # DeepSeek Reasoner的思维链
            
            # 调试模式下输出AI响应
            from config import Config
            if Config.DEBUG_MODE:
                print("\n" + "="*80)
                print("📥 AI完整响应")
                print("="*80)
                
                # 输出推理过程（如果有）- 调试模式显示完整内容
                if reasoning_content:
                    print("\n【推理过程 (Reasoning)】:")
                    print("-" * 80)
                    print(reasoning_content)  # 调试模式显示完整推理过程
                    print("-" * 80)
                
                # 输出最终决策
                print("\n【最终决策 (Decision)】:")
                print("-" * 80)
                print(content)
                print("-" * 80)
                print("\n")
            
            # 检查content是否为空（JSON Output已知问题）
            if not content or content.strip() == '':
                return {
                    'success': False,
                    'error': 'AI返回空响应，请重试'
                }
            
            # 解析AI响应
            parsed_result = self._parse_response(content, current_price)
            
            # 将推理过程添加到结果中
            if parsed_result['success'] and reasoning_content:
                parsed_result['reasoning'] = reasoning_content
            
            return parsed_result
        
        except Exception as e:
            return {
                'success': False,
                'error': f'分析失败: {str(e)}'
            }
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词（精简版）"""
        return """你是BTC短线交易AI。基于K线数据（OHLCV）直接分析价格走势和成交量变化。

核心任务：分析K线形态，判断趋势，决定BUY/SELL/HOLD。

关键约束：
- 手续费：每边0.09%，买卖共0.18%
- 最小交易：0.00001 BTC
- 无需计算技术指标，直接从K线形态判断

直接输出JSON：
{"action": "BUY/SELL/HOLD", "confidence": 0-100, "reason": "中文简短理由", "risk_level": "LOW/MEDIUM/HIGH", "suggested_usdt": 金额(BUY时), "suggested_amount": 数量(SELL时)}"""
    
    def _build_prompt(self, price: float, btc: float, usdt: float, 
                     market_data: dict, position: dict, trades: list, performance: dict = None) -> str:
        """构建提示词（精简版）"""
        # 账户状态
        total_value = btc * price + usdt
        prompt = f"""当前状态:
价格: ${price:,.0f}
余额: {btc:.8f} BTC (${btc*price:,.0f}) | ${int(usdt)} USDT
总值: ${total_value:,.0f}"""
        
        # 持仓信息
        if position and position.get('has_position') and position.get('amount', 0) >= 0.00001:
            avg_price = position.get('avg_price', price)
            pnl_percent = ((price - avg_price) / avg_price * 100) if avg_price > 0 else 0
            prompt += f"\n持仓: 成本${avg_price:,.0f} ({pnl_percent:+.1f}%)"
        
        
        
        # 直接发送完整K线数据
        if market_data and 'timeframes' in market_data:
            prompt += "\n\nK线数据（从旧到新排序）:"
            for tf in ['15m', '1H']:
                if tf in market_data['timeframes']:
                    klines = market_data['timeframes'][tf].get('recent_klines', [])
                    if klines:
                        # 15分钟发30根（7.5小时），1小时发24根（24小时）
                        num_klines = 30 if tf == '15m' else 24
                        selected_klines = klines[-num_klines:]
                        prompt += f"\n\n{tf}周期（共{len(selected_klines)}根，最新在最后）:"
                        for i, k in enumerate(selected_klines, 1):
                            # 格式：序号. [开,高,低,收,量]
                            prompt += f"\n{i:2d}. [{k['open']:.0f},{k['high']:.0f},{k['low']:.0f},{k['close']:.0f},{k['volume']:.2f}]"
        
        
        # 最近表现（如果有）
        if performance and performance.get('total_trades', 0) >= 5:
            prompt += f"\n\n最近{performance['total_trades']}笔: "
            prompt += f"胜率{performance['win_rate']:.0f}% "
            prompt += f"累计{performance['total_profit']:+.0f}$"
        
        # 最后一笔交易
        if trades and len(trades) > 0:
            last_trade = trades[0]
            prompt += f"\n上次: {last_trade.get('action')} "
            prompt += f"${last_trade.get('price', 0):,.0f}"
            if last_trade.get('profit'):
                prompt += f" ({last_trade.get('profit'):+.0f}$)"
        
        prompt += f"\n\n可用资金: ${int(usdt)} USDT | 可卖: {btc:.8f} BTC"
        
        return prompt
    
    def _parse_response(self, content: str, price: float = 0) -> Dict:
        """解析AI响应（支持JSON Output格式）"""
        try:
            thought_chain = ""
            
            # 尝试直接解析JSON（JSON Output模式）
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # 如果直接解析失败，尝试提取JSON（兼容旧格式）
                # 提取思维链（如果有）
                if "思维链分析" in content or "Chain of Thought" in content:
                    thought_start = content.find("===")
                    json_start = content.find("JSON", thought_start)
                    if thought_start != -1 and json_start != -1:
                        thought_chain = content[thought_start:json_start].strip()
                
                # 提取JSON
                start = content.find('{')
                end = content.rfind('}') + 1
                
                if start == -1 or end == 0:
                    return {
                        'success': False,
                        'error': 'AI响应格式错误'
                    }
                
                json_str = content[start:end]
                data = json.loads(json_str)
            
            # 验证必要字段
            base_fields = ['action', 'confidence', 'reason', 'risk_level']
            
            # 检查基本字段
            if not all(field in data for field in base_fields):
                return {
                    'success': False,
                    'error': 'AI响应缺少必要字段'
                }
            
            # 检查必要的交易参数
            if data['action'] == 'BUY':
                # BUY需要suggested_usdt
                if 'suggested_usdt' not in data:
                    return {
                        'success': False,
                        'error': 'AI建议BUY但缺少交易金额参数(suggested_usdt)'
                    }
            elif data['action'] == 'SELL':
                # SELL需要suggested_amount
                if 'suggested_amount' not in data:
                    return {
                        'success': False,
                        'error': 'AI建议SELL但缺少交易数量参数(suggested_amount)'
                    }
            
            # 验证action值
            if data['action'] not in ['BUY', 'SELL', 'HOLD']:
                data['action'] = 'HOLD'
            
            # 构建返回结果
            result = {
                'success': True,
                'action': data['action'],
                'confidence': data['confidence'],
                'reason': data['reason'],
                'risk_level': data['risk_level'],
                'thought_chain': thought_chain  # 保存思维链供调试
            }
            
            # 添加交易参数
            if data['action'] == 'BUY':
                suggested_usdt = float(data['suggested_usdt'])
                
                # 验证USDT金额合理性（最小1，最大100000）
                if suggested_usdt < 1 or suggested_usdt > 100000:
                    return {
                        'success': False,
                        'error': f'AI建议的USDT金额不合理: ${suggested_usdt}'
                    }
                
                result.update({
                    'suggested_usdt': suggested_usdt
                })
                
            elif data['action'] == 'SELL':
                suggested_amount = float(data['suggested_amount'])
                
                # 验证BTC数量合理性
                if suggested_amount <= 0 or suggested_amount > 10:
                    return {
                        'success': False,
                        'error': f'AI建议的BTC数量不合理: {suggested_amount}'
                    }
                
                result.update({
                    'suggested_amount': suggested_amount
                })
            
            return result
        
        except json.JSONDecodeError:
            return {
                'success': False,
                'error': 'JSON解析失败'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'解析错误: {str(e)}'
            }
