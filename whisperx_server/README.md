# WhisperX STT Server

WAV 파일을 받아 텍스트로 변환하는 FastAPI 서버입니다.

---

## 사전 준비

### 1. ffmpeg 설치 (필수)

WhisperX가 오디오 처리에 ffmpeg를 사용합니다. **없으면 서버가 실행되지 않습니다.**

PowerShell(비관리자)에서 실행:
```powershell
winget install ffmpeg
```

설치 후 **터미널 재시작** 필요. 확인:
```bash
ffmpeg -version
```

### 2. Python 가상환경 (선택)

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. 나머지 패키지 설치

```bash
pip install -r requirements.txt
```

### 4. PyTorch 설치 (CUDA 버전에 맞게)

**반드시 requirements.txt를 설치한 뒤에 Torch를 설치해야 합니다!**

먼저 본인 CUDA 버전을 확인합니다:
```bash
nvidia-smi
```

설치된 Pytorch 및 관련 라이브러리를 제거합니다.
`pip uninstall -y torch torchaudio torchvision`

- CUDA 추천 버전: 13.0
- Pytorch 추천 버전: 12.1
- 해당 조건에서는 CUDA와 Pytorch 버전이 상이해도 작동합니다.

| CUDA 버전 | 설치 명령어 |
|---|---|
| 12.8 | `pip install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/cu128` |
| 12.1 | `pip install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/cu121` |
| 11.8 | `pip install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/cu118` |

> CUDA가 없는 경우: `pip install torch torchaudio` (CPU 모드로 실행, 속도 매우 느림)

---

## 실행

```bash
python main.py
```

서버가 뜨면 아래 로그가 출력됩니다:

```
[startup] 모델 로딩: large-v2 / device=cuda / compute=float16
[startup] 모델 로딩 완료
INFO:     Uvicorn running on http://127.0.0.1:8000
```

> 최초 실행 시 large-v2 모델(약 3GB)을 자동 다운로드합니다. 시간이 걸릴 수 있습니다.

---

## API 사용법

### 서버 상태 확인

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "model": "large-v2",
  "device": "cuda",
  "loaded": true
}
```

### 음성 변환

```bash
curl -X POST http://localhost:8000/transcribe \
  -F "file=@sample.wav"
```

**응답 예시:**
```json
{
  "text": "안녕하세요 반갑습니다",
  "segments": [
    { "start": 0.0, "end": 2.3, "text": "안녕하세요 반갑습니다" }
  ],
  "language": "ko",
  "processing_time_sec": 1.234,
  "timestamp_kst": "2026-02-18T15:30:00.000000+09:00",
  "model": "large-v2",
  "device": "cuda"
}
```

### 언어 변경 (선택)

기본값은 한국어(`ko`)입니다. 다른 언어를 사용하려면 쿼리 파라미터로 전달합니다:

```bash
curl -X POST "http://localhost:8000/transcribe?language=en" \
  -F "file=@sample.wav"
```

---

## 환경변수

기본값을 바꾸고 싶을 때 사용합니다.

| 변수명 | 기본값 | 설명 |
|-------|-------|-----|
| `MODEL_SIZE` | `large-v2` | WhisperX 모델 크기 (`tiny`, `base`, `small`, `medium`, `large-v2`) |
| `LANGUAGE` | `ko` | 기본 언어 코드 |

```bash
# 예시: 모델을 medium으로 변경
MODEL_SIZE=medium python main.py
```

---

## 기존 백엔드에서 호출하는 방법

```python
import requests

with open("audio.wav", "rb") as f:
    response = requests.post(
        "http://<노트북_IP>:8000/transcribe",
        files={"file": ("audio.wav", f, "audio/wav")},
    )

result = response.json()
print(result["text"])
```

> `<노트북_IP>`는 서버를 실행하는 노트북의 로컬 IP입니다. (`ipconfig`로 확인)
