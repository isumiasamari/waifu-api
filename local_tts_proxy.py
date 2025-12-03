import os
import asyncio
import tempfile
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import edge_tts

app = FastAPI(title="Local TTS Proxy (edge_tts, stable async version)")

# 单任务队列，避免 edge-tts 并发导致崩溃
tts_queue = asyncio.Lock()

# 超时时间（避免某条卡死）
TTS_TIMEOUT = 12   # 秒


class TtsProxyRequest(BaseModel):
    text: str
    voice: str = "zh-CN-XiaoyiNeural"
    rate: str = "-5%"; pitch: str = "+30Hz"


async def run_tts(text, voice, rate, pitch, path):
    """真正执行 TTS 的子任务（支持超时）"""
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(path)


@app.post("/tts_proxy")
async def tts_proxy(req: TtsProxyRequest):

    text = req.text.strip()
    if not text:
        raise HTTPException(400, "text 不能为空")

    # 拦截过长文本（edge_tts 可能会卡）
    if len(text) > 300:
        raise HTTPException(400, "文本过长，可能导致 TTS 卡死，请缩短。")

    async with tts_queue:  # 队列锁，确保顺序处理，避免错误
        tmp_path = None
        try:
            # 创建临时文件
            fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)

            # 加入超时保护 —— 如果 edge-tts 卡住，会抛 TimeoutError，不影响下一条语音
            try:
                await asyncio.wait_for(
                    run_tts(text, req.voice, req.rate, req.pitch, tmp_path),
                    timeout=TTS_TIMEOUT
                )
            except asyncio.TimeoutError:
                raise HTTPException(500, "TTS 超时（edge-tts 卡住），已自动跳过。")

            # 流式读取 (播放完删除)
            async def stream():
                try:
                    with open(tmp_path, "rb") as f:
                        while chunk := f.read(8192):
                            yield chunk
                finally:
                    try: os.remove(tmp_path)
                    except: pass

            return StreamingResponse(stream(), media_type="audio/mpeg")

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"TTS 失败: {e}")
