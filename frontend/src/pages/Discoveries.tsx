import React, { useState, useEffect } from 'react';
import { VideoCandidate, VideoAnalysis } from '../types';
import { api } from '../api/client';
import { Compass, Eye, Sparkles, Clock, User, Tag, PlusCircle, CheckCircle2 } from 'lucide-react';

interface DiscoveriesProps {
  onNavigateToDiary: (bvid?: string) => void;
}

export const Discoveries: React.FC<DiscoveriesProps> = ({ onNavigateToDiary }) => {
  const [candidates, setCandidates] = useState<VideoCandidate[]>([]);
  const [loading, setLoading] = useState(false);
  const [watchingBvid, setWatchingBvid] = useState<string | null>(null);
  const [customBvid, setCustomBvid] = useState('');
  const [customTitle, setCustomTitle] = useState('');
  const [customAuthor, setCustomAuthor] = useState('');
  const [customDesc, setCustomDesc] = useState('');
  const [customModalOpen, setCustomModalOpen] = useState(false);
  const [analyzingCustom, setAnalyzingCustom] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  useEffect(() => {
    loadCandidates();
  }, []);

  const loadCandidates = async () => {
    setLoading(true);
    try {
      const list = await api.getCandidates();
      setCandidates(list);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleExplore = async () => {
    setLoading(true);
    try {
      const list = await api.explore(true);
      setCandidates(list);
      showToast('大肥鱼刚刚出去逛了一圈，发现了新的好玩视频！');
    } catch (e) {
      console.error(e);
      showToast('探索失败，请检查后端服务');
    } finally {
      setLoading(false);
    }
  };

  const handleWatch = async (candidate: VideoCandidate) => {
    setWatchingBvid(candidate.bvid);
    try {
      const analysis = await api.watchCandidate(candidate.bvid);
      showToast(`已看完《${candidate.title.slice(0, 12)}...》并整理好了日记！`);
      // Update candidate status locally
      setCandidates(prev => prev.map(c => c.bvid === candidate.bvid ? { ...c, status: 'watched' } : c));
      setTimeout(() => {
        onNavigateToDiary(analysis.bvid);
      }, 1200);
    } catch (e) {
      console.error(e);
      showToast('观看分析失败，请稍后重试');
    } finally {
      setWatchingBvid(null);
    }
  };

  const handleAnalyzeCustom = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customBvid.trim() || !customTitle.trim()) return;

    setAnalyzingCustom(true);
    try {
      const analysis = await api.analyzeCustomVideo({
        bvid: customBvid.trim(),
        title: customTitle.trim(),
        author: customAuthor.trim() || 'UP主',
        description: customDesc.trim()
      });
      showToast(`大肥鱼已完成对 ${customBvid} 的分析！`);
      setCustomModalOpen(false);
      setCustomBvid('');
      setCustomTitle('');
      setCustomAuthor('');
      setCustomDesc('');
      setTimeout(() => {
        onNavigateToDiary(analysis.bvid);
      }, 1000);
    } catch (err) {
      console.error(err);
      showToast('分析失败');
    } finally {
      setAnalyzingCustom(false);
    }
  };

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">今天的发现 🧭</h2>
          <p className="page-desc">
            小肥鱼基于自身好奇心、兴趣偏好与求知欲自主发现的内容，透明解释选择理由
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn btn-secondary" onClick={() => setCustomModalOpen(true)}>
            <PlusCircle size={16} /> 手动输入BV号
          </button>
          <button className="btn btn-primary" onClick={handleExplore} disabled={loading}>
            <Compass size={16} /> {loading ? '探索中...' : '重新出去逛逛'}
          </button>
        </div>
      </div>

      {toastMessage && (
        <div style={{
          background: '#ecfdf5',
          color: '#065f46',
          padding: '12px 18px',
          borderRadius: '8px',
          marginBottom: '20px',
          border: '1px solid #a7f3d0',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <CheckCircle2 size={18} color="#059669" />
          {toastMessage}
        </div>
      )}

      {/* Candidates List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
        {candidates.map(item => {
          const isWatching = watchingBvid === item.bvid;
          const isWatched = item.status === 'watched';

          return (
            <div key={item.bvid} className="card" style={{ display: 'flex', gap: '20px', padding: '18px' }}>
              {/* Cover Image */}
              <div style={{
                width: '220px',
                height: '135px',
                borderRadius: '10px',
                overflow: 'hidden',
                background: '#e2e8f0',
                flexShrink: 0,
                position: 'relative'
              }}>
                {item.cover ? (
                  <img
                    src={item.cover}
                    alt={item.title}
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  />
                ) : (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#94a3b8' }}>
                    无封面
                  </div>
                )}
                <span style={{
                  position: 'absolute',
                  bottom: '6px',
                  right: '6px',
                  background: 'rgba(0,0,0,0.7)',
                  color: 'white',
                  fontSize: '11px',
                  padding: '2px 6px',
                  borderRadius: '4px'
                }}>
                  {item.duration}
                </span>
              </div>

              {/* Info & Reason */}
              <div style={{ flexGrow: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '10px' }}>
                    <h3 style={{ fontSize: '16px', fontWeight: 'bold', color: '#1e293b' }}>
                      {item.title}
                    </h3>
                    <span className="badge badge-amber" style={{ whiteSpace: 'nowrap' }}>
                      匹配度: {Math.round(item.score * 100)}%
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '13px', color: 'var(--text-muted)', margin: '6px 0 10px 0' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <User size={14} /> {item.author}
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={14} /> BV号: {item.bvid}
                    </span>
                  </div>

                  {/* Why Chosen Reason Box */}
                  <div style={{
                    background: '#eff6ff',
                    border: '1px solid #bfdbfe',
                    borderRadius: '8px',
                    padding: '8px 12px',
                    fontSize: '13px',
                    color: '#1e40af',
                    marginBottom: '8px',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '6px'
                  }}>
                    <Sparkles size={16} style={{ flexShrink: 0, marginTop: '2px', color: '#2563eb' }} />
                    <div>
                      <b style={{ color: '#1d4ed8' }}>为什么选择它？</b> {item.reason}
                    </div>
                  </div>

                  {/* Tags */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px' }}>
                    {item.tags.map((t, idx) => (
                      <span key={idx} style={{
                        background: '#f1f5f9',
                        color: '#475569',
                        fontSize: '11px',
                        padding: '2px 8px',
                        borderRadius: '4px'
                      }}>
                        #{t}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Bottom Action */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '12px' }}>
                  {isWatched ? (
                    <button className="btn btn-secondary" onClick={() => onNavigateToDiary(item.bvid)}>
                      <CheckCircle2 size={16} color="#059669" /> 查看已生成的日记
                    </button>
                  ) : (
                    <button
                      className="btn btn-primary"
                      onClick={() => handleWatch(item)}
                      disabled={isWatching}
                    >
                      <Eye size={16} /> {isWatching ? '小肥鱼观看思考中...' : '让小肥鱼去观看并分析'}
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Custom BV Analysis Modal */}
      {customModalOpen && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div className="card" style={{ width: '480px', margin: 0 }}>
            <h3 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '14px' }}>
              📺 手动推荐 B站视频给大肥鱼
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px' }}>
              输入 B站视频的 BV 号与基本信息，大肥鱼将以独立视角深入理解并撰写日记。
            </p>
            <form onSubmit={handleAnalyzeCustom} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '13px', fontWeight: '600', display: 'block', marginBottom: '4px' }}>
                  BV 号 *
                </label>
                <input
                  type="text"
                  className="input"
                  placeholder="例如：BV1xx411c7mD"
                  value={customBvid}
                  onChange={e => setCustomBvid(e.target.value)}
                  required
                />
              </div>

              <div>
                <label style={{ fontSize: '13px', fontWeight: '600', display: 'block', marginBottom: '4px' }}>
                  视频标题 *
                </label>
                <input
                  type="text"
                  className="input"
                  placeholder="视频的完整标题"
                  value={customTitle}
                  onChange={e => setCustomTitle(e.target.value)}
                  required
                />
              </div>

              <div>
                <label style={{ fontSize: '13px', fontWeight: '600', display: 'block', marginBottom: '4px' }}>
                  UP 主昵称
                </label>
                <input
                  type="text"
                  className="input"
                  placeholder="例如：极客工匠"
                  value={customAuthor}
                  onChange={e => setCustomAuthor(e.target.value)}
                />
              </div>

              <div>
                <label style={{ fontSize: '13px', fontWeight: '600', display: 'block', marginBottom: '4px' }}>
                  视频简介 / 关键看点
                </label>
                <textarea
                  className="textarea"
                  placeholder="视频的主要介绍或核心探讨点..."
                  value={customDesc}
                  onChange={e => setCustomDesc(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setCustomModalOpen(false)}
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={analyzingCustom || !customBvid.trim() || !customTitle.trim()}
                >
                  {analyzingCustom ? '正在深度分析...' : '提交给大肥鱼'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
