import os
import asyncio
import tempfile
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import edge_tts

app = FastAPI(title="Local TTS Proxy")

class TtsProxyRequest(BaseModel):
    text: str
    voice: str = "zh-CN-XiaoyiNeural"
    rate: str = "-5%"
    pitch: str = "+30Hz"

tts_lock = asyncio.Lock()

@app.post("/tts_proxy")
async def tts_proxy(req: TtsProxyRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(400, "text 不能为空")

    async with tts_lock:
        try:
            # 临时 mp3 文件
            fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)

            # 生成 TTS（同步写入）
            communicate = edge_tts.Communicate(
                text=req.text,
                voice=req.voice,
                rate=req.rate,
                pitch=req.pitch
            )
            await communicate.save(tmp_path)

            # 返回完整 MP3 文件，不流式传输
            return FileResponse(
                tmp_path,
                media_type="audio/mpeg",
                filename="tts.mp3",
                background=None  # FastAPI 4.0 做兼容用
            )

        except Exception as e:
            raise HTTPException(500, f"TTS 失败: {e}")
        finally:
            # 删除临时文件
            try:
                os.remove(tmp_path)
            except:
                pass
