import os
import re
import json
import math
from collections import Counter
from typing import List, Dict, Tuple


DOC_SHARD_CONFIGS = {
    "ARCHITECTURE": {
        "chapters": [
            {"key": "overview", "title": "总体架构概览", "instruction": "系统整体架构图描述、高层架构视图"},
            {"key": "layers", "title": "分层架构设计", "instruction": "各层职责、层间接口、分层原则"},
            {"key": "modules", "title": "模块划分", "instruction": "模块列表、模块职责、模块间依赖"},
            {"key": "tech_stack", "title": "技术栈选型", "instruction": "技术选型理由、版本、替代方案"},
            {"key": "deployment", "title": "部署架构", "instruction": "部署拓扑、环境划分、容灾策略"},
        ]
    },
    "FRONTEND": {
        "chapters": [
            {"key": "tech_stack", "title": "前端技术栈", "instruction": "框架、UI库、构建工具、版本"},
            {"key": "component_tree", "title": "组件树设计", "instruction": "组件层级、复用策略、组件职责"},
            {"key": "routing", "title": "路由设计", "instruction": "路由结构、懒加载、权限路由"},
            {"key": "state_mgmt", "title": "状态管理", "instruction": "状态方案、Store结构、数据流"},
            {"key": "layout", "title": "页面布局", "instruction": "布局框架、响应式方案、主题"},
        ]
    },
    "BACKEND": {
        "chapters": [
            {"key": "tech_stack", "title": "后端技术栈", "instruction": "语言、框架、中间件、版本"},
            {"key": "api_design", "title": "API接口设计", "instruction": "接口列表、RESTful规范、版本策略"},
            {"key": "data_flow", "title": "数据流设计", "instruction": "核心业务流程数据流、消息队列"},
            {"key": "middleware", "title": "中间件配置", "instruction": "缓存、消息队列、搜索引擎等"},
            {"key": "security", "title": "安全策略", "instruction": "认证、授权、数据加密、防攻击"},
        ]
    },
    "DATABASE": {
        "chapters": [
            {"key": "overview", "title": "ER概述", "instruction": "ER图描述、核心实体关系"},
            {"key": "tables", "title": "表结构DDL", "instruction": "所有表的完整DDL、字段说明"},
            {"key": "indexes", "title": "索引策略", "instruction": "索引列表、复合索引设计、性能考量"},
            {"key": "constraints", "title": "外键约束", "instruction": "外键定义、参照完整性、级联策略"},
            {"key": "migrations", "title": "迁移脚本", "instruction": "版本迁移策略、初始脚本、回滚方案"},
        ]
    },
    "SRS": {
        "chapters": [
            {"key": "overview", "title": "项目概述", "instruction": "项目背景、目标、范围、术语表"},
            {"key": "functional", "title": "功能需求", "instruction": "所有功能需求的详细描述",
             "dynamic_sub": True},
            {"key": "non_functional", "title": "非功能需求", "instruction": "性能、安全、可用性等非功能需求"},
            {"key": "constraints", "title": "约束条件", "instruction": "技术约束、业务约束、法规约束"},
            {"key": "glossary", "title": "术语表", "instruction": "项目专用术语定义"},
        ]
    },
    "ENV": {
        "chapters": [
            {"key": "repo", "title": "代码仓库", "instruction": "仓库初始化、分支策略、Git配置"},
            {"key": "framework", "title": "开发框架", "instruction": "框架搭建、项目结构、启动脚本"},
            {"key": "dependencies", "title": "依赖配置", "instruction": "依赖管理、版本锁定、构建配置"},
            {"key": "database_init", "title": "数据库初始化", "instruction": "数据库创建、迁移执行、种子数据"},
            {"key": "cicd", "title": "CI/CD流水线", "instruction": "流水线配置、自动化测试、部署策略"},
        ]
    },
}


def get_shard_config(doc_type: str) -> list:
    cfg = DOC_SHARD_CONFIGS.get(doc_type, {})
    chapters = cfg.get("chapters", [])
    result = []
    for ch in chapters:
        result.append(ch)
    return result


def get_parent_chapter(key: str) -> str:
    """Extract parent chapter key from a dotted key like 'functional.auth' → 'functional'"""
    if "." in key:
        return key.split(".")[0]
    return key


def get_chapter_filename(doc_type: str, chapter_key: str, docs_dir: str, slug: str) -> str:
    return os.path.join(docs_dir, f"{slug}_{doc_type}_{chapter_key}.md")


def get_dynamic_sub_chapters(doc_type: str, parent_key: str, docs_dir: str, slug: str) -> Dict[str, Dict]:
    prefix = f"{slug}_{doc_type}_func-"
    result = {}
    if not os.path.isdir(docs_dir):
        return result
    for fname in sorted(os.listdir(docs_dir)):
        if fname.startswith(prefix) and fname.endswith(".md"):
            sub_key = fname[len(prefix):-3]
            full_key = f"func-{sub_key}"
            fpath = os.path.join(docs_dir, fname)
            content = ""
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                pass
            result[full_key] = {
                "key": full_key,
                "title": f"功能需求-{sub_key}",
                "content": content,
                "path": fpath,
                "parent_key": parent_key,
            }
    return result


