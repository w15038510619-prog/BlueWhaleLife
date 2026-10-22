import React, { useState, useEffect } from 'react';
import { VideoAnalysis } from '../types';
import { api } from '../api/client';
import {
  BookOpen,
  ExternalLink,
  Copy,
  Check,
  MessageSquare,
  HelpCircle,
  Lightbulb,
  Clock,
  User,
  Edit3,
  Send,
  ShieldCheck,
  AlertTriangle,
  FileText,
  Layers
} from 'lucide-react';

interface VideoDiaryProps {
  initialBvid?: string;
}

export const VideoDiary: React.FC<VideoDiaryProps> = ({ initialBvid }) => {
  const [videos, setVideos] = useState<VideoAnalysis[]>([]);
  const [selectedVideo, setSelectedVideo] = useState<VideoAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [editingDraft, setEditingDraft] = useState('');
  const [editingStatus, setEditingStatus] = useState<string>('draft');
  const [editingNotes, setEditingNotes] = useState('');
  const [editingPublisher, setEditingPublisher] = useState<string>('pending_approval');
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [publishMessage, setPublishMessage] = useState<{ type: 'success' | 'warn' | 'error'; text: string } | null>(null);

  useEffect(() => {
    loadVideos();
  }, []);

  const loadVideos = async () => {
    setLoading(true);
    try {
      const list = await api.getVideos();
      setVideos(list);
      if (list.length > 0) {
        if (initialBvid) {
          const matched = list.find(v => v.bvid === initialBvid);
          selectVideo(matched || list[0]);
        } else {
          selectVideo(list[0]);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const selectVideo = (v: VideoAnalysis) => {
    setSelectedVideo(v);
    setEditingDraft(v.comment_draft);
    setEditingStatus(v.draft_status);
    setEditingNotes(v.user_notes || '');
    setEditingPublisher(v.publisher_type || 'pending_approval');
    setCopied(false);
    setSaveSuccess(false);
    setPublishMessage(null);
  };

  const handleCopyDraft = () => {
    if (!editingDraft) return;
    navigator.clipboard.writeText(editingDraft);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);

    if (editingStatus === 'draft') {
      setEditingStatus('copied');
      handleSave('copied');
    }
  };

  const handleSave = async (overrideStatus?: string) => {
    if (!selectedVideo) return;
    setSaving(true);
    try {
      const statusToSave = overrideStatus || editingStatus;
      const updated = await api.updateDraft(
        selectedVideo.bvid,
        statusToSave,
        editingDraft,
        editingNotes,
        editingPublisher
      );
      setSelectedVideo(updated);
      setVideos(prev => prev.map(v => v.bvid === updated.bvid ? updated : v));
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2500);
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async () => {
    if (!selectedVideo) return;
    setPublishing(true);
    setPublishMessage(null);
    try {
      const res = await api.publishComment(selectedVideo.bvid);
      if (res.status === 'published') {
        setPublishMessage({
          type: 'success',
          text: `发布成功！平台评论编号: ${res.platform_comment_id || '已确认'}`
        });
      } else if (res.status === 'needs_scope') {
        setPublishMessage({
          type: 'warn',
          text: `缺少官方开放平台写权限 (${res.missing_scope || 'scope'})，已安全转入待审队列。可点击“一键复制草稿”在B站手动发表。`
        });
      } else {
        setPublishMessage({
          type: 'error',
          text: res.reason || '发布未成功，已归档'
        });
      }
      // Refresh video details
      const refreshed = await api.getVideo(selectedVideo.bvid);
      if (refreshed) {
        setSelectedVideo(refreshed);
        setVideos(prev => prev.map(v => v.bvid === refreshed.bvid ? refreshed : v));
      }
    } catch (e: any) {
      setPublishMessage({
        type: 'error',
        text: `发布请求异常: ${e.message || e}`
      });
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">观影日记与深度交流 📖</h2>
          <p className="page-desc">
            记录大肥鱼看过的每个视频：分级理解度、证据锚点、独立观点、自主评论决策与发布通道。
          </p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '24px' }}>
        {/* Left Sidebar: Video List */}
        <div className="card" style={{ padding: '16px', maxHeight: 'calc(100vh - 180px)', overflowY: 'auto' }}>
          <h3 style={{ fontSize: '15px', fontWeight: 'bold', marginBottom: '12px', color: '#1e293b' }}>
            已记录作品 ({videos.length})
          </h3>
          {videos.length === 0 ? (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '30px 0', fontSize: '13px' }}>
              暂无观影记录<br />让小肥鱼先去“今天的发现”看个视频吧！
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {videos.map(v => {
                const isSelected = selectedVideo?.bvid === v.bvid;
                return (
                  <div
                    key={v.bvid}
                    onClick={() => selectVideo(v)}
                    style={{
                      padding: '12px',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      border: isSelected ? '1px solid #bfdbfe' : '1px solid transparent',
                      background: isSelected ? '#eff6ff' : '#f8fafc',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <div style={{ fontSize: '13px', fontWeight: isSelected ? '700' : '500', color: isSelected ? '#1e40af' : '#1e293b', marginBottom: '4px', lineHeight: '1.4' }}>
                      {v.title}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                      <span>{v.author}</span>
                      <span className={`badge ${v.comprehension_tier === 'subtitles' ? 'badge-green' : 'badge-amber'}`} style={{ fontSize: '10px', padding: '1px 6px' }}>
                        {v.comprehension_tier === 'subtitles' ? '字幕全片' : '简介部分'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Content: Selected Video Detail */}
        {selectedVideo ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Header Card */}
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                    <span className={`badge ${selectedVideo.comprehension_tier === 'subtitles' ? 'badge-green' : 'badge-amber'}`}>
                      {selectedVideo.comprehension_tier === 'subtitles' ? '📜 全片字幕深度研读' : '🔍 公开简介部分理解'}
                    </span>
                    {selectedVideo.is_partial && (
                      <span className="badge badge-amber" style={{ fontSize: '11px' }}>
                        真实声明：未获取完整音视频画面
                      </span>
                    )}
                  </div>

                  <h3 style={{ fontSize: '20px', fontWeight: 'bold', color: '#0f172a', marginBottom: '8px' }}>
                    {selectedVideo.title}
                  </h3>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '13px', color: 'var(--text-muted)' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <User size={14} /> UP主：{selectedVideo.author}
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={14} /> 记录时间：{selectedVideo.watched_at}
                    </span>
                    <span>BV号：{selectedVideo.bvid}</span>
                  </div>
                </div>

                <a
                  href={`https://www.bilibili.com/video/${selectedVideo.bvid}`}
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn-secondary"
                  style={{ textDecoration: 'none', whiteSpace: 'nowrap' }}
                >
                  <ExternalLink size={16} /> 在B站打开原视频
                </a>
              </div>

              {selectedVideo.choice_reason && (
                <div style={{
                  marginTop: '14px',
                  background: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  padding: '8px 12px',
                  fontSize: '13px',
                  color: '#475569'
                }}>
                  <b>选择初衷：</b> {selectedVideo.choice_reason}
                </div>
              )}
            </div>

            {/* Analysis Grid */}
            <div className="grid-2">
              {/* Summary */}
              <div className="card" style={{ margin: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', color: '#2563eb', fontWeight: 'bold', fontSize: '15px' }}>
                  <BookOpen size={18} /> 内容概述
                </div>
                <p style={{ fontSize: '14px', color: '#334155', lineHeight: '1.6' }}>
                  {selectedVideo.summary}
                </p>
              </div>

              {/* What learned */}
              <div className="card" style={{ margin: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', color: '#059669', fontWeight: 'bold', fontSize: '15px' }}>
                  <Lightbulb size={18} /> 学到了什么
                </div>
                <p style={{ fontSize: '14px', color: '#334155', lineHeight: '1.6' }}>
                  {selectedVideo.learned}
                </p>
              </div>

              {/* Viewpoint */}
              <div className="card" style={{ margin: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', color: '#7c3aed', fontWeight: 'bold', fontSize: '15px' }}>
                  <MessageSquare size={18} /> 大肥鱼的独立观点
                </div>
                <p style={{ fontSize: '14px', color: '#334155', lineHeight: '1.6' }}>
                  {selectedVideo.viewpoint}
                </p>
              </div>

              {/* Doubts */}
              <div className="card" style={{ margin: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', color: '#d97706', fontWeight: 'bold', fontSize: '15px' }}>
                  <HelpCircle size={18} /> 存疑与考证
                </div>
                <p style={{ fontSize: '14px', color: '#334155', lineHeight: '1.6' }}>
                  {selectedVideo.doubts}
                </p>
              </div>
            </div>

            {/* Evidence Anchors Box (when available) */}
            {selectedVideo.evidence_map && Object.keys(selectedVideo.evidence_map).length > 0 && (
              <div className="card" style={{ background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', fontSize: '14px', fontWeight: 'bold', color: '#334155' }}>
                  <Layers size={16} /> 论据与信息来源锚点（真实可追溯）
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {Object.entries(selectedVideo.evidence_map).map(([k, v]) => (
                    Array.isArray(v) && v.map((item, idx) => (
                      <span key={`${k}-${idx}`} style={{ fontSize: '12px', background: '#ffffff', border: '1px solid #cbd5e1', padding: '3px 8px', borderRadius: '4px', color: '#475569' }}>
                        📌 {item}
                      </span>
                    ))
                  ))}
                </div>
              </div>
            )}

            {/* Autonomous Comment Decision & Publisher Section */}
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Edit3 size={18} color="#2563eb" />
                  <h4 style={{ fontSize: '16px', fontWeight: 'bold' }}>评论交流与自主发布通道</h4>
                  <span className={`badge ${selectedVideo.worth_commenting ? 'badge-green' : 'badge-amber'}`}>
                    {selectedVideo.worth_commenting ? '决策：值得交流' : '决策：不参与评论'}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <select
                    className="select"
                    style={{ width: '130px', padding: '6px 10px', fontSize: '13px' }}
                    value={editingStatus}
                    onChange={e => setEditingStatus(e.target.value)}
                  >
                    <option value="draft">草稿</option>
                    <option value="pending_approval">待主人批准</option>
                    <option value="approved">已批准</option>
                    <option value="published">已发布</option>
                    <option value="declined">放弃交流</option>
                  </select>

                  <button className="btn btn-secondary" onClick={handleCopyDraft} title="复制草稿到剪贴板">
                    {copied ? <Check size={16} /> : <Copy size={16} />}
                    {copied ? '已复制！' : '复制草稿'}
                  </button>

                  <button
                    className="btn btn-primary"
                    onClick={handlePublish}
                    disabled={publishing || !editingDraft}
                  >
                    <Send size={16} />
                    {publishing ? '发布中...' : '提交发布'}
                  </button>
                </div>
              </div>

              {/* Autonomous Decision Explanation */}
              {selectedVideo.comment_decision_reason && (
                <div style={{
                  background: '#f0fdf4',
                  border: '1px solid #bbf7d0',
                  borderRadius: '6px',
                  padding: '8px 12px',
                  fontSize: '13px',
                  color: '#166534',
                  marginBottom: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}>
                  <ShieldCheck size={16} />
                  <span><b>大肥鱼决策理由：</b> {selectedVideo.comment_decision_reason}</span>
                </div>
              )}

              {/* Publish Result Banner */}
              {publishMessage && (
                <div style={{
                  marginBottom: '12px',
                  padding: '10px 14px',
                  borderRadius: '6px',
                  fontSize: '13px',
                  background: publishMessage.type === 'success' ? '#dcfce7' : publishMessage.type === 'warn' ? '#fef3c7' : '#fee2e2',
                  color: publishMessage.type === 'success' ? '#15803d' : publishMessage.type === 'warn' ? '#b45309' : '#b91c1c',
                  border: `1px solid ${publishMessage.type === 'success' ? '#86efac' : publishMessage.type === 'warn' ? '#fcd34d' : '#fca5a5'}`
                }}>
                  {publishMessage.text}
                </div>
              )}

              <textarea
                className="textarea"
                style={{ fontSize: '14px', lineHeight: '1.6', minHeight: '100px', marginBottom: '12px' }}
                value={editingDraft}
                onChange={e => setEditingDraft(e.target.value)}
                placeholder="评论草稿内容..."
              />

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div>
                  <label style={{ fontSize: '13px', fontWeight: '600', color: '#475569', display: 'block', marginBottom: '4px' }}>
                    发布通道设定：
                  </label>
                  <select
                    className="select"
                    value={editingPublisher}
                    onChange={e => setEditingPublisher(e.target.value)}
                    style={{ width: '100%' }}
                  >
                    <option value="pending_approval">主人确认队列 (优雅降级/安全待审)</option>
                    <option value="official_api">B站官方开放平台 API (需要 OAuth2 写权限)</option>
                    <option value="webhook">外部 Webhook 通道 (推送通知与自动化脚本)</option>
                    <option value="local_audit">本地合规审计模式 (仅落库不外发)</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '13px', fontWeight: '600', color: '#475569', display: 'block', marginBottom: '4px' }}>
                    主人批注与备忘：
                  </label>
                  <input
                    type="text"
                    className="input"
                    placeholder="记录您对该评论或视频的个人想法..."
                    value={editingNotes}
                    onChange={e => setEditingNotes(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '14px' }}>
                {saveSuccess && (
                  <span style={{ color: '#059669', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Check size={15} /> 已保存修改
                  </span>
                )}
                <button className="btn btn-secondary" onClick={() => handleSave()} disabled={saving}>
                  {saving ? '保存中...' : '保存修改与通道'}
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '300px', color: 'var(--text-muted)' }}>
            请在左侧选择一部观影日记查看详情
          </div>
        )}
      </div>
    </div>
  );
};
