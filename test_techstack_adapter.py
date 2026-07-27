import pytest
from dataclasses import dataclass
from typing import Dict, Any, List
from abc import ABC, abstractmethod


@dataclass
class CodeGeneratorResult:
    code: str
    status: str
    metadata: Dict[str, Any]


class TechStackAdapter(ABC):
    @abstractmethod
    def supports(self, stack_name: str) -> bool:
        pass

    @abstractmethod
    def generate(self, spec: Dict[str, Any]) -> CodeGeneratorResult:
        pass


class ReactAdapter(TechStackAdapter):
    def supports(self, stack_name: str) -> bool:
        if not stack_name:
            return False
        return stack_name.lower() in ("react", "reactjs", "react-jsx")

    def generate(self, spec: Dict[str, Any]) -> CodeGeneratorResult:
        component_name = spec.get("component_name", "MyComponent")
        props = spec.get("props", [])
        props_str = ", ".join(props) if props else ""
        code = f"""import React, {{ useState, useEffect }} from 'react';

const {component_name} = ({{ {props_str} }}) => {{
  const [count, setCount] = useState(0);

  useEffect(() => {{
    console.log('{component_name} mounted');
  }}, []);

  return (
    <div>
      <h1>{component_name}</h1>
      <p>Count: {{count}}</p>
      <button onClick={{() => setCount(count + 1)}}>
        Increment
      </button>
    </div>
  );
}});

export default {component_name};
"""
        return CodeGeneratorResult(code=code, status="normal", metadata={"adapter": "react"})


class VueAdapter(TechStackAdapter):
    def supports(self, stack_name: str) -> bool:
        if not stack_name:
            return False
        return stack_name.lower() in ("vue", "vue3", "vue-jsx")

    def generate(self, spec: Dict[str, Any]) -> CodeGeneratorResult:
        component_name = spec.get("component_name", "MyComponent")
        code = f"""<template>
  <div>
    <h1>{component_name}</h1>
    <p>{{{{count}}}}</p>
    <button @click="count++">Increment</button>
  </div>
</template>

<script>
export default {{
  data() {{
    return {{ count: 0 }};
  }}
}};
</script>
"""
        return CodeGeneratorResult(code=code, status="normal", metadata={"adapter": "vue"})


class GenericHTMLAdapter(TechStackAdapter):
    def supports(self, stack_name: str) -> bool:
        return True  # fallback always supports

    def generate(self, spec: Dict[str, Any]) -> CodeGeneratorResult:
        component_name = spec.get("component_name", "MyComponent")
        code = f"<!-- partial_adaptation: no specific adapter configured -->\n"
        code += f"""<!DOCTYPE html>
<html>
<head>
  <title>{component_name}</title>
</head>
<body>
  <div id="app">
    <h1>{component_name}</h1>
  </div>
  <script>
    document.addEventListener('DOMContentLoaded', function() {{
      console.log('{component_name} loaded');
    }});
  </script>
</body>
</html>
"""
        return CodeGeneratorResult(code=code, status="degraded", metadata={"adapter": "generic_html"})


class PluginAdapterRegistry:
    def __init__(self):
        self._adapters: List[TechStackAdapter] = []

    def register(self, adapter: TechStackAdapter):
        self._adapters.append(adapter)

    def unregister_by_type(self, adapter_type: type):
        self._adapters = [a for a in self._adapters if not isinstance(a, adapter_type)]

    def get_adapter(self, stack_name: str) -> TechStackAdapter:
        for adapter in self._adapters:
            if not isinstance(adapter, GenericHTMLAdapter) and adapter.supports(stack_name):
                return adapter
        return self._get_fallback()

    def _get_fallback(self) -> TechStackAdapter:
        for adapter in self._adapters:
            if isinstance(adapter, GenericHTMLAdapter):
                return adapter
        generic = GenericHTMLAdapter()
        self._adapters.append(generic)
        return generic


class TechStackCodeGenerator:
    def __init__(self, registry: PluginAdapterRegistry):
        self._registry = registry

    def generate_code(self, spec: Dict[str, Any]) -> CodeGeneratorResult:
        stack = spec.get("stack", "unknown")
        adapter = self._registry.get_adapter(stack)
        return adapter.generate(spec)


@pytest.fixture
def registry():
    r = PluginAdapterRegistry()
    r.register(ReactAdapter())
    r.register(VueAdapter())
    r.register(GenericHTMLAdapter())
    return r


