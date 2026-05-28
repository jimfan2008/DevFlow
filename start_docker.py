#!/usr/bin/env python3
"""
DevFlow Docker 启动和验证脚本
"""

import subprocess
import sys
import time
import json
import os

def run_command(cmd, check=True, timeout=300):
    """执行命令并返回结果"""
    try:
        print(f"执行: {cmd}")
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=timeout
        )
        if result.stdout:
            print(f"输出: {result.stdout[:500]}")
        if result.stderr:
            print(f"错误: {result.stderr[:500]}")
        if check and result.returncode != 0:
            print(f"命令执行失败，返回码: {result.returncode}")
            return None
        return result
    except subprocess.TimeoutExpired:
        print(f"命令超时: {cmd}")
        return None
    except Exception as e:
        print(f"执行命令时出错: {e}")
        return None


def check_docker():
    """检查 Docker 和 Docker Compose"""
    print("=" * 60)
    print("检查 Docker 环境...")
    print("=" * 60)
    
    result = run_command("docker --version", check=False)
    if not result or result.returncode != 0:
        print("错误: Docker 未安装或未运行")
        return False
    print(f"Docker 版本: {result.stdout.strip()}")
    
    result = run_command("docker-compose --version", check=False)
    if not result or result.returncode != 0:
        result = run_command("docker compose version", check=False)
        if not result or result.returncode != 0:
            print("错误: Docker Compose 未安装")
            return False
    print(f"Docker Compose 版本: {result.stdout.strip()}")
    
    return True


def cleanup_old_containers():
    """清理旧的容器和卷"""
    print("\n" + "=" * 60)
    print("清理旧容器...")
    print("=" * 60)
    
    containers = [
        "devflow-backend", "devflow-postgres", "devflow-redis",
        "devflow-nginx", "devflow-celery-worker", "devflow-celery-beat",
        "devflow-frontend-builder", "devflow-gitea", "devflow-gitea-db"
    ]
    
    for container in containers:
        run_command(f"docker stop {container} 2>nul || true", check=False)
        run_command(f"docker rm {container} 2>nul || true", check=False)
    
    print("旧容器已清理")


def build_images():
    """构建 Docker 镜像"""
    print("\n" + "=" * 60)
    print("构建 Docker 镜像...")
    print("=" * 60)
    
    print("\n构建后端镜像...")
    result = run_command("docker-compose -f docker-compose.min.yml build backend", timeout=600)
    if not result:
        print("错误: 后端镜像构建失败")
        return False
    
    print("\n镜像构建完成")
    return True


def start_services():
    """启动服务"""
    print("\n" + "=" * 60)
    print("启动服务...")
    print("=" * 60)
    
    print("\n启动 PostgreSQL 和 Redis...")
    result = run_command("docker-compose -f docker-compose.min.yml up -d postgres redis", timeout=120)
    if not result:
        print("错误: 数据库服务启动失败")
        return False
    
    print("\n等待数据库就绪...")
    for i in range(30):
        result = run_command("docker inspect -f '{{.State.Health.Status}}' devflow-postgres", check=False)
        if result and "healthy" in result.stdout:
            print("PostgreSQL 已就绪")
            break
        time.sleep(2)
    else:
        print("警告: PostgreSQL 健康检查超时，继续尝试")
    
    for i in range(30):
        result = run_command("docker inspect -f '{{.State.Health.Status}}' devflow-redis", check=False)
        if result and "healthy" in result.stdout:
            print("Redis 已就绪")
            break
        time.sleep(1)
    else:
        print("警告: Redis 健康检查超时，继续尝试")
    
    print("\n启动后端服务...")
    result = run_command("docker-compose -f docker-compose.min.yml up -d backend", timeout=120)
    if not result:
        print("错误: 后端服务启动失败")
        return False
    
    return True


def wait_for_backend():
    """等待后端服务就绪"""
    print("\n" + "=" * 60)
    print("等待后端服务就绪...")
    print("=" * 60)
    
    for i in range(60):
        result = run_command("curl -s http://localhost:8000/health 2>nul || true", check=False)
        if result and "healthy" in result.stdout:
            print("后端服务已就绪")
            return True
        time.sleep(2)
    
    print("警告: 后端健康检查超时，检查容器日志...")
    run_command("docker logs devflow-backend --tail 50", check=False)
    return False


def verify_services():
    """验证服务"""
    print("\n" + "=" * 60)
    print("验证服务状态...")
    print("=" * 60)
    
    print("\n容器状态:")
    run_command("docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'", check=False)
    
    print("\n后端健康检查:")
    result = run_command("curl -s http://localhost:8000/health", check=False)
    if result:
        print(f"响应: {result.stdout.strip()}")
    
    print("\nAPI 文档:")
    result = run_command("curl -s http://localhost:8000/docs -o nul -w '%{http_code}'", check=False)
    if result and "200" in result.stdout:
        print("API 文档可访问: http://localhost:8000/docs")
    
    return True


def test_api():
    """测试 API 端点"""
    print("\n" + "=" * 60)
    print("API 功能测试...")
    print("=" * 60)
    
    print("\n1. 测试根端点...")
    result = run_command("curl -s http://localhost:8000/", check=False)
    if result and result.returncode == 0:
        print(f"✓ 根端点响应: {result.stdout[:200]}")
    else:
        print("✗ 根端点测试失败")
    
    print("\n2. 测试健康检查...")
    result = run_command("curl -s http://localhost:8000/health", check=False)
    if result and "healthy" in result.stdout:
        print("✓ 健康检查通过")
    else:
        print("✗ 健康检查失败")
    
    print("\n3. 测试 API 文档...")
    result = run_command("curl -s -o nul -w '%{http_code}' http://localhost:8000/docs", check=False)
    if result and "200" in result.stdout:
        print("✓ API 文档可访问")
    else:
        print("✗ API 文档访问失败")
    
    print("\n4. 测试 OpenAPI 规范...")
    result = run_command("curl -s http://localhost:8000/openapi.json", check=False)
    if result and result.returncode == 0:
        try:
            data = json.loads(result.stdout)
            print(f"✓ OpenAPI 规范加载成功，版本: {data.get('openapi', 'N/A')}")
            print(f"  - 标题: {data.get('info', {}).get('title', 'N/A')}")
            print(f"  - 路径数量: {len(data.get('paths', {}))}")
        except:
            print("✓ OpenAPI 规范可访问")
    else:
        print("✗ OpenAPI 规范访问失败")
    
    return True


def main():
    """主函数"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    print("=" * 60)
    print("DevFlow Docker 启动脚本")
    print("=" * 60)
    
    if not check_docker():
        return 1
    
    cleanup_old_containers()
    
    if not build_images():
        return 1
    
    if not start_services():
        return 1
    
    if not wait_for_backend():
        print("\n警告: 后端服务可能未完全就绪，但继续验证...")
    
    verify_services()
    test_api()
    
    print("\n" + "=" * 60)
    print("启动完成!")
    print("=" * 60)
    print("\n访问地址:")
    print("  - 后端 API: http://localhost:8000")
    print("  - API 文档: http://localhost:8000/docs")
    print("  - PostgreSQL: localhost:15432")
    print("  - Redis: localhost:6379")
    print("\n常用命令:")
    print("  - 查看日志: docker logs devflow-backend")
    print("  - 停止服务: docker-compose -f docker-compose.min.yml down")
    print("  - 停止并删除数据: docker-compose -f docker-compose.min.yml down -v")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
