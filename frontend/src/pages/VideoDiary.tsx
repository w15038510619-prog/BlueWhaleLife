import React, { useState, useEffect } from 'react';
import { VideoAnalysis } from '../types';
import { api } from '../api/client';
import { BookOpen, ExternalLink, Copy, Check, MessageSquare, HelpCircle, Lightbulb, Clock, User, Edit3 } from 'lucide-react';

interface VideoDiaryProps {
  initialBvid?: string;
}

export const VideoDiary: React.FC<VideoDiaryProps> = ({ initialBvid }) => {
  const [videos, setVideos] = useState<VideoAnalysis[]>([]);
  const [selectedVideo, setSelectedVideo] = useState<VideoAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [editingDraft, setEditingDraft] = useState('');
  const [editingStatus, setEditingStatus] = useState<any>('draft');
  const [editingNotes, setEditingNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

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
    setCopied(false);
    setSaveSuccess(false);
  };

  const handleCopyDraft = () => {
    if (!editingDraft) return;
    navigator.clipboard.writeText(editingDraft);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);

    // Update status to 'copied' automatically if still in draft
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
        editingNotes
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

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">观影日记 📖</h2>
          <p className="page-desc">
            记录大肥鱼看过的每个视频：学到了什么、独立观点、存疑与评论草稿（由主人审核确认，手动发布）
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
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)' }}>
                      <span>{v.author}</span>
                      <span>{v.watched_at ? v.watched_at.split(' ')[0] : ''}</span>
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
                  <h3 style={{ fontSize: '20px', fontWeight: 'bold', color: '#0f172a', marginBottom: '8px' }}>
                    {selectedVideo.title}
                  </h3>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '13px', color: 'var(--text-muted)' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <User size={14} /> UP主：{selectedVideo.author}
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={14} /> 观看时间：{selectedVideo.watched_at}
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
                  <HelpCircle size={18} /> 存疑与延伸思考
                </div>
                <p style={{ fontSize: '14px', color: '#334155', lineHeight: '1.6' }}>
                  {selectedVideo.doubts}
                </p>
              </div>
            </div>

            {/* Comment Draft Section (Safe Human-in-the-loop manual review) */}
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Edit3 size={18} color="#2563eb" />
                  <h4 style={{ fontSize: '16px', fontWeight: 'bold' }}>评论交流草稿</h4>
                  <span className={`badge ${selectedVideo.worth_commenting ? 'badge-green' : 'badge-amber'}`}>
                    {selectedVideo.worth_commenting ? '推荐参与交流' : '暂不建议评论'}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <select
                    className="select"
                    style={{ width: '130px', padding: '6px 10px', fontSize: '13px' }}
                    value={editingStatus}
                    onChange={e => setEditingStatus(e.target.value)}
                  >
                    <option value="draft">草稿待审</option>
                    <option value="approved">主人已批准</option>
                    <option value="copied">已复制草稿</option>
                    <option value="rejected">放弃交流</option>
                  </select>

                  <button className="btn btn-primary" onClick={handleCopyDraft}>
                    {copied ? <Check size={16} /> : <Copy size={16} />}
                    {copied ? '已复制到剪贴板！' : '一键复制草稿'}
                  </button>
                </div>
              </div>

              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                【安全机制】：大肥鱼绝不会未经确认自动发布评论。请在此审核/微调，复制后到B站页面由您手动发送。
              </div>

              <textarea
                className="textarea"
                style={{ fontSize: '14px', lineHeight: '1.6', minHeight: '100px', marginBottom: '12px' }}
                value={editingDraft}
                onChange={e => setEditingDraft(e.target.value)}
                placeholder="评论草稿内容..."
              />

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

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '14px' }}>
                {saveSuccess && (
                  <span style={{ color: '#059669', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Check size={15} /> 已保存修改
                  </span>
                )}
                <button className="btn btn-secondary" onClick={() => handleSave()} disabled={saving}>
                  {saving ? '保存中...' : '保存草稿与批注'}
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
