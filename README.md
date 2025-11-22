# 🤖 OKX AI Trading Bot

<div align="center">

**基于 DeepSeek Reasoner 的 BTC 自动交易系统**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![OKX](https://img.shields.io/badge/Exchange-OKX-brightgreen.svg)](https://www.okx.com/)
[![DeepSeek](https://img.shields.io/badge/AI-DeepSeek%20Reasoner-orange.svg)](https://platform.deepseek.com/)

使用 DeepSeek Reasoner AI 深度推理市场，在 OKX 交易所自动交易 BTC

[快速开始](#-快速开始) • [Docker部署](#-docker-部署推荐) • [配置说明](#-配置说明) • [常见问题](#-常见问题)

<!-- 项目预览图 -->
![项目预览](./image/preview.png)
> *Web监控面板实时显示交易数据和AI决策*

</div>

---

## ✨ 核心特性

- 🧠 **AI 深度推理** - DeepSeek Reasoner 分析原始 K线数据（OHLCV）
- 📊 **多周期分析** - 15分钟/1小时 K线综合决策
- 🎯 **智能风控** - AI 自主决定交易量和止盈止损
- ⚡ **K线对齐** - 每15分钟精准执行，避免滑点
- 📈 **Web 监控** - 实时查看账户、交易、AI 决策
- 🐳 **Docker 支持** - 一键部署，开箱即用

---

## 🚀 快速开始

### 方式一：本地运行

**1. 克隆并安装**
```bash
git clone https://github.com/ZH0531/OKX-AI-Trading.git
cd OKX-AI-Trading
pip install -r requirements.txt
```

**2. 配置 API**
```bash
cp .env.example .env
# 编辑 .env 填入 OKX 和 DeepSeek API 密钥
```

**3. 启动**
```bash
# Windows
start.bat

# Linux/Mac
python run.py
```

> **💡 代理设置**：如需访问 OKX API（国内网络），在 `.env` 中设置：
> ```env
> USE_PROXY=true
> HTTP_PROXY=http://127.0.0.1:7890
> HTTPS_PROXY=http://127.0.0.1:7890
> ```

### 方式二：Docker 部署（推荐）

**适合服务器部署，自动重启，日志持久化**

```bash
# 1. 配置环境变量
cp .env.example .env
vim .env  # 填入 API 密钥

# 2. 启动（后台运行）
docker-compose up -d

# 3. 查看日志
docker-compose logs -f trading-bot

# 4. 停止服务
docker-compose down
```

**Docker Compose 包含**：
- `trading-bot` - 交易机器人（自动重启）
- `web-panel` - Web 监控面板（端口 8000）
- 数据卷：`data/`（数据库）、`logs/`（日志）

---

## 🔧 工作原理

```
每15分钟 K线结束后 → 获取多周期数据 → AI 分析 OHLCV → 决策（BUY/SELL/HOLD）
                                                  ↓
                                      信心度 ≥ 60% → 执行交易
                                      信心度 < 60% → 继续观望
```

**关键机制**：
- 在 15 分钟 K线结束后执行（`00:00`, `00:15`, `00:30`, `00:45`）
- 不预计算技术指标，让 AI 直接分析 K线形态
- 模拟盘/实盘使用独立数据库

---

## ⚙️ 配置说明

**核心参数**：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `OKX_SIMULATED` | 模拟盘/实盘 | `true` |
| `MAX_TRADING_AMOUNT` | 单次最大 BTC 数量 | `0.01` |
| `MAX_POSITION_PERCENT` | 最大仓位百分比 | `30` |
| `AI_MIN_CONFIDENCE` | AI 最低信心阈值 | `60` |

**可选配置**：

```env
# 调试
DEBUG_MODE=false           # 显示完整 AI 推理过程
LOG_AI_DECISIONS=true      # 记录所有决策（含 HOLD）

# 代理（国内访问 OKX API）
USE_PROXY=false
HTTP_PROXY=http://127.0.0.1:7890

# Web 面板
WEB_PORT=8000
PANEL_TOKEN=               # Web面板访问密码（留空=无密码访问）
                           # 填写后需在面板登录时输入此 Token
                           # 示例：PANEL_TOKEN=my_secret_token_123
```

查看 `.env.example` 获取完整配置项。

---

## 📊 Web 监控面板

访问 `http://localhost:8000` 查看：

- **账户余额** - USDT/BTC 余额和总价值
- **交易统计** - 交易次数、盈亏情况
- **AI 决策** - 最新建议和理由
- **交易历史** - 最近 20 笔交易记录
- **系统状态** - 运行模式、配置参数

### 🔐 面板安全访问

如需保护 Web 面板，在 `.env` 中设置 `PANEL_TOKEN`：

```env
PANEL_TOKEN=your_secret_token_here
```

设置后：
- 首次访问面板会提示输入口令
- 输入正确的 `PANEL_TOKEN` 后才能查看数据
- Token 会保存在浏览器本地存储（关闭页面后仍有效）
- 留空 = 无需密码，任何人可访问（仅建议本地测试使用）

---

## ❓ 常见问题

**Q: 为什么不交易？**
- AI 建议 HOLD（观望）
- AI 信心度 < 60%
- 余额不足
- 查看日志或 Web 面板了解原因

**Q: 如何切换实盘？**
1. 模拟盘充分测试
2. 修改 `.env`: `OKX_SIMULATED=false`
3. 重启（数据库自动切换到 `trading_live.db`）

**Q: API 调用失败？**
- **OKX**: 检查 Key 正确性、交易权限、模拟/实盘匹配
- **DeepSeek**: 检查 Key 有效性、账户余额、代理设置

**Q: 交易频率能调整吗？**
- 固定 15 分钟 K线对齐，无法调整

**Q: 国内如何访问 OKX？**
- 部分地区可能需要代理，设置 `.env`：`USE_PROXY=true`

---

## ⚠️ 风险提示

> **加密货币交易风险极高，可能导致全部资金损失**

- ✅ **先用模拟盘**充分测试
- ✅ **小额资金**验证策略
- ✅ **合理限制**交易量和仓位
- ❌ **不保证盈利**，AI 仅供参考
- ❌ **后果自负**，仅供学习交流

> 如果这个项目能稳定赚钱的话，那他可能不会出现在Github上...
>
> 不要抱有侥幸，用通用AI去挑战金融机构的专业量化交易，再加上币市本来就千变万化，用来分析还行，完全依赖就不太可能了
---

## 📄 许可证

MIT License - 仅供学习交流，实盘风险自负。

---

<div align="center">

**⭐ 觉得有用？给个 Star 吧！**

Made with ❤️ by [ZH0531](https://github.com/ZH0531)

</div>
