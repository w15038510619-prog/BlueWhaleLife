import os
import pytest
from datetime import datetime, timedelta

from backend.app.config import protect_secret, unprotect_secret, current_settings
from backend.app.services.publisher import (
    CommentDecisionEngine,
    CommentPublishRequest,
    OfficialApiPublisher,
    PendingApprovalPublisher,
    LocalAuditPublisher
)
from backend.app.services.scheduler import AutonomousScheduler
from backend.app.services.bilibili_source import BilibiliSource


def test_secret_protection():
    raw_key = "sk-test-secret-key-1234567890"
    protected = protect_secret(raw_key)
    assert protected.startswith("enc:")
    assert protected != raw_key

    recovered = unprotect_secret(protected)
    assert recovered == raw_key


def test_comment_decision_engine_rules():
    # 1. Very short generic comment -> should be rejected
    worth, reason = CommentDecisionEngine.evaluate_decision(
        bvid="BV1test1",
        comment_draft="好厉害！",
        viewpoint="不错",
        learned="新知识",
        comprehension_tier="metadata_only",
        is_partial=True
    )
    assert worth is False
    assert "过于简短" in reason or "套话" in reason

    # 2. Honest and insightful comment with understanding -> should pass
    worth2, reason2 = CommentDecisionEngine.evaluate_decision(
        bvid="BV1test2",
        comment_draft="视频对端侧大模型量化损耗的分析非常切中要害，特别是第3点的注意力蒸馏对比很有启发！",
        viewpoint="端侧量化需要平衡显存与精度",
        learned="注意力蒸馏技术细节",
        comprehension_tier="subtitles",
        is_partial=False
    )
    assert worth2 is True
    assert "值得真诚交流" in reason2


@pytest.mark.anyio
async def test_official_publisher_scope_downgrade():
    # When no official token is provided, OfficialApiPublisher must gracefully return needs_scope
    current_settings.bilibili_access_token = ""
    pub = OfficialApiPublisher()
    req = CommentPublishRequest(
        bvid="BV1test3",
        comment_text="测试评论内容具有深度探讨价值",
        viewpoint="独特观点",
        comprehension_tier="metadata_only",
        is_partial=True
    )
    res = await pub.publish(req)
    assert res.success is False
    assert res.status == "needs_scope"
    assert "bilibili.openapi" in res.missing_scope


def test_scheduler_quiet_hours_and_budget():
    # Test quiet hours logic
    current_settings.quiet_hours_start = 23
    current_settings.quiet_hours_end = 7
    assert AutonomousScheduler._is_quiet_hours(23) is True
    assert AutonomousScheduler._is_quiet_hours(0) is True
    assert AutonomousScheduler._is_quiet_hours(4) is True
    assert AutonomousScheduler._is_quiet_hours(14) is False
    assert AutonomousScheduler._is_quiet_hours(18) is False
