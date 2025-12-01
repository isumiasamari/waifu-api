# -*- coding: utf-8 -*-
import os
import uuid
import json
import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import edge_tts
from edge_tts.exceptions import NoAudioReceived
from fastapi import HTTPException

# ---------------------- 配置和调试信息 ----------------------
print("=" * 50)
print("🚀 启动 Waifu Backend 服务器")
print("=" * 50)

# 加载环境变量
load_dotenv()

# 获取 API 密钥
APP_API_TOKEN = os.getenv("APP_API_TOKEN", "please-change-me")
API_KEY = os.getenv("API_KEY")

print(f"🔐 APP_API_TOKEN: {'已设置' if APP_API_TOKEN and APP_API_TOKEN != 'please-change-me' else '未设置'}")
print(f"🔐 API_KEY: {'已设置' if API_KEY else '未设置'}")

# 只在 API_KEY 存在时初始化 OpenAI 客户端
llm_client = None
if API_KEY:
    try:
        from openai import OpenAI

        llm_client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
        print("✅ DeepSeek 客户端初始化成功")
    except Exception as e:
        print(f"❌ DeepSeek 客户端初始化失败: {e}")
        llm_client = None
else:
    print("⚠️  API_KEY 未设置，AI 对话功能将不可用")

# 其他配置...
DATA_DIR = Path(os.getenv("DATA_DIR", "server_data"))
AUDIO_DIR = DATA_DIR / "audio"
STATE_FILE = DATA_DIR / "state.json"
MAX_MEMORY = 30
AUDIO_TTL_SECONDS = 60 * 60

DATA_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

tts_lock = asyncio.Lock()

print("=" * 50)

# ---------------------- FastAPI ----------------------
app = FastAPI(title="Waifu Backend (Edge-TTS + DeepSeek)")
security = HTTPBearer(auto_error=False)


# ---------------------- 数据模型 ----------------------
class ChatRequest(BaseModel):
    user_id: Optional[str] = "default_user"
    message: str


class ChatResponse(BaseModel):
    reply: str
    tts_url: Optional[str] = None


# ---------------------- 内存状态 ----------------------
state = {
    "character": {"name": "麻毬", "age": 18, "seikaku": "温柔"},
    "memory": [],
}

if STATE_FILE.exists():
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        print("state file corrupted, starting fresh")


def save_state():
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------- 鉴权 ----------------------
async def check_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not APP_API_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: APP_API_TOKEN not set"
        )

    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Missing auth token. Please provide Authorization header with Bearer token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if credentials.credentials != APP_API_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    return True


# ---------------------- 调用 DeepSeek ----------------------
async def call_llm_api(user_message: str, recent_memory: List[str]) -> str:
    # 检查客户端是否可用
    if not llm_client:
        print("❌ LLM 客户端未初始化")
        return "抱歉，AI 服务暂时不可用。请检查 API 密钥配置。"

    system_prompt = f"你扮演 {state['character']['name']}，年龄 {state['character']['age']}，用温柔的口吻回复。"

    try:
        print(f"🔍 准备调用 DeepSeek API，用户消息长度: {len(user_message)}")
        print(f"📝 系统提示: {system_prompt[:100]}...")  # 只打印前100字符

        response = llm_client.chat.completions.create(
            model="deepseek-chat",
            max_tokens=500,
            messages=[
                {"role": "system", "content": system_prompt + "\n最近对话：\n" + "\n".join(recent_memory)},
                {"role": "user", "content": user_message}
            ]
        )

        print(f"✅ API 调用成功，回复长度: {len(response.choices[0].message.content)}")
        return response.choices[0].message.content

    except Exception as e:
        print(f"❌ AI 调用失败: {e}")
        print(f"🔍 异常类型: {type(e)}")
        import traceback
        print(f"📋 完整堆栈: {traceback.format_exc()}")
        return "抱歉，AI 服务暂时出了点问题，请稍后再试。"

