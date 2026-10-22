import React, { useState } from 'react';
import { Home } from './pages/Home';
import { Discoveries } from './pages/Discoveries';
import { VideoDiary } from './pages/VideoDiary';
import { MemoryGrowth } from './pages/MemoryGrowth';
import { Settings } from './pages/Settings';
import { Home as HomeIcon, Compass, BookOpen, Brain, Settings as SettingsIcon, Heart } from 'lucide-react';

export const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState('home');
  const [selectedBvid, setSelectedBvid] = useState<string | undefined>();

  const navigateToDiaryWithBvid = (bvid?: string) => {
    setSelectedBvid(bvid);
    setCurrentPage('diary');
  };

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="brand-header">
          <div className="brand-avatar" style={{ background: 'linear-gradient(135deg, #38bdf8, #2563eb)' }}>
            🦈
          </div>
          <div className="brand-text">
            <h1>大肥鱼 · 鲨鱼娘</h1>
            <p>BlueWhaleLife v1.0</p>
          </div>
        </div>

        <ul className="nav-menu">
          <li>
            <button
              className={`nav-item ${currentPage === 'home' ? 'active' : ''}`}
              onClick={() => setCurrentPage('home')}
            >
              <HomeIcon size={18} /> 小肥鱼的家
            </button>
          </li>
          <li>
            <button
              className={`nav-item ${currentPage === 'discoveries' ? 'active' : ''}`}
              onClick={() => setCurrentPage('discoveries')}
            >
              <Compass size={18} /> 今天的发现
            </button>
          </li>
          <li>
            <button
              className={`nav-item ${currentPage === 'diary' ? 'active' : ''}`}
              onClick={() => {
                setSelectedBvid(undefined);
                setCurrentPage('diary');
              }}
            >
              <BookOpen size={18} /> 观影日记
            </button>
          </li>
          <li>
            <button
              className={`nav-item ${currentPage === 'memory' ? 'active' : ''}`}
              onClick={() => setCurrentPage('memory')}
            >
              <Brain size={18} /> 记忆与成长
            </button>
          </li>
          <li>
            <button
              className={`nav-item ${currentPage === 'settings' ? 'active' : ''}`}
              onClick={() => setCurrentPage('settings')}
            >
              <SettingsIcon size={18} /> 设置
            </button>
          </li>
        </ul>

        <div className="sidebar-footer">
          <span>开源 AI 角色养成</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '3px', color: '#ec4899' }}>
            <Heart size={13} fill="#ec4899" /> Windows
          </span>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        {currentPage === 'home' && <Home onNavigate={setCurrentPage} />}
        {currentPage === 'discoveries' && <Discoveries onNavigateToDiary={navigateToDiaryWithBvid} />}
        {currentPage === 'diary' && <VideoDiary initialBvid={selectedBvid} />}
        {currentPage === 'memory' && <MemoryGrowth />}
        {currentPage === 'settings' && <Settings />}
      </main>
    </div>
  );
};

export default App;
