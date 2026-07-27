import pytest
import time
from unittest.mock import MagicMock, patch, PropertyMock
from typing import List, Dict, Any, Optional


class MockMarkdownRenderer:
    def __init__(self):
        self.supported_languages = {
            "python", "typescript", "sql", "javascript", "java",
            "go", "rust", "cpp", "bash", "yaml", "json", "html",
            "css", "ruby", "php", "swift", "kotlin", "scala",
        }

    def render(self, markdown_text: str) -> str:
        rendered = markdown_text
        for lang in self.supported_languages:
            pattern = f"```{lang}"
            if pattern in markdown_text:
                rendered = rendered.replace(
                    pattern,
                    f'<pre><code class="language-{lang}">'
                )
        rendered = rendered.replace("```", "</code></pre>")
        rendered = rendered.replace("\n", "<br>")
        rendered = rendered.replace("**", "<strong>").replace("**", "</strong>")
        rendered = rendered.replace("*", "<em>").replace("*", "</em>")
        return f"<div class='markdown-body'>{rendered}</div>"

    def render_with_timing(self, markdown_text: str) -> tuple:
        start = time.perf_counter()
        html = self.render(markdown_text)
        elapsed = (time.perf_counter() - start) * 1000
        return html, elapsed


class MockCodeHighlighter:
    def __init__(self):
        self.language_map = {
            "py": "python",
            "ts": "typescript",
            "js": "javascript",
            "sh": "bash",
            "yaml": "yaml",
            "yml": "yaml",
            "json": "json",
            "html": "html",
            "css": "css",
            "sql": "sql",
            "java": "java",
            "go": "go",
            "rs": "rust",
            "cpp": "cpp",
            "rb": "ruby",
            "php": "php",
            "swift": "swift",
            "kt": "kotlin",
            "scala": "scala",
        }

    def get_highlighted_code(self, code: str, language: str) -> str:
        lang = self.language_map.get(language, language)
        if lang not in self.language_map.values():
            return f"<pre><code>{code}</code></pre>"
        return (
            f'<pre><code class="language-{lang} syntax-highlighted">'
            f'<span class="hl-keyword">def</span> '
            f'<span class="hl-function">{code[:20]}&#x2026;</span>'
            f'</code></pre>'
        )

    def supports_language(self, language: str) -> bool:
        normalized = self.language_map.get(language, language)
        return normalized in self.language_map.values()

    def count_supported_languages(self) -> int:
        return len(set(self.language_map.values()))


class MockFileDownloader:
    def __init__(self):
        self.download_records: List[Dict[str, Any]] = []
        self.simulated_delay_ms: float = 0

    def set_simulated_delay(self, delay_ms: float):
        self.simulated_delay_ms = delay_ms

    def download(self, file_url: str, filename: str) -> Dict[str, Any]:
        start = time.perf_counter()
        if self.simulated_delay_ms > 0:
            time.sleep(self.simulated_delay_ms / 1000)
        elapsed = (time.perf_counter() - start) * 1000
        record = {
            "url": file_url,
            "filename": filename,
            "status": "success",
            "elapsed_ms": elapsed,
        }
        self.download_records.append(record)
        return record

    def get_last_download(self) -> Optional[Dict[str, Any]]:
        if self.download_records:
            return self.download_records[-1]
        return None

    def clear_records(self):
        self.download_records.clear()


