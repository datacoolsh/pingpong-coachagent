"""
媒体文件路由 - 帧图片、视频、PDF 下载
"""

import logging
from urllib.parse import quote
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse, StreamingResponse, Response
from sqlmodel import Session

from ..database import get_session
from ..auth.dependencies import get_effective_user_id
from ..services.task_service import find_task_globally, get_user_run_dir, get_runs_dir, load_result_from_file
from ..pdf import generate_pdf_report
from ..routers.results import _ensure_new_format

logger = logging.getLogger(__name__)

router = APIRouter(tags=["媒体文件"])

RUNS_DIR = get_runs_dir()


@router.get("/frames/{task_id}/{frame_name}")
async def get_frame_image(
    task_id: str,
    frame_name: str,
    user_id: str = Depends(get_effective_user_id),
    session: Session = Depends(get_session),
):
    """获取关键帧图片"""
    task = find_task_globally(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 验证权限
    if not task.is_public and task.user_id and task.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此任务")

    task_user_id = task.user_id or user_id
    user_run_dir = get_user_run_dir(task_user_id)
    frame_path = user_run_dir / task_id / "frames" / frame_name

    # 兼容旧目录结构
    if not frame_path.exists():
        legacy_frame_path = RUNS_DIR / task_id / "frames" / frame_name
        if legacy_frame_path.exists():
            frame_path = legacy_frame_path

    if not frame_path.exists():
        frames_dir = user_run_dir / task_id / "frames"
        available_frames = []
        if frames_dir.exists():
            available_frames = sorted([f.name for f in frames_dir.iterdir() if f.is_file()])

        error_detail = f"关键帧图片不存在: {frame_name}"
        if available_frames:
            error_detail += f"\n可用的帧文件: {', '.join(available_frames[:10])}"
        else:
            error_detail += "\n帧目录不存在或为空"
        raise HTTPException(status_code=404, detail=error_detail)

    return FileResponse(frame_path)


@router.get("/results/{task_id}/pdf")
async def download_pdf_report(
    task_id: str,
    user_id: str = Depends(get_effective_user_id),
    session: Session = Depends(get_session),
):
    """下载 PDF 报告"""
    task = find_task_globally(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if not task.is_public and task.user_id and task.user_id != user_id:
        raise HTTPException(status_code=403, detail="只有任务创建者才能下载 PDF 报告")

    result = load_result_from_file(task)
    if not result:
        raise HTTPException(status_code=404, detail="分析结果不存在")

    result = _ensure_new_format(result, task_id)

    task_user_id = task.user_id or user_id
    task_run_dir = get_user_run_dir(task_user_id) / task_id

    try:
        pdf_data = generate_pdf_report(result, task_run_dir)

        filename_zh = "乒乓球训练分析报告.pdf"
        filename_ascii = "pingpong_training_analysis_report.pdf"
        filename_encoded = quote(filename_zh, safe="")

        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename_ascii}\"; filename*=UTF-8''{filename_encoded}",
            },
        )
    except Exception as e:
        import traceback
        logger.error(f"[PDF 下载] 生成 PDF 失败: task_id={task_id}, error={e}")
        logger.error(f"[PDF 下载] 错误堆栈:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"生成 PDF 失败: {str(e)}")


@router.get("/videos/{task_id}")
async def get_task_video(
    task_id: str,
    user_id: str = Depends(get_effective_user_id),
    session: Session = Depends(get_session),
):
    """获取任务的原始视频"""
    task = find_task_globally(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if not task.is_public and task.user_id and task.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此任务")

    task_user_id = task.user_id or user_id
    user_run_dir = get_user_run_dir(task_user_id)
    task_dir = user_run_dir / task_id

    video_extensions = [".mp4", ".mov", ".avi", ".mkv"]
    video_path = None

    input_video = task_dir / "input.mp4"
    if input_video.exists():
        video_path = input_video
    else:
        if task_dir.exists():
            for file in task_dir.iterdir():
                if file.is_file() and file.suffix.lower() in video_extensions:
                    video_path = file
                    break

    # 兼容旧目录
    if not video_path:
        legacy_task_dir = RUNS_DIR / task_id
        if legacy_task_dir.exists():
            input_video = legacy_task_dir / "input.mp4"
            if input_video.exists():
                video_path = input_video
            else:
                for file in legacy_task_dir.iterdir():
                    if file.is_file() and file.suffix.lower() in video_extensions:
                        video_path = file
                        break

    if not video_path:
        raise HTTPException(status_code=404, detail="视频文件不存在")

    def iter_file():
        with open(video_path, "rb") as f:
            while chunk := f.read(8192):
                yield chunk

    media_type = "video/mp4"
    if video_path.suffix.lower() == ".mov":
        media_type = "video/quicktime"
    elif video_path.suffix.lower() == ".avi":
        media_type = "video/x-msvideo"
    elif video_path.suffix.lower() == ".mkv":
        media_type = "video/x-matroska"

    return StreamingResponse(
        iter_file(),
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="video{video_path.suffix}"',
            "Accept-Ranges": "bytes",
        },
    )
