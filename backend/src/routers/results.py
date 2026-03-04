"""
结果路由 - GET /api/results/{task_id}
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session

from ..database import get_session
from ..auth.dependencies import get_effective_user_id
from ..services.task_service import find_task_globally, load_result_from_file
from ..schemas.task import AnalysisResult

logger = logging.getLogger(__name__)

router = APIRouter(tags=["结果"])


def _ensure_new_format(data: dict, task_id: str = None) -> dict:
    """
    确保结果数据包含新格式的三个必需字段

    处理两种旧格式：
    1. report 格式（assemble_report 返回）：{metadata, frames, features, analysis}
    2. 旧 result 格式：{summary, improvements, details}
    转换为新格式：{task_id, status, created_at, coach_comment, problems, suggestions}
    """
    if data.get("task_id") and data.get("coach_comment"):
        return data

    # 情况1：处理 report 格式
    if "metadata" in data and "analysis" in data:
        metadata = data.get("metadata", {})
        analysis = data.get("analysis", {})

        analysis_suggestions = analysis.get("suggestions", [])
        if not analysis_suggestions:
            analysis_suggestions = [
                {"title": "加强基本动作", "description": "训练方法：\n多球练习\n空挥练习", "priority": "high"},
                {"title": "提升击球稳定性", "description": "训练方法：\n定点训练\n节奏控制", "priority": "medium"},
                {"title": "改善还原速度", "description": "训练方法：\n快速还原\n步法训练", "priority": "medium"},
            ]

        formatted_suggestions = [
            {
                "title": s.get("title", "训练建议"),
                "description": s.get("description", ""),
                "priority": s.get("priority", "medium"),
            }
            for s in analysis_suggestions[:3]
        ]

        return {
            "task_id": task_id or metadata.get("task_id", ""),
            "name": metadata.get("name", f"训练视频_{task_id}" if task_id else "训练视频"),
            "status": "completed",
            "created_at": metadata.get("created_at", datetime.now().isoformat()),
            "target_player": metadata.get("target_player", {}),
            "coach_comment": analysis.get("coach_comment", {
                "strengths": "动作基础扎实，建议继续加强练习",
                "weaknesses": "需要进一步规范化动作细节",
                "summary": "整体表现良好，继续保持训练",
            }),
            "problems": analysis.get("problems", [
                {"title": "动作规范性", "description": "建议加强基本动作的规范性训练"},
                {"title": "击球稳定性", "description": "通过多球练习提升击球稳定性"},
                {"title": "还原速度", "description": "加强击球后的快速还原训练"},
            ]),
            "suggestions": formatted_suggestions,
            "overall_score": analysis.get("score", 70),
            "details": {},
        }

    # 情况2：有 coach_comment 但可能缺少其他字段
    if data.get("coach_comment"):
        if not data.get("problems"):
            data["problems"] = [
                {"title": "动作规范性", "description": "建议加强基本动作的规范性训练"},
                {"title": "击球稳定性", "description": "通过多球练习提升击球稳定性"},
                {"title": "还原速度", "description": "加强击球后的快速还原训练"},
            ]
        if not data.get("suggestions"):
            data["suggestions"] = [
                {"title": "加强基本动作", "description": "训练方法：\n多球练习\n空挥练习", "priority": "high"},
                {"title": "提升击球稳定性", "description": "训练方法：\n定点训练\n节奏控制", "priority": "medium"},
                {"title": "改善还原速度", "description": "训练方法：\n快速还原\n步法训练", "priority": "medium"},
            ]
        if "overall_score" not in data or data["overall_score"] is None:
            data["overall_score"] = 70
        if "details" not in data:
            data["details"] = {}
        return data

    # 旧格式转换
    summary = data.get("summary", {})
    improvements = data.get("improvements", [])
    details = data.get("details", {})

    coach_comment = {
        "strengths": summary.get("overview", "动作基础扎实，建议继续加强练习"),
        "weaknesses": "",
        "summary": summary.get("overview", "整体表现良好，继续保持训练"),
    }
    old_weaknesses = summary.get("weaknesses", [])
    if old_weaknesses:
        coach_comment["weaknesses"] = (
            "、".join(old_weaknesses) if isinstance(old_weaknesses, list) else str(old_weaknesses)
        )
    else:
        coach_comment["weaknesses"] = "需要进一步规范化动作细节"

    problems = []
    if isinstance(details, dict):
        technique = details.get("technique", {})
        if isinstance(technique, dict):
            for key, value in technique.items():
                problems.append({"title": key, "description": str(value)})
    while len(problems) < 3:
        problems.append({"title": "动作规范性", "description": "建议加强基本动作的规范性训练"})

    suggestions = []
    for imp in improvements[:3]:
        if isinstance(imp, dict):
            suggestions.append({
                "title": imp.get("title", "训练建议"),
                "description": "训练方法：\n" + "\n".join(imp.get("drills", [])),
            })
    default_suggestions = [
        {"title": "加强基本动作", "description": "训练方法：\n多球练习\n空挥练习"},
        {"title": "提升击球稳定性", "description": "训练方法：\n定点训练\n节奏控制"},
        {"title": "改善还原速度", "description": "训练方法：\n快速还原\n步法训练"},
    ]
    while len(suggestions) < 3:
        suggestions.append(default_suggestions[len(suggestions)])

    data["coach_comment"] = coach_comment
    data["problems"] = problems[:3]
    data["suggestions"] = suggestions[:3]
    if "task_id" not in data:
        data["task_id"] = task_id or ""
    if "status" not in data:
        data["status"] = "completed"
    if "created_at" not in data:
        data["created_at"] = datetime.now().isoformat()
    if "name" not in data:
        data["name"] = f"训练视频_{task_id}" if task_id else "训练视频"
    if "target_player" not in data:
        data["target_player"] = {}
    if "overall_score" not in data:
        data["overall_score"] = 70
    if "details" not in data:
        data["details"] = {}

    return data


@router.get("/api/results/{task_id}", response_model=AnalysisResult)
async def get_analysis_result(
    task_id: str,
    user_id: str = Depends(get_effective_user_id),
    session: Session = Depends(get_session),
):
    """获取分析结果"""
    task = find_task_globally(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 验证权限
    is_public = task.is_public
    if not is_public and task.user_id and task.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此任务")

    # 从文件加载结果
    result = load_result_from_file(task)
    if not result:
        return AnalysisResult(
            task_id=task_id,
            status=task.status,
            created_at=task.created_at.isoformat() if task.created_at else datetime.now().isoformat(),
        )

    result = _ensure_new_format(result, task_id)
    return AnalysisResult(**result)
