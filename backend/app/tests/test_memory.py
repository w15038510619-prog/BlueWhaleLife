import pytest
from backend.app.database import init_db
from backend.app.models.video import VideoAnalysis, UpdateDraftRequest
from backend.app.models.memory import KnowledgeNoteCreate, KnowledgeNoteUpdate
from backend.app.services.memory import MemoryService


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_memory_record_and_retrieve():
    test_video = VideoAnalysis(
        bvid="BV1_TEST_001",
        title="测试视频：深海仿生学",
        author="测试UP",
        cover="http://example.com/cover.jpg",
        description="测试描述",
        tags=["深海", "仿生学"],
        watched_at="2026-10-22 10:00:00",
        choice_reason="测试理由",
        summary="测试概述",
        learned="学到了仿生皮肤流体减阻",
        viewpoint="我认为这项技术潜力很大",
        doubts="耐久性如何？",
        worth_commenting=True,
        comment_draft="非常有启发！",
        draft_status="draft"
    )
    MemoryService.record_watch(test_video)

    retrieved = MemoryService.get_watch_by_bvid("BV1_TEST_001")
    assert retrieved is not None
    assert retrieved.title == "测试视频：深海仿生学"
    assert retrieved.worth_commenting is True

    # Test draft update
    updated = MemoryService.update_draft("BV1_TEST_001", UpdateDraftRequest(
        draft_status="copied",
        user_notes="已手动复制并准备发布"
    ))
    assert updated.draft_status == "copied"
    assert updated.user_notes == "已手动复制并准备发布"


def test_knowledge_notes_crud_and_deduplication():
    note = MemoryService.add_knowledge_note(KnowledgeNoteCreate(
        topic="流体力学测试",
        content="表面微结构能够显著降低水阻",
        source_bvid="BV1_TEST_001",
        importance=4
    ))
    assert note.id is not None
    assert note.topic == "流体力学测试"

    # Search
    search_res = MemoryService.search_memories("流体")
    assert len(search_res.notes) >= 1

    # Forget (soft delete)
    success = MemoryService.forget_knowledge_note(note.id)
    assert success is True

    active_notes = MemoryService.get_knowledge_notes(active_only=True)
    assert not any(n.id == note.id for n in active_notes)
