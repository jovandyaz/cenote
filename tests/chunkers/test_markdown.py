# SPDX-License-Identifier: Apache-2.0
"""Tests for MarkdownChunker."""

from __future__ import annotations

from cenote.chunkers import MarkdownChunker
from cenote.models import Document


class TestMarkdownChunker:
    def test_splits_on_h1_h2_h3(self) -> None:
        doc = Document(
            id="doc1",
            content=(
                "# Title\nIntro paragraph.\n\n"
                "## Section A\nBody of section A.\n\n"
                "## Section B\nBody of section B.\n"
            ),
        )
        chunks = MarkdownChunker(chunk_size=512).chunk(doc)
        assert len(chunks) >= 3
        assert any("Section A" in c.content for c in chunks)
        assert any("Section B" in c.content for c in chunks)

    def test_heading_hierarchy_in_metadata(self) -> None:
        doc = Document(
            id="doc1",
            content=("# Title\n## Section A\n### Subsection 1\nBody under subsection.\n"),
        )
        chunks = MarkdownChunker(chunk_size=512).chunk(doc)
        last = chunks[-1]
        assert last.metadata["headings"] == ["Title", "Section A", "Subsection 1"]

    def test_chunk_content_includes_heading_prefix(self) -> None:
        doc = Document(
            id="doc1",
            content="# Title\n\n## Section\n\nBody.\n",
        )
        chunks = MarkdownChunker().chunk(doc)
        section_chunk = next(c for c in chunks if "Body" in c.content)
        assert "Title" in section_chunk.content
        assert "Section" in section_chunk.content

    def test_fenced_code_block_atomic(self) -> None:
        code = "```python\n" + ("x = 1\n" * 200) + "```"
        doc = Document(id="doc1", content=f"# Title\n\n{code}\n")
        chunks = MarkdownChunker(chunk_size=100).chunk(doc)
        intact = [c for c in chunks if "```python" in c.content and "```" in c.content[3:]]
        assert len(intact) == 1

    def test_unfinished_fence_falls_through(self) -> None:
        doc = Document(id="doc1", content="# Title\n\n```python\nx = 1\nno close\n")
        chunks = MarkdownChunker(chunk_size=512).chunk(doc)
        assert len(chunks) >= 1

    def test_list_kept_intact(self) -> None:
        doc = Document(
            id="doc1",
            content=("# Title\n\n- item one\n- item two\n- item three\n- item four\n- item five\n"),
        )
        chunks = MarkdownChunker(chunk_size=512).chunk(doc)
        body = "\n".join(c.content for c in chunks)
        for label in ("item one", "item two", "item three", "item four", "item five"):
            assert label in body

    def test_table_preserved_atomic(self) -> None:
        table = "| col1 | col2 |\n|---|---|\n| a | b |\n| c | d |\n"
        doc = Document(id="doc1", content=f"# Title\n\n{table}\n")
        chunks = MarkdownChunker(chunk_size=100).chunk(doc)
        intact = [c for c in chunks if "col1" in c.content and "| c | d |" in c.content]
        assert len(intact) == 1

    def test_blockquote_preserved(self) -> None:
        doc = Document(
            id="doc1",
            content="# Title\n\n> line one of quote\n> line two of quote\n",
        )
        chunks = MarkdownChunker().chunk(doc)
        intact = [c for c in chunks if "line one" in c.content and "line two" in c.content]
        assert len(intact) == 1

    def test_long_section_falls_back_to_recursive(self) -> None:
        size = 512
        long_body = "Lorem ipsum dolor sit amet. " * 200
        doc = Document(id="doc1", content=f"# Title\n\n## Section\n\n{long_body}\n")
        chunks = MarkdownChunker(chunk_size=size, chunk_overlap=50).chunk(doc)
        assert len(chunks) >= 2
        assert all(len(c.content) <= size * 2 for c in chunks), "fallback overshot slack"

    def test_no_markdown_structure(self) -> None:
        text = "Just a long paragraph of plain text. " * 60
        doc = Document(id="doc1", content=text)
        chunks = MarkdownChunker(chunk_size=256).chunk(doc)
        assert len(chunks) >= 2
        assert all(c.metadata.get("headings") == [] for c in chunks)

    def test_chunk_ids_deterministic(self) -> None:
        doc = Document(id="doc1", content="# Title\n\n## Section A\nA body.\n")
        a = MarkdownChunker().chunk(doc)
        b = MarkdownChunker().chunk(doc)
        assert [c.id for c in a] == [c.id for c in b]

    def test_metadata_deep_copied(self) -> None:
        meta = {"source": "test", "tags": ["a"]}
        doc = Document(id="doc1", content="# Title\n\nBody.\n", metadata=meta)
        chunks = MarkdownChunker().chunk(doc)
        chunks[0].metadata["tags"].append("mutated")
        assert meta["tags"] == ["a"]
