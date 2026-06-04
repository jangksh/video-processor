import gradio as gr
import ffmpeg
import os
import tempfile
from pathlib import Path

def get_video_metadata(video_path):
    if not video_path:
        return 0.0, "📥 영상을 업로드하면 비디오 상세 정보가 여기에 표시됩니다."
    try:
        probe = ffmpeg.probe(video_path)
        video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
        if not video_stream:
            return 0.0, "⚠️ 비디오 트랙을 찾을 수 없습니다."
        duration = float(video_stream.get('duration') or probe['format']['duration'])
        w = video_stream.get('width', 0)
        h = video_stream.get('height', 0)
        fps_str = video_stream.get('r_frame_rate', '0/1')
        num, den = map(int, fps_str.split('/'))
        fps = round(num / den, 2) if den else 0
        info = (
            f"📊 **원본 비디오 정보**\n"
            f"- **해상도**: {w}x{h}\n"
            f"- **길이**: {duration:.2f}초\n"
            f"- **프레임레이트**: {fps} FPS"
        )
        return duration, info
    except Exception as e:
        return 0.0, f"⚠️ 메타데이터 읽기 오류: {str(e)}"

def has_audio_stream(video_path):
    try:
        probe = ffmpeg.probe(video_path)
        return any(s['codec_type'] == 'audio' for s in probe['streams'])
    except Exception:
        return False

def convert_video(input_video, target_ratio, method, crop_align, bg_color, blur_intensity, trim_start, trim_end, volume_level, progress=gr.Progress()):
    if input_video is None:
        return None, "❌ 영상을 업로드해주세요!"

    progress(0.0, desc="🚀 변환 준비 중...")

    try:
        if target_ratio == "9:16 (쇼츠용 세로)":
            target_w, target_h = 720, 1280
        elif target_ratio == "16:9 (롱폼용 가로)":
            target_w, target_h = 1280, 720
        elif target_ratio == "1:1 (정사각형)":
            target_w, target_h = 1080, 1080
        else:  # 4:5
            target_w, target_h = 864, 1080

        ratio_str = target_ratio.split(" ")[0].replace(":", "x")
        output_path = str(Path(tempfile.gettempdir()) / f"converted_{ratio_str}_{os.urandom(4).hex()}.mp4")

        progress(0.15, desc="🔍 비디오 분석 중...")
        has_audio = has_audio_stream(input_video)

        progress(0.3, desc="⚙️ FFmpeg 필터 구성 중...")

        input_opts = {}
        if trim_start > 0:
            input_opts['ss'] = trim_start

        input_stream = ffmpeg.input(input_video, **input_opts)

        if method == "블러 배경 (가장 예쁨)":
            bg = (
                input_stream.video
                .filter('scale', target_w, target_h, force_original_aspect_ratio='increase')
                .filter('crop', target_w, target_h)
                .filter('boxblur', luma_radius=int(blur_intensity), luma_power=3)
            )
            fg = input_stream.video.filter('scale', target_w, target_h, force_original_aspect_ratio='decrease')
            video_stream = ffmpeg.overlay(bg, fg, x='(W-w)/2', y='(H-h)/2')

        elif method == "스마트 크롭 (피사체 유지)":
            stream = input_stream.video.filter('scale', target_w, target_h, force_original_aspect_ratio='increase')
            if crop_align == "왼쪽 / 위 (Left/Top)":
                x_expr, y_expr = "0", "0"
            elif crop_align == "오른쪽 / 아래 (Right/Bottom)":
                x_expr, y_expr = "iw-ow", "ih-oh"
            else:
                x_expr, y_expr = "(iw-ow)/2", "(ih-oh)/2"
            video_stream = stream.filter('crop', target_w, target_h, x=x_expr, y=y_expr)

        else:  # 레터박스
            stream = input_stream.video.filter('scale', target_w, target_h, force_original_aspect_ratio='decrease')
            video_stream = stream.filter('pad', target_w, target_h, '(ow-iw)/2', '(oh-ih)/2', color=bg_color)

        audio_stream = None
        if has_audio and volume_level != "음소거 (Mute)":
            audio_stream = input_stream.audio
            if volume_level == "50% (줄임)":
                audio_stream = audio_stream.filter('volume', 0.5)
            elif volume_level == "150% (키움)":
                audio_stream = audio_stream.filter('volume', 1.5)
            elif volume_level == "200% (두 배)":
                audio_stream = audio_stream.filter('volume', 2.0)

        output_opts = {'vcodec': 'libx264', 'preset': 'veryfast', 'crf': 23}
        if trim_end > trim_start:
            output_opts['t'] = trim_end - trim_start

        progress(0.5, desc="🎬 인코딩 진행 중...")

        if audio_stream is not None:
            output_opts['acodec'] = 'aac'
            cmd = ffmpeg.output(video_stream, audio_stream, output_path, **output_opts)
        else:
            cmd = ffmpeg.output(video_stream, output_path, **output_opts)

        cmd.run(overwrite_output=True)
        progress(1.0, desc="✨ 완료!")
        return output_path, "✅ 변환 완료! 아래 영상을 재생하거나 다운로드하세요."

    except ffmpeg.Error as e:
        stderr_msg = e.stderr.decode('utf-8') if e.stderr else "알 수 없는 FFmpeg 오류"
        return None, f"❌ FFmpeg 오류: {stderr_msg[:500]}"
    except Exception as e:
        return None, f"❌ 오류: {str(e)}"

