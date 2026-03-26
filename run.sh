#!/bin/bash

# 加载.env文件中的环境变量
if [ -f .env ]; then
    echo "正在加载 .env 配置文件..."
    set -a
    source .env
    set +a
    echo "✅ 环境变量已加载"
    echo ""
else
    echo "⚠️  未找到 .env 文件"
    exit 1
fi

# 运行程序
echo "正在启动基金监控工具..."
echo "=========================================="

# 支持传递命令行参数
python3 fund.py "$@"
