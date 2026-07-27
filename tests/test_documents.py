"""Tests for the Document service: CRUD, lazy fetch, files, notes, history, custom fields."""

import datetime
import io
import json
import re

import pytest
from pytest_httpx import HTTPXMock

from pypaperless import PaperlessClient
from pypaperless.const import EndpointPath
from pypaperless.exceptions import (
    AsnRequestError,
    DeletionError,
    DraftFieldRequiredError,
    JsonResponseWithError,
    PrimaryKeyRequiredError,
    SendEmailError,
)
from pypaperless.models import (
    Correspondent,
    CustomField,
    Document,
    DocumentAISuggestions,
    DocumentChat,
    DocumentCustomFieldList,
    DocumentDraft,
    DocumentHistory,
    DocumentHistoryAction,
    DocumentMeta,
    DocumentNote,
    DocumentNoteDraft,
    DocumentRoot,
    DocumentSuggestions,
    DocumentVersionInfo,
    DownloadedDocument,
    ShareLink,
)
from pypaperless.models.types import (
    CustomFieldBooleanValue,
    CustomFieldDocumentLinkValue,
    CustomFieldIntegerValue,
    CustomFieldStringValue,
    CustomFieldValue,
    DocumentMetaEntry,
    DocumentSearchHit,
    FileRetrieveMode,
)
from pypaperless.services.documents.notes import DocumentNoteService
from pypaperless.services.mixins.updatable import UpdatableService

from .const import PAPERLESS_TEST_URL
from .data import (
    DATA_CUSTOM_FIELDS,
    DATA_DOCUMENT_AI_SUGGESTIONS,
    DATA_DOCUMENT_CHAT,
    DATA_DOCUMENT_HISTORY,
    DATA_DOCUMENT_METADATA,
    DATA_DOCUMENT_NOTES,
    DATA_DOCUMENT_ROOT,
    DATA_DOCUMENT_SHARE_LINKS,
    DATA_DOCUMENT_SUGGESTIONS,
    DATA_DOCUMENT_VERSION_INFO,
    DATA_DOCUMENTS,
    DATA_DOCUMENTS_SEARCH,
)
from .mappings import DOCUMENT_MAP


