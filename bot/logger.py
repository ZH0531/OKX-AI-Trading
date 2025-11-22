"""日志记录模块"""
import os
import logging
from datetime import datetime
from typing import Dict, Any
from config import Config

class TradingLogger:
    """交易日志记录器"""
    
    def __init__(self):
        """初始化日志"""
        # 确保logs目录存在
        self.log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 创建日志文件名（按日期）
        today = datetime.now().strftime('%Y%m%d')
        self.log_file = os.path.join(self.log_dir, f'trading_{today}.log')
        self.decision_file = os.path.join(self.log_dir, f'ai_decisions_{today}.log')
        
        # 配置主日志
        self.logger = logging.getLogger('TradingBot')
        self.logger.setLevel(logging.INFO)
        
        # 避免重复添加handler
        if not self.logger.handlers:
            # 文件handler
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            # 控制台handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # 格式化
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
        
        # 配置AI决策日志（独立文件）
        self.decision_logger = logging.getLogger('AIDecisions')
        self.decision_logger.setLevel(logging.INFO)
        
        if not self.decision_logger.handlers:
            decision_handler = logging.FileHandler(self.decision_file, encoding='utf-8')
            decision_handler.setLevel(logging.INFO)
            decision_formatter = logging.Formatter(
                '%(asctime)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            decision_handler.setFormatter(decision_formatter)
            self.decision_logger.addHandler(decision_handler)
            # 不传播到父logger，避免重复
            self.decision_logger.propagate = False
    
    def log_ai_decision(self, decision: Dict[str, Any], price: float, balance: Dict[str, float]):
        """记录AI决策到日志"""
        if not Config.LOG_AI_DECISIONS:
            return
        
        action = decision.get('action', 'UNKNOWN')
        confidence = decision.get('confidence', 0)
        reason = decision.get('reason', '')
        risk_level = decision.get('risk_level', 'UNKNOWN')
        
        # 构建日志消息
        log_msg = f"""
{'='*80}
AI决策记录
{'='*80}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
当前价格: ${price:,.2f}
账户状态: USDT ${balance.get('usdt', 0):.2f} | BTC {balance.get('btc', 0):.8f}

决策结果:
  动作: {action}
  信心度: {confidence}%
  风险等级: {risk_level}
  理由: {reason}
"""
        
        # 如果是BUY/SELL，添加建议数量
        if action in ['BUY', 'SELL']:
            suggested_amount = decision.get('suggested_amount', 0)
            log_msg += f"  建议数量: {suggested_amount:.8f} BTC\n"
        
        # 如果有推理过程，添加到日志
        if 'reasoning' in decision and Config.DEBUG_MODE:
            reasoning = decision['reasoning']
            log_msg += f"\nAI推理过程:\n{reasoning[:500]}...\n"  # 截取前500字符
        
        log_msg += "="*80 + "\n"
        
        # 写入日志
        self.decision_logger.info(log_msg)
    
    def log_trade(self, action: str, price: float, amount: float, result: str = 'SUCCESS'):
        """记录交易执行"""
        self.logger.info(f"交易执行 - {action} {amount:.8f} BTC @ ${price:,.2f} - {result}")
    
    def log_error(self, error_msg: str):
        """记录错误"""
        self.logger.error(error_msg)
    
    def log_info(self, info_msg: str):
        """记录信息"""
        self.logger.info(info_msg)
    
    def log_warning(self, warning_msg: str):
        """记录警告"""
        self.logger.warning(warning_msg)

# 全局logger实例
_logger_instance = None

def get_logger() -> TradingLogger:
    """获取全局logger实例"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = TradingLogger()
    return _logger_instance
