import React, { useState, useEffect } from 'react';
import { PetStatus, VideoAnalysis } from '../types';
import { api } from '../api/client';
import { Compass, Sparkles, Send, BookOpen, Heart, Activity } from 'lucide-react';

interface HomeProps {
  onNavigate: (page: string) => void;
}

export const Home: React.FC<HomeProps> = ({ onNavigate }) => {
  const [status, setStatus] = useState<PetStatus | null>(null);
  const [chatInput, setChatInput] = useState('');
  const [messages, setMessages] = useState<Array<{ sender: 'user' | 'pet'; text: string }>>([
    { sender: 'pet', text: '咕噜噜~ 嗨！我是大肥鱼（你的专属鲨鱼娘看板）！今天想和我聊聊什么，还是让我出去逛逛B站探索新奇视频？' }
  ]);
  const [loadingChat, setLoadingChat] = useState(false);
  const [recentVideo, setRecentVideo] = useState<VideoAnalysis | null>(null);
  const [reflecting, setReflecting] = useState(false);
  const [reflectFeedback, setReflectFeedback] = useState<string | null>(null);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const s = await api.getPetStatus();
      setStatus(s);
      const videos = await api.getVideos();
      if (videos.length > 0) {
        setRecentVideo(videos[0]);
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
    setReflectFeedback(null);
    try {
      const res = await api.triggerReflection();
      setReflectFeedback(`反思完成！成长值 +${res.growth_score}，新心境：${res.mood}`);
      loadData();
    } catch (err) {
      setReflectFeedback('反思触发失败，请检查服务。');
    } finally {
      setReflecting(false);
    }
  };

  const getStateEmoji = (st?: string) => {
    switch (st) {
      case 'thinking': return '💭';
      case 'happy': return '🌟';
      case 'confused': return '❓';
      case 'studying': return '📖';
      case 'resting': return '💤';
      default: return '🌊';
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">小肥鱼的家 🏠</h2>
          <p className="page-desc">看看小肥鱼此时此刻的状态与心思，和她随时畅聊</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn btn-primary" onClick={() => onNavigate('discoveries')}>
            <Compass size={16} /> 让小肥鱼出去逛逛
          </button>
          <button className="btn btn-secondary" onClick={handleTriggerReflection} disabled={reflecting}>
            <Sparkles size={16} /> {reflecting ? '反思整理中...' : '日常反思'}
          </button>
        </div>
      </div>

      {reflectFeedback && (
        <div style={{ background: '#ecfdf5', color: '#065f46', padding: '12px 16px', borderRadius: '8px', marginBottom: '20px', border: '1px solid #a7f3d0' }}>
          ✨ {reflectFeedback}
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
              background: 'linear-gradient(135deg, #38bdf8, #2563eb)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '44px',
              boxShadow: '0 8px 16px rgba(59, 130, 246, 0.25)'
            }}>
              🦈
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3 style={{ fontSize: '20px', fontWeight: 'bold' }}>大肥鱼 (鲨鱼娘)</h3>
                <span className="badge badge-blue">
                  {getStateEmoji(status?.state)} {status?.state || 'idle'}
                </span>
                <span className="badge badge-green">
                  心境：{status?.mood || '好奇'}
                </span>
              </div>
              <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: 'var(--text-muted)' }}>
                <Activity size={14} /> 模拟成长值：
                <b style={{ color: 'var(--primary)', fontSize: '15px' }}>{status?.growth_score || 100}</b> 经验点
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
              💬 当前心语：
            </div>
            <p style={{ fontSize: '14px', color: '#1e3a8a', fontStyle: 'italic' }}>
              “{status?.bubble_text || '今天有什么好玩的知识在等着我们呢？'}”
            </p>
          </div>

          <div style={{ fontSize: '13px', color: '#475569', display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
            <span style={{ fontWeight: 'bold' }}>📍 当前动向：</span>
            <span>{status?.current_activity || '正在虚拟水缸里巡游，观察周围的世界...'}</span>
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
        <div className="card" style={{ display: 'flex', flexDirection: 'column', height: '420px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', paddingBottom: '10px', borderBottom: '1px solid var(--border)' }}>
            <Heart size={18} color="#ec4899" />
            <h3 style={{ fontSize: '16px', fontWeight: '600' }}>与大肥鱼聊天</h3>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>（她有自己的观点，不刻意讨好任何人）</span>
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
                🐟 大肥鱼正在认真构思回话...
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
