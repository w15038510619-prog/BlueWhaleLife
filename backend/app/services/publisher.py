from __future__ import annotations
import abc
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import httpx
from pydantic import BaseModel, Field

from backend.app.config import current_settings
from backend.app.database import get_db_connection


class CommentPublishRequest(BaseModel):
    bvid: str
    comment_text: str
    viewpoint: str = ""
    learned: str = ""
    comprehension_tier: str = "metadata_only"
    is_partial: bool = False


class CommentPublishResult(BaseModel):
    success: bool
    status: str  # 'published' | 'pending_approval' | 'declined' | 'failed' | 'needs_scope'
    publisher_type: str
    platform_comment_id: str = ""
    reason: str = ""
    missing_scope: str = ""
    published_content: str = ""


class BasePublisher(abc.ABC):
    @abc.abstractmethod
    async def publish(self, req: CommentPublishRequest) -> CommentPublishResult:
        pass


class OfficialApiPublisher(BasePublisher):
    """
    Official Bilibili Open Platform API Publisher.
    Respects OAuth2 token scopes, appends mandatory AI transparency disclosure,
    and gracefully falls back to PendingApprovalPublisher if write scope is missing.
    """

    AI_DISCLOSURE = "\n\n（本评论由开源 AI 桌宠【大肥鱼】自主阅读后生成）"

    async def publish(self, req: CommentPublishRequest) -> CommentPublishResult:
        token = current_settings.bilibili_access_token.strip()

        # Check official OAuth2 write scope
        if not token:
            return CommentPublishResult(
                success=False,
                status="needs_scope",
                publisher_type="official_api",
                reason="未配置 B站开放平台官方授权令牌 (Access Token)，已安全转入主人待审队列",
                missing_scope="bilibili.openapi.comment.write / video_reply",
                published_content=req.comment_text
            )

        full_content = req.comment_text.strip() + self.AI_DISCLOSURE

        # Call official Open Platform comment API endpoint
        url = "https://api.bilibili.com/x/v2/reply/add"
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0 BlueWhaleLife-OpenBot/2.0 (Windows NT 10.0)",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(
                    url,
                    headers=headers,
                    data={
                        "bvid": req.bvid,
                        "type": 1,
                        "message": full_content
                    }
                )
                data = res.json()
                code = data.get("code", -1)
                if code == 0:
                    r_id = str(data.get("data", {}).get("rpid", ""))
                    return CommentPublishResult(
                        success=True,
                        status="published",
                        publisher_type="official_api",
                        platform_comment_id=r_id,
                        reason="已成功通过官方开放平台通道发布评论",
                        published_content=full_content
                    )
                elif code in [-101, -403, 12002, 12003]:
                    # Missing write scope or token expired
                    return CommentPublishResult(
                        success=False,
                        status="needs_scope",
                        publisher_type="official_api",
                        reason=f"B站开放平台拒绝写入 (Code {code}): {data.get('message', '缺少写权限')}",
                        missing_scope="bilibili.openapi.comment.write",
                        published_content=full_content
                    )
                else:
                    return CommentPublishResult(
                        success=False,
                        status="failed",
                        publisher_type="official_api",
                        reason=f"平台接口返回错误: {data.get('message', '未知错误')}",
                        published_content=full_content
                    )
        except Exception as e:
            return CommentPublishResult(
                success=False,
                status="failed",
                publisher_type="official_api",
                reason=f"网络请求失败: {str(e)}",
                published_content=full_content
            )


class PendingApprovalPublisher(BasePublisher):
    """
    Compliant Pending Approval Publisher:
    Safely routes comment drafts into the dashboard queue for owner inspection and 1-click publishing.
    """

    async def publish(self, req: CommentPublishRequest) -> CommentPublishResult:
        return CommentPublishResult(
            success=True,
            status="pending_approval",
            publisher_type="pending_approval",
            reason="已加入主人待审队列，待主人确认后即可复制或一键批准",
            published_content=req.comment_text
        )