def handle_video_upload(video_path):
    if not video_path:
        return (
            gr.Slider(value=0.0, minimum=0.0, maximum=100.0, interactive=False, label="시작 시간 (초)"),
            gr.Slider(value=0.0, minimum=0.0, maximum=100.0, interactive=False, label="종료 시간 (초)"),
            gr.Markdown("📥 영상을 업로드하면 비디오 상세 정보가 여기에 표시됩니다.")
        )
    duration, info = get_video_metadata(video_path)
    if duration > 0:
        return (
            gr.Slider(value=0.0, minimum=0.0, maximum=duration, step=0.1, interactive=True, label=f"시작 시간 (초) — 최대 {duration:.1f}초"),
            gr.Slider(value=duration, minimum=0.0, maximum=duration, step=0.1, interactive=True, label=f"종료 시간 (초) — 최대 {duration:.1f}초"),
            gr.Markdown(info)
        )
    else:
        return (
            gr.Slider(value=0.0, minimum=0.0, maximum=60.0, step=0.1, interactive=True, label="시작 시간 (초)"),
            gr.Slider(value=10.0, minimum=0.0, maximum=60.0, step=0.1, interactive=True, label="종료 시간 (초)"),
            gr.Markdown(info)
        )

def update_method_visibility(method_val):
    crop_vis = (method_val == "스마트 크롭 (피사체 유지)")
    color_vis = (method_val == "레터박스 (여백 채우기)")
    blur_vis  = (method_val == "블러 배경 (가장 예쁨)")
    return (
        gr.Radio(visible=crop_vis),
        gr.ColorPicker(visible=color_vis),
        gr.Slider(visible=blur_vis)
    )


with gr.Blocks(title="시네마틱 영상 비율 변환기") as demo:

    gr.Markdown("# 🎬 시네마틱 영상 비율 변환기\n숏폼(9:16), 롱폼(16:9), 정사각형(1:1) 등으로 빠르게 변환합니다.")

    with gr.Row(equal_height=False):
        with gr.Column(scale=6):
            gr.Markdown("### 📤 1단계: 원본 동영상 업로드")
            input_video = gr.Video(label="원본 영상", height=320)

            with gr.Accordion("📐 2단계: 비율 및 채우기 방식 설정", open=True):
                target_ratio = gr.Radio(
                    ["9:16 (쇼츠용 세로)", "16:9 (롱폼용 가로)", "1:1 (정사각형)", "4:5 (인스타 세로)"],
                    value="9:16 (쇼츠용 세로)",
                    label="타겟 비율"
                )
                method = gr.Radio(
                    ["블러 배경 (가장 예쁨)", "스마트 크롭 (피사체 유지)", "레터박스 (여백 채우기)"],
                    value="블러 배경 (가장 예쁨)",
                    label="변환 방식"
                )
                crop_align = gr.Radio(
                    ["가운데 (Center)", "왼쪽 / 위 (Left/Top)", "오른쪽 / 아래 (Right/Bottom)"],
                    value="가운데 (Center)",
                    label="크롭 기준 정렬",
                    visible=False
                )
                bg_color = gr.ColorPicker(value="#000000", label="여백 배경 색상", visible=False)
                blur_intensity = gr.Slider(minimum=10, maximum=100, value=40, step=5, label="배경 블러 강도", visible=True)

            with gr.Accordion("✂️ 3단계: 트리밍 & 볼륨 세부 설정", open=False):
                with gr.Row():
                    trim_start = gr.Slider(minimum=0.0, maximum=100.0, value=0.0, step=0.1, interactive=False, label="시작 시간 (초)")
                    trim_end   = gr.Slider(minimum=0.0, maximum=100.0, value=0.0, step=0.1, interactive=False, label="종료 시간 (초)")
                volume_level = gr.Radio(
                    ["100% (기본값)", "음소거 (Mute)", "50% (줄임)", "150% (키움)", "200% (두 배)"],
                    value="100% (기본값)",
                    label="출력 비디오 볼륨"
                )

            convert_btn = gr.Button("🚀 비디오 변환 시작", variant="primary")

        with gr.Column(scale=5):
            gr.Markdown("### 📊 비디오 사양 및 결과물")
            meta_display = gr.Markdown("📥 영상을 업로드하면 비디오 상세 정보가 여기에 표시됩니다.")
            output_video = gr.Video(label="📥 변환 완료된 영상", height=320)
            status = gr.Textbox(label="상태 로그", interactive=False)

    input_video.change(fn=handle_video_upload, inputs=[input_video], outputs=[trim_start, trim_end, meta_display])
    method.change(fn=update_method_visibility, inputs=[method], outputs=[crop_align, bg_color, blur_intensity])
    convert_btn.click(
        fn=convert_video,
        inputs=[input_video, target_ratio, method, crop_align, bg_color, blur_intensity, trim_start, trim_end, volume_level],
        outputs=[output_video, status]
    )

    gr.Markdown("💡 **팁**: 블러 배경은 세로 영상을 가로로, 가로 영상을 세로로 변환할 때 가장 자연스럽습니다.")

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())
