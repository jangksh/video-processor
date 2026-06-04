import gradio as gr
import ffmpeg
import tempfile
from pathlib import Path


def convert_video(input_video, target_ratio, method):
    if input_video is None:
        return None, "❌ 영상을 업로드해주세요!"

    try:
        ratio_tag = "9x16" if "9:16" in target_ratio else "16x9"
        output_path = str(Path(tempfile.gettempdir()) / f"converted_{ratio_tag}.mp4")

        if "9:16" in target_ratio:
            target_w, target_h = 1080, 1920
        else:
            target_w, target_h = 1920, 1080

        if method == "블러 배경 (가장 예쁨)":
            # 배경: 원본을 타겟 크기로 스케일 후 boxblur
            # 전경: 원본을 비율 유지하며 타겟 안에 맞춤, 중앙 오버레이
            bg = (
                ffmpeg.input(input_video)
                .video
                .filter("scale", target_w, target_h, force_original_aspect_ratio="increase")
                .filter("crop", target_w, target_h)
                .filter("boxblur", luma_radius=30, luma_power=3)
            )
            fg = (
                ffmpeg.input(input_video)
                .video
                .filter("scale", target_w, target_h, force_original_aspect_ratio="decrease")
                .filter("pad", target_w, target_h, "(ow-iw)/2", "(oh-ih)/2", color="black@0")
            )
            audio = ffmpeg.input(input_video).audio
            video_out = ffmpeg.overlay(bg, fg)
            cmd = ffmpeg.output(
                video_out, audio, output_path,
                vcodec="libx264", acodec="aac", preset="veryfast", crf=23,
                movflags="+faststart"
            )

        elif method == "스마트 크롭 (중앙 유지)":
            if "9:16" in target_ratio:
                # 가로 영상 → 세로: 세로 전체 유지, 좌우 크롭
                video_out = (
                    ffmpeg.input(input_video).video
                    .filter("crop", "ih*9/16", "ih")
                    .filter("scale", target_w, target_h)
                )
            else:
                # 세로 영상 → 가로: 가로 전체 유지, 상하 크롭
                video_out = (
                    ffmpeg.input(input_video).video
                    .filter("crop", "iw", "iw*9/16")
                    .filter("scale", target_w, target_h)
                )
            audio = ffmpeg.input(input_video).audio
            cmd = ffmpeg.output(
                video_out, audio, output_path,
                vcodec="libx264", acodec="aac", preset="veryfast", crf=23,
                movflags="+faststart"
            )

        else:  # 레터박스
            video_out = (
                ffmpeg.input(input_video).video
                .filter("scale", target_w, target_h, force_original_aspect_ratio="decrease")
                .filter("pad", target_w, target_h, "(ow-iw)/2", "(oh-ih)/2", color="black")
            )
            audio = ffmpeg.input(input_video).audio
            cmd = ffmpeg.output(
                video_out, audio, output_path,
                vcodec="libx264", acodec="aac", preset="veryfast", crf=23,
                movflags="+faststart"
            )

        cmd.run(overwrite_output=True, quiet=True)
        return output_path, f"✅ 변환 완료! → {target_w}×{target_h} ({method})"

    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "알 수 없는 오류"
        return None, f"❌ ffmpeg 오류:\n{stderr}"
    except Exception as e:
        return None, f"❌ 오류 발생: {str(e)}"


# ==================== Gradio UI ====================
with gr.Blocks(title="영상 비율 변환기", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 🎥 16:9 ↔ 9:16 영상 변환기
    유튜브 쇼츠·릴스·틱톡 ↔ 유튜브 롱폼 비율 자동 변환
    """)

    with gr.Row():
        with gr.Column(scale=1):
            input_video = gr.Video(label="📤 원본 영상 업로드", height=320)

            target_ratio = gr.Radio(
                choices=["9:16 (쇼츠·릴스·틱톡)", "16:9 (유튜브 가로)"],
                value="9:16 (쇼츠·릴스·틱톡)",
                label="🎯 변환할 비율",
            )

            method = gr.Radio(
                choices=["블러 배경 (가장 예쁨)", "스마트 크롭 (중앙 유지)", "레터박스 (검은 여백)"],
                value="블러 배경 (가장 예쁨)",
                label="✂️ 변환 방식",
            )

            with gr.Row():
                convert_btn = gr.Button("🚀 변환하기", variant="primary", size="lg")

        with gr.Column(scale=1):
            output_video = gr.Video(label="📥 변환된 영상", height=320)
            status = gr.Textbox(label="상태", interactive=False, lines=2)

    gr.Markdown("""
    ---
    | 방식 | 설명 | 추천 상황 |
    |------|------|-----------|
    | **블러 배경** | 원본을 흐리게 확대해 배경으로 사용 | 여백 없이 자연스럽게 |
    | **스마트 크롭** | 중앙을 기준으로 잘라냄 | 주요 피사체가 중앙에 있을 때 |
    | **레터박스** | 검은 여백으로 채움 | 원본 전체를 보여줘야 할 때 |
    """)

    convert_btn.click(
        fn=convert_video,
        inputs=[input_video, target_ratio, method],
        outputs=[output_video, status],
    )

if __name__ == "__main__":
    demo.launch()
