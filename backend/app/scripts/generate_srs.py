#!/usr/bin/env python3
"""由 delegate_task 子Agent调用的SRS文档生成脚本。

读取问卷答案JSON和提示词模板，调用LLM生成SRS文档，写入到输出文件。
"""
import argparse
import json
import os
import sys
import yaml
import httpx


HERMES_HOME = os.path.expanduser("~/.hermes")


def _load_llm_config():
    profiles_dir = os.path.join(HERMES_HOME, "profiles", "houxing")
    config_path = os.path.join(profiles_dir, "config.yaml")
    if not os.path.exists(config_path):
        config_path = os.path.join(HERMES_HOME, "config.yaml")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        model_cfg = config.get("model", {})
        base_url = model_cfg.get("base_url", "")
        api_key = model_cfg.get("api_key", "")
        model_name = model_cfg.get("default", "")
        if base_url and model_name:
            return base_url, api_key, model_name
    base_url = os.environ.get("LLM_API_BASE", "http://10.34.1.96:8000/v1")
    api_key = os.environ.get("LLM_API_KEY", "gbm_cq")
    model_name = os.environ.get("LLM_MODEL", "CQ-deepseek-v4-flash")
    return base_url, api_key, model_name


def main():
    parser = argparse.ArgumentParser(description="Generate SRS document from questionnaire answers")
    parser.add_argument("--input-answers", required=True, help="Path to JSON file with answers")
    parser.add_argument("--output-path", required=True, help="Path to write the generated SRS document")
    parser.add_argument("--prompt-file", required=True, help="Path to SRS generation prompt template")
    parser.add_argument("--core-goal", default="", help="Project core goal")
    parser.add_argument("--refs-dir", default="", help="Path to refs documents directory")
    args = parser.parse_args()

    if not os.path.exists(args.input_answers):
        print(json.dumps({"status": "error", "message": f"Answers file not found: {args.input_answers}"}))
        sys.exit(1)
    if not os.path.exists(args.prompt_file):
        print(json.dumps({"status": "error", "message": f"Prompt file not found: {args.prompt_file}"}))
        sys.exit(1)

    with open(args.input_answers, "r", encoding="utf-8") as f:
        answers = json.load(f)
    with open(args.prompt_file, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    answers_text = json.dumps(answers, ensure_ascii=False, indent=2)
    user_prompt = prompt_template.format(answers_text=answers_text)

    base_url, api_key, model_name = _load_llm_config()
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    system_parts = ["你是一位资深软件需求分析师，正在编写一份高质量的正式软件需求规格说明书（SRS）。输出将直接交付给开发团队和测试团队。不要输出任何对话内容、工作日志、分析过程或说明文字——只输出SRS文档正文。"]
    if args.core_goal:
        system_parts.insert(0, f"[项目核心目标]\n{args.core_goal}")
    if args.refs_dir and os.path.isdir(args.refs_dir):
        ref_texts = []
        for fname in sorted(os.listdir(args.refs_dir)):
            fpath = os.path.join(args.refs_dir, fname)
            if os.path.isfile(fpath):
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    if content.strip():
                        ref_texts.append(f"【参考文档: {fname}】\n{content[:8000]}")
                except Exception:
                    pass
        if ref_texts:
            system_parts.append(f"===== 参考文档 =====\n\n" + "\n\n---\n\n".join(ref_texts))
    system_content = "\n\n".join(system_parts)

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "temperature": 0.3,
        "max_tokens": 32000,
    }

    try:
        with httpx.Client(timeout=600) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                print(json.dumps({"status": "error", "message": f"LLM API error {resp.status_code}: {resp.text[:200]}"}))
                sys.exit(1)
            result = resp.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not content or len(content.strip()) < 50:
                print(json.dumps({"status": "error", "message": "LLM returned empty or too short content"}))
                sys.exit(1)

            os.makedirs(os.path.dirname(args.output_path), exist_ok=True)
            with open(args.output_path, "w", encoding="utf-8") as f:
                f.write(content)

            print(json.dumps({"status": "ok", "path": args.output_path}))
    except httpx.ConnectError as e:
        print(json.dumps({"status": "error", "message": f"Cannot connect to LLM at {url}: {str(e)}"}))
        sys.exit(1)
    except httpx.TimeoutException:
        print(json.dumps({"status": "error", "message": "LLM request timed out"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
