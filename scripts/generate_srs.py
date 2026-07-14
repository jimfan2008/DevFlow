#!/usr/bin/env python3
"""
SRS 文档生成脚本 — 直接调用 LLM API 生成纯净 SRS 文档

用法:
    python generate_srs.py --project "项目描述" --output /path/to/output.md
    python generate_srs.py --input /path/to/requirements.md --output-dir /path/to/docs
"""
import argparse
import json
import os
import sys
import httpx
import yaml
from datetime import datetime


def _load_hermes_config():
    hermes_real_home = os.environ.get("HERMES_REAL_HOME", "/home/jim")
    config_path = os.path.join(hermes_real_home, ".hermes/profiles/houxing/config.yaml")
    if not os.path.exists(config_path):
        return None
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    api_server = cfg.get("platforms", {}).get("api_server", {})
    if api_server:
        extra = api_server.get("extra", {})
        return {
            "api_base": f"http://{extra.get('host', '127.0.0.1')}:{extra.get('port', 8748)}/v1",
            "api_key": extra.get("key", ""),
            "model": cfg.get("model", {}).get("default", "Qwen3.6-27B-AWQ-INT4"),
        }
    model_cfg = cfg.get("model", {})
    if model_cfg.get("base_url"):
        return {
            "api_base": model_cfg["base_url"].rstrip("/"),
            "api_key": model_cfg.get("api_key", ""),
            "model": model_cfg.get("default", "Qwen3.6-27B-AWQ-INT4"),
        }
    return None


def _load_env_file():
    env_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", ".env"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"),
    ]
    for path in env_paths:
        path = os.path.realpath(path)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value


_load_env_file()
_hermes_cfg = _load_hermes_config()

if _hermes_cfg:
    LLM_API_BASE = _hermes_cfg["api_base"]
    LLM_API_KEY = _hermes_cfg["api_key"]
    LLM_MODEL = _hermes_cfg["model"]
else:
    LLM_API_BASE = os.environ.get("HERMES_API_BASE", "http://127.0.0.1:8748/v1")
    LLM_API_KEY = os.environ.get("HERMES_API_KEY", "")
    LLM_MODEL = os.environ.get("LLM_MODEL", "Qwen3.6-27B-AWQ-INT4")

API_URL = f"{LLM_API_BASE.rstrip('/')}/chat/completions"


def call_llm(messages: list, max_tokens: int = 16000, temperature: float = 0.3) -> str:
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "stream": False,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    with httpx.Client(timeout=300.0) as client:
        resp = client.post(API_URL, headers=headers, json=payload)
        if resp.status_code != 200:
            print(f"ERROR: HTTP {resp.status_code}: {resp.text[:300]}")
            sys.exit(1)
        result = resp.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content:
            print("ERROR: LLM 返回空内容")
            sys.exit(1)
        usage = result.get("usage", {})
        if usage:
            print(f"Token: prompt={usage.get('prompt_tokens', '?')} completion={usage.get('completion_tokens', '?')} total={usage.get('total_tokens', '?')}")
        return content


def generate_srs_chapter(chapter_num: int, chapter_name: str, project_desc: str, prev_chapters: str = "") -> str:
    """生成单个章节，避免一次性生成太长导致截断"""
    context = f"\n\n之前章节的摘要：\n{prev_chapters[-500:]}" if prev_chapters else ""

    user_prompt = f"""你是软件需求分析师。请为以下项目撰写 SRS 文档的第 {chapter_num} 章：{chapter_name}。

项目描述：{project_desc}{context}

要求：
- 用中文写
- 以 `## {chapter_num}. {chapter_name}` 开头
- 内容详细、专业
- 不要写其他章节的内容，只写这一章
- 不要写前缀或后缀，直接从章节标题开始"""

    return call_llm(
        [{"role": "user", "content": user_prompt}],
        max_tokens=4000,
        temperature=0.3,
    )


CHAPTERS = [
    (1, "引言", ["目的", "范围", "术语与缩略语"]),
    (2, "总体描述", ["产品愿景", "用户角色与特征", "运行环境"]),
    (3, "功能需求", ["每个功能带编号(FR-xxx)，描述、输入、处理、输出、可量化验收标准"]),
    (4, "非功能需求", ["性能", "安全性", "可用性", "兼容性", "可维护性"]),
    (5, "接口需求", ["外部接口", "内部接口"]),
    (6, "数据需求", ["数据模型概述", "数据存储", "数据流说明"]),
    (7, "系统架构概述", ["技术栈", "模块划分", "部署架构"]),
    (8, "约束条件", ["技术约束", "业务约束", "法规约束"]),
    (9, "验收标准与测试策略", ["整体验收标准", "测试方法", "测试环境"]),
    (10, "附录", ["参考资料", "变更日志"]),
]


