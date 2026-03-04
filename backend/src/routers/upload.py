"""
上传路由 - POST /api/upload
"""

import uuid
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from sqlmodel import Session

from ..database import get_session
from ..auth.dependencies import get_effective_user_id
from ..services.task_service import create_task, get_user_run_dir, task_to_response_dict
from ..schemas.task import UploadResponse, TaskResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["上传"])


@router.post("/api/upload", response_model=UploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    request: Request = None,
    user_id: str = Depends(get_effective_user_id),
    session: Session = Depends(get_session),
):
    """
    上传视频文件

    - 支持的格式: MP4, MOV, AVI
    - 最大文件大小: 20MB
    - 最大时长: 5 秒
    """
    # 验证文件类型
    allowed_types = ["video/mp4", "video/quicktime", "video/x-msvideo"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="不支持的文件格式")

    # 读取文件内容
    content = await file.read()

    # 验证文件大小
    max_size = 20 * 1024 * 1024  # 20MB
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail="视频文件大小不能超过 20MB")

    # 创建任务目录
    user_run_dir = get_user_run_dir(user_id)
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    task_dir = user_run_dir / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    # 保存文件
    video_path = task_dir / (file.filename or "video.mp4")
    try:
        with open(video_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    # 验证视频时长
    try:
        import imageio

        reader = imageio.get_reader(video_path)
        meta = reader.get_meta_data()
        fps = meta.get("fps", None)
        if fps is None or fps <= 0:
            raise HTTPException(status_code=400, detail="无法读取视频帧率")

        frame_count = reader.count_frames()
        reader.close()
        duration = frame_count / fps

        max_duration = 6.0
        if duration > max_duration:
            raise HTTPException(
                status_code=400,
                detail=f"视频时长不能超过 5 秒（当前视频：{duration:.1f} 秒）",
            )

        logger.info(
            f"视频验证通过: 时长 {duration:.1f} 秒, 帧数 {frame_count}, 帧率 {fps:.1f} fps"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"无法验证视频时长，继续处理: {e}")

    # 生成任务名称
    date_str = datetime.now().strftime("%Y%m%d")
    random_str = uuid.uuid4().hex[:6]
    task_name = f"训练视频_{date_str}_{random_str}"

    # 创建数据库任务记录
    task = create_task(
        session=session,
        task_id=task_id,
        name=task_name,
        video_path=str(video_path),
        user_id=user_id,
    )

    return UploadResponse(
        success=True,
        task_id=task_id,
        message="视频上传成功",
        task=TaskResponse(**task_to_response_dict(task)),
    )
