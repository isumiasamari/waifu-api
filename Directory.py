# -*- coding: utf-8 -*-
import os
import uuid
import json
import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import edge_tts

# ---------------------- 启动日志 ----------------------
print("=" * 50)
print("🚀 启动 Waifu Backend 服务器")
print("=" * 50)

load_dotenv()

APP_API_TOKEN = os.getenv("APP_API_TOKEN", "please-change-me")
API_KEY = os.getenv("API_KEY")
TTS_PROXY_URL = os.getenv("TTS_PROXY_URL", "").strip() or None

print(f"🔐 APP_API_TOKEN: {'已设置' if APP_API_TOKEN != 'please-change-me' else '未设置'}")
print(f"🔐 API_KEY: {'已设置' if API_KEY else '未设置'}")

# ---------------------- 初始化 DeepSeek ----------------------
llm_client = None
if API_KEY:
    try:
        from openai import OpenAI
        llm_client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
        print("✅ DeepSeek 客户端初始化成功")
    except Exception as e:
        print("❌ DeepSeek 客户端初始化失败:", e)

# ---------------------- 基础路径 ----------------------
DATA_DIR = Path(os.getenv("DATA_DIR", "server_data"))
AUDIO_DIR = DATA_DIR / "audio"
STATE_FILE = DATA_DIR / "state.json"
MAX_MEMORY = 30
AUDIO_TTL_SECONDS = 60 * 60

DATA_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

tts_lock = asyncio.Lock()

# ---------------------- FastAPI ----------------------
app = FastAPI(title="Waifu Backend (Edge-TTS + DeepSeek)")
security = HTTPBearer(auto_error=False)

# 在 FastAPI 中保存故事任务，不要用 global
app.state.story_task = None

# ---------------------- 数据模型 ----------------------
class ChatRequest(BaseModel):
    user_id: Optional[str] = "default_user"
    message: str

class ChatResponse(BaseModel):
    reply: str
    tts_url: Optional[str] = None

# ---------------------- 全局状态 ----------------------
state = {
    "character": {"name": "麻毬", "age": 18, "seikaku": "温柔"},
    "memory": [],
    "story_mode": {
        "enabled": False,
        "last_reply": None,
        "last_time": None,
    }
}

if STATE_FILE.exists():
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except:
        print("⚠️ state.json 损坏，重新初始化")

def save_state():
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------------------- 鉴权 ----------------------
async def check_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(401, "Missing auth token")
    if credentials.credentials != APP_API_TOKEN:
        raise HTTPException(401, "Invalid token")
    return True

# ---------------------- 调用 DeepSeek ----------------------
async def call_llm_api(user_message: str, recent_memory: List[str]) -> str:
    if not llm_client:
        return "抱歉，AI 暂不可用。"

    system_prompt = """
设定：你是麻毬。
回复需要超过 100 字，自然、温柔、连贯。
"""

    try:
        resp = llm_client.chat.completions.create(
            model="deepseek-chat",
            max_tokens=500,
            messages=[
                {"role": "system", "content": system_prompt + "\n最近对话：\n" + "\n".join(recent_memory)},
                {"role": "user", "content": user_message},
            ]
        )
        return resp.choices[0].message.content

    except Exception as e:
        print("❌ LLM 调用失败:", e)
        return "抱歉，我有点头晕……先休息一下~"
# ---------------------- Edge-TTS 生成 ----------------------
async def synthesize_tts(
        text: str,
        voice: str = "zh-CN-XiaoyiNeural",
        rate: str = "-5%",
        pitch: str = "+30Hz",
) -> Path:
    async with tts_lock:
        timestamp = int(time.time() * 1000)
        filename = f"reply_{timestamp}.mp3"
        dest = AUDIO_DIR / filename

        # -------- 优先调用 TTS 代理（你的本地电脑）--------
        if TTS_PROXY_URL:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(
                        TTS_PROXY_URL,
                        json={
                            "text": text,
                            "voice": voice,
                            "rate": rate,
                            "pitch": pitch
                        },
                    )

                if resp.status_code != 200:
                    raise RuntimeError(f"TTS 代理失败: {resp.text[:200]}")

                dest.write_bytes(resp.content)

            except Exception as e:
                raise HTTPException(503, f"TTS 代理失败: {e}")

        else:
            # -------- Fallback：云端自己生成（不推荐）--------
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                pitch=pitch,
            )
            await communicate.save(str(dest))

        # meta 信息
        (dest.with_suffix(".mp3.meta")).write_text(
            json.dumps({"created": datetime.utcnow().isoformat()})
        )
        return dest