def _clean_output(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()
    return content


def main():
    parser = argparse.ArgumentParser(description="SRS 文档生成")
    parser.add_argument("--project", "-p", help="项目描述")
    parser.add_argument("--input", "-i", help="需求文件路径")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--output-dir", "-d", default="./srs_output", help="输出目录")
    parser.add_argument("--name", "-n", default="", help="项目名称")
    parser.add_argument("--context", "-c", default="", help="补充上下文")
    parser.add_argument("--max-tokens", type=int, default=16000)
    parser.add_argument("--temperature", type=float, default=0.3)
    args = parser.parse_args()

    if not args.project and not args.input:
        print("ERROR: 必须提供 --project 或 --input")
        parser.print_help()
        sys.exit(1)

    project_desc = args.project
    if args.input:
        if not os.path.exists(args.input):
            print(f"ERROR: 文件不存在: {args.input}")
            sys.exit(1)
        with open(args.input, "r", encoding="utf-8") as f:
            project_desc = f.read()

    project_name = args.name or "SRS"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = args.output or os.path.join(args.output_dir, f"{project_name}_SRS_{timestamp}.md")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    print(f"项目: {project_name}")
    print(f"输出: {output_path}")
    print(f"API: {API_URL}")
    print(f"模型: {LLM_MODEL}")
    print("=" * 60)

    full_srs = []

    # 生成文档头
    today = datetime.now().strftime("%Y-%m-%d")
    header = f"""# {project_name or '项目'} 软件需求规格说明书 (SRS)

| 版本 | 作者 | 日期 | 状态 |
|------|------|------|------|
| v1.0 | AI 自动生成 | {today} | 初稿 |

<!-- CHAPTER: SRS Full Document -->
"""
    full_srs.append(header)

    # 逐章生成
    prev_summary = ""
    for i, (ch_num, ch_name, _) in enumerate(CHAPTERS):
        print(f"\n[{i+1}/{len(CHAPTERS)}] 正在生成第 {ch_num} 章：{ch_name} ...")

        user_msg = f"""你是软件需求分析师。请撰写 SRS 文档的以下章节。

项目：{project_name or '项目'}
项目描述：{project_desc}
{f'补充信息：{args.context}\n' if args.context else ''}
{'之前章节摘要：\n' + prev_summary[-800:] if prev_summary else ''}

请写：第 {ch_num} 章：{ch_name}

要求：
1. 以 `### {ch_num}.1 {CHAPTERS[i][2][0] if CHAPTERS[i][2] else '概述'}` 开头（如有子节则逐个写）
2. 内容详细、专业、可量化
3. 全中文
4. 直接写内容，不要前缀后缀，不要代码块包裹
5. 只写这一章的内容"""

        try:
            chapter_content = call_llm(
                [{"role": "user", "content": user_msg}],
                max_tokens=min(args.max_tokens, 6000),
                temperature=args.temperature,
            )
            chapter_content = _clean_output(chapter_content)
            # 如果 LLM 返回的不是章节内容（比如幻觉），跳过
            if not chapter_content or len(chapter_content) < 50:
                print(f"  警告：第 {ch_num} 章内容太短，可能生成失败")
                chapter_content = f"## {ch_num}. {ch_name}\n\n_（待补充）_"
            elif chapter_content.startswith("```"):
                lines = chapter_content.split("\n")
                if lines[0].strip().startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                chapter_content = "\n".join(lines).strip()

            # 确保章节有正确的标题
            if not chapter_content.startswith(f"## {ch_num}") and not chapter_content.startswith(f"### {ch_num}"):
                chapter_content = f"## {ch_num}. {ch_name}\n\n{chapter_content}"

            full_srs.append(chapter_content)
            prev_summary += f"\n第{ch_num}章 {ch_name}：{chapter_content[:200]}..."
            print(f"  完成：{len(chapter_content)} 字符")
        except Exception as e:
            print(f"  错误：第 {ch_num} 章生成失败: {e}")
            full_srs.append(f"## {ch_num}. {ch_name}\n\n_（生成失败: {e}）_")

    # 合并所有章节
    final_content = "\n\n".join(full_srs) + "\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_content)

    size = os.path.getsize(output_path)
    lines = final_content.count("\n") + 1
    print(f"\n{'=' * 60}")
    print(f"完成！SRS 文档已保存")
    print(f"  文件: {output_path}")
    print(f"  大小: {size} 字节 ({lines} 行)")
    print(f"  章节: {len(CHAPTERS)} 章（逐章生成）")
    print(output_path)


if __name__ == "__main__":
    main()
