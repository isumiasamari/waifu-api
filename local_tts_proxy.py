import os
import asyncio
import tempfile

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import edge_tts

app = FastAPI(title="Local TTS Proxy (edge_tts)")

class TtsProxyRequest(BaseModel):
    text: str
    voice: str = "zh-CN-XiaoyiNeural"
    rate: str = "-5%"
    pitch: str = "+30Hz"

tts_lock = asyncio.Lock()

@app.post("/tts_proxy")
async def tts_proxy(req: TtsProxyRequest):
    """
    本地 TTS 代理：接收文字，调用 edge_tts，返回 MP3 二进制流
    """
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text 不能为空")

    async with tts_lock:
        tmp_file = None
        try:
            # 1. 临时文件
            fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)   # 关掉底层文件描述符
            tmp_file = tmp_path

            # 2. 调用 edge_tts 生成语音
            communicate = edge_tts.Communicate(
                text=text,
                voice=req.voice,
                rate=req.rate,
                pitch=req.pitch
            )
            await communicate.save(tmp_path)

            # 3. 以流的方式把 mp3 内容返回，并在读完后删除临时文件
            async def iterfile():
                try:
                    with open(tmp_path, "rb") as f:
                        while True:
                            chunk = f.read(8192)
                            if not chunk:
                                break
                            yield chunk
                finally:
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass

            return StreamingResponse(iterfile(), media_type="audio/mpeg")

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"TTS 失败: {e}")