# ---------------------- 自动讲故事后台任务 ----------------------
async def story_loop():
    """
    自动讲故事循环：
    - 每 1 分钟发一条
    - 使用 story_memory 做上下文
    """
    print("📚【故事模式】后台任务启动")

    while state["story_mode"]["enabled"]:
        try:
            memory = state["story_mode"]["story_memory"][-10:]
            prompt = "续写刚才的故事，继续讲下一段，保持连贯，至少 120 字。"

            reply = await call_llm_api(prompt, memory)

            # 保存进故事 memory
            state["story_mode"]["story_memory"].append({"role": "assistant", "text": reply})
            save_state()

            # 生成 TTS
            await synthesize_tts(
                reply,
                voice="zh-CN-XiaoyiNeural",
                rate="-5%",
                pitch="+30Hz"
            )

            print("📚【故事模式】已生成新的段落")

        except Exception as e:
            print("❌ 故事生成失败：", e)

        await asyncio.sleep(60)   # 每 1 分钟一段

    print("📕【故事模式】后台任务结束")
# ---------------------- API: 普通聊天 ----------------------
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
        req: ChatRequest,
        background_tasks: BackgroundTasks,
        auth: bool = Depends(check_auth)
):
    msg = req.message.strip()

    # ===== 特殊命令 =====
    if msg == "开始":
        state["story_mode"]["enabled"] = True
        save_state()

        if app.state.story_task is None or app.state.story_task.done():
            app.state.story_task = asyncio.create_task(story_loop())

        return ChatResponse(reply="好的主人，我会开始为你连贯地讲故事~", tts_url=None)

    if msg == "停":
        state["story_mode"]["enabled"] = False
        save_state()
        return ChatResponse(reply="已经停下故事了~", tts_url=None)

    if msg == "继续":
        state["story_mode"]["enabled"] = True
        save_state()

        if app.state.story_task is None or app.state.story_task.done():
            app.state.story_task = asyncio.create_task(story_loop())

        return ChatResponse(reply="嗯~我接着讲刚才的故事~", tts_url=None)

    # ===== 普通聊天 =====
    state["memory"].append({"role": "user", "text": msg})
    state["memory"] = state["memory"][-MAX_MEMORY:]
    save_state()

    recent_memory = [f"{m['role']}: {m['text']}" for m in state["memory"][-10:]]
    reply_text = await call_llm_api(msg, recent_memory)

    state["memory"].append({"role": "assistant", "text": reply_text})
    save_state()

    # ---- 后台生成 TTS ----
    async def gen():
        try:
            await synthesize_tts(
                reply_text,
                voice="zh-CN-XiaoyiNeural",
                rate="-5%",
                pitch="+30Hz"
            )
        except Exception as e:
            print("TTS failed:", e)

    background_tasks.add_task(gen)

    return ChatResponse(reply=reply_text, tts_url=None)


# ---------------------- 其他 API ----------------------
@app.post("/tts")
async def tts_endpoint(payload: dict, auth: bool = Depends(check_auth)):
    text = payload.get("text")
    audio_path = await synthesize_tts(text)
    return FileResponse(audio_path, media_type="audio/mpeg", filename=audio_path.name)


@app.get("/state")
def get_state(auth: bool = Depends(check_auth)):
    return JSONResponse(state)


# ---------------------- 启动事件 ----------------------
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Backend Starting...")
    if state["story_mode"]["enabled"]:
        print("📚 检测到故事模式开启，自动恢复任务")
        app.state.story_task = asyncio.create_task(story_loop())
    yield
    print("🛑 Backend Stopping...")

# 重新创建 app（带 lifespan）
app = FastAPI(title="Waifu Backend", lifespan=lifespan)

# 重新注册路由（必须保持）
app.post("/chat", response_model=ChatResponse)(chat_endpoint)
app.post("/tts")(tts_endpoint)
app.get("/state")(get_state)
