"""
微信 JS-SDK 路由
"""

import logging

from fastapi import APIRouter, HTTPException

from ..wechat_service import wechat_jsdk

logger = logging.getLogger(__name__)

router = APIRouter(tags=["微信"])


@router.get("/api/wechat/jssdk-config")
async def get_wechat_jsdk_config(url: str):
    """获取微信 JS-SDK 配置"""
    try:
        config = await wechat_jsdk.get_jsdk_config(url)
        return {"success": True, "data": config}
    except Exception as e:
        logger.error(f"获取微信 JS-SDK 配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")