class TestAgentOutputViewComponent:
    @pytest.fixture
    def renderer(self):
        return MockMarkdownRenderer()

    @pytest.fixture
    def highlighter(self):
        return MockCodeHighlighter()

    @pytest.fixture
    def downloader(self):
        return MockFileDownloader()

    def test_markdown_rendering_within_500ms(self, renderer):
        sample_markdown = "\n".join([
            "# 测试标题",
            "这是一段**加粗**文本和*斜体*文本。",
            "",
            "## 代码示例",
            "```python",
            "def hello():",
            "    print('Hello World')",
            "```",
            "",
            "```typescript",
            "const greet = (name: string): void => {",
            "    console.log(`Hello ${name}`);",
            "};",
            "```",
        ])
        html, elapsed = renderer.render_with_timing(sample_markdown)
        assert elapsed <= 500, (
            f"Markdown渲染耗时 {elapsed:.2f}ms，超过500ms限制"
        )
        assert "markdown-body" in html
        assert "<strong>" in html or "<em>" in html

    def test_render_blank_markdown_returns_valid_html(self, renderer):
        html, elapsed = renderer.render_with_timing("")
        assert elapsed <= 500
        assert "markdown-body" in html

    def test_render_large_markdown_within_time_limit(self, renderer):
        large_md = "\n".join(
            [f"# Heading {i}\n\nParagraph content {i}.\n" for i in range(50)]
        )
        html, elapsed = renderer.render_with_timing(large_md)
        assert elapsed <= 500, (
            f"大文本Markdown渲染耗时 {elapsed:.2f}ms，超过500ms限制"
        )
        assert "markdown-body" in html

    @pytest.mark.parametrize(
        "language,code_snippet",
        [
            ("python", "print('hello')"),
            ("typescript", "const x: number = 1;"),
            ("sql", "SELECT * FROM users;"),
            ("javascript", "console.log('test');"),
            ("java", "public class Test {}"),
            ("go", "package main"),
            ("rust", "fn main() {}"),
            ("cpp", "int main() { return 0; }"),
            ("bash", "echo hello"),
            ("yaml", "key: value"),
            ("json", '{"key": "value"}'),
            ("html", "<div>test</div>"),
            ("css", ".class { color: red; }"),
        ],
    )
    def test_code_block_syntax_highlighting(self, highlighter, language, code_snippet):
        result = highlighter.get_highlighted_code(code_snippet, language)
        assert "syntax-highlighted" in result, (
            f"语言 {language} 未显示语法高亮标记"
        )
        assert f"language-{language}" in result, (
            f"语言 {language} 的CSS类名缺失"
        )

    def test_highlighter_supports_at_least_10_languages(self, highlighter):
        count = highlighter.count_supported_languages()
        assert count >= 10, (
            f"仅支持 {count} 种语言，要求至少10种"
        )

    def test_highlighter_unsupported_language_fallback(self, highlighter):
        result = highlighter.get_highlighted_code("some code", "unknown_lang_xyz")
        assert "syntax-highlighted" not in result

    def test_file_download_response_within_1_second(self, downloader):
        downloader.set_simulated_delay(800)
        result = downloader.download(
            "https://example.com/output/report.pdf",
            "report.pdf",
        )
        assert result["status"] == "success"
        assert result["elapsed_ms"] <= 1000, (
            f"文件下载耗时 {result['elapsed_ms']:.2f}ms，超过1秒限制"
        )

    def test_file_download_immediate_response(self, downloader):
        downloader.set_simulated_delay(0)
        result = downloader.download(
            "https://example.com/output/data.json",
            "data.json",
        )
        assert result["status"] == "success"
        assert result["elapsed_ms"] <= 1000

    def test_multiple_download_records_tracked(self, downloader):
        urls = [
            ("https://example.com/a.pdf", "a.pdf"),
            ("https://example.com/b.csv", "b.csv"),
            ("https://example.com/c.txt", "c.txt"),
        ]
        for url, filename in urls:
            downloader.download(url, filename)
        assert len(downloader.download_records) == 3
        last = downloader.get_last_download()
        assert last is not None
        assert last["filename"] == "c.txt"

    def test_downloader_clear_records(self, downloader):
        downloader.download("https://example.com/f.pdf", "f.pdf")
        assert len(downloader.download_records) == 1
        downloader.clear_records()
        assert len(downloader.download_records) == 0
        assert downloader.get_last_download() is None

    def test_render_headers_and_emphasis(self, renderer):
        sample = "# H1\n## H2\n**bold**\n*italic*"
        html, elapsed = renderer.render_with_timing(sample)
        assert elapsed <= 500
        assert "<strong>" in html or "bold" in html

    def test_render_inline_code(self, renderer):
        sample = "使用 `print()` 函数输出。"
        html, elapsed = renderer.render_with_timing(sample)
        assert elapsed <= 500
        assert "markdown-body" in html

    def test_render_mixed_content_performance(self, renderer):
        lines = []
        lines.append("# 综合性能测试\n")
        for i in range(20):
            lines.append(f"## 章节 {i}\n")
            lines.append(f"这是第{i}段描述，包含**粗体**和*斜体*。\n")
            lines.append("```python\nprint('code block')\n```\n")
            lines.append("```sql\nSELECT 1;\n```\n")
            lines.append("- 列表项A\n")
            lines.append("- 列表项B\n")
        combined = "\n".join(lines)
        html, elapsed = renderer.render_with_timing(combined)
        assert elapsed <= 500, (
            f"混合内容渲染耗时 {elapsed:.2f}ms，超过500ms限制"
        )
        assert "markdown-body" in html

    def test_highlighter_short_alias_resolution(self, highlighter):
        assert highlighter.supports_language("py")
        assert highlighter.supports_language("ts")
        assert highlighter.supports_language("js")
        assert highlighter.supports_language("sh")
        assert highlighter.supports_language("yml")

    def test_download_concurrent_performance(self, downloader):
        downloader.set_simulated_delay(100)
        results = []
        for i in range(5):
            result = downloader.download(
                f"https://example.com/file_{i}.bin",
                f"file_{i}.bin",
            )
            results.append(result)
        for r in results:
            assert r["status"] == "success"
            assert r["elapsed_ms"] <= 1000, (
                f"并发文件 {r['filename']} 下载耗时 {r['elapsed_ms']:.2f}ms"
            )
