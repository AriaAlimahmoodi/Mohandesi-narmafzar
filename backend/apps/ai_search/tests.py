
from django.test import TestCase

from apps.ai_search.models import ResourceChunk
from apps.ai_search.services.chunking import (
    build_resource_chunks,
    parse_ocr_pages,
    split_text,
)
from apps.document_processing.models import OCRJob
from apps.identity.models import User
from apps.resources.models import Resource, ResourceFile


class OCRPageParsingTests(TestCase):
    def test_parse_pages(self):
        text = """--- Page 1 ---
First page text.

--- Page 2 ---
Second page text.
"""

        pages = parse_ocr_pages(text)

        self.assertEqual(
            pages,
            [
                (1, "First page text."),
                (2, "Second page text."),
            ],
        )

    def test_empty_text(self):
        self.assertEqual(parse_ocr_pages(""), [])

    def test_text_without_page_markers(self):
        self.assertEqual(
            parse_ocr_pages("Some OCR text"),
            [(1, "Some OCR text")],
        )


class TextChunkingTests(TestCase):
    def test_short_text_returns_one_chunk(self):
        chunks = split_text(
            "This is a short text.",
            chunk_size=100,
            overlap=20,
        )

        self.assertEqual(
            chunks,
            ["This is a short text."],
        )

    def test_long_text_is_split(self):
        text = "A" * 250

        chunks = split_text(
            text,
            chunk_size=100,
            overlap=20,
        )

        self.assertGreater(len(chunks), 1)
        self.assertEqual(len(chunks[0]), 100)
        self.assertEqual(chunks[1][:20], chunks[0][-20:])

    def test_invalid_overlap_raises_error(self):
        with self.assertRaises(ValueError):
            split_text(
                "test",
                chunk_size=100,
                overlap=100,
            )


class BuildResourceChunksTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ai_test_user",
            password="test-password-123",
        )

        self.resource = Resource.objects.create(
            title="AI Search Test Resource",
            created_by=self.user,
        )

        self.resource_file = ResourceFile.objects.create(
            resource=self.resource,
            file="resources/test.pdf",
            file_type=ResourceFile.FileType.PDF,
            size_bytes=1000,
            sha256="a" * 64,
        )

        self.ocr_job = OCRJob.objects.create(
            resource_file=self.resource_file,
            status=OCRJob.Status.COMPLETED,
            extracted_text=(
                "--- Page 1 ---\n"
                "First page content.\n"
                "--- Page 2 ---\n"
                "Second page content."
            ),
            created_by=self.user,
        )

    def test_build_chunks_preserves_page_numbers(self):
        chunks = build_resource_chunks(
            self.resource_file,
            self.ocr_job,
        )

        self.assertEqual(
            [chunk.page_number for chunk in chunks],
            [1, 2],
        )

        self.assertEqual(
            [chunk.content for chunk in chunks],
            [
                "First page content.",
                "Second page content.",
            ],
        )

    def test_chunk_indexes_start_from_zero_per_page(self):
        self.ocr_job.extracted_text = (
            "--- Page 1 ---\n"
            + ("A" * 250)
            + "\n--- Page 2 ---\n"
            + ("B" * 250)
        )

        chunks = build_resource_chunks(
            self.resource_file,
            self.ocr_job,
            chunk_size=100,
            overlap=20,
        )

        page_one_indexes = [
            chunk.chunk_index
            for chunk in chunks
            if chunk.page_number == 1
        ]

        page_two_indexes = [
            chunk.chunk_index
            for chunk in chunks
            if chunk.page_number == 2
        ]

        self.assertEqual(page_one_indexes, [0, 1, 2])
        self.assertEqual(page_two_indexes, [0, 1, 2])

    def test_build_chunks_does_not_save_to_database(self):
        chunks = build_resource_chunks(
            self.resource_file,
            self.ocr_job,
        )

        self.assertGreater(len(chunks), 0)

        self.assertEqual(
            ResourceChunk.objects.count(),
            0,
        )

    def test_build_chunks_does_not_delete_existing_records(self):
        existing_chunk = ResourceChunk.objects.create(
            resource_file=self.resource_file,
            ocr_job=self.ocr_job,
            page_number=1,
            chunk_index=99,
            content="Existing chunk",
        )

        build_resource_chunks(
            self.resource_file,
            self.ocr_job,
        )

        self.assertTrue(
            ResourceChunk.objects.filter(
                pk=existing_chunk.pk,
                content="Existing chunk",
            ).exists()
        )