# ---------------------- Edge-TTS 生成 ----------------------
async def synthesize_tts(text: str, voice: str = "zh-CN-XiaoyouNeural") -> Path:
    async with tts_lock:
        # 确保目录存在（Render 这种云环境默认是没有这个目录的）
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)

        timestamp = int(time.time() * 1000)
        filename = f"reply_{timestamp}.mp3"
        dest = AUDIO_DIR / filename

        communicate = edge_tts.Communicate(text=text, voice=voice)

        try:
            # 这里如果云端拿不到音频，就会抛 NoAudioReceived
            await communicate.save(str(dest))
        except NoAudioReceived:
            # 不要让整个接口 500，改成 503 + 友好提示
            raise HTTPException(
                status_code=503,
                detail="TTS 服务没有返回音频（云端可能被限制了），先用文字吧。"
            )
        except Exception as e:
            # 兜底异常，方便以后排查
            raise HTTPException(
                status_code=500,
                detail=f"TTS 生成失败: {e}"
            )

        # 只有成功生成音频时才写 meta
        (dest.with_suffix(".mp3.meta")).write_text(
            json.dumps({"created": datetime.utcnow().isoformat()})
        )

        return dest


# ---------------------- 清理音频 ----------------------
def cleanup_expired_audio():
    now = datetime.utcnow()
    for f in AUDIO_DIR.glob("reply_*.mp3"):
        meta = f.with_suffix(".mp3.meta")
        try:
            if meta.exists():
                info = json.loads(meta.read_text(encoding="utf-8"))
                created = datetime.fromisoformat(info.get("created"))
                if (now - created).total_seconds() > AUDIO_TTL_SECONDS:
                    f.unlink(missing_ok=True)
                    meta.unlink(missing_ok=True)
            else:
                f.unlink(missing_ok=True)
        except Exception:
            pass


# ---------------------- API 路由 ----------------------
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
        req: ChatRequest,
        background_tasks: BackgroundTasks,
        auth: bool = Depends(check_auth)
):
    # 更新内存
    state["memory"].append({"role": "user", "text": req.message, "ts": datetime.utcnow().isoformat()})
    state["memory"] = state["memory"][-MAX_MEMORY:]
    save_state()

    recent_memory = [f"{m['role']}: {m['text']}" for m in state["memory"][-10:]]
    reply_text = await call_llm_api(req.message, recent_memory)
    state["memory"].append({"role": "assistant", "text": reply_text, "ts": datetime.utcnow().isoformat()})
    save_state()

    # 后台生成 TTS
    async def gen_tts():
        try:
            await synthesize_tts(reply_text)
        except Exception as e:
            print("TTS failed:", e)

    background_tasks.add_task(gen_tts)
    cleanup_expired_audio()
    return ChatResponse(reply=reply_text, tts_url=None)


@app.post("/tts")
async def tts_endpoint(payload: dict, auth: bool = Depends(check_auth)):
    text = payload.get("text")
    if not text:
        raise HTTPException(status_code=400, detail="text required")
    audio_path = await synthesize_tts(text)
    return FileResponse(audio_path, media_type="audio/mpeg", filename=audio_path.name)


@app.get("/state")
def get_state(auth: bool = Depends(check_auth)):
    return JSONResponse(state)


@app.post("/state/save")
def save_state_endpoint(auth: bool = Depends(check_auth)):
    save_state()
    return {"ok": True}


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "auth_configured": bool(APP_API_TOKEN and APP_API_TOKEN != "please-change-me"),
        "ai_configured": bool(API_KEY)
    }


# ---------------------- 启动事件 ----------------------
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Waifu Backend 启动中...")
    print(f"🔐 APP_API_TOKEN: {'已配置' if APP_API_TOKEN and APP_API_TOKEN != 'please-change-me' else '未配置'}")
    print(f"🤖 AI 服务: {'可用' if llm_client else '不可用'}")
    cleanup_expired_audio()

    yield

    print("🛑 Waifu Backend 关闭中...")


# 重新创建 app 以使用 lifespan
app = FastAPI(
    title="Waifu Backend (Edge-TTS + DeepSeek)",
    lifespan=lifespan
)

# 重新注册路由
app.post("/chat", response_model=ChatResponse)(chat_endpoint)
app.post("/tts")(tts_endpoint)
app.get("/state")(get_state)
app.post("/state/save")(save_state_endpoint)
app.get("/health")(health_check)