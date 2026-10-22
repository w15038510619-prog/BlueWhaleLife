import React, { useState, useEffect } from 'react';
import { PetStatus, VideoAnalysis, SchedulerStatus } from '../types';
import { api } from '../api/client';
import { Compass, Sparkles, Send, Heart, Activity, Zap, Moon, ShieldAlert, CheckCircle2 } from 'lucide-react';

interface HomeProps {
  onNavigate: (page: string) => void;
}

export const Home: React.FC<HomeProps> = ({ onNavigate }) => {
  const [status, setStatus] = useState<PetStatus | null>(null);
  const [scheduler, setScheduler] = useState<SchedulerStatus | null>(null);
  const [chatInput, setChatInput] = useState('');
  const [messages, setMessages] = useState<Array<{ sender: 'user' | 'pet'; text: string }>>([
    { sender: 'pet', text: '咕噜噜~ 嗨！我是大肥鱼（你的专属鲸鱼娘桌宠）！今天想和我聊聊什么，还是让我自主去B站探索新奇视频？' }
  ]);
  const [loadingChat, setLoadingChat] = useState(false);
  const [recentVideo, setRecentVideo] = useState<VideoAnalysis | null>(null);
  const [reflecting, setReflecting] = useState(false);
  const [triggeringCycle, setTriggeringCycle] = useState(false);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);

  useEffect(() => {
    loadData();
    loadChatHistory();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const s = await api.getPetStatus();
      setStatus(s);
      const sched = await api.getSchedulerStatus();
      setScheduler(sched);
      const videos = await api.getVideos();
      if (videos.length > 0) {
        setRecentVideo(videos[0]);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const loadChatHistory = async () => {
    try {
      const history = await api.getChatHistory();
      if (history && history.length > 0) {
        setMessages(history.map(h => ({
          sender: h.role === 'user' ? 'user' : 'pet',
          text: h.content
        })));
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSendChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || loadingChat) return;

    const userMsg = chatInput.trim();
    setMessages(prev => [...prev, { sender: 'user', text: userMsg }]);
    setChatInput('');
    setLoadingChat(true);

    try {
      const res = await api.chatWithPet(userMsg);
      setMessages(prev => [...prev, { sender: 'pet', text: res.reply }]);
      if (status) {
        setStatus({ ...status, state: res.pet_state as any, mood: res.mood });
      }
    } catch (err) {
      setMessages(prev => [...prev, { sender: 'pet', text: '咕噜噜~ 刚才水流有点湍急，连接主脑稍有波动，但我还在你身边！' }]);
    } finally {
      setLoadingChat(false);
    }
  };

  const handleTriggerReflection = async () => {
    setReflecting(true);
    setActionFeedback(null);
    try {
      const res = await api.triggerReflection();
      setActionFeedback(`日常反思完成！成长值 +${res.growth_score}，新心境：${res.mood}`);
      loadData();
    } catch (err) {
      setActionFeedback('反思触发失败，请检查服务连接。');
    } finally {
      setReflecting(false);
    }
  };

  const handleTriggerCycle = async () => {
    setTriggeringCycle(true);
    setActionFeedback(null);
    try {
      const res = await api.triggerSchedulerCycle();
      setActionFeedback(`自主周期触发：${res.result || '已完成'}`);
      loadData();
    } catch (err) {
      setActionFeedback('自主周期触发失败。');
    } finally {
      setTriggeringCycle(false);
    }
  };

  const getStateEmoji = (st?: string) => {
    switch (st) {
      case 'thinking': return '💭';
      case 'happy': return '🌟';
      case 'confused': return '❓';
      case 'reading':
      case 'studying': return '📖';
      case 'computer': return '💻';
      case 'watching': return '📺';
      case 'sleep':
      case 'resting': return '💤';
      case 'walking_right':
      case 'walking_left': return '🏃';
      default: return '🌊';
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">小肥鱼的家 🏠</h2>
          <p className="page-desc">看看小肥鱼此时此刻的状态与心思，观察她的自主漫游与成长</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn btn-secondary" onClick={handleTriggerCycle} disabled={triggeringCycle}>
            <Zap size={16} /> {triggeringCycle ? '正在漫游探索...' : '立即自主漫游'}
          </button>
          <button className="btn btn-primary" onClick={() => onNavigate('discoveries')}>
            <Compass size={16} /> 发现候选池
          </button>
          <button className="btn btn-secondary" onClick={handleTriggerReflection} disabled={reflecting}>
            <Sparkles size={16} /> {reflecting ? '反思整理中...' : '日常反思'}
          </button>
        </div>
      </div>

      {actionFeedback && (
        <div style={{ background: '#ecfdf5', color: '#065f46', padding: '12px 16px', borderRadius: '8px', marginBottom: '20px', border: '1px solid #a7f3d0' }}>
          ✨ {actionFeedback}
        </div>
      )}

      {/* Autonomous Scheduler Status Strip */}
      {scheduler && (
        <div className="card" style={{ marginBottom: '20px', padding: '14px 20px', background: scheduler.emergency_stop ? '#fef2f2' : '#f0fdf4', border: `1px solid ${scheduler.emergency_stop ? '#fca5a5' : '#bbf7d0'}` }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              {scheduler.emergency_stop ? (
                <ShieldAlert size={22} color="#dc2626" />
              ) : scheduler.status === 'sleeping' ? (
                <Moon size={22} color="#6366f1" />
              ) : (
                <Zap size={22} color="#16a34a" />
              )}
              <div>
                <div style={{ fontSize: '14px', fontWeight: 'bold', color: scheduler.emergency_stop ? '#b91c1c' : '#15803d' }}>
                  {scheduler.emergency_stop ? '紧急停止开关已激活（所有操作冻结）' : `自主生活调度器：${scheduler.status === 'sleeping' ? '深夜安睡' : scheduler.status === 'resting' ? '静心消化' : '活跃探索就绪'}`}
                </div>
                <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>
                  📍 {scheduler.current_activity}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '13px', color: '#475569' }}>
              <div>
                今日探索：<b>{scheduler.today_explores_count}</b> / {scheduler.daily_budget} 次
              </div>
              <div>
                安静时段：<b>{scheduler.quiet_hours}</b>
              </div>
              <span className={`badge ${scheduler.enabled ? 'badge-green' : 'badge-amber'}`}>
                {scheduler.enabled ? '自动调度运行中' : '自动调度已暂停'}
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="grid-2" style={{ marginBottom: '24px' }}>
        {/* Left: Pet Live Status Card */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{
              width: '84px',
              height: '84px',
              borderRadius: '20px',
              background: 'linear-gradient(135deg, #60a5fa, #2563eb)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '44px',
              boxShadow: '0 8px 16px rgba(59, 130, 246, 0.25)'
            }}>
              🐬
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3 style={{ fontSize: '20px', fontWeight: 'bold' }}>大肥鱼 (鲸鱼娘)</h3>
                <span className="badge badge-blue">
                  {getStateEmoji(status?.state)} {status?.state || 'idle'}
                </span>
                <span className="badge badge-green">
                  心境：{status?.mood || '好奇探索'}
                </span>
              </div>
              <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: 'var(--text-muted)' }}>
                <Activity size={14} /> 角色成长值：
                <b style={{ color: 'var(--primary)', fontSize: '15px' }}>{status?.growth_score || 100}</b> 点
              </div>
            </div>
          </div>

          <div style={{
            background: 'var(--primary-light)',
            padding: '14px',
            borderRadius: '10px',
            border: '1px solid #bfdbfe'
          }}>
            <div style={{ fontSize: '12px', fontWeight: 'bold', color: 'var(--primary)', marginBottom: '4px' }}>
              💬 桌宠实时心语：
            </div>
            <p style={{ fontSize: '14px', color: '#1e3a8a', fontStyle: 'italic' }}>
              “{status?.bubble_text || '今天有什么好玩的知识在等着我们呢？'}”
            </p>
          </div>

          <div style={{ fontSize: '13px', color: '#475569', display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
            <span style={{ fontWeight: 'bold' }}>📍 当前动向：</span>
            <span>{status?.current_activity || '正在虚拟桌宠世界里巡游，观察周围的世界...'}</span>
          </div>

          {recentVideo && (
            <div style={{ borderTop: '1px solid var(--border)', paddingTop: '14px', marginTop: 'auto' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                🎬 最近看过的视频：
              </div>
              <div
                style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-main)', cursor: 'pointer' }}
                onClick={() => onNavigate('diary')}
              >
                《{recentVideo.title}》
              </div>
            </div>
          )}
        </div>

        {/* Right: Interactive Chat Dialog */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', height: '440px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', paddingBottom: '10px', borderBottom: '1px solid var(--border)' }}>
            <Heart size={18} color="#ec4899" />
            <h3 style={{ fontSize: '16px', fontWeight: '600' }}>与大肥鱼聊天</h3>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>（独立人格与长期记忆，对话真实留存）</span>
          </div>

          <div style={{
            flexGrow: 1,
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            paddingRight: '6px',
            marginBottom: '12px'
          }}>
            {messages.map((m, idx) => (
              <div
                key={idx}
                style={{
                  alignSelf: m.sender === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: '85%',
                  background: m.sender === 'user' ? 'var(--primary)' : '#f1f5f9',
                  color: m.sender === 'user' ? '#ffffff' : '#1e293b',
                  padding: '10px 14px',
                  borderRadius: '12px',
                  fontSize: '13px',
                  lineHeight: '1.5'
                }}
              >
                <b>{m.sender === 'user' ? '主人：' : '大肥鱼：'}</b>
                {m.text}
              </div>
            ))}
            {loadingChat && (
              <div style={{ alignSelf: 'flex-start', color: 'var(--text-muted)', fontSize: '12px', fontStyle: 'italic' }}>
                🐬 大肥鱼正在认真构思回话...
              </div>
            )}
          </div>

          <form onSubmit={handleSendChat} style={{ display: 'flex', gap: '8px' }}>
            <input
              type="text"
              className="input"
              placeholder="给大肥鱼发消息..."
              value={chatInput}
              onChange={e => setChatInput(e.target.value)}
              disabled={loadingChat}
            />
            <button type="submit" className="btn btn-primary" disabled={loadingChat || !chatInput.trim()}>
              <Send size={15} /> 发送
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