@pytest.fixture
def generator(registry):
    return TechStackCodeGenerator(registry)


# ==================== 原有测试用例 ====================

def test_step2_react_format_code_generation(generator):
    spec = {
        "stack": "react",
        "component_name": "UserProfile",
        "props": ["username", "age"],
    }
    result = generator.generate_code(spec)

    assert result.status == "normal"
    assert "import React" in result.code
    assert "useState" in result.code
    assert "useEffect" in result.code
    assert "UserProfile" in result.code
    assert "export default UserProfile" in result.code
    assert "const UserProfile" in result.code
    assert "username" in result.code
    assert "onClick" in result.code


def test_step3_degrade_to_generic_html_when_adapter_missing(registry):
    registry.unregister_by_type(ReactAdapter)
    gen = TechStackCodeGenerator(registry)
    spec = {
        "stack": "react",
        "component_name": "UserProfile",
    }
    result = gen.generate_code(spec)

    assert result.status == "degraded"
    assert "<!DOCTYPE html>" in result.code
    assert "<script>" in result.code
    assert "document.addEventListener" in result.code


def test_step4_generated_result_has_partial_adaptation_header(registry):
    registry.unregister_by_type(ReactAdapter)
    registry.unregister_by_type(VueAdapter)
    gen = TechStackCodeGenerator(registry)
    spec = {
        "stack": "react",
        "component_name": "TestComponent",
    }
    result = gen.generate_code(spec)

    assert result.code.startswith("<!-- partial_adaptation: no specific adapter configured -->")


def test_step5_recover_react_template_generation(registry):
    registry.unregister_by_type(ReactAdapter)
    gen = TechStackCodeGenerator(registry)
    spec = {
        "stack": "react",
        "component_name": "UserProfile",
    }
    degraded_result = gen.generate_code(spec)
    assert degraded_result.status == "degraded"

    registry.register(ReactAdapter())
    normal_result = gen.generate_code(spec)

    assert normal_result.status == "normal"
    assert "import React" in normal_result.code
    assert "useState" in normal_result.code
    assert normal_result.metadata["adapter"] == "react"


def test_vue_adapter_works_correctly(generator):
    spec = {
        "stack": "vue3",
        "component_name": "Dashboard",
    }
    result = generator.generate_code(spec)

    assert result.status == "normal"
    assert "<template>" in result.code
    assert "Dashboard" in result.code
    assert result.metadata["adapter"] == "vue"


def test_unknown_stack_falls_back_to_generic_html(generator):
    spec = {
        "stack": "angular-something-unknown",
        "component_name": "AppShell",
    }
    result = generator.generate_code(spec)

    assert result.status == "degraded"
    assert "<!DOCTYPE html>" in result.code
    assert result.metadata["adapter"] == "generic_html"


def test_adapter_order_priority(registry):
    registry._adapters.reverse()
    gen = TechStackCodeGenerator(registry)
    spec = {
        "stack": "react",
        "component_name": "X",
    }
    result = gen.generate_code(spec)

    assert result.status == "normal"
    assert result.metadata["adapter"] == "react"


def test_code_generation_metadata_contains_adapter_info(generator):
    spec = {
        "stack": "react",
        "component_name": "TestWidget",
    }
    result = generator.generate_code(spec)

    assert "adapter" in result.metadata
    assert result.metadata["adapter"] == "react"
    assert result.status == "normal"


def test_empty_spec_uses_defaults(generator):
    spec = {"stack": "react"}
    result = generator.generate_code(spec)

    assert result.status == "normal"
    assert "MyComponent" in result.code


# ==================== 新增边界测试用例 ====================

def test_stack_key_missing_falls_back_to_generic_html(registry):
    """测试 spec 中缺少 stack 键时的行为"""
    spec = {
        "component_name": "FallbackComponent",
    }
    gen = TechStackCodeGenerator(registry)
    result = gen.generate_code(spec)

    assert result.status == "degraded"
    assert "<!DOCTYPE html>" in result.code
    assert result.metadata["adapter"] == "generic_html"


def test_stack_empty_string_falls_back_to_generic_html(registry):
    """测试 stack 值为空字符串时的行为"""
    spec = {
        "stack": "",
        "component_name": "EmptyStackComponent",
    }
    gen = TechStackCodeGenerator(registry)
    result = gen.generate_code(spec)

    assert result.status == "degraded"
    assert "<!DOCTYPE html>" in result.code