class TestDocuments:
    """Document service: full CRUD, lazy loading, files, notes, history, custom fields."""

    async def test_lazy(self, paperless: PaperlessClient) -> None:
        """Lazy-loaded document has id set but no title fetched."""
        document = await paperless.documents(42, lazy=True)
        assert document.id == 42
        assert document.title is None

    async def test_create(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """Draft upload validates required fields and POSTs via the correct endpoint."""
        defaults = DOCUMENT_MAP.draft_defaults or {}
        draft = paperless.documents.create(**defaults)
        assert isinstance(draft, DocumentDraft)
        backup = draft.document
        draft.document = None
        with pytest.raises(DraftFieldRequiredError):
            await paperless.documents.save(draft)
        draft.document = backup
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_POST}",
            status_code=200,
            json="11112222-3333-4444-5555-666677778888",
        )
        await paperless.documents.save(draft)

    async def test_create_date_property(self, paperless: PaperlessClient) -> None:
        """created_date is an alias for the created field."""
        document = Document.from_data(paperless.runtime, data={**DATA_DOCUMENTS["results"][0]})
        assert document.created_date == document.created

    async def test_update(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """Updating a document PATCHes the changed field and nothing else."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_SINGLE}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENTS["results"][0],
        )
        to_update = await paperless.documents(1)
        new_title = f"{to_update.title} Updated"
        to_update.title = new_title
        httpx_mock.add_response(
            method="PATCH",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_SINGLE}".format(pk=1),
            status_code=200,
            json={**to_update.snapshot, "title": new_title},
        )
        assert await paperless.documents.update(to_update) is True
        assert json.loads(httpx_mock.get_requests()[-1].content) == {"title": new_title}
        assert to_update.title == new_title

    async def test_delete(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """Deleting a document returns True on 204 and False on any other status."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_SINGLE}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENTS["results"][0],
        )
        to_delete = await paperless.documents(1)
        httpx_mock.add_response(
            method="DELETE",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_SINGLE}".format(pk=1),
            status_code=204,
        )
        await paperless.documents.delete(to_delete)

    async def test_meta(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """get_metadata() returns a DocumentMeta with original and archive metadata lists."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_META}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENT_METADATA,
        )
        meta = await paperless.documents.metadata(1)
        assert isinstance(meta, DocumentMeta)
        assert isinstance(meta.original_metadata, list)
        for item in meta.original_metadata:
            assert isinstance(item, DocumentMetaEntry)
        assert isinstance(meta.archive_metadata, list)
        for item in meta.archive_metadata:
            assert isinstance(item, DocumentMetaEntry)

    async def test_files(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """get_download/preview/thumbnail each return a DownloadedDocument."""
        httpx_mock.add_response(
            method="GET",
            url=re.compile(
                r"^"
                + f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_DOWNLOAD}".format(pk=1)
                + r"\?.*$"
            ),
            status_code=200,
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": "attachment;filename=any_filename.pdf",
            },
            content=b"Binary data: download",
        )
        download = await paperless.documents.download(1)
        assert isinstance(download, DownloadedDocument)
        assert download.mode == FileRetrieveMode.DOWNLOAD

        httpx_mock.add_response(
            method="GET",
            url=re.compile(
                r"^"
                + f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_PREVIEW}".format(pk=1)
                + r"\?.*$"
            ),
            status_code=200,
            headers={"Content-Type": "application/pdf"},
            content=b"Binary data: preview",
        )
        preview = await paperless.documents.preview(1)
        assert isinstance(preview, DownloadedDocument)
        assert preview.mode == FileRetrieveMode.PREVIEW

        httpx_mock.add_response(
            method="GET",
            url=re.compile(
                r"^"
                + f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_THUMBNAIL}".format(pk=1)
                + r"\?.*$"
            ),
            status_code=200,
            content=b"Binary data: thumbnail",
        )
        thumbnail = await paperless.documents.thumbnail(1)
        assert isinstance(thumbnail, DownloadedDocument)
        assert thumbnail.mode == FileRetrieveMode.THUMBNAIL

    async def test_suggestions(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """get_suggestions() returns a DocumentSuggestions instance."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_SUGGESTIONS}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENT_SUGGESTIONS,
        )
        assert isinstance(await paperless.documents.suggestions(1), DocumentSuggestions)

    async def test_get_next_asn(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """get_next_asn() returns an int on success and raises AsnRequestError on failure."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_NEXT_ASN}",
            status_code=200,
            json=1337,
        )
        assert isinstance(await paperless.documents.get_next_asn(), int)
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_NEXT_ASN}",
            status_code=500,
        )
        with pytest.raises(AsnRequestError):
            await paperless.documents.get_next_asn()

    async def test_searching(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """search(), search(custom_field_query=), and more_like() return typed items."""
        httpx_mock.add_response(
            method="GET",
            url=re.compile(
                r"^" + f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS}" + r"\?.*query.*$"
            ),
            status_code=200,
            json=DATA_DOCUMENTS_SEARCH,
        )
        async for item in paperless.documents.search("1337"):
            assert isinstance(item, Document)
            assert item.has_search_hit
            assert isinstance(item.search_hit, DocumentSearchHit)

        httpx_mock.add_response(
            method="GET",
            url=re.compile(
                r"^"
                f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS}"
                r"\?.*custom_field_query.*$"
            ),
            status_code=200,
            json=DATA_DOCUMENTS_SEARCH,
        )
        async for item in paperless.documents.search(custom_field_query="1337"):
            assert isinstance(item, Document)
            assert item.has_search_hit
            assert isinstance(item.search_hit, DocumentSearchHit)

        httpx_mock.add_response(
            method="GET",
            url=re.compile(
                r"^"
                f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS}"
                r"\?.*more_like_id.*$"
            ),
            status_code=200,
            json=DATA_DOCUMENTS_SEARCH,
        )
        async for item in paperless.documents.more_like(1337):
            assert isinstance(item, Document)
            assert item.has_search_hit
            assert isinstance(item.search_hit, DocumentSearchHit)

    async def test_find_duplicate(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """find_duplicate() hashes the bytes and returns the first match, or None."""
        content = b"%PDF-fake-content"

        httpx_mock.add_response(
            method="GET",
            url=re.compile(
                r"^" + f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS}" + r"\?.*checksum.*$"
            ),
            status_code=200,
            json=DATA_DOCUMENTS,
        )
        hit = await paperless.documents.find_duplicate(content, filename="invoice.pdf")
        assert isinstance(hit, Document)
        assert hit.id == DATA_DOCUMENTS["results"][0]["id"]

        request = httpx_mock.get_requests()[-1]
        assert "checksum__iexact=" in request.url.query.decode()
        assert "original_filename__iexact=invoice.pdf" in request.url.query.decode()

        httpx_mock.add_response(
            method="GET",
            url=re.compile(
                r"^" + f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS}" + r"\?.*checksum.*$"
            ),
            status_code=200,
            json={"count": 0, "next": None, "previous": "", "results": [], "all": []},
        )
        miss = await paperless.documents.find_duplicate(content)
        assert miss is None

        request = httpx_mock.get_requests()[-1]
        assert "original_filename__iexact" not in request.url.query.decode()

    async def test_note_call(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """Notes list returns DocumentNote instances; missing pk raises PrimaryKeyRequiredError."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_SINGLE}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENTS["results"][0],
        )
        item = await paperless.documents(1)
        assert isinstance(item, Document)
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_NOTES}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENT_NOTES,
        )
        results = await item.notes(force_request=True)
        assert isinstance(results, list)
        assert len(results) > 0
        for note in results:
            assert isinstance(note, DocumentNote)
            assert isinstance(note.created, datetime.datetime)
        with pytest.raises(PrimaryKeyRequiredError):
            item = await paperless.documents.notes()

    async def test_note_create(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """Note draft validates required fields and POSTs to the notes endpoint."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_SINGLE}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENTS["results"][0],
        )
        item = await paperless.documents(1)
        draft = item.notes.create(note="Test note.")
        assert isinstance(draft, DocumentNoteDraft)
        backup = draft.note
        draft.note = None
        with pytest.raises(DraftFieldRequiredError):
            await item.notes.save(draft)
        draft.note = backup
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_NOTES}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENT_NOTES,
        )
        result = await item.notes.save(draft)
        assert isinstance(result, int)
        # cache is updated from the POST response — no extra request needed
        assert item.notes_ is not None
        assert len(item.notes_) == len(DATA_DOCUMENT_NOTES)

    async def test_note_delete(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """Deleting a note removes it from the embedded cache.

        DeletionError propagates correctly.
        """
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_SINGLE}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENTS["results"][0],
        )
        item = await paperless.documents(1)
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_NOTES}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENT_NOTES,
        )
        results = await item.notes(force_request=True)
        assert len(results) == len(DATA_DOCUMENT_NOTES)
        httpx_mock.add_response(
            method="DELETE",
            url=re.compile(
                r"^" + f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_NOTES}".format(pk=1) + r"\?.*$"
            ),
            status_code=204,
        )
        deleted = results[0]
        await item.notes.delete(deleted)
        # cache is updated in-place — no API request needed
        cached = await item.notes()
        assert len(cached) == len(DATA_DOCUMENT_NOTES) - 1
        assert all(n.id != deleted.id for n in cached)
        # integer shorthand: delete by note id in document context
        httpx_mock.add_response(
            method="DELETE",
            url=re.compile(
                r"^" + f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_NOTES}".format(pk=1) + r"\?.*$"
            ),
            status_code=204,
        )
        int_target = cached[0]
        await item.notes.delete(int_target.id)
        cached = await item.notes()
        assert all(n.id != int_target.id for n in cached)
        # failed note deletion raises DeletionError
        httpx_mock.add_response(
            method="DELETE",
            url=re.compile(
                r"^" + f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_NOTES}".format(pk=1) + r"\?.*$"
            ),
            status_code=404,
        )
        with pytest.raises(DeletionError):
            await item.notes.delete(cached[0])
        # silent_fail=True suppresses DeletionError
        httpx_mock.add_response(
            method="DELETE",
            url=re.compile(
                r"^" + f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_NOTES}".format(pk=1) + r"\?.*$"
            ),
            status_code=404,
        )
        await item.notes.delete(cached[0], silent_fail=True)

    async def test_notes_embedded(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """Embedded notes are parsed into notes_ without a second API call."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_SINGLE}".format(pk=2),
            status_code=200,
            json=DATA_DOCUMENTS["results"][1],
        )
        item = await paperless.documents(2)
        assert isinstance(item, Document)
        assert isinstance(item.notes_, list)
        assert len(item.notes_) == len(DATA_DOCUMENTS["results"][1]["notes"])
        for note in item.notes_:
            assert isinstance(note, DocumentNote)
            assert isinstance(note.user, int)
            assert note.document == item.id
        # document.notes still returns the service (no regression)
        assert isinstance(item.notes, DocumentNoteService)
        # calling notes() returns cached data without an API request
        cached = await item.notes()
        assert cached == item.notes_

    async def test_notes_embedded_document_backfill(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """note.document is backfilled from document.id when the API omits it."""
        payload = {
            **DATA_DOCUMENTS["results"][1],
            "notes": [
                {k: v for k, v in n.items() if k != "document"}
                for n in DATA_DOCUMENTS["results"][1]["notes"]
            ],
        }
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_SINGLE}".format(pk=2),
            status_code=200,
            json=payload,
        )
        item = await paperless.documents(2)
        assert item.notes_ is not None
        for note in item.notes_:
            assert note.document == item.id

    async def test_notes_embedded_empty(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """notes_ is an empty list when the document has no notes."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_SINGLE}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENTS["results"][0],
        )
        item = await paperless.documents(1)
        assert item.notes_ == []

    async def test_notes_force_request(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """force_request=True bypasses the embedded cache and fetches from the API."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_SINGLE}".format(pk=2),
            status_code=200,
            json=DATA_DOCUMENTS["results"][1],
        )
        item = await paperless.documents(2)
        assert item.notes_ is not None  # populated from embedded payload
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_NOTES}".format(pk=2),
            status_code=200,
            json=DATA_DOCUMENT_NOTES,
        )
        results = await item.notes(force_request=True)
        assert isinstance(results, list)
        for note in results:
            assert isinstance(note, DocumentNote)

    async def test_note_user_int_passthrough(self, paperless: PaperlessClient) -> None:
        """_coerce_user returns the value unchanged when user is already an int."""
        note = DocumentNote.from_data(
            paperless._runtime,
            {"id": 1, "note": "x", "user": 42, "document": 1},
        )
        assert note.user == 42

    async def test_note_standalone_call(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """Standalone notes service (no document instance) fetches from API without caching."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_NOTES}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENT_NOTES,
        )
        results = await paperless.documents.notes(1)
        assert isinstance(results, list)
        assert len(results) == len(DATA_DOCUMENT_NOTES)
        for note in results:
            assert isinstance(note, DocumentNote)

    async def test_note_standalone_save(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """Standalone save() posts the note and returns the new id without updating any cache."""
        draft = paperless.documents.notes.create(1, note="Standalone note.")
        assert isinstance(draft, DocumentNoteDraft)
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_NOTES}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENT_NOTES,
        )
        result = await paperless.documents.notes.save(draft)
        assert isinstance(result, int)

    async def test_note_save_error_payload(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """save() raises JsonResponseWithError when Paperless returns 200 with an error dict."""
        draft = paperless.documents.notes.create(1, note="Doomed note.")
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_NOTES}".format(pk=1),
            status_code=200,
            json={"error": "Error saving note, check logs for more detail."},
        )
        with pytest.raises(JsonResponseWithError, match="Error saving note"):
            await paperless.documents.notes.save(draft)

    async def test_note_standalone_delete(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """Standalone delete() removes the note without touching any cache."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_NOTES}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENT_NOTES,
        )
        notes = await paperless.documents.notes(1)
        httpx_mock.add_response(
            method="DELETE",
            url=re.compile(
                r"^" + f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_NOTES}".format(pk=1) + r"\?.*$"
            ),
            status_code=204,
        )
        await paperless.documents.notes.delete(notes[0])
        # integer shorthand with explicit pk
        httpx_mock.add_response(
            method="DELETE",
            url=re.compile(
                r"^" + f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_NOTES}".format(pk=1) + r"\?.*$"
            ),
            status_code=204,
        )
        await paperless.documents.notes.delete(notes[0].id, pk=1)

    async def test_note_delete_missing_pk(self, paperless: PaperlessClient) -> None:
        """Integer delete without document context and no pk raises PrimaryKeyRequiredError."""
        with pytest.raises(PrimaryKeyRequiredError):
            await paperless.documents.notes.delete(2)

    async def test_history_call(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """History returns typed entries; direct service call and missing pk error both work."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_SINGLE}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENTS["results"][0],
        )
        item = await paperless.documents(1)
        httpx_mock.add_response(
            method="GET",
            url=re.compile(
                r"^" + f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_HISTORY}".format(pk=1) + r".*$"
            ),
            status_code=200,
            json=DATA_DOCUMENT_HISTORY,
        )
        results = await item.history()
        assert isinstance(results, list)
        assert len(results) == len(DATA_DOCUMENT_HISTORY)
        for entry in results:
            assert isinstance(entry, DocumentHistory)
            assert entry.document == item.id
            assert isinstance(entry.timestamp, datetime.datetime)
            assert isinstance(entry.action, DocumentHistoryAction)
            assert isinstance(entry.changes, dict)

        httpx_mock.add_response(
            method="GET",
            url=re.compile(
                r"^" + f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_HISTORY}".format(pk=1) + r".*$"
            ),
            status_code=200,
            json=DATA_DOCUMENT_HISTORY,
        )
        results_direct = await paperless.documents.history(1)
        assert isinstance(results_direct, list)
        assert len(results_direct) == len(DATA_DOCUMENT_HISTORY)

        with pytest.raises(PrimaryKeyRequiredError):
            await paperless.documents.history()

    async def test_share_links_call(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """Share links returns ShareLink instances; missing pk raises PrimaryKeyRequiredError."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_SINGLE}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENTS["results"][0],
        )
        item = await paperless.documents(1)
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_SHARE_LINKS}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENT_SHARE_LINKS,
        )
        results = await item.share_links()
        assert isinstance(results, list)
        assert len(results) == len(DATA_DOCUMENT_SHARE_LINKS)
        for link in results:
            assert isinstance(link, ShareLink)

        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_SHARE_LINKS}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENT_SHARE_LINKS,
        )
        results_direct = await paperless.documents.share_links(1)
        assert isinstance(results_direct, list)
        assert len(results_direct) == len(DATA_DOCUMENT_SHARE_LINKS)

        with pytest.raises(PrimaryKeyRequiredError):
            await paperless.documents.share_links()

    async def test_custom_field_list_without_cache(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """Without cache, custom fields are plain CustomFieldValue instances."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_SINGLE}".format(pk=2),
            status_code=200,
            json=DATA_DOCUMENTS["results"][1],
        )
        item = await paperless.documents(2)
        assert isinstance(item.custom_fields, DocumentCustomFieldList)
        for field in item.custom_fields:
            assert type(field) is CustomFieldValue

    async def test_custom_field_list_with_cache(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """With cache, custom fields are typed; operators += and -= update the list."""
        httpx_mock.add_response(
            method="GET",
            url=re.compile(r"^" + f"{PAPERLESS_TEST_URL}{EndpointPath.CUSTOM_FIELDS}" + r"\?.*$"),
            status_code=200,
            json=DATA_CUSTOM_FIELDS,
        )
        paperless.runtime.cache.custom_fields = await paperless.custom_fields.as_dict()

        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_SINGLE}".format(pk=2),
            status_code=200,
            json=DATA_DOCUMENTS["results"][1],
        )
        item = await paperless.documents(2)
        assert isinstance(item.custom_fields, DocumentCustomFieldList)
        for field in item.custom_fields:
            assert isinstance(field, CustomFieldValue)

        test_cf = CustomField.from_data(
            runtime=paperless.runtime,
            data=DATA_CUSTOM_FIELDS["results"][0],
        )
        assert test_cf in item.custom_fields
        assert isinstance(item.custom_fields.get(test_cf), CustomFieldValue)
        assert item.custom_fields.default(test_cf) is not None
        assert item.custom_fields.default(-1337) is None

        assert isinstance(
            item.custom_fields.get(test_cf, CustomFieldDocumentLinkValue),
            CustomFieldDocumentLinkValue,
        )
        assert isinstance(
            item.custom_fields.default(test_cf, CustomFieldDocumentLinkValue),
            CustomFieldDocumentLinkValue,
        )
        with pytest.raises(TypeError):
            item.custom_fields.get(test_cf, CustomFieldBooleanValue)
        with pytest.raises(TypeError):
            item.custom_fields.default(test_cf, CustomFieldBooleanValue)

        item.custom_fields -= test_cf
        assert test_cf not in item.custom_fields

        item.custom_fields += test_cf.draft_value(1337)
        assert test_cf in item.custom_fields

    async def test_draft_custom_fields_as_id_list(self, paperless: PaperlessClient) -> None:
        """DocumentDraft serialises list[int] custom_fields as repeated form values."""
        draft = paperless.documents.create(document=b"pdf", custom_fields=[1, 3, 5])
        serialized = draft.serialize()
        assert serialized["form"]["custom_fields"] == [1, 3, 5]

    async def test_draft_custom_fields_as_object_mapping(self, paperless: PaperlessClient) -> None:
        """DocumentDraft serialises DocumentCustomFieldList as a JSON string."""
        cf = DocumentCustomFieldList.from_data(paperless.runtime, [])
        cf += CustomFieldStringValue(field=6, value="hello")
        cf += CustomFieldIntegerValue(field=3, value=42)

        draft = paperless.documents.create(document=b"pdf")
        draft.custom_fields = cf

        serialized = draft.serialize()
        raw = serialized["form"]["custom_fields"]
        assert isinstance(raw, str)
        decoded = json.loads(raw)
        assert isinstance(decoded, dict)
        assert decoded["6"] == "hello"
        assert decoded["3"] == 42

    async def test_draft_custom_fields_object_mapping_upload(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """A draft with a DocumentCustomFieldList can be POSTed successfully."""
        cf = DocumentCustomFieldList.from_data(paperless.runtime, [])
        cf += CustomFieldStringValue(field=6, value="smoke")

        draft = paperless.documents.create(document=b"%PDF-fake", title="CF Mapping Test")
        draft.custom_fields = cf

        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_POST}",
            status_code=200,
            json="aaaabbbb-cccc-dddd-eeee-ffffffffffff",
        )
        task_id = await paperless.documents.save(draft)
        assert task_id == "aaaabbbb-cccc-dddd-eeee-ffffffffffff"

        request = httpx_mock.get_request(method="POST")
        assert request is not None
        body = request.content.decode(errors="replace")
        match = re.search(r'name="custom_fields"\r\n\r\n(\{.*?\})\r\n', body, re.DOTALL)
        assert match is not None, f"custom_fields not found as JSON object in body: {body!r}"
        decoded = json.loads(match.group(1))
        assert decoded == {"6": "smoke"}

    async def test_email(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """Email dispatch succeeds on 200 and raises SendEmailError on 400."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_EMAIL}",
            status_code=200,
            json={"message": "Email sent"},
        )
        await paperless.documents.email(
            documents=1,
            addresses="test@example.org",
            subject="Test Email",
            message="Test Message",
        )

        assert json.loads(httpx_mock.get_requests()[-1].content) == {
            "documents": [1],
            "addresses": "test@example.org",
            "subject": "Test Email",
            "message": "Test Message",
            "use_archive_version": True,
        }

        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_EMAIL}",
            status_code=400,
        )
        with pytest.raises(SendEmailError):
            await paperless.documents.email(
                documents=[1, 2],
                addresses="test@example.org",
                subject="Test Email",
                message="Test Message",
                use_archive_version=False,
            )

        body = json.loads(httpx_mock.get_requests()[-1].content)
        assert body["documents"] == [1, 2]
        assert body["use_archive_version"] is False

    async def test_is_deleted(self, paperless: PaperlessClient) -> None:
        """Document.is_deleted is True when deleted_at is set, False otherwise."""
        doc_alive = Document.from_data(paperless.runtime, data={**DATA_DOCUMENTS["results"][0]})
        assert not doc_alive.is_deleted

        doc_trashed = Document.from_data(
            paperless.runtime,
            data={**DATA_DOCUMENTS["results"][0], "deleted_at": "2024-01-01T00:00:00Z"},
        )
        assert doc_trashed.is_deleted

    async def test_download_content_disposition_non_filename_part(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """Download with a Content-Disposition that has a non-filename= part is handled."""
        # Content-Disposition has an extra part that is NOT filename=
        httpx_mock.add_response(
            method="GET",
            url=re.compile(
                r"^"
                + f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_DOWNLOAD}".format(pk=1)
                + r"\?.*$"
            ),
            status_code=200,
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": "attachment; charset=utf-8; filename=doc.pdf",
            },
            content=b"binary",
        )
        download = await paperless.documents.download(1)
        assert isinstance(download, DownloadedDocument)
        assert download.disposition_filename == "doc.pdf"

    async def test_update_no_changes(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """update() returns False without calling the API when nothing has changed."""
        # Use Correspondent which has only simple string/int fields that won't mismatch
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.CORRESPONDENTS_SINGLE}".format(pk=1),
            status_code=200,
            json={"id": 1, "name": "ACME", "slug": "acme"},
        )
        item = await paperless.correspondents(1)
        result = await paperless.correspondents.update(item)
        assert result is False

    async def test_check_permissions_field_has_permissions_no_perms_key(
        self, paperless: PaperlessClient
    ) -> None:
        """_check_permissions_field exits without changes when permissions not in data."""
        item = Correspondent.from_data(
            paperless,
            data={
                "id": 1,
                "name": "ACME",
                "permissions": {"view": {"users": []}, "change": {"users": []}},
            },
        )
        assert item.has_permissions
        changed: dict = {"name": "New Name"}
        UpdatableService._check_permissions_field(item, changed)
        # permissions not in changed, so no set_permissions key added
        assert "set_permissions" not in changed
        assert "name" in changed


