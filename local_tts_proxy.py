import os
import asyncio
import tempfile
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
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
        tmp_path = None
        try:
            # 创建临时 mp3 文件
            fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)

            # TTS 生成
            communicate = edge_tts.Communicate(
                text=req.text,
                voice=req.voice,
                rate=req.rate,
                pitch=req.pitch
            )
            await communicate.save(tmp_path)

            # 读取二进制
            with open(tmp_path, "rb") as f:
                data = f.read()

            # ⭐ 返回二进制，而不是 FileResponse
            return Response(
                content=data,
                media_type="audio/mpeg"
            )

        except Exception as e:
            raise HTTPException(500, f"TTS 失败: {e}")

        finally:
            # 安全删除文件（如果存在）
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except:
                    pass
