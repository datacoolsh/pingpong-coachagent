"""
分析路由 - POST /api/analyze, GET /api/preprocess/{task_id}
"""

import os
import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Request
from sqlmodel import Session

from ..database import get_session
from ..auth.dependencies import get_effective_user_id
from ..services.task_service import (
    get_task,
    update_task,
    get_user_run_dir,
    load_result_from_file,
)
from ..core.task_queue import task_queue
from ..schemas.task import AnalysisRequest, AnalysisResponse
from ..steps import extract_frames, compute_features, run_llm_analysis, assemble_report
from ..player_detector import detect_target_player
from ..constants import AGENT_MODE_MOCK, AGENT_MODE_REAL

logger = logging.getLogger(__name__)

router = APIRouter(tags=["分析"])


@router.get("/api/preprocess/{task_id}")
async def preprocess_video(
    task_id: str,
    user_id: str = Depends(get_effective_user_id),
    session: Session = Depends(get_session),
):
    """预处理视频：检测目标运动员"""
    task = get_task(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 验证任务所有权
    if task.user_id and task.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此任务")

    video_path = Path(task.video_path or "")
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="视频文件不存在")

    user_run_dir = get_user_run_dir(user_id)
    run_dir = user_run_dir / task_id
    run_dir.mkdir(parents=True, exist_ok=True)
    frames_output = run_dir / "frames"
    frames_output.mkdir(parents=True, exist_ok=True)

    try:
        frames_data = extract_frames(
            video_path,
            frames_output,
            max_frames=10,
            num_segments=2,
            frames_per_segment=5,
            strategy="per_segment",
        )

        target_player_config = detect_target_player(
            frames_data,
            run_dir,
            motion_threshold=0.05,
            confidence_threshold=0.65,
        )

        return {
            "success": True,
            "task_id": task_id,
            "target_player": target_player_config,
        }

    except Exception as e:
        logger.error(f"[{task_id}] 预处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"预处理失败: {str(e)}")


@router.post("/api/analyze", response_model=AnalysisResponse)
async def start_analysis(
    request_data: AnalysisRequest,
    user_id: str = Depends(get_effective_user_id),
    session: Session = Depends(get_session),
):
    """开始分析任务"""
    task = get_task(session, request_data.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 验证任务所有权
    if task.user_id and task.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此任务")

    if task.status == "completed":
        return AnalysisResponse(
            success=True, message="任务已完成", task_id=request_data.task_id
        )

    # 更新任务状态
    update_task(session, request_data.task_id, status="queued", stage="正在准备分析...", progress=10, user_id=user_id)

    # 推送 WebSocket 状态
    task_queue.set_runtime_state(request_data.task_id, {
        "task_id": request_data.task_id,
        "name": task.name,
        "status": "queued",
        "progress": 10,
        "stage": "正在准备分析...",
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    })

    await asyncio.sleep(0.01)

    video_path = Path(task.video_path or "")
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="视频文件不存在")

    user_run_dir = get_user_run_dir(user_id)
    run_dir = user_run_dir / request_data.task_id
    run_dir.mkdir(parents=True, exist_ok=True)
    frames_output = run_dir / "frames"
    frames_output.mkdir(parents=True, exist_ok=True)

    try:
        # 构建目标球员配置
        target_player_config = None
        if request_data.target_player:
            target_player_config = {
                "mode": "user_choice",
                "auto_pick": request_data.target_player,
                "confidence": 1.0,
                "reason": "用户手动选择",
                "override": None,
                "scene_type": request_data.scene_type or "single",
            }

        # 辅助函数：更新状态并推送 WebSocket
        def _update_status(status: str, progress: int, stage: str):
            update_task(session, request_data.task_id, status=status, progress=progress, stage=stage)
            task_queue.set_runtime_state(request_data.task_id, {
                "task_id": request_data.task_id,
                "name": task.name,
                "status": status,
                "progress": progress,
                "stage": stage,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
            })

        # Step 1: 抽帧
        _update_status("extracting", 30, "正在从视频中提取关键帧...")
        await asyncio.sleep(0.01)

        frames_data = extract_frames(
            video_path,
            frames_output,
            max_frames=100,
            num_segments=8,
            frames_per_segment=12,
            strategy="per_segment",
        )

        # Step 2: 特征计算
        _update_status("computing", 50, "正在计算动作特征...")
        await asyncio.sleep(0.01)

        features_data = compute_features(frames_data, num_segments=8)

        # Step 3: AI 分析
        _update_status("analyzing", 60, "AI 正在分析动作...")
        await asyncio.sleep(0.01)

        api_key = (
            os.environ.get("ZHIPU_API_KEY", "").strip()
            or os.environ.get("DEEPSEEK_API_KEY", "").strip()
        )
        agent_mode = AGENT_MODE_REAL if api_key else AGENT_MODE_MOCK

        llm_result = run_llm_analysis(
            frames_data,
            features_data,
            agent_mode,
            llm_model="deepseek-chat",
            run_dir=run_dir,
            target_player_config=target_player_config,
        )

        # Step 4: 组装报告
        _update_status("assembling_report", 90, "正在生成分析报告...")
        await asyncio.sleep(0.01)

        report = assemble_report(
            frames_data, features_data, llm_result, target_player_config
        )

        # 构建最终结果
        llm_coach_comment = llm_result.get("coach_comment", {})
        llm_problems = llm_result.get("problems", [])
        llm_suggestions = llm_result.get("suggestions", [])
        llm_score = llm_result.get("score")

        # 教练评语默认值
        if not llm_coach_comment or not isinstance(llm_coach_comment, dict):
            llm_coach_comment = {
                "strengths": "动作基础扎实，建议继续加强练习",
                "weaknesses": "需要进一步规范化动作细节",
                "summary": "整体表现良好，继续保持训练",
            }
        else:
            if not llm_coach_comment.get("strengths"):
                llm_coach_comment["strengths"] = "动作基础扎实，建议继续加强练习"
            if not llm_coach_comment.get("weaknesses"):
                llm_coach_comment["weaknesses"] = "需要进一步规范化动作细节"
            if not llm_coach_comment.get("summary"):
                llm_coach_comment["summary"] = "整体表现良好，继续保持训练"

        if not llm_problems or len(llm_problems) == 0:
            llm_problems = [
                {"title": "动作规范性", "description": "建议加强基本动作的规范性训练"},
                {"title": "击球稳定性", "description": "通过多球练习提升击球稳定性"},
                {"title": "还原速度", "description": "加强击球后的快速还原训练"},
            ]

        if not llm_suggestions or len(llm_suggestions) == 0:
            llm_suggestions = [
                {"title": "加强基本动作", "description": "训练方法：\n多球练习\n空挥练习", "priority": "high"},
                {"title": "提升击球稳定性", "description": "训练方法：\n定点训练\n节奏控制", "priority": "medium"},
                {"title": "改善还原速度", "description": "训练方法：\n快速还原\n步法训练", "priority": "medium"},
            ]

        formatted_suggestions = []
        for s in llm_suggestions[:3]:
            if isinstance(s, dict):
                formatted_suggestions.append({
                    "title": s.get("title", "训练建议"),
                    "description": s.get("description", ""),
                    "priority": s.get("priority", "medium"),
                })

        result = {
            "task_id": request_data.task_id,
            "name": task.name,
            "status": "completed",
            "created_at": task.created_at.isoformat(),
            "target_player": target_player_config or {},
            "coach_comment": llm_coach_comment,
            "problems": llm_problems[:3],
            "suggestions": formatted_suggestions,
            "overall_score": llm_score if llm_score is not None else 70,
            "details": {},
            "user_id": user_id,
        }

        # 保存到文件
        import json
        report_path = run_dir / "report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        # 更新数据库
        update_task(
            session, request_data.task_id,
            status="completed", progress=100, stage=None,
            run_dir=str(run_dir),
        )

        # 推送完成状态
        task_queue.set_runtime_state(request_data.task_id, {
            **result,
            "progress": 100,
            "result": result,
        })

        return AnalysisResponse(
            success=True, message="分析完成", task_id=request_data.task_id
        )

    except Exception as e:
        logger.error(f"[{request_data.task_id}] 分析失败: {e}")
        update_task(session, request_data.task_id, status="failed", error=str(e))
        task_queue.set_runtime_state(request_data.task_id, {
            "task_id": request_data.task_id,
            "name": task.name,
            "status": "failed",
            "error": str(e),
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        })
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")
