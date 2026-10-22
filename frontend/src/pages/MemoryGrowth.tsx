import React, { useState, useEffect } from 'react';
import { KnowledgeNote, ReflectionLog, PersonalityState } from '../types';
import { api } from '../api/client';
import { Brain, History, Sparkles, Search, Trash2, Edit2, RotateCcw, Plus, RefreshCw, CheckCircle2 } from 'lucide-react';

export const MemoryGrowth: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'notes' | 'reflections' | 'personality'>('notes');

  // Notes state
  const [notes, setNotes] = useState<KnowledgeNote[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [newTopic, setNewTopic] = useState('');
  const [newContent, setNewContent] = useState('');
  const [isAddingNote, setIsAddingNote] = useState(false);
  const [showArchived, setShowArchived] = useState(false);

  // Reflections state
  const [reflections, setReflections] = useState<ReflectionLog[]>([]);
  const [reflecting, setReflecting] = useState(false);

  // Personality & Rollback state
  const [personalityHistory, setPersonalityHistory] = useState<PersonalityState[]>([]);
  const [currentPersonality, setCurrentPersonality] = useState<PersonalityState | null>(null);
  const [rollingBackVer, setRollingBackVer] = useState<number | null>(null);

  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    loadAll();
  }, [showArchived]);

  const loadAll = async () => {
    try {
      const n = await api.getKnowledgeNotes(!showArchived);
      setNotes(n);
      const r = await api.getReflectionLogs();
      setReflections(r);
      const cur = await api.getSoulCurrent();
      setCurrentPersonality(cur);
      const hist = await api.getSoulHistory();
      setPersonalityHistory(hist);
    } catch (e) {
      console.error(e);
    }
  };

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3500);
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      loadAll();
      return;
    }
    try {
      const res = await api.searchMemories(searchQuery.trim());
      setNotes(res.notes);
    } catch (err) {
      console.error(err);
    }
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTopic.trim() || !newContent.trim()) return;
    try {
      await api.createKnowledgeNote({
        topic: newTopic.trim(),
        content: newContent.trim(),
        importance: 4
      });
      setNewTopic('');
      setNewContent('');
      setIsAddingNote(false);
      showToast('新知识笔记已记录到长期记忆库！');
      loadAll();
    } catch (e) {
      console.error(e);
    }
  };

  const handleForgetNote = async (id?: number) => {
    if (!id) return;
    try {
      await api.forgetKnowledgeNote(id);
      showToast('该笔记已被遗忘并移入归档区。');
      loadAll();
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeduplicate = async () => {
    try {
      const res = await api.deduplicateNotes();
      showToast(`知识库整理完成！已合并归档 ${res.merged_count} 条重复信息。`);
      loadAll();
    } catch (e) {
      console.error(e);
    }
  };

  const handleTriggerReflection = async () => {
    setReflecting(true);
    try {
      const log = await api.triggerReflection();
      showToast(`日常反思完成！大肥鱼模拟心境：${log.mood}`);
      loadAll();
    } catch (e) {
      console.error(e);
    } finally {
      setReflecting(false);
    }
  };

  const handleRollback = async (version: number) => {
    if (!window.confirm(`确定要将大肥鱼的性格与兴趣设定回滚到版本 v${version} 吗？`)) return;
    setRollingBackVer(version);
    try {
      const updated = await api.rollbackSoul(version);
      showToast(`成功回滚到版本 v${version}！已生成新版本记录。`);
      loadAll();
    } catch (e) {
      console.error(e);
      showToast('回滚失败');
    } finally {
      setRollingBackVer(null);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">记忆与成长 🌱</h2>
          <p className="page-desc">
            大肥鱼的长期知识笔记、日常反思日志，以及可解释且支持主人回滚的性格演化轨迹
          </p>
        </div>
      </div>

      {toast && (
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
          {toast}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '10px', borderBottom: '1px solid var(--border)', marginBottom: '24px' }}>
        <button
          className={`btn ${activeTab === 'notes' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('notes')}
          style={{ borderRadius: '8px 8px 0 0', borderBottom: 'none' }}
        >
          <Brain size={16} /> 知识笔记库 ({notes.length})
        </button>
        <button
          className={`btn ${activeTab === 'reflections' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('reflections')}
          style={{ borderRadius: '8px 8px 0 0', borderBottom: 'none' }}
        >
          <Sparkles size={16} /> 日常反思日志 ({reflections.length})
        </button>
        <button
          className={`btn ${activeTab === 'personality' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('personality')}
          style={{ borderRadius: '8px 8px 0 0', borderBottom: 'none' }}
        >
          <History size={16} /> 人格演化与回滚
        </button>
      </div>

      {/* Tab 1: Knowledge Notes */}
      {activeTab === 'notes' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px', gap: '12px' }}>
            <form onSubmit={handleSearch} style={{ display: 'flex', gap: '8px', flexGrow: 1, maxWidth: '450px' }}>
              <input
                type="text"
                className="input"
                placeholder="搜索长期记忆关键词..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
              <button type="submit" className="btn btn-secondary">
                <Search size={16} /> 搜索
              </button>
            </form>

            <div style={{ display: 'flex', gap: '8px' }}>
              <button className="btn btn-secondary" onClick={handleDeduplicate}>
                <RefreshCw size={16} /> 记忆去重与整理
              </button>
              <button className="btn btn-primary" onClick={() => setIsAddingNote(!isAddingNote)}>
                <Plus size={16} /> 添加知识点
              </button>
            </div>
          </div>

          {isAddingNote && (
            <div className="card" style={{ marginBottom: '20px', background: '#eff6ff', borderColor: '#bfdbfe' }}>
              <h4 style={{ fontSize: '15px', fontWeight: 'bold', marginBottom: '10px', color: '#1e40af' }}>
                ✏️ 为大肥鱼添加一条新记忆
              </h4>
              <form onSubmit={handleAddNote} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <input
                  type="text"
                  className="input"
                  placeholder="知识点主题（例如：深海热泉生态）"
                  value={newTopic}
                  onChange={e => setNewTopic(e.target.value)}
                  required
                />
                <textarea
                  className="textarea"
                  placeholder="具体知识内容与启示..."
                  value={newContent}
                  onChange={e => setNewContent(e.target.value)}
                  required
                />
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                  <button type="button" className="btn btn-secondary" onClick={() => setIsAddingNote(false)}>
                    取消
                  </button>
                  <button type="submit" className="btn btn-primary">
                    存入记忆库
                  </button>
                </div>
              </form>
            </div>
          )}

          <div className="grid-2">
            {notes.map(n => (
              <div key={n.id} className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', margin: 0 }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                    <h4 style={{ fontSize: '16px', fontWeight: 'bold', color: '#1e293b' }}>
                      {n.topic}
                    </h4>
                    <span className="badge badge-blue">
                      重要度: {n.importance}/5
                    </span>
                  </div>
                  <p style={{ fontSize: '14px', color: '#334155', lineHeight: '1.6', marginBottom: '12px' }}>
                    {n.content}
                  </p>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border)', paddingTop: '10px', fontSize: '12px', color: 'var(--text-muted)' }}>
                  <span>记录于：{n.created_at}</span>
                  <button
                    className="btn btn-danger"
                    style={{ padding: '4px 8px', fontSize: '12px' }}
                    onClick={() => handleForgetNote(n.id)}
                    title="将该信息移入遗忘区"
                  >
                    <Trash2 size={13} /> 遗忘
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 2: Reflection Logs */}
      {activeTab === 'reflections' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '18px' }}>
            <button className="btn btn-primary" onClick={handleTriggerReflection} disabled={reflecting}>
              <Sparkles size={16} /> {reflecting ? '反思生成中...' : '立即执行今日反思'}
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {reflections.map(r => (
              <div key={r.id} className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', paddingBottom: '8px', borderBottom: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <h3 style={{ fontSize: '17px', fontWeight: 'bold' }}>📅 {r.date} 成长反思</h3>
                    <span className="badge badge-green">模拟心境：{r.mood}</span>
                  </div>
                  <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                    记录于：{r.created_at}
                  </span>
                </div>

                <div className="grid-2">
                  <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '8px' }}>
                    <b style={{ color: '#2563eb', display: 'block', marginBottom: '4px' }}>🔍 今天发现了什么：</b>
                    <p style={{ fontSize: '13px', color: '#334155' }}>{r.discoveries_summary}</p>
                  </div>

                  <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '8px' }}>
                    <b style={{ color: '#059669', display: 'block', marginBottom: '4px' }}>🔄 哪些知识改变了原先的看法：</b>
                    <p style={{ fontSize: '13px', color: '#334155' }}>{r.viewpoint_shifts}</p>
                  </div>

                  <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '8px' }}>
                    <b style={{ color: '#7c3aed', display: 'block', marginBottom: '4px' }}>🌟 萌生的新兴趣领域：</b>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '4px' }}>
                      {r.new_interests.map((it, idx) => (
                        <span key={idx} className="badge badge-purple">
                          #{it}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div style={{ background: '#f8fafc', padding: '12px', borderRadius: '8px' }}>
                    <b style={{ color: '#d97706', display: 'block', marginBottom: '4px' }}>❓ 仍需继续核实的观点：</b>
                    <p style={{ fontSize: '13px', color: '#334155' }}>{r.pending_doubts}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 3: Personality History & Rollback */}
      {activeTab === 'personality' && (
        <div>
          {/* Current State Summary */}
          {currentPersonality && (
            <div className="card" style={{ background: '#eff6ff', borderColor: '#bfdbfe', marginBottom: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: '#1e3a8a' }}>
                  当前生效人格 (v{currentPersonality.version})
                </h3>
                <span className="badge badge-blue">当前活跃版本</span>
              </div>

              <div style={{ marginBottom: '14px', fontSize: '13px', color: '#1e40af' }}>
                <b>版本说明：</b> {currentPersonality.reason}
              </div>

              <div className="grid-2">
                <div>
                  <h4 style={{ fontSize: '14px', fontWeight: 'bold', color: '#1e3a8a', marginBottom: '8px' }}>
                    🎭 基础性格特质
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {Object.entries(currentPersonality.traits).map(([trait, val]) => (
                      <div key={trait} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', color: '#334155' }}>
                        <span>{trait}:</span>
                        <b>{Math.round(val * 100)}%</b>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 style={{ fontSize: '14px', fontWeight: 'bold', color: '#1e3a8a', marginBottom: '8px' }}>
                    🧭 兴趣领域偏好权重
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {Object.entries(currentPersonality.interests).map(([topic, weight]) => (
                      <div key={topic} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', color: '#334155' }}>
                        <span>{topic}:</span>
                        <b>{Math.round(weight * 100)}%</b>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Historical Versions Timeline */}
          <h3 style={{ fontSize: '17px', fontWeight: 'bold', marginBottom: '16px', color: '#1e293b' }}>
            📜 人格演化历史与主人回滚记录
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {personalityHistory.map(state => (
              <div
                key={state.version}
                className="card"
                style={{
                  borderLeft: state.is_current ? '4px solid #2563eb' : '4px solid #cbd5e0',
                  margin: 0
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                      <span style={{ fontSize: '16px', fontWeight: 'bold', color: '#0f172a' }}>
                        版本 v{state.version}
                      </span>
                      {state.is_current ? (
                        <span className="badge badge-blue">当前运行中</span>
                      ) : (
                        <span className="badge badge-amber">历史快照</span>
                      )}
                    </div>
                    <div style={{ fontSize: '13px', color: '#334155', marginBottom: '8px' }}>
                      {state.reason}
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      创建时间：{state.created_at}
                    </div>
                  </div>

                  {!state.is_current && (
                    <button
                      className="btn btn-secondary"
                      onClick={() => handleRollback(state.version)}
                      disabled={rollingBackVer === state.version}
                    >
                      <RotateCcw size={15} />
                      {rollingBackVer === state.version ? '回滚中...' : `回滚至 v${state.version}`}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
