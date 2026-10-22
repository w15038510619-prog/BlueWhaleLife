from __future__ import annotations
import json
import re
import time
from typing import Dict, Any, Optional, List
import httpx
from backend.app.config import AppSettings, current_settings
from backend.app.database import log_api_usage, get_daily_api_cost


class LLMAPIError(Exception):
    """Custom exception for LLM API connection, auth, or rate-limiting errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or ""


class LLMClient:
    def __init__(self, settings: Optional[AppSettings] = None):
        self.settings = settings or current_settings

    def _get_headers(self, custom_key: Optional[str] = None) -> Dict[str, str]:
        key = custom_key if custom_key is not None else self.settings.llm_api_key
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return headers

    async def chat_completion(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 1500,
        response_json: bool = False,
        caller: str = "general"
    ) -> str:
        # If in demo mode or no key configured, use intelligent mock
        if self.settings.demo_mode or not self.settings.llm_api_key:
            return self._mock_completion(messages, response_json)

        # Safety Check 1: Emergency stop switch
        if self.settings.emergency_stop:
            raise LLMAPIError("紧急制动已触发：主人开启了紧急停止开关，大肥鱼已暂停所有 AI 自主调用。")

        # Safety Check 2: Daily cost budget guard
        today_cost = get_daily_api_cost()
        if today_cost >= self.settings.daily_cost_budget:
            raise LLMAPIError(
                f"已达到今日 API 费用预算限制 (今日已消耗: ¥{today_cost:.3f} / 预算: ¥{self.settings.daily_cost_budget:.2f})，大肥鱼正在休养生息。"
            )

        base_url = self.settings.llm_base_url.rstrip("/")
        protocol = getattr(self.settings, "llm_protocol", "responses")
        model = self.settings.llm_model

        t_start = time.time()
        try:
            if protocol == "responses":
                content, in_tok, out_tok = await self._call_responses_api(
                    base_url=base_url,
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_json=response_json
                )
            else:
                content, in_tok, out_tok = await self._call_chat_completions_api(
                    base_url=base_url,
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_json=response_json
                )

            latency_ms = int((time.time() - t_start) * 1000)
            log_api_usage(
                model=model,
                endpoint=f"{base_url}/{'responses' if protocol == 'responses' else 'chat/completions'}",
                protocol=protocol,
                input_tokens=in_tok,
                output_tokens=out_tok,
                caller=caller,
                latency_ms=latency_ms,
                status="success"
            )
            return content

        except LLMAPIError as e:
            latency_ms = int((time.time() - t_start) * 1000)
            log_api_usage(
                model=model,
                endpoint=base_url,
                protocol=protocol,
                input_tokens=0,
                output_tokens=0,
                caller=caller,
                latency_ms=latency_ms,
                status="error",
                error_message=f"{e.message} ({e.details})"[:200]
            )
            # CRITICAL REQUIREMENT: In real mode, NEVER silently fall back to fake mock generation!
            raise

        except Exception as e:
            latency_ms = int((time.time() - t_start) * 1000)
            err_msg = f"未知的网络或解析异常: {e}"
            log_api_usage(
                model=model,
                endpoint=base_url,
                protocol=protocol,
                input_tokens=0,
                output_tokens=0,
                caller=caller,
                latency_ms=latency_ms,
                status="error",
                error_message=err_msg[:200]
            )
            raise LLMAPIError(err_msg, details=str(e))

    async def _call_responses_api(
        self,
        base_url: str,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        response_json: bool,
        custom_key: Optional[str] = None
    ) -> tuple[str, int, int]:
        """Call Aixoras /v1/responses endpoint."""
        url = f"{base_url}/responses"
        
        # Split system instructions and user/conversation inputs
        instructions = ""
        user_parts = []
        for m in messages:
            role = m.get("role", "")
            content = m.get("content", "")
            if role == "system":
                instructions += content + "\n"
            else:
                user_parts.append(f"{role.upper()}: {content}")

        input_text = "\n\n".join(user_parts) if user_parts else "你好"

        payload: Dict[str, Any] = {
            "model": model,
            "input": input_text,
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "stream": False
        }
        if instructions.strip():
            payload["instructions"] = instructions.strip()
        if response_json:
            payload["text"] = {"format": {"type": "json_object"}}

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(url, headers=self._get_headers(custom_key), json=payload)
                if res.status_code in (401, 403):
                    try:
                        err_data = res.json()
                        server_msg = err_data.get("error", {}).get("message") or err_data.get("message") or res.text
                    except Exception:
                        server_msg = res.text[:200]
                    raise LLMAPIError(f"API 鉴权/权限失败 ({res.status_code}): {server_msg}", status_code=res.status_code, details=server_msg)
                if res.status_code == 429:
                    raise LLMAPIError("API 速率限制 (429): 当前请求过多或已达平台限流配额", status_code=429)
                if res.status_code == 404:
                    raise LLMAPIError("API 端点未找到 (404): 该服务商可能不支持 /v1/responses 接口，请尝试切换为 Chat Completions 协议", status_code=404)
                if res.status_code >= 500:
                    raise LLMAPIError(f"服务商后端故障 ({res.status_code})", status_code=res.status_code, details=res.text[:200])

                res.raise_for_status()
                data = res.json()

                # Extract content from Aixoras responses schema
                # Structure: data["output"][0]["content"][0]["text"]
                content = ""
                output_list = data.get("output", [])
                if isinstance(output_list, list) and len(output_list) > 0:
                    item = output_list[0]
                    c_list = item.get("content", [])
                    if isinstance(c_list, list) and len(c_list) > 0:
                        content = c_list[0].get("text", "")
                    elif "text" in item:
                        content = item["text"]
                elif "choices" in data:
                    content = data["choices"][0]["message"]["content"]
                elif "text" in data:
                    content = data["text"]

                usage = data.get("usage", {})
                in_tok = usage.get("input_tokens", usage.get("prompt_tokens", 0))
                out_tok = usage.get("output_tokens", usage.get("completion_tokens", 0))

                return content.strip(), in_tok, out_tok

        except httpx.TimeoutException:
            raise LLMAPIError("API 请求超时 (45s): 无法在规定时间内从 Aixoras 获得响应", status_code=408)
        except httpx.ConnectError as e:
            raise LLMAPIError(f"API 网络连接失败: 无法连接至 {base_url}", details=str(e))

    async def _call_chat_completions_api(
        self,
        base_url: str,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        response_json: bool,
        custom_key: Optional[str] = None
    ) -> tuple[str, int, int]:
        """Call standard OpenAI /v1/chat/completions endpoint."""
        url = f"{base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        if response_json:
            payload["response_format"] = {"type": "json_object"}

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(url, headers=self._get_headers(custom_key), json=payload)
                if res.status_code in (401, 403):
                    try:
                        err_data = res.json()
                        server_msg = err_data.get("error", {}).get("message") or err_data.get("message") or res.text
                    except Exception:
                        server_msg = res.text[:200]
                    raise LLMAPIError(f"API 鉴权/权限失败 ({res.status_code}): {server_msg}", status_code=res.status_code, details=server_msg)
                if res.status_code == 429:
                    raise LLMAPIError("API 速率限制 (429): 已触发服务商并发或配额限制", status_code=429)
                if res.status_code == 404:
                    raise LLMAPIError("API 端点未找到 (404): /chat/completions 不存在，请检查 Base URL", status_code=404)
                if res.status_code >= 500:
                    raise LLMAPIError(f"服务商后端故障 ({res.status_code})", status_code=res.status_code, details=res.text[:200])

                res.raise_for_status()
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                in_tok = usage.get("prompt_tokens", 0)
                out_tok = usage.get("completion_tokens", 0)
                return content.strip(), in_tok, out_tok

        except httpx.TimeoutException:
            raise LLMAPIError("API 请求超时 (45s): 无法在规定时间内获得响应", status_code=408)
        except httpx.ConnectError as e:
            raise LLMAPIError(f"API 网络连接失败: 无法连接至 {base_url}", details=str(e))

    async def fetch_models(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> List[str]:
        """Query /v1/models to discover which models this API token actually has access to."""
        test_base_url = (base_url or self.settings.llm_base_url).rstrip("/")
        test_key = api_key if api_key is not None else self.settings.llm_api_key
        url = f"{test_base_url}/models"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url, headers=self._get_headers(test_key))
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("id") for m in data.get("data", []) if m.get("id")]
                    return models
                return []
        except Exception:
            return []

    async def test_connection(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        protocol: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform a real live connection test and return latency, model reply, and usage."""
        test_base_url = (base_url or self.settings.llm_base_url).rstrip("/")
        test_key = api_key if api_key is not None else self.settings.llm_api_key
        test_model = model or self.settings.llm_model
        test_protocol = protocol or getattr(self.settings, "llm_protocol", "responses")

        if not test_key:
            return {
                "success": False,
                "latency_ms": 0,
                "error_message": "测试失败：未提供 API Key，请在输入框填入密钥后测试。",
                "status_code": 400
            }

        messages = [
            {"role": "system", "content": "你是一只叫大肥鱼的AI小鲸鱼助手。"},
            {"role": "user", "content": "请用简短的一句话（20字以内）回复：大肥鱼已连接成功！"}
        ]

        t_start = time.time()
        try:
            if test_protocol == "responses":
                content, in_tok, out_tok = await self._call_responses_api(
                    base_url=test_base_url,
                    model=test_model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=60,
                    response_json=False,
                    custom_key=test_key
                )
            else:
                content, in_tok, out_tok = await self._call_chat_completions_api(
                    base_url=test_base_url,
                    model=test_model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=60,
                    response_json=False,
                    custom_key=test_key
                )

            latency_ms = int((time.time() - t_start) * 1000)
            return {
                "success": True,
                "latency_ms": latency_ms,
                "reply": content,
                "model": test_model,
                "protocol": test_protocol,
                "tokens": {"input": in_tok, "output": out_tok, "total": in_tok + out_tok}
            }
        except LLMAPIError as e:
            latency_ms = int((time.time() - t_start) * 1000)
            return {
                "success": False,
                "latency_ms": latency_ms,
                "error_message": e.message,
                "status_code": e.status_code,
                "details": e.details
            }
        except Exception as e:
            latency_ms = int((time.time() - t_start) * 1000)
            return {
                "success": False,
                "latency_ms": latency_ms,
                "error_message": f"连接错误: {e}",
                "status_code": None,
                "details": str(e)
            }

    def _mock_completion(self, messages: list[dict], response_json: bool) -> str:
        # Extract system and user prompts
        user_content = ""
        system_content = ""
        for m in messages:
            if m.get("role") == "user":
                user_content += m.get("content", "") + " "
            elif m.get("role") == "system":
                system_content += m.get("content", "") + " "

        # Video Analysis Mock Response
        if "视频分析" in system_content or "Video Analysis" in system_content or "summary" in user_content.lower():
            title_match = re.search(r"标题[：:]\s*(.+)", user_content)
            title = title_match.group(1).strip() if title_match else "这个有趣的B站视频"
            
            mock_data = {
                "summary": f"这部作品围绕《{title}》展开，通过详实的演示与直观的案例，深入浅出地剖析了核心原理与背后蕴含的构思逻辑。内容层层递进，既有宏观视角，也有耐人寻味的细节。",
                "learned": f"在观看《{title}》中，我发现了一个之前未曾注意到的视角：很多看似理所当然的技术或自然规律，其实背后都有着精巧的权衡（Trade-off）。尤其是细节处理上的巧思，让我重新审视了相关的常识。",
                "viewpoint": "我觉得UP主最打动我的一点是保持了审慎求证的态度，而不是简单得出绝对化的结论。不过对于文末提到的部分推论，我认为在极端环境或不同基准下可能需要更多证据支持，保留合理的怀疑是很有趣的事。",
                "doubts": "这个结论如果在规模化（Scale-up）或者长时间跨度下，是否会产生意料之外的边际衰减？或者是否存在其他未被讨论的干扰变量？我还想再找一些论文或后续对比视频看看。",
                "worth_commenting": True,
                "comment_draft": f"看完了！特别喜欢视频中间关于细节权衡的那段拆解。以前总觉得这套机制很直观，今天才意识到背后有这么多考量。另外最后提到的那个推论，如果在极端场景下会不会有不同的表现呢？感谢UP主带来这么扎实的分享~ (大肥鱼路过留念)",
                "new_knowledge_topic": f"{title[:12]}核心机制",
                "new_knowledge_content": f"关于《{title}》中展现的关键论点与验证逻辑。提示我们在面对复杂系统时，必须关注边界条件与初始设定。",
                "mood": "求知欲旺盛"
            }
            return json.dumps(mock_data, ensure_ascii=False)

        # Daily Reflection Mock Response
        if "日常反思" in system_content or "Reflection" in system_content:
            mock_reflection = {
                "discoveries_summary": "今天探索了几个充满创意和硬核知识的领域，了解到了大自然与工程设计的奇妙共性，脑海中积累了不少新素材。",
                "viewpoint_shifts": "原先我觉得复杂问题一定要用复杂的系统去解决，但今天看到的一些极简设计让我意识到，有时候约束反而是创新的最好催化剂。",
                "new_interests": ["深海仿生工程", "极简算法美学", "科幻动画概念设计"],
                "pending_doubts": "关于高阶系统在极端扰动下的鲁棒性，现有模型给出的结论真的足够稳健吗？需要继续留意相关实证。",
                "growth_score": 15,
                "mood": "充实且若有所思"
            }
            return json.dumps(mock_reflection, ensure_ascii=False)

        # Interactive Chat Mock Response
        if "【大肥鱼角色设定】" in system_content or "chat" in system_content.lower() or len(user_content) < 200:
            user_msg = user_content.strip()
            if "你好" in user_msg or "嗨" in user_msg:
                return "咕噜噜~ 嗨！主人！今天鱼缸里的水温刚刚好，我正在好奇地四处巡视呢。你想聊聊什么，还是让我出去看看有什么新视频？"
            elif "你在干嘛" in user_msg or "忙什么" in user_msg:
                return "我正在整理刚才在记忆里记下的小笔记呢！还顺便吐了几个透明的泡泡。你有什么想探讨的问题吗？"
            elif "喜欢" in user_msg:
                return "我喜欢深海生物、硬核小实验、治愈系独立游戏，还有开源社区里那些天马行空的点子！对了，我也挺喜欢跟你聊天的，因为你不会给我硬塞任务~"
            elif "不知道" in user_msg or "懂吗" in user_msg:
                return "这个领域我目前掌握的记忆还不多，我不能假装很懂。不过只要你告诉我，或者我回头找到相关视频，我很乐意学习它！"
            else:
                return f"咕噜~ 听到你说的“{user_msg[:30]}”，我脑海里冒出了好多联想。虽然我只是一只生活在电脑里的小肥鱼，但每次和你交流，我的记忆库都会悄悄丰富一点点！"

        if response_json:
            return "{}"
        return "咕噜噜~ 大肥鱼正在认真思考中！"
