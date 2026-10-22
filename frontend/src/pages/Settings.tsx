import React, { useState, useEffect } from 'react';
import { SettingsResponse } from '../types';
import { api } from '../api/client';
import { Settings as SettingsIcon, Key, ShieldCheck, Save, Eye, EyeOff, CheckCircle2, ShieldAlert, Radio, Clock, Zap } from 'lucide-react';

export const Settings: React.FC = () => {
  const [settings, setSettings] = useState<SettingsResponse | null>(null);

  // LLM Settings
  const [baseUrl, setBaseUrl] = useState('');
  const [model, setModel] = useState('');
  const [protocol, setProtocol] = useState('responses');
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [demoMode, setDemoMode] = useState(true);
  const [dailyCostBudget, setDailyCostBudget] = useState(5.0);
  const [testingConnection, setTestingConnection] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; latency_ms: number; reply?: string; model?: string; protocol?: string; error_message?: string; status_code?: number } | null>(null);
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [fetchingModels, setFetchingModels] = useState(false);

  const [characterName, setCharacterName] = useState('大肥鱼');
  const [curiosity, setCuriosity] = useState(0.85);
  const [novelty, setNovelty] = useState(0.35);

  // Publisher & Autonomous Comment Settings
  const [publisherType, setPublisherType] = useState('pending_approval');
  const [bilibiliToken, setBilibiliToken] = useState('');
  const [showBiliToken, setShowBiliToken] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState('');
  const [emergencyStop, setEmergencyStop] = useState(false);
  const [maxCommentsPerDay, setMaxCommentsPerDay] = useState(3);
  const [autoCommentEnabled, setAutoCommentEnabled] = useState(false);

  // Scheduler Settings
  const [schedulerEnabled, setSchedulerEnabled] = useState(true);
  const [intervalMinutes, setIntervalMinutes] = useState(30);
  const [quietHoursStart, setQuietHoursStart] = useState(23);
  const [quietHoursEnd, setQuietHoursEnd] = useState(7);
  const [dailyExploreBudget, setDailyExploreBudget] = useState(5);

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
      setProtocol(s.llm_protocol || 'responses');
      setDemoMode(s.demo_mode);
      setDailyCostBudget(s.daily_cost_budget || 5.0);
      setCharacterName(s.character_name);
      setCuriosity(s.curiosity_level);
      setNovelty(s.novelty_weight);

      setPublisherType(s.publisher_type || 'pending_approval');
      setWebhookUrl(s.webhook_url || '');
      setEmergencyStop(s.emergency_stop || false);
      setMaxCommentsPerDay(s.max_comments_per_day || 3);
      setAutoCommentEnabled(s.auto_comment_enabled || false);

      setSchedulerEnabled(s.scheduler_enabled !== undefined ? s.scheduler_enabled : true);
      setIntervalMinutes(s.scheduler_interval_minutes || 30);
      setQuietHoursStart(s.quiet_hours_start !== undefined ? s.quiet_hours_start : 23);
      setQuietHoursEnd(s.quiet_hours_end !== undefined ? s.quiet_hours_end : 7);
      setDailyExploreBudget(s.daily_explore_budget || 5);
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
        llm_protocol: protocol,
        demo_mode: demoMode,
        daily_cost_budget: dailyCostBudget,
        character_name: characterName.trim(),
        curiosity_level: curiosity,
        novelty_weight: novelty,

        publisher_type: publisherType,
        webhook_url: webhookUrl.trim(),
        emergency_stop: emergencyStop,
        max_comments_per_day: maxCommentsPerDay,
        auto_comment_enabled: autoCommentEnabled,

        scheduler_enabled: schedulerEnabled,
        scheduler_interval_minutes: intervalMinutes,
        quiet_hours_start: quietHoursStart,
        quiet_hours_end: quietHoursEnd,
        daily_explore_budget: dailyExploreBudget
      };

      if (apiKey.trim()) {
        updateData.llm_api_key = apiKey.trim();
      }
      if (bilibiliToken.trim()) {
        updateData.bilibili_access_token = bilibiliToken.trim();
      }

      const updated = await api.updateSettings(updateData);
      setSettings(updated);
      setApiKey('');
      setBilibiliToken('');
      setToast('设置已成功保存！密钥与令牌已安全加密存储。');
      setTimeout(() => setToast(null), 3500);
    } catch (e) {
      console.error(e);
      setToast('保存失败，请检查服务');
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    setTestingConnection(true);
    setTestResult(null);
    try {
      const res = await api.testConnection({
        base_url: baseUrl.trim(),
        api_key: apiKey.trim() || undefined,
        model: model.trim(),
        protocol: protocol
      });
      setTestResult(res);
    } catch (e: any) {
      setTestResult({
        success: false,
        latency_ms: 0,
        error_message: `测试请求异常: ${e.message || e}`
      });
    } finally {
      setTestingConnection(false);
    }
  };

  const handleFetchModels = async () => {
    setFetchingModels(true);
    try {
      const res = await api.fetchModels({
        base_url: baseUrl.trim(),
        api_key: apiKey.trim() || undefined
      });
      if (res.models && res.models.length > 0) {
        setAvailableModels(res.models);
        if (!res.models.includes(model)) {
          setModel(res.models[0]);
        }
        setToast(`已获取到可用模型列表: ${res.models.join(', ')}`);
        setTimeout(() => setToast(null), 4000);
      } else {
        setToast('未获取到模型列表，请确认 Base URL 与 Key 是否有效');
        setTimeout(() => setToast(null), 3500);
      }
    } catch (e: any) {
      setToast(`获取模型失败: ${e.message || e}`);
      setTimeout(() => setToast(null), 3500);
    } finally {
      setFetchingModels(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">系统与安全配置 ⚙️</h2>
          <p className="page-desc">
            配置大模型地址、自主评论发布通道、安全紧急开关及自主生活作息调度。
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
          <span>{toast}</span>
        </div>
      )}

      <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {/* Section 1: Emergency Stop Switch */}
        <div className="card" style={{ background: emergencyStop ? '#fef2f2' : '#ffffff', border: `1px solid ${emergencyStop ? '#fca5a5' : '#e2e8f0'}` }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <ShieldAlert size={24} color={emergencyStop ? '#dc2626' : '#64748b'} />
              <div>
                <h3 style={{ fontSize: '16px', fontWeight: 'bold', color: emergencyStop ? '#b91c1c' : '#1e293b' }}>
                  主人的紧急停止开关 (Emergency Stop)
                </h3>
                <p style={{ fontSize: '13px', color: '#64748b', marginTop: '2px' }}>
                  一旦开启，立即冻结大肥鱼所有的自主漫游、评论发布与外部请求操作，提供绝对安全控制。
                </p>
              </div>
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontWeight: 'bold', fontSize: '14px', color: emergencyStop ? '#dc2626' : '#475569' }}>
              <input
                type="checkbox"
                checked={emergencyStop}
                onChange={e => setEmergencyStop(e.target.checked)}
                style={{ width: '18px', height: '18px' }}
              />
              {emergencyStop ? '紧急停止已激活' : '正常待机中'}
            </label>
          </div>
        </div>

        {/* Section 2: LLM Configuration */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--primary)' }}>
              <Key size={20} />
              <h3 style={{ fontSize: '16px', fontWeight: 'bold' }}>大语言模型设置（Aixoras / DeepSeek / OpenAI 兼容）</h3>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ fontSize: '12px', padding: '4px 10px' }}
                onClick={() => {
                  setBaseUrl('https://api.aixoras.com/v1');
                  setProtocol('responses');
                  setModel('deepseek-v4.1-flash');
                }}
              >
                🌊 预设: Aixoras (鲨鱼娘)
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ fontSize: '12px', padding: '4px 10px' }}
                onClick={() => {
                  setBaseUrl('https://api.deepseek.com/v1');
                  setProtocol('chat_completions');
                  setModel('deepseek-chat');
                }}
              >
                🐋 预设: DeepSeek 官方
              </button>
            </div>
          </div>

          <div className="grid-2">
            <div>
              <label style={{ fontSize: '13px', fontWeight: '600', color: '#475569', display: 'block', marginBottom: '6px' }}>
                API Base URL：
              </label>
              <input
                type="text"
                className="input"
                value={baseUrl}
                onChange={e => setBaseUrl(e.target.value)}
                placeholder="例如: https://api.aixoras.com/v1"
                required
              />
            </div>

            <div>
              <label style={{ fontSize: '13px', fontWeight: '600', color: '#475569', display: 'block', marginBottom: '6px' }}>
                API 协议 (Protocol)：
              </label>
              <select
                className="select"
                value={protocol}
                onChange={e => setProtocol(e.target.value)}
                style={{ width: '100%' }}
              >
                <option value="responses">Responses API (/v1/responses，Aixoras 平台推荐)</option>
                <option value="chat_completions">Chat Completions (/v1/chat/completions，OpenAI 标准)</option>
              </select>
            </div>
          </div>

          <div className="grid-2" style={{ marginTop: '14px' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <label style={{ fontSize: '13px', fontWeight: '600', color: '#475569' }}>
                  模型名称 (Model ID，非令牌分组名)：
                </label>
                <button
                  type="button"
                  style={{ background: 'none', border: 'none', color: '#2563eb', fontSize: '12px', cursor: 'pointer', padding: 0 }}
                  onClick={handleFetchModels}
                  disabled={fetchingModels}
                >
                  {fetchingModels ? '正在查询...' : '🔍 获取可用模型'}
                </button>
              </div>
              <div style={{ display: 'flex', gap: '6px' }}>
                <input
                  type="text"
                  className="input"
                  value={model}
                  onChange={e => setModel(e.target.value)}
                  placeholder="例如: deepseek-v4.1-flash"
                  required
                />
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ whiteSpace: 'nowrap', fontSize: '11px', padding: '4px 8px' }}
                  onClick={() => setModel('deepseek-v4.1-flash')}
                  title="Aixoras 鲨鱼娘令牌绑定的真实模型 ID"
                >
                  Flash (Aixoras)
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ whiteSpace: 'nowrap', fontSize: '11px', padding: '4px 8px' }}
                  onClick={() => setModel('deepseek-chat')}
                >
                  Chat
                </button>
              </div>
              {availableModels.length > 0 && (
                <div style={{ marginTop: '6px', display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '11px', color: '#64748b' }}>可用模型:</span>
                  {availableModels.map(m => (
                    <span
                      key={m}
                      onClick={() => setModel(m)}
                      style={{
                        fontSize: '11px',
                        cursor: 'pointer',
                        padding: '1px 6px',
                        borderRadius: '4px',
                        background: model === m ? '#dbeafe' : '#f1f5f9',
                        color: model === m ? '#1d4ed8' : '#334155',
                        fontWeight: model === m ? 'bold' : 'normal',
                        border: '1px solid #cbd5e1'
                      }}
                    >
                      {m}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div>
              <label style={{ fontSize: '13px', fontWeight: '600', color: '#475569', display: 'block', marginBottom: '6px' }}>
                每日 API 消耗预算上限 (¥ CNY)：
              </label>
              <input
                type="number"
                step="any"
                min="0"
                max="1000"
                className="input"
                value={dailyCostBudget}
                onChange={e => setDailyCostBudget(parseFloat(e.target.value) || 0)}
              />
              <span style={{ fontSize: '11px', color: '#64748b', marginTop: '4px', display: 'block' }}>
                设置每日允许消耗的人民币上限（输入整数或小数均可，如 5 或 10.5）
              </span>
            </div>
          </div>

          <div style={{ marginTop: '14px' }}>
            <label style={{ fontSize: '13px', fontWeight: '600', color: '#475569', display: 'block', marginBottom: '6px' }}>
              API 密钥 (Secret Key - 本地 Windows DPAPI 加密防护)：
            </label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                type={showKey ? 'text' : 'password'}
                className="input"
                value={apiKey}
                onChange={e => setApiKey(e.target.value)}
                placeholder={settings?.has_api_key ? `已安全加密存储: ${settings.llm_api_key_masked} (输入新Key覆盖)` : '输入 sk-... 密钥'}
              />
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowKey(!showKey)}
                title="显示/隐藏密钥"
              >
                {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
              <button
                type="button"
                className="btn btn-primary"
                style={{ whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: '6px' }}
                onClick={handleTestConnection}
                disabled={testingConnection}
              >
                <Zap size={16} />
                {testingConnection ? '连接测试中...' : '测试连接'}
              </button>
            </div>
          </div>

          {/* Test Connection Live Result */}
          {testResult && (
            <div style={{
              marginTop: '12px',
              padding: '12px 16px',
              borderRadius: '8px',
              fontSize: '13px',
              background: testResult.success ? '#f0fdf4' : '#fef2f2',
              border: `1px solid ${testResult.success ? '#bbf7d0' : '#fecaca'}`,
              color: testResult.success ? '#166534' : '#991b1b'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <b>{testResult.success ? '✅ 连接成功！' : '❌ 连接失败'}</b>
                <span style={{ fontSize: '12px', opacity: 0.8 }}>耗时: {testResult.latency_ms}ms</span>
              </div>
              {testResult.success ? (
                <div>
                  <p>模型回复: “{testResult.reply}”</p>
                  <span style={{ fontSize: '11px', color: '#15803d' }}>
                    协议: {testResult.protocol} | 模型: {testResult.model}
                  </span>
                </div>
              ) : (
                <div>
                  <p>错误原因: {testResult.error_message}</p>
                  {testResult.status_code && <span>HTTP 状态码: {testResult.status_code}</span>}
                </div>
              )}
            </div>
          )}

          <div style={{ marginTop: '14px', background: '#f8fafc', padding: '12px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px', color: '#334155' }}>
              <input
                type="checkbox"
                checked={demoMode}
                onChange={e => setDemoMode(e.target.checked)}
              />
              <span><b>启用内置仿真模式 (Demo Mode)：</b> 未配置有效 API Key 或脱机测试时，使用智能仿真思考逻辑。若关闭且配置了 Key，将直连模型并在失败时如实报错。</span>
            </label>
          </div>
        </div>

        {/* Section 3: Autonomous Comment & Publisher Channel */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', color: '#059669' }}>
            <Radio size={20} />
            <h3 style={{ fontSize: '16px', fontWeight: 'bold' }}>自主评论与发布通道设置</h3>
          </div>

          <div className="grid-2">
            <div>
              <label style={{ fontSize: '13px', fontWeight: '600', color: '#475569', display: 'block', marginBottom: '6px' }}>
                默认发布通道：
              </label>
              <select
                className="select"
                value={publisherType}
                onChange={e => setPublisherType(e.target.value)}
                style={{ width: '100%' }}
              >
                <option value="pending_approval">主人确认队列 (PendingApproval - 优雅降级/安全待审)</option>
                <option value="official_api">B站官方开放平台 API (OfficialApi - 需要官方 OAuth2 授权)</option>
                <option value="webhook">外部 Webhook 转发 (Webhook - 推送自动化与通知)</option>
                <option value="local_audit">本地合规审计模式 (LocalAudit - 仅本地归档不发外网)</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '13px', fontWeight: '600', color: '#475569', display: 'block', marginBottom: '6px' }}>
                每日评论安全上限：
              </label>
              <input
                type="number"
                min="1"
                max="10"
                className="input"
                value={maxCommentsPerDay}
                onChange={e => setMaxCommentsPerDay(parseInt(e.target.value) || 3)}
              />
            </div>
          </div>

          <div style={{ marginTop: '14px' }}>
            <label style={{ fontSize: '13px', fontWeight: '600', color: '#475569', display: 'block', marginBottom: '6px' }}>
              B站开放平台 OAuth2 授权令牌 (Access Token)：
            </label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                type={showBiliToken ? 'text' : 'password'}
                className="input"
                value={bilibiliToken}
                onChange={e => setBilibiliToken(e.target.value)}
                placeholder={settings?.has_bilibili_token ? `已配置: ${settings.bilibili_token_masked} (输入新Token覆盖)` : '未配置官方 Token（无授权时自动转入主人待审队列）'}
              />
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowBiliToken(!showBiliToken)}
                title="显示/隐藏"
              >
                {showBiliToken ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
              提示：若未配置官方 Token 或平台缺少写权限，大肥鱼会将评论草稿安全转入待审队列，绝不进行非法注入或伪造发布。
            </div>
          </div>

          <div style={{ marginTop: '14px' }}>
            <label style={{ fontSize: '13px', fontWeight: '600', color: '#475569', display: 'block', marginBottom: '6px' }}>
              Webhook 推送目标 URL（选填）：
            </label>
            <input
              type="text"
              className="input"
              value={webhookUrl}
              onChange={e => setWebhookUrl(e.target.value)}
              placeholder="例如: https://open.feishu.cn/open-apis/bot/v2/hook/... 或本地自动化脚本"
            />
          </div>

          <div style={{ marginTop: '14px', background: '#f8fafc', padding: '12px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px', color: '#334155' }}>
              <input
                type="checkbox"
                checked={autoCommentEnabled}
                onChange={e => setAutoCommentEnabled(e.target.checked)}
              />
              <span><b>允许大肥鱼自主提交发布：</b> 开启后，在通过深度理解、独立观点、无重复度与安全审计时，大肥鱼将自动调用选定通道提交发布。</span>
            </label>
          </div>
        </div>

        {/* Section 4: Autonomous Life Scheduler */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', color: '#7c3aed' }}>
            <Clock size={20} />
            <h3 style={{ fontSize: '16px', fontWeight: 'bold' }}>自主探索作息调度（无需每天手动点击）</h3>
          </div>

          <div className="grid-2">
            <div>
              <label style={{ fontSize: '13px', fontWeight: '600', color: '#475569', display: 'block', marginBottom: '6px' }}>
                探索巡检周期（分钟）：
              </label>
              <input
                type="number"
                min="5"
                max="180"
                className="input"
                value={intervalMinutes}
                onChange={e => setIntervalMinutes(parseInt(e.target.value) || 30)}
              />
            </div>

            <div>
              <label style={{ fontSize: '13px', fontWeight: '600', color: '#475569', display: 'block', marginBottom: '6px' }}>
                每日自主探索上限（次数）：
              </label>
              <input
                type="number"
                min="1"
                max="20"
                className="input"
                value={dailyExploreBudget}
                onChange={e => setDailyExploreBudget(parseInt(e.target.value) || 5)}
              />
            </div>
          </div>

          <div className="grid-2" style={{ marginTop: '14px' }}>
            <div>
              <label style={{ fontSize: '13px', fontWeight: '600', color: '#475569', display: 'block', marginBottom: '6px' }}>
                深夜安睡起始时间（小时 0-23）：
              </label>
              <input
                type="number"
                min="0"
                max="23"
                className="input"
                value={quietHoursStart}
                onChange={e => setQuietHoursStart(parseInt(e.target.value) || 23)}
              />
            </div>

            <div>
              <label style={{ fontSize: '13px', fontWeight: '600', color: '#475569', display: 'block', marginBottom: '6px' }}>
                深夜安睡结束时间（小时 0-23）：
              </label>
              <input
                type="number"
                min="0"
                max="23"
                className="input"
                value={quietHoursEnd}
                onChange={e => setQuietHoursEnd(parseInt(e.target.value) || 7)}
              />
            </div>
          </div>

          <div style={{ marginTop: '14px', background: '#f8fafc', padding: '12px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px', color: '#334155' }}>
              <input
                type="checkbox"
                checked={schedulerEnabled}
                onChange={e => setSchedulerEnabled(e.target.checked)}
              />
              <span><b>开启后台自主生活：</b> 小肥鱼会在主人使用电脑期间自主漫游、发现视频、休息安睡，并在桌宠上实时更新动作。</span>
            </label>
          </div>
        </div>

        {/* Section 5: Character Exploration Weights */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', color: '#d97706' }}>
            <SettingsIcon size={20} />
            <h3 style={{ fontSize: '16px', fontWeight: 'bold' }}>角色个性与探索偏好</h3>
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ fontSize: '13px', fontWeight: '600', color: '#475569', display: 'block', marginBottom: '6px' }}>
              桌宠角色名称：
            </label>
            <input
              type="text"
              className="input"
              value={characterName}
              onChange={e => setCharacterName(e.target.value)}
              placeholder="例如: 大肥鱼"
              required
            />
          </div>

          <div className="grid-2">
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '6px' }}>
                <span style={{ fontWeight: '600', color: '#475569' }}>求知探索权重 (Curiosity)：</span>
                <b>{curiosity}</b>
              </div>
              <input
                type="range"
                min="0.1"
                max="1.0"
                step="0.05"
                value={curiosity}
                onChange={e => setCuriosity(parseFloat(e.target.value))}
                style={{ width: '100%' }}
              />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', marginBottom: '6px' }}>
                <span style={{ fontWeight: '600', color: '#475569' }}>新领域探索权重 (Novelty)：</span>
                <b>{novelty}</b>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={novelty}
                onChange={e => setNovelty(parseFloat(e.target.value))}
                style={{ width: '100%' }}
              />
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
          <button type="submit" className="btn btn-primary" style={{ padding: '10px 24px' }} disabled={saving}>
            <Save size={16} /> {saving ? '保存中...' : '保存全部配置'}
          </button>
        </div>
      </form>
    </div>
  );
};
