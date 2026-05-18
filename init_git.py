#!/usr/bin/env python3
"""
Git 初始化和推送到 GitHub 的自动化脚本

使用方法:
    python init_git.py
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, check=True):
    """执行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        if check and result.returncode != 0:
            print(f"错误: 命令执行失败")
            print(f"命令: {cmd}")
            if result.stderr:
                print(f"错误信息: {result.stderr}")
            return None
        return result
    except Exception as e:
        print(f"错误: 执行命令时发生异常: {e}")
        return None


def check_git_installed():
    """检查 git 是否安装"""
    result = run_command("git --version", check=False)
    if result and result.returncode == 0:
        version = result.stdout.strip()
        print(f"✓ Git 已安装: {version}")
        return True
    print("✗ Git 未安装，请先安装 Git")
    print("下载地址: https://git-scm.com/downloads")
    return False


def is_git_repo():
    """检查当前目录是否已经是 git 仓库"""
    result = run_command("git rev-parse --is-inside-work-tree", check=False)
    return result and result.returncode == 0


def get_git_config(key):
    """获取 git 配置"""
    result = run_command(f"git config --global {key}", check=False)
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None


def set_git_config(key, value):
    """设置 git 配置"""
    result = run_command(f'git config --global {key} "{value}"', check=False)
    return result and result.returncode == 0


def init_repo():
    """初始化 git 仓库"""
    print("\n初始化 git 仓库...")
    result = run_command("git init")
    if result:
        print("✓ Git 仓库初始化成功")
        return True
    return False


def add_files():
    """添加所有文件到暂存区"""
    print("\n添加文件到暂存区...")
    result = run_command("git add .")
    if result:
        print("✓ 文件已添加到暂存区")
        return True
    return False


def commit(message="Initial commit"):
    """创建提交"""
    print(f"\n创建提交: {message}")
    result = run_command(f'git commit -m "{message}"')
    if result:
        print("✓ 提交成功")
        return True
    return False


def add_remote(url):
    """添加远程仓库"""
    print(f"\n添加远程仓库: {url}")
    result = run_command(f"git remote add origin {url}")
    if result:
        print("✓ 远程仓库添加成功")
        return True
    return False


def push_to_remote():
    """推送到远程仓库"""
    print("\n推送到远程仓库...")
    result = run_command("git branch -M main")
    if not result:
        return False
    
    result = run_command("git push -u origin main")
    if result:
        print("✓ 代码已成功推送到 GitHub")
        return True
    return False


def get_user_input():
    """获取用户输入"""
    print("\n" + "=" * 60)
    print("Git 初始化和推送到 GitHub")
    print("=" * 60)
    
    name = get_git_config("user.name")
    if not name:
        name = input("\n请输入您的 Git 用户名: ").strip()
        if not name:
            print("错误: 用户名不能为空")
            return None
        set_git_config("user.name", name)
    else:
        print(f"\n检测到 Git 用户名: {name}")
        change = input("是否修改? (y/N): ").strip().lower()
        if change == 'y':
            name = input("请输入新的 Git 用户名: ").strip()
            if name:
                set_git_config("user.name", name)
    
    email = get_git_config("user.email")
    if not email:
        email = input("请输入您的 Git 邮箱: ").strip()
        if not email:
            print("错误: 邮箱不能为空")
            return None
        set_git_config("user.email", email)
    else:
        print(f"检测到 Git 邮箱: {email}")
        change = input("是否修改? (y/N): ").strip().lower()
        if change == 'y':
            email = input("请输入新的 Git 邮箱: ").strip()
            if email:
                set_git_config("user.email", email)
    
    remote_url = input("\n请输入 GitHub 仓库地址 (例如: https://github.com/username/repo.git): ").strip()
    if not remote_url:
        print("错误: 仓库地址不能为空")
        return None
    
    commit_msg = input("请输入提交信息 (默认: Initial commit): ").strip()
    if not commit_msg:
        commit_msg = "Initial commit"
    
    return {
        'name': name,
        'email': email,
        'remote_url': remote_url,
        'commit_msg': commit_msg
    }


def main():
    """主函数"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    if not check_git_installed():
        return 1
    
    if is_git_repo():
        print("\n警告: 当前目录已经是 Git 仓库")
        confirm = input("是否继续? 这可能会影响现有的 Git 历史。(y/N): ").strip().lower()
        if confirm != 'y':
            print("操作已取消")
            return 0
    
    config = get_user_input()
    if not config:
        return 1
    
    print("\n" + "=" * 60)
    print("开始执行...")
    print("=" * 60)
    
    if not is_git_repo():
        if not init_repo():
            return 1
    else:
        print("\n跳过仓库初始化（已存在）")
    
    if not add_files():
        return 1
    
    if not commit(config['commit_msg']):
        return 1
    
    if not add_remote(config['remote_url']):
        return 1
    
    if not push_to_remote():
        return 1
    
    print("\n" + "=" * 60)
    print("完成！代码已成功推送到 GitHub")
    print(f"仓库地址: {config['remote_url']}")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
