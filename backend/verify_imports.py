#!/usr/bin/env python3
"""
验证所有新添加的模块是否可以正常导入
"""
import sys
import traceback

def test_imports():
    print("=" * 60)
    print("验证 groupchat 合并的模块导入")
    print("=" * 60)
    
    modules_to_test = [
        # 配置
        "app.config",
        # 工具
        "app.utils.hermes_fs",
        # 服务层
        "app.services.profile_scanner_service",
        "app.services.gateway_client",
        "app.services.conversation_coordinator",
        "app.services.group_service",
        # 模型
        "app.models.group",
        # 模式
        "app.schemas.group",
        # API
        "app.api.profiles",
        "app.api.groups",
        "app.api.websocket",
        "app.api.hermes_integration",
        # 主应用
        "app.api",
    ]
    
    success_count = 0
    failed_modules = []
    
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"[OK] {module_name}")
            success_count += 1
        except Exception as e:
            print(f"[FAIL] {module_name}")
            print(f"       Error: {e}")
            print(f"       Traceback:\n{traceback.format_exc()}")
            failed_modules.append(module_name)
    
    print("\n" + "=" * 60)
    print(f"结果: {success_count}/{len(modules_to_test)} 模块导入成功")
    if failed_modules:
        print(f"失败的模块: {failed_modules}")
        sys.exit(1)
    else:
        print("所有模块导入成功!")
        sys.exit(0)


if __name__ == "__main__":
    test_imports()