def load_all_chapters(doc_type: str, docs_dir: str, slug: str) -> Dict[str, Dict]:
    chapters = get_shard_config(doc_type)
    result = {}
    for ch in chapters:
        if ch.get("dynamic_sub"):
            subs = get_dynamic_sub_chapters(doc_type, ch["key"], docs_dir, slug)
            if subs:
                result.update(subs)
                continue
        fpath = get_chapter_filename(doc_type, ch["key"], docs_dir, slug)
        content = ""
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
        result[ch["key"]] = {
            "key": ch["key"],
            "title": ch["title"],
            "content": content,
            "path": fpath,
        }
    return result


def load_single_chapter(doc_type: str, chapter_key: str, docs_dir: str, slug: str) -> str:
    fpath = get_chapter_filename(doc_type, chapter_key, docs_dir, slug)
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def save_chapter(doc_type: str, chapter_key: str, content: str, docs_dir: str, slug: str) -> str:
    fpath = get_chapter_filename(doc_type, chapter_key, docs_dir, slug)
    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
    return fpath


def build_chapter_prompt(doc_type: str, chapter_key: str, docs_dir: str, slug: str,
                         requirement: str = "") -> str:
    configs = get_shard_config(doc_type)
    ch = next((c for c in configs if c["key"] == chapter_key), None)
    if not ch:
        return ""
    lines = [
        f"=== {ch['title']} ===",
        f"请编写章节：{ch['instruction']}",
    ]
    if requirement:
        lines.append(f"\n参考需求：\n{requirement[:2000]}")
    return "\n".join(lines)


def build_all_chapters_prompt(doc_type: str, docs_dir: str, slug: str) -> str:
    all_ch = load_all_chapters(doc_type, docs_dir, slug)
    parts = []
    for key, data in all_ch.items():
        if data["content"]:
            summary = data["content"][:200].replace("\n", " ") + "..."
            parts.append(f"[{key}] {data['title']}: {summary}")
    return "\n".join(parts) if parts else ""


def build_cacheable_chapter_summaries(doc_type: str, docs_dir: str, slug: str,
                                       exclude_key: str = None) -> List[str]:
    all_ch = load_all_chapters(doc_type, docs_dir, slug)
    cache_parts = []
    for key, data in all_ch.items():
        if exclude_key and key == exclude_key:
            continue
        if data["content"]:
            summary = data["content"][:300].replace("\n", " ")
            cache_parts.append(f"【{data['title']} ({key})】\n{summary}")
    return cache_parts


class ShardRetriever:
    def __init__(self, docs_dir: str, slug: str, doc_type: str = None):
        self.docs_dir = docs_dir
        self.slug = slug
        self.doc_type = doc_type

    def _tokenize(self, text: str) -> List[str]:
        tokens = re.findall(r'[\w\u4e00-\u9fff]+', text.lower())
        return tokens

    def _tfidf(self, query: str, doc_text: str) -> float:
        q_tokens = set(self._tokenize(query))
        d_tokens = self._tokenize(doc_text)
        if not q_tokens or not d_tokens:
            return 0.0
        d_counter = Counter(d_tokens)
        shared = q_tokens & set(d_tokens)
        score = sum(math.log1p(d_counter[t]) for t in shared)
        return score / (len(q_tokens) ** 0.5 + 1)

    def retrieve(self, query: str, doc_type: str = None,
                 top_k: int = 2, exclude_key: str = None) -> List[Dict]:
        dt = doc_type or self.doc_type
        if not dt:
            return []
        all_ch = load_all_chapters(dt, self.docs_dir, self.slug)
        scored = []
        for key, data in all_ch.items():
            if exclude_key and key == exclude_key:
                continue
            if not data["content"]:
                continue
            score = self._tfidf(query, data["content"])
            scored.append({"key": key, "title": data["title"], "score": score})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def build_context_prompt(self, query: str, doc_type: str = None,
                              top_k: int = 2, exclude_key: str = None) -> str:
        results = self.retrieve(query, doc_type, top_k, exclude_key)
        if not results:
            return ""
        parts = ["【相关章节参考（向量检索）】"]
        for r in results:
            if r["score"] > 0:
                content = load_single_chapter(doc_type or self.doc_type, r["key"],
                                               self.docs_dir, self.slug)
                snippet = content[:500].replace("\n", " ") if content else ""
                parts.append(f"\n--- {r['title']} (相关度:{r['score']:.2f}) ---\n{snippet}")
        return "\n".join(parts)
