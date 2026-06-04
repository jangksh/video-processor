# 🎬 시네마틱 영상 비율 변환기

유튜브 쇼츠(9:16), 롱폼(16:9), 인스타그램(1:1, 4:5) 등 원하는 비율로 영상을 빠르게 변환하는 도구입니다.

## 기능

- **비율 변환**: 9:16 / 16:9 / 1:1 / 4:5 지원
- **세 가지 변환 방식**
  - 블러 배경 — 원본을 흐리게 확대해 배경으로 사용 (가장 자연스러움)
  - 스마트 크롭 — 중앙/좌/우 기준으로 잘라냄
  - 레터박스 — 원하는 색상의 여백으로 채움
- **트리밍** — 시작·종료 시간 지정
- **볼륨 조절** — 음소거 / 50% / 100% / 150% / 200%
- **자동 변환 모드** (`auto_converter.py`) — `input_videos/` 폴더에 파일을 넣으면 자동 변환

## 실행 방법

### 사전 준비

**FFmpeg**가 시스템에 설치되어 있어야 합니다.

- macOS: `brew install ffmpeg`
- Ubuntu: `sudo apt install ffmpeg`
- Windows: [ffmpeg.org](https://ffmpeg.org/download.html) 에서 다운로드 후 PATH 등록

### 패키지 설치

```bash
pip install -r requirements.txt
```

### 웹 UI 실행 (`app.py`)

```bash
python app.py
```

브라우저에서 `http://127.0.0.1:7860` 으로 접속합니다.

### 자동 변환 모드 (`auto_converter.py`)

```bash
python auto_converter.py
```

`input_videos/` 폴더에 영상 파일을 넣으면 자동으로 감지해 변환 후 `output_videos/`에 저장합니다. 변환 완료된 원본은 `input_videos/done/`으로 이동됩니다.

지원 포맷: `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`, `.m4v`

## 파일 구조

```
.
├── app.py               # Gradio 웹 UI (메인)
├── auto_converter.py    # 폴더 감시 자동 변환기
├── video_converter.py   # 초기 프로토타입
├── requirements.txt
├── input_videos/        # 자동 변환 입력 폴더
└── output_videos/       # 변환 결과 저장 폴더
```

## 기술 스택

- [Gradio](https://gradio.app/) — 웹 UI
- [ffmpeg-python](https://github.com/kkroening/ffmpeg-python) — 영상 처리
- [watchdog](https://github.com/gorakhargosh/watchdog) — 폴더 감시 (자동 변환 모드)
