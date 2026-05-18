#!/bin/bash
# DevFlow 项目管理平台 - 测试运行脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 脚本目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/backend"

echo "=========================================="
echo "  DevFlow 项目管理平台 - 测试运行器"
echo "=========================================="
echo ""

# 检查 pytest 是否安装
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}pytest 未安装，正在安装...${NC}"
    pip install pytest pytest-asyncio pytest-cov httpx -q
fi

# 检查依赖
echo -e "${YELLOW}检查依赖...${NC}"
pip install -q -r requirements.txt 2>/dev/null || echo "requirements.txt 不存在，跳过"

# 显示测试选项
echo ""
echo "请选择测试类型:"
echo "1. 运行所有后端测试"
echo "2. 运行认证模块测试"
echo "3. 运行看板管理测试"
echo "4. 运行任务管理测试"
echo "5. 运行依赖管理测试"
echo "6. 运行负载分析测试"
echo "7. 运行收件箱测试"
echo "8. 运行集成测试"
echo "9. 运行带覆盖率测试"
echo "0. 退出"
echo ""

read -p "请输入选项 (0-9): " choice

case $choice in
    1)
        echo ""
        echo -e "${YELLOW}运行所有后端测试...${NC}"
        pytest tests/ -v --tb=short
        ;;
    2)
        echo ""
        echo -e "${YELLOW}运行认证模块测试...${NC}"
        pytest tests/test_auth.py -v --tb=short
        ;;
    3)
        echo ""
        echo -e "${YELLOW}运行看板管理测试...${NC}"
        pytest tests/test_board.py -v --tb=short
        ;;
    4)
        echo ""
        echo -e "${YELLOW}运行任务管理测试...${NC}"
        pytest tests/test_task.py -v --tb=short
        ;;
    5)
        echo ""
        echo -e "${YELLOW}运行依赖管理测试...${NC}"
        pytest tests/test_dependency.py -v --tb=short
        ;;
    6)
        echo ""
        echo -e "${YELLOW}运行负载分析测试...${NC}"
        pytest tests/test_workload.py -v --tb=short
        ;;
    7)
        echo ""
        echo -e "${YELLOW}运行收件箱测试...${NC}"
        pytest tests/test_inbox.py -v --tb=short
        ;;
    8)
        echo ""
        echo -e "${YELLOW}运行集成测试...${NC}"
        pytest tests/test_integration.py -v --tb=short
        ;;
    9)
        echo ""
        echo -e "${YELLOW}运行带覆盖率测试...${NC}"
        pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html --tb=short
        echo ""
        echo -e "${GREEN}覆盖率报告已生成在 htmlcov/index.html${NC}"
        ;;
    0)
        echo "退出测试运行器"
        exit 0
        ;;
    *)
        echo -e "${RED}无效选项${NC}"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo -e "${GREEN}测试完成!${NC}"
echo "=========================================="
