import React, { useState, useEffect } from 'react';
import { SettingsResponse } from '../types';
import { api } from '../api/client';
import { Settings as SettingsIcon, Key, ShieldCheck, Save, Eye, EyeOff, CheckCircle2 } from 'lucide-react';

export const Settings: React.FC = () => {
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [baseUrl, setBaseUrl] = useState('');
  const [model, setModel] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [demoMode, setDemoMode] = useState(true);
  const [characterName, setCharacterName] = useState('大肥鱼');
  const [curiosity, setCuriosity] = useState(0.85);
  const [novelty, setNovelty] = useState(0.35);

  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const s = await api.getSettings();
      setSettings(s);
      setBaseUrl(s.llm_base_url);
      setModel(s.llm_model);
      setDemoMode(s.demo_mode);
      setCharacterName(s.character_name);
      setCuriosity(s.curiosity_level);
      setNovelty(s.novelty_weight);
    } catch (e) {
      console.error(e);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updateData: any = {
        llm_base_url: baseUrl.trim(),
        llm_model: model.trim(),
        demo_mode: demoMode,
        character_name: characterName.trim(),
        curiosity_level: curiosity,
        novelty_weight: novelty
      };
      if (apiKey.trim()) {
        updateData.llm_api_key = apiKey.trim();
      }
      const updated = await api.updateSettings(updateData);
      setSettings(updated);
      setApiKey(''); // clear plain input after saving
      setToast('设置已成功保存！密钥安全存储在本地。');
      setTimeout(() => setToast(null), 3500);
    } catch (e) {
      console.error(e);
      setToast('保存失败，请检查服务');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">系统与模型设置 ⚙️</h2>
          <p className="page-desc">
            配置兼容 OpenAI 格式的大语言模型服务（如 DeepSeek 等），设定小肥鱼的探索倾向
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

      <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* LLM Config Card */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', color: '#2563eb' }}>
            <Key size={20} />
            <h3 style={{ fontSize: '17px', fontWeight: 'bold' }}>大模型 API 配置 (兼容 OpenAI 格式)</h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <label style={{ fontSize: '13px', fontWeight: '600', display: 'block', marginBottom: '4px' }}>
                API Base URL
              </label>
              <input
                type="text"
                className="input"
                placeholder="例如：https://api.deepseek.com/v1 或 https://api.openai.com/v1"
                value={baseUrl}
                onChange={e => setBaseUrl(e.target.value)}
                required
              />
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                DeepSeek 官方兼容地址为 https://api.deepseek.com/v1
              </span>
            </div>

            <div>
              <label style={{ fontSize: '13px', fontWeight: '600', display: 'block', marginBottom: '4px' }}>
                模型名称 (Model)
              </label>
              <input
                type="text"
                className="input"
                placeholder="例如：deepseek-chat 或 gpt-4o-mini"
                value={model}
                onChange={e => setModel(e.target.value)}
                required
              />
            </div>

            <div>
              <label style={{ fontSize: '13px', fontWeight: '600', display: 'block', marginBottom: '4px' }}>
                API Key
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showKey ? 'text' : 'password'}
                  className="input"
                  placeholder={settings?.has_api_key ? `已配置 (${settings.llm_api_key_masked})，输入新密钥覆盖` : '输入您的 API Key（如 sk-...）'}
                  value={apiKey}
                  onChange={e => setApiKey(e.target.value)}
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  style={{
                    position: 'absolute',
                    right: '12px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: 'var(--text-muted)'
                  }}
                >
                  {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Demo Mode Toggle */}
            <div style={{
              background: '#f8fafc',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              padding: '12px 16px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div>
                <b style={{ fontSize: '14px', color: '#1e293b' }}>离线演示模式 (Demo Mode)</b>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  无需配置真实 API Key 或 B站账号，大肥鱼使用内置高拟真算法生成生动思考与观点
                </p>
              </div>
              <input
                type="checkbox"
                style={{ width: '20px', height: '20px', cursor: 'pointer' }}
                checked={demoMode}
                onChange={e => setDemoMode(e.target.checked)}
              />
            </div>
          </div>
        </div>

        {/* Character Tendency Card */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', color: '#059669' }}>
            <SettingsIcon size={20} />
            <h3 style={{ fontSize: '17px', fontWeight: 'bold' }}>角色探索倾向设置</h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label style={{ fontSize: '13px', fontWeight: '600', display: 'block', marginBottom: '4px' }}>
                角色名称
              </label>
              <input
                type="text"
                className="input"
                value={characterName}
                onChange={e => setCharacterName(e.target.value)}
                required
              />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <label style={{ fontSize: '13px', fontWeight: '600' }}>
                  好奇心强度 (Curiosity): {Math.round(curiosity * 100)}%
                </label>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  决定主动发现新视频的求知驱动力
                </span>
              </div>
              <input
                type="range"
                min="0.1"
                max="1.0"
                step="0.05"
                value={curiosity}
                onChange={e => setCuriosity(parseFloat(e.target.value))}
                style={{ width: '100%', cursor: 'pointer' }}
              />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <label style={{ fontSize: '13px', fontWeight: '600' }}>
                  新颖度权重 (Novelty Weight): {Math.round(novelty * 100)}%
                </label>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  越高越倾向探索从未接触过的冷门奇妙领域，跳出信息茧房
                </span>
              </div>
              <input
                type="range"
                min="0.1"
                max="0.8"
                step="0.05"
                value={novelty}
                onChange={e => setNovelty(parseFloat(e.target.value))}
                style={{ width: '100%', cursor: 'pointer' }}
              />
            </div>
          </div>
        </div>

        {/* Security & Open Source Compliance Notice */}
        <div style={{
          background: '#eff6ff',
          border: '1px solid #bfdbfe',
          borderRadius: '10px',
          padding: '14px 18px',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '12px'
        }}>
          <ShieldCheck size={22} style={{ color: '#2563eb', flexShrink: 0, marginTop: '2px' }} />
          <div style={{ fontSize: '13px', color: '#1e40af', lineHeight: '1.6' }}>
            <b>隐私与安全承诺：</b>
            所有 API 密钥均仅保存在本地 <code>data/config.json</code>，受到 <code>.gitignore</code> 严格保护，绝不会被上传或写入代码仓库。
            B站数据仅以只读方式获取，无任何自动化刷赞、刷评或骚扰行为。
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button type="submit" className="btn btn-primary" style={{ padding: '10px 24px' }} disabled={saving}>
            <Save size={16} /> {saving ? '正在保存...' : '保存所有设置'}
          </button>
        </div>
      </form>
    </div>
  );
};