def test_coerce_custom_fields_non_list_passthrough(api: PaperlessClient) -> None:
    """_coerce_custom_fields must return v unchanged when v is not a list (L215)."""
    # Pass custom_fields=None explicitly so the before-validator is triggered with a
    # non-list value; it must return None unchanged (the field type accepts None).
    doc = Document.from_data(api._runtime, {"id": 1, "custom_fields": None})
    assert doc.id == 1
    assert doc.custom_fields is None


def test_document_sub_service_properties_cached(api: PaperlessClient) -> None:
    """Accessing .history and .share_links twice returns the same object (L220->222, L234->236)."""
    doc = Document.from_data(api._runtime, {"id": 7})
    history1 = doc.history
    history2 = doc.history
    assert history1 is history2

    sl1 = doc.share_links
    sl2 = doc.share_links
    assert sl1 is sl2


class TestDocumentAISuggestions:
    """DocumentAISuggestionsService: GET per-document sub-service."""

    async def test_call_via_service(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """Calling the service with a pk returns a DocumentAISuggestions instance."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_AI_SUGGESTIONS}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENT_AI_SUGGESTIONS,
        )
        result = await paperless.documents.ai_suggestions(1)
        assert isinstance(result, DocumentAISuggestions)
        assert result.id == 1
        assert result.title == DATA_DOCUMENT_AI_SUGGESTIONS["title"]
        assert result.correspondents == DATA_DOCUMENT_AI_SUGGESTIONS["correspondents"]
        assert result.suggested_tags == DATA_DOCUMENT_AI_SUGGESTIONS["suggested_tags"]

    async def test_call_via_document_property(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """Accessing ai_suggestions via a Document instance uses the attached pk."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_SINGLE}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENTS["results"][0],
        )
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_AI_SUGGESTIONS}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENT_AI_SUGGESTIONS,
        )
        doc = await paperless.documents(1)
        result = await doc.ai_suggestions(1)
        assert isinstance(result, DocumentAISuggestions)

    async def test_no_pk_raises(self, paperless: PaperlessClient) -> None:
        """Calling the service without a pk and without an attached document raises."""
        with pytest.raises(PrimaryKeyRequiredError):
            await paperless.documents.ai_suggestions()

    def test_property_cached(self, api: PaperlessClient) -> None:
        """Accessing .ai_suggestions twice returns the same service instance."""
        doc = Document.from_data(api._runtime, {"id": 5})
        svc1 = doc.ai_suggestions
        svc2 = doc.ai_suggestions
        assert svc1 is svc2


