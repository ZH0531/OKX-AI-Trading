#!/bin/bash
# AI炒币机器人部署脚本

echo "======================================"
echo "   AI炒币机器人 - Linux部署"
echo "======================================"
echo ""

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    echo "安装命令: curl -fsSL https://get.docker.com | bash"
    exit 1
fi

# 检查Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装，请先安装"
    echo "安装命令: sudo apt-get install docker-compose"
    exit 1
fi

echo "✓ Docker环境检查通过"
echo ""

# 检查.env文件
if [ ! -f .env ]; then
    echo "❌ 未找到.env配置文件"
    echo "请先创建.env文件并配置API密钥"
    exit 1
fi

echo "✓ 配置文件检查通过"
echo ""

# 创建必要的目录
mkdir -p data logs

echo "开始构建Docker镜像..."
docker-compose build

echo ""
echo "启动服务..."
docker-compose up -d

echo ""
echo "======================================"
echo "✓ 部署完成！"
echo "======================================"
echo ""
echo "查看日志："
echo "  交易机器人: docker-compose logs -f trading-bot"
echo "  Web面板:    docker-compose logs -f web-panel"
echo ""
echo "停止服务: docker-compose stop"
echo "重启服务: docker-compose restart"
echo "删除服务: docker-compose down"
echo ""
