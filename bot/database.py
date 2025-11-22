"""数据库操作"""
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import os


class Database:
    """交易数据库"""
    
    def __init__(self, db_path: str = 'data/trading.db'):
        self.db_path = db_path
        self._ensure_database()
    
    def _ensure_database(self):
        """确保数据库和表存在"""
        # 确保data目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建交易记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                action TEXT NOT NULL,
                price REAL NOT NULL,
                amount REAL NOT NULL,
                reason TEXT,
                profit REAL DEFAULT 0,
                balance_usdt REAL,
                balance_btc REAL
            )
        ''')
        
        # 创建系统状态表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                btc_price REAL NOT NULL,
                usdt_balance REAL,
                btc_balance REAL,
                total_value REAL,
                ai_suggestion TEXT,
                ai_reasoning TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_trade(self, action: str, price: float, amount: float, 
                  reason: str = '', profit: float = 0,
                  balance_usdt: float = 0, balance_btc: float = 0):
        """添加交易记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trades (action, price, amount, reason, profit, balance_usdt, balance_btc)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (action, price, amount, reason, profit, balance_usdt, balance_btc))
        
        conn.commit()
        conn.close()
    
    def add_status(self, btc_price: float, usdt_balance: float = 0,
                   btc_balance: float = 0, total_value: float = 0,
                   ai_suggestion: str = '', ai_reasoning: str = ''):
        """添加系统状态记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO status (btc_price, usdt_balance, btc_balance, total_value, ai_suggestion, ai_reasoning)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (btc_price, usdt_balance, btc_balance, total_value, ai_suggestion, ai_reasoning))
        
        conn.commit()
        conn.close()
    
    def get_recent_trades(self, limit: int = 10) -> List[Dict]:
        """获取最近的交易记录"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_latest_status(self) -> Optional[Dict]:
        """获取最新状态
        优先返回最新一条 JSON 格式(ai_suggestion 以"{"开头) 的记录，
        避免旧版本写入的纯字符串覆盖新AI结果。
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 先取最近一条 JSON 格式的状态
        cursor.execute('''
            SELECT * FROM status
            WHERE ai_suggestion IS NOT NULL
              AND TRIM(ai_suggestion) LIKE '{%%'
            ORDER BY timestamp DESC
            LIMIT 1
        ''')
        row = cursor.fetchone()
        
        # 如果还没有JSON记录，退回到最新一条任意记录
        if row is None:
            cursor.execute('''
                SELECT * FROM status ORDER BY timestamp DESC LIMIT 1
            ''')
            row = cursor.fetchone()
        
        conn.close()
        return dict(row) if row else None
    
    def get_recent_performance(self, limit: int = 20) -> Dict:
        """获取最近N笔交易的表现统计，用于AI历史反馈"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 获取最近的交易记录（只统计有盈亏的SELL）
        cursor.execute('''
            SELECT * FROM trades 
            WHERE action = 'SELL' AND profit IS NOT NULL
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        recent_trades = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        if not recent_trades:
            return {
                'total_trades': 0,
                'win_count': 0,
                'loss_count': 0,
                'win_rate': 0.0,
                'avg_profit': 0.0,
                'total_profit': 0.0,
                'best_trade': None,
                'worst_trade': None,
                'recent_trades_summary': []
            }
        
        total_trades = len(recent_trades)
        win_count = sum(1 for t in recent_trades if t['profit'] > 0)
        loss_count = total_trades - win_count
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
        
        profits = [t['profit'] for t in recent_trades]
        total_profit = sum(profits)
        avg_profit = total_profit / total_trades if total_trades > 0 else 0
        
        best_trade = max(recent_trades, key=lambda x: x['profit'])
        worst_trade = min(recent_trades, key=lambda x: x['profit'])
        
        # 生成最近交易摘要（最多5笔）
        recent_summary = []
        for i, trade in enumerate(recent_trades[:5]):
            profit_pct = (trade['profit'] / (trade['price'] * trade['amount']) * 100) if trade['amount'] > 0 else 0
            recent_summary.append({
                'action': trade['action'],
                'price': trade['price'],
                'profit': trade['profit'],
                'profit_pct': round(profit_pct, 2),
                'result': '✓' if trade['profit'] > 0 else '✗'
            })
        
        return {
            'total_trades': total_trades,
            'win_count': win_count,
            'loss_count': loss_count,
            'win_rate': round(win_rate, 1),
            'avg_profit': round(avg_profit, 2),
            'total_profit': round(total_profit, 2),
            'best_trade': {
                'profit': round(best_trade['profit'], 2),
                'price': best_trade['price']
            } if best_trade else None,
            'worst_trade': {
                'profit': round(worst_trade['profit'], 2),
                'price': worst_trade['price']
            } if worst_trade else None,
            'recent_trades_summary': recent_summary
        }
    
    def get_recent_ai_decisions(self, limit: int = 10) -> list:
        """获取最近N条AI决策记录（用于AI记忆）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, btc_price, ai_suggestion 
            FROM status 
            WHERE ai_suggestion IS NOT NULL AND ai_suggestion != ''
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        decisions = []
        for row in cursor.fetchall():
            timestamp = row[0]
            price = row[1]
            ai_suggestion = row[2]
            
            # 解析AI建议JSON
            try:
                import json
                suggestion = json.loads(ai_suggestion)
                decisions.append({
                    'timestamp': timestamp,
                    'price': price,
                    'action': suggestion.get('action'),
                    'confidence': suggestion.get('confidence'),
                    'reason': suggestion.get('reason', ''),
                })
            except:
                pass
        
        conn.close()
        # 按时间正序返回（从旧到新）
        return list(reversed(decisions))
    
    def get_statistics(self) -> Dict:
        """获取统计数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 总交易次数
        cursor.execute('SELECT COUNT(*) FROM trades')
        total_trades = cursor.fetchone()[0]
        
        # 总盈亏
        cursor.execute('SELECT SUM(profit) FROM trades')
        total_profit = cursor.fetchone()[0] or 0
        
        # 买入次数
        cursor.execute('SELECT COUNT(*) FROM trades WHERE action = "BUY"')
        buy_count = cursor.fetchone()[0]
        
        # 卖出次数
        cursor.execute('SELECT COUNT(*) FROM trades WHERE action = "SELL"')
        sell_count = cursor.fetchone()[0]
        
        # 平均盈亏（只统计SELL交易，因为BUY没有盈亏）
        avg_profit = total_profit / sell_count if sell_count > 0 else 0
        
        conn.close()
        
        return {
            'total_trades': total_trades,
            'total_profit': round(total_profit, 2),
            'buy_count': buy_count,
            'sell_count': sell_count,
            'avg_profit': round(avg_profit, 2)
        }
