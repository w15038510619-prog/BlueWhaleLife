from __future__ import annotations
import json
import re
from typing import Dict, Any, Optional
import httpx
from backend.app.config import AppSettings, current_settings


class LLMClient:
    def __init__(self, settings: Optional[AppSettings] = None):
        self.settings = settings or current_settings

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.settings.llm_api_key:
            headers["Authorization"] = f"Bearer {self.settings.llm_api_key}"
        return headers

    async def chat_completion(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 1500,
        response_json: bool = False
    ) -> str:
        # If in demo mode or no key is provided, return intelligent mock
        if self.settings.demo_mode or not self.settings.llm_api_key:
            return self._mock_completion(messages, response_json)

        base_url = self.settings.llm_base_url.rstrip("/")
        url = f"{base_url}/chat/completions"
        payload = {
            "model": self.settings.llm_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_json:
            payload["response_format"] = {"type": "json_object"}

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(url, headers=self._get_headers(), json=payload)
                res.raise_for_status()
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                return content
        except Exception as e:
            print(f"[LLMClient] API error: {e}. Falling back to demo mock generation.")
            return self._mock_completion(messages, response_json)

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
            # Parse video title if possible
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
