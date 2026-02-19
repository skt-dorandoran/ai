import os
import time
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

# winget으로 설치된 ffmpeg PATH 자동 등록 (Windows)
_winget_links = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Links")
if os.path.isdir(_winget_links):
    os.environ["PATH"] = _winget_links + os.pathsep + os.environ.get("PATH", "")

import torch
import whisperx
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

# ── 설정 ─────────────────────────────────────────────────────────────────────
MODEL_SIZE   = os.getenv("MODEL_SIZE", "large-v2")
LANGUAGE     = os.getenv("LANGUAGE", "ko")
DEVICE       = "cuda" if torch.cuda.is_available() else "cpu"
COMPUTE_TYPE = "float16" if DEVICE == "cuda" else "int8"
KST          = ZoneInfo("Asia/Seoul")

# ── 앱 ───────────────────────────────────────────────────────────────────────
model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    print(f"[startup] 모델 로딩: {MODEL_SIZE} / device={DEVICE} / compute={COMPUTE_TYPE}")
    model = whisperx.load_model(
        MODEL_SIZE,
        DEVICE,
        compute_type=COMPUTE_TYPE,
        language=LANGUAGE,
    )
    print("[startup] 모델 로딩 완료")
    yield


app = FastAPI(title="WhisperX STT Server", version="1.0.0", lifespan=lifespan)


# ── 엔드포인트 ────────────────────────────────────────────────────────────────
@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(..., description="변환할 WAV 파일"),
    language: str = LANGUAGE,
):
    """
    WAV 파일을 받아 텍스트로 변환합니다.

    - **file**: WAV 형식 오디오 파일
    - **language**: 언어 코드 (기본값: ko). 쿼리 파라미터로 덮어쓸 수 있음.
    """
    if model is None:
        raise HTTPException(status_code=503, detail="모델이 아직 로딩 중입니다. 잠시 후 재시도해 주세요.")

    if not file.filename.lower().endswith(".wav"):
        raise HTTPException(status_code=400, detail="WAV 파일만 지원합니다.")

    start_time = time.perf_counter()

    # 임시 파일에 저장
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        audio = whisperx.load_audio(tmp_path)
        result = model.transcribe(audio, language=language)
    finally:
        os.unlink(tmp_path)

    segments = result.get("segments", [])
    full_text = " ".join(seg["text"].strip() for seg in segments)
    elapsed   = round(time.perf_counter() - start_time, 3)

    return JSONResponse({
        "text":                full_text,
        "segments":            segments,
        "language":            result.get("language", language),
        "processing_time_sec": elapsed,
        "timestamp_kst":       datetime.now(KST).isoformat(),
        "model":               MODEL_SIZE,
        "device":              DEVICE,
    })


@app.get("/health")
async def health():
    return {
        "status":  "ok",
        "model":   MODEL_SIZE,
        "device":  DEVICE,
        "loaded":  model is not None,
    }


# ── 실행 ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