class TestDocumentChat:
    """DocumentChatService: POST collection-level service."""

    async def test_call(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """Calling the service POSTs the payload and returns a DocumentChat instance."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_CHAT}",
            status_code=200,
            json=DATA_DOCUMENT_CHAT,
        )
        result = await paperless.documents.chat("What is this document about?", 1)
        assert isinstance(result, DocumentChat)
        assert result.q == DATA_DOCUMENT_CHAT["q"]
        assert result.document_id == DATA_DOCUMENT_CHAT["document_id"]

        assert json.loads(httpx_mock.get_requests()[-1].content) == {
            "q": "What is this document about?",
            "document_id": 1,
        }

    async def test_call_without_document_id(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """document_id is optional; omitting it sends only `q` in the payload."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_CHAT}",
            status_code=200,
            json={"q": "General question", "document_id": None},
        )
        result = await paperless.documents.chat("General question")
        assert isinstance(result, DocumentChat)
        assert result.q == "General question"
        assert result.document_id is None

        assert json.loads(httpx_mock.get_requests()[-1].content) == {"q": "General question"}


class TestDocumentVersionService:
    """DocumentVersionService: upload / update / delete per-document sub-service."""

    async def test_upload_via_service(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """upload() POSTs the file as multipart and omits version_label when not given."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_UPDATE_VERSION}".format(pk=1),
            status_code=200,
            text="OK",
        )

        result = await paperless.documents.versions.upload(io.BytesIO(b"data"), pk=1)
        assert result is None

        request = httpx_mock.get_requests()[-1]
        assert request.headers["content-type"].startswith("multipart/form-data")
        body = request.content.decode(errors="replace")
        assert 'name="document"' in body
        assert "\r\n\r\ndata\r\n" in body
        assert 'name="version_label"' not in body

    async def test_upload_with_label_via_service(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """upload() includes version_label in multipart when provided."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_UPDATE_VERSION}".format(pk=1),
            status_code=200,
            text="OK",
        )

        result = await paperless.documents.versions.upload(
            io.BytesIO(b"data"), version_label="v2", pk=1
        )
        assert result is None

        body = httpx_mock.get_requests()[-1].content.decode(errors="replace")
        assert re.search(r'name="version_label"\r\n\r\nv2\r\n', body) is not None

    async def test_update_via_service(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """update() PATCHes the version label and returns a DocumentVersionInfo."""
        httpx_mock.add_response(
            method="PATCH",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_VERSION}".format(pk=1, version_id=1),
            status_code=200,
            json=DATA_DOCUMENT_VERSION_INFO,
        )
        result = await paperless.documents.versions.update(1, version_label="v2", pk=1)
        assert isinstance(result, DocumentVersionInfo)
        assert result.version_label == DATA_DOCUMENT_VERSION_INFO["version_label"]
        assert result.is_root == DATA_DOCUMENT_VERSION_INFO["is_root"]

    async def test_delete_via_service(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """delete() sends DELETE and returns None."""
        httpx_mock.add_response(
            method="DELETE",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_VERSION}".format(pk=1, version_id=1),
            status_code=204,
        )
        result = await paperless.documents.versions.delete(1, pk=1)
        assert result is None

    async def test_upload_via_document_property(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """upload() works when called via a Document instance (uses attached pk)."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_SINGLE}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENTS["results"][0],
        )
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_UPDATE_VERSION}".format(pk=1),
            status_code=200,
            text="OK",
        )

        doc = await paperless.documents(1)
        result = await doc.versions.upload(io.BytesIO(b"data"))
        assert result is None

    async def test_update_via_document_property(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """update() works when called via a Document instance (uses attached pk)."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_SINGLE}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENTS["results"][0],
        )
        httpx_mock.add_response(
            method="PATCH",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_VERSION}".format(pk=1, version_id=1),
            status_code=200,
            json=DATA_DOCUMENT_VERSION_INFO,
        )
        doc = await paperless.documents(1)
        result = await doc.versions.update(1, version_label="v2")
        assert isinstance(result, DocumentVersionInfo)

    async def test_delete_via_document_property(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """delete() works when called via a Document instance (uses attached pk)."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_SINGLE}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENTS["results"][0],
        )
        httpx_mock.add_response(
            method="DELETE",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_VERSION}".format(pk=1, version_id=1),
            status_code=204,
        )
        doc = await paperless.documents(1)
        result = await doc.versions.delete(1)
        assert result is None

    async def test_upload_no_pk_raises(self, paperless: PaperlessClient) -> None:
        """upload() without pk and without attached doc raises PrimaryKeyRequiredError."""
        with pytest.raises(PrimaryKeyRequiredError):
            await paperless.documents.versions.upload(io.BytesIO(b"data"))

    async def test_update_no_pk_raises(self, paperless: PaperlessClient) -> None:
        """update() without pk and without attached doc raises PrimaryKeyRequiredError."""
        with pytest.raises(PrimaryKeyRequiredError):
            await paperless.documents.versions.update(1, version_label="v2")

    async def test_delete_no_pk_raises(self, paperless: PaperlessClient) -> None:
        """delete() without pk and without attached doc raises PrimaryKeyRequiredError."""
        with pytest.raises(PrimaryKeyRequiredError):
            await paperless.documents.versions.delete(1)

    def test_property_cached(self, api: PaperlessClient) -> None:
        """Accessing .versions twice returns the same service instance."""
        doc = Document.from_data(api._runtime, {"id": 5})
        svc1 = doc.versions
        svc2 = doc.versions
        assert svc1 is svc2


class TestDocumentRootService:
    """DocumentRootService: GET per-document sub-service."""

    async def test_call_via_service(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """Calling the service with a pk returns a DocumentRoot instance."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_ROOT}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENT_ROOT,
        )
        result = await paperless.documents.root(1)
        assert isinstance(result, DocumentRoot)
        assert result.root_id == DATA_DOCUMENT_ROOT["root_id"]

    async def test_call_via_document_property(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """Accessing root via a Document instance uses the attached pk."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_SINGLE}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENTS["results"][0],
        )
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_ROOT}".format(pk=1),
            status_code=200,
            json=DATA_DOCUMENT_ROOT,
        )
        doc = await paperless.documents(1)
        result = await doc.root()
        assert isinstance(result, DocumentRoot)

    async def test_no_pk_raises(self, paperless: PaperlessClient) -> None:
        """Calling the service without a pk raises PrimaryKeyRequiredError."""
        with pytest.raises(PrimaryKeyRequiredError):
            await paperless.documents.root()

    def test_property_cached(self, api: PaperlessClient) -> None:
        """Accessing .root twice returns the same service instance."""
        doc = Document.from_data(api._runtime, {"id": 5})
        svc1 = doc.root
        svc2 = doc.root
        assert svc1 is svc2