class WebhookPublisher(BasePublisher):
    """
    Webhook Publisher:
    Sends formatted comment draft to a user-configured Webhook endpoint (Feishu, DingTalk, Discord, local script).
    """

    async def publish(self, req: CommentPublishRequest) -> CommentPublishResult:
        webhook_url = current_settings.webhook_url.strip()
        if not webhook_url:
            return CommentPublishResult(
                success=False,
                status="failed",
                publisher_type="webhook",
                reason="未配置 Webhook URL，无法推送评论",
                published_content=req.comment_text
            )

        payload = {
            "source": "BlueWhaleLife",
            "event": "comment_candidate",
            "bvid": req.bvid,
            "comment": req.comment_text,
            "viewpoint": req.viewpoint,
            "is_partial": req.is_partial,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.post(webhook_url, json=payload)
                if res.status_code in [200, 204]:
                    return CommentPublishResult(
                        success=True,
                        status="published",
                        publisher_type="webhook",
                        reason="已成功推送到主人配置的 Webhook 服务",
                        published_content=req.comment_text
                    )
                else:
                    return CommentPublishResult(
                        success=False,
                        status="failed",
                        publisher_type="webhook",
                        reason=f"Webhook 响应异常状态码: {res.status_code}",
                        published_content=req.comment_text
                    )
        except Exception as e:
            return CommentPublishResult(
                success=False,
                status="failed",
                publisher_type="webhook",
                reason=f"Webhook 连接失败: {str(e)}",
                published_content=req.comment_text
            )


class LocalAuditPublisher(BasePublisher):
    """
    Strict Local Audit Publisher:
    Records comment and evaluation data exclusively to the local database without external network writes.
    """

    async def publish(self, req: CommentPublishRequest) -> CommentPublishResult:
        return CommentPublishResult(
            success=True,
            status="pending_approval",
            publisher_type="local_audit",
            reason="本地合规审计模式：已安全归档至本地审计日志，不向外部网络发起写请求",
            published_content=req.comment_text
        )


class CommentDecisionEngine:
    """
    Autonomous Comment Decision & Safety Audit Engine.
    Ensures comments are only posted when truly warranted, non-repetitive, respectful, and safe.
    """

    @classmethod
    def evaluate_decision(
        cls,
        bvid: str,
        comment_draft: str,
        viewpoint: str,
        learned: str,
        comprehension_tier: str,
        is_partial: bool
    ) -> Tuple[bool, str]:
        """
        Determines whether the fish should participate in comments.
        Returns: (worth_commenting, decision_reason)
        """
        # 1. Emergency Stop Check
        if current_settings.emergency_stop:
            return False, "主人的紧急停止开关已开启，所有评论决策立即冻结。"

        # 2. Minimum text quality check
        clean_draft = comment_draft.strip()
        if not clean_draft or len(clean_draft) < 12:
            return False, "思考草稿过于简短，缺乏具体观点，不值得为了发评论而发表敷衍内容。"

        # 3. Cliché and generic filler rejection
        cliches = ["好厉害", "点赞支持", "太强了", "学到了学到了", "催更", "第一第一", "支持支持", "留名"]
        if clean_draft in cliches or any(c == clean_draft for c in cliches):
            return False, "草稿属于套话模式，大肥鱼拒绝发布没有独立观点的机械回复。"

        # 4. Comprehension tier check
        if is_partial and comprehension_tier == "metadata_only":
            # If only metadata was available, evaluate if the comment is speculative
            if "看完了" in clean_draft or "视频里演到" in clean_draft:
                return False, "未能获取到完整字幕，不能在评论中谎称已完整观看视频细节。"

        # 5. Rate limit and budget protection
        now = datetime.now()
        one_hour_ago = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        today_str = now.strftime("%Y-%m-%d")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Hourly limit
            cursor.execute("""
                SELECT COUNT(*) FROM comment_publications
                WHERE published_at > ? AND status = 'published'
            """, (one_hour_ago,))
            hourly_count = cursor.fetchone()[0]
            if hourly_count >= current_settings.max_comments_per_hour:
                return False, f"最近1小时已发布过评论（已达每小时 {current_settings.max_comments_per_hour} 条上限），静心倾听不刷屏。"

            # Daily limit
            cursor.execute("""
                SELECT COUNT(*) FROM comment_publications
                WHERE published_at LIKE ? AND status = 'published'
            """, (f"{today_str}%",))
            daily_count = cursor.fetchone()[0]
            if daily_count >= current_settings.max_comments_per_day:
                return False, f"今日交流次数已达上限（每日 {current_settings.max_comments_per_day} 条），大肥鱼进入休息与知识沉淀状态。"

            # Repetition check against past comments
            cursor.execute("SELECT comment_draft FROM watch_history WHERE worth_commenting = 1 LIMIT 30")
            past_drafts = [r["comment_draft"] for r in cursor.fetchall() if r["comment_draft"]]
            for past in past_drafts:
                if past.strip() and past.strip() == clean_draft:
                    return False, "与之前的某条历史评论完全雷同，拒绝复读机行为。"

        # If all checks pass
        return True, "理解充分、具备独特观点，且能与创作者形成良性探讨，值得真诚交流。"

    @classmethod
    async def dispatch_publisher(cls, req: CommentPublishRequest) -> CommentPublishResult:
        """
        Dispatches comment publication according to active settings and logs audit trail.
        """
        pub_type = current_settings.publisher_type

        publisher: BasePublisher
        if pub_type == "official_api":
            publisher = OfficialApiPublisher()
        elif pub_type == "webhook":
            publisher = WebhookPublisher()
        elif pub_type == "local_audit":
            publisher = LocalAuditPublisher()
        else:
            publisher = PendingApprovalPublisher()

        # Execute publication attempt
        result = await publisher.publish(req)

        # If official API lacked scope, gracefully downgrade to PendingApproval
        if result.status == "needs_scope":
            fallback = PendingApprovalPublisher()
            await fallback.publish(req)

        # Log audit trail to comment_publications table
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO comment_publications (
                    bvid, comment_content, publisher_type, status,
                    platform_comment_id, created_at, published_at,
                    ai_disclaimer_included, audit_passed, audit_details, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                req.bvid,
                result.published_content or req.comment_text,
                pub_type,
                result.status,
                result.platform_comment_id,
                now_str,
                now_str if result.status == "published" else "",
                1,
                1 if result.success else 0,
                result.reason,
                result.missing_scope or result.reason
            ))

            # Update watch_history record
            cursor.execute("""
                UPDATE watch_history SET
                    publisher_type = ?,
                    draft_status = ?,
                    published_at = ?,
                    published_comment_id = ?,
                    publish_error = ?
                WHERE bvid = ?
            """, (
                pub_type,
                result.status,
                now_str if result.status == "published" else "",
                result.platform_comment_id,
                result.missing_scope if result.status == "needs_scope" else "",
                req.bvid
            ))

        return result
