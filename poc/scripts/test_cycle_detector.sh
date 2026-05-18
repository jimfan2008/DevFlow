#!/bin/bash
# 测试脚本：运行循环依赖检测算法测试
# 使用方法：./test_cycle_detector.sh

set -e

echo "=================================================="
echo "DevFlow 项目 POC 测试"
echo "=================================================="
echo ""

# 检查 Python 环境
echo "检查 Python 环境..."
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "错误：未找到 Python 解释器"
    exit 1
fi

echo "使用 Python: $($PYTHON --version)"
echo ""

# 运行算法测试
echo "=================================================="
echo "运行循环依赖检测算法测试"
echo "=================================================="
echo ""

cd /home/jim/DevFlow/poc/algorithms

$PYTHON cycle_detector_dfs.py --demo

echo ""
echo "=================================================="
echo "POC 测试完成！"
echo "=================================================="