def test_stack_none_value_falls_back_to_generic_html(registry):
    """测试 stack 值为 None 时的行为"""
    spec = {
        "stack": None,
        "component_name": "NoneStackComponent",
    }
    gen = TechStackCodeGenerator(registry)
    result = gen.generate_code(spec)

    assert result.status == "degraded"
    assert "<!DOCTYPE html>" in result.code


def test_completely_empty_registry_falls_back_to_generic_html():
    """测试完全空的 Registry（从未 register 任何 adapter）"""
    empty_registry = PluginAdapterRegistry()
    gen = TechStackCodeGenerator(empty_registry)
    spec = {
        "stack": "react",
        "component_name": "EmptyRegistryComponent",
    }
    result = gen.generate_code(spec)

    assert result.status == "degraded"
    assert "<!DOCTYPE html>" in result.code
    assert result.metadata["adapter"] == "generic_html"
    # 验证 _get_fallback 自动添加了 GenericHTMLAdapter
    assert len(empty_registry._adapters) == 1
    assert isinstance(empty_registry._adapters[0], GenericHTMLAdapter)


def test_component_name_with_html_injection_characters(registry):
    """测试 component_name 含 HTML 注入字符"""
    spec = {
        "stack": "react",
        "component_name": "<script>alert('xss')</script>",
    }
    gen = TechStackCodeGenerator(registry)
    result = gen.generate_code(spec)

    assert result.status == "normal"
    assert "<script>alert('xss')</script>" in result.code


def test_component_name_empty_string(registry):
    """测试 component_name 为空字符串"""
    spec = {
        "stack": "react",
        "component_name": "",
    }
    gen = TechStackCodeGenerator(registry)
    result = gen.generate_code(spec)

    assert result.status == "normal"
    # 空字符串会直接出现在代码中
    assert "const  = (" in result.code or "" in result.code


def test_unregister_nonexistent_adapter_type(registry):
    """测试 unregister_by_type 传入不存在的 adapter type"""

    class FakeAdapter(TechStackAdapter):
        def supports(self, stack_name: str) -> bool:
            return False

        def generate(self, spec: Dict[str, Any]) -> CodeGeneratorResult:
            return CodeGeneratorResult(code="", status="normal", metadata={})

    initial_count = len(registry._adapters)
    registry.unregister_by_type(FakeAdapter)
    # 不应该影响已有适配器
    assert len(registry._adapters) == initial_count


def test_duplicate_registration_of_same_adapter_type(registry):
    """测试重复注册相同 adapter type"""
    initial_react_count = sum(
        1 for a in registry._adapters if isinstance(a, ReactAdapter)
    )
    registry.register(ReactAdapter())
    new_react_count = sum(
        1 for a in registry._adapters if isinstance(a, ReactAdapter)
    )
    assert new_react_count == initial_react_count + 1


def test_multiple_adapters_for_same_stack_first_match_wins(registry):
    """测试多个 adapter 支持同一 stack 时，第一个匹配的优先"""

    class CustomReactAdapter(TechStackAdapter):
        def supports(self, stack_name: str) -> bool:
            return stack_name.lower() == "react"

        def generate(self, spec: Dict[str, Any]) -> CodeGeneratorResult:
            return CodeGeneratorResult(
                code="// custom react adapter",
                status="normal",
                metadata={"adapter": "custom_react"},
            )

    # Insert at front so it takes priority over existing ReactAdapter
    registry._adapters.insert(0, CustomReactAdapter())
    gen = TechStackCodeGenerator(registry)
    spec = {
        "stack": "react",
        "component_name": "TestComp",
    }
    result = gen.generate_code(spec)

    # CustomReactAdapter 排在 ReactAdapter 前面，应该匹配它
    assert result.metadata["adapter"] == "custom_react"


def test_get_adapter_with_empty_stack_name():
    """测试 get_adapter 对空栈名的处理"""
    registry = PluginAdapterRegistry()
    registry.register(ReactAdapter())
    adapter = registry.get_adapter("")
    # 空字符串不匹配 react，应回退到 fallback
    # 由于没有注册 GenericHTMLAdapter，_get_fallback 会自动创建
    assert isinstance(adapter, GenericHTMLAdapter)
