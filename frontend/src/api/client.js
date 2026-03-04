/**
 * API 客户端 - 处理所有后端 API 调用
 */

import { getAuthToken, getRefreshToken, setAuthTokens, clearAuth } from '../utils/userCookie.js';

// API 基础 URL 配置
// 开发环境（未设置 VITE_API_URL）：直连 localhost:8000
// 生产环境（VITE_API_URL=""）：使用相对路径（通过 nginx 代理）
const getApiBaseUrl = () => {
    const envUrl = import.meta.env.VITE_API_URL;
    // 明确配置了（包括空字符串，用于生产环境相对路径）
    if (envUrl !== undefined) {
        return envUrl;
    }

    // 开发环境回退：直连后端 8000 端口
    const host = window.location.hostname;
    const protocol = window.location.protocol;
    return `${protocol}//${host}:8000`;
};

const API_BASE_URL = getApiBaseUrl();

// 调试：输出 API 地址
console.log('API Base URL:', API_BASE_URL);


// 获取非 /api 前缀的基础 URL（用于 /auth、/admin 等根路径路由）
const getRootBaseUrl = () => {
    if (API_BASE_URL.startsWith('/')) {
        // 相对路径模式（如 /api），根路径用空字符串
        return '';
    }
    // 绝对路径模式（如 http://localhost:8000），直接使用
    return API_BASE_URL;
};

const ROOT_BASE_URL = getRootBaseUrl();


// ============ 认证 API ============

/**
 * 用户登录
 */
export async function login(username, password) {
    const url = `${ROOT_BASE_URL}/auth/login`;
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username, password }),
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.detail || '登录失败');
    }
    setAuthTokens(data.access_token, data.refresh_token);
    return data;
}

/**
 * 用户注册
 */
export async function register(username, password) {
    const url = `${ROOT_BASE_URL}/auth/register`;
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username, password }),
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.detail || '注册失败');
    }
    setAuthTokens(data.access_token, data.refresh_token);
    return data;
}

/**
 * 刷新 access token
 */
async function refreshAccessToken() {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return false;

    try {
        const url = `${ROOT_BASE_URL}/auth/refresh`;
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!response.ok) return false;

        const data = await response.json();
        setAuthTokens(data.access_token, data.refresh_token);
        return true;
    } catch {
        return false;
    }
}

/**
 * 获取当前用户信息
 */
export async function fetchCurrentUser() {
    return apiRequest('/auth/me');
}


/**
 * 创建 API 请求（自动附加 Authorization header，401 自动刷新/跳转）
 */
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    console.log('API Request:', url, options);

    const defaultOptions = {
        credentials: 'include', // 发送 cookie
        headers: {
            'Content-Type': 'application/json',
        },
    };

    const config = { ...defaultOptions, ...options };

    // 自动附加 Authorization header
    const token = getAuthToken();
    if (token) {
        config.headers = { ...config.headers, 'Authorization': `Bearer ${token}` };
    }

    try {
        let response = await fetch(url, config);
        console.log('API Response status:', response.status);

        // 401: 尝试刷新 token 后重试
        if (response.status === 401 && token) {
            const refreshed = await refreshAccessToken();
            if (refreshed) {
                const newToken = getAuthToken();
                config.headers['Authorization'] = `Bearer ${newToken}`;
                response = await fetch(url, config);
            } else {
                // 刷新失败，清除认证并跳转登录页
                clearAuth();
                window.location.hash = '#/login';
                throw new Error('登录已过期，请重新登录');
            }
        }

        const data = await response.json();
        console.log('API Response data:', data);

        if (!response.ok) {
            if (response.status === 422) {
                console.error('[422 ERROR] 请求体验证失败:', {
                    url,
                    method: config.method,
                    body: config.body,
                    responseData: data,
                    detail: data.detail || data.message || '未知错误'
                });
            }
            throw new Error(data.message || data.detail || '请求失败');
        }

        return data;
    } catch (error) {
        console.error('API 请求错误:', error);
        throw error;
    }
}

/**
 * 视频上传 API
 */
export async function uploadVideo(file, onProgress) {
    const url = `${API_BASE_URL}/api/upload`;
    console.log('上传视频开始:', url, '文件名:', file.name, '文件大小:', file.size);

    const formData = new FormData();
    formData.append('file', file);  // 后端参数名是 'file'

    // 创建超时控制器（30秒超时）
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    try {
        console.log('发起 fetch 请求...');
        const headers = {};
        const token = getAuthToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        const response = await fetch(url, {
            method: 'POST',
            body: formData,
            signal: controller.signal,
            credentials: 'include',
            headers,
        });

        clearTimeout(timeoutId);

        console.log('上传响应状态:', response.status, response.statusText);
        console.log('上传响应头:', [...response.headers.entries()]);

        // 处理非 JSON 响应或错误响应
        const contentType = response.headers.get('content-type');
        console.log('响应 Content-Type:', contentType);

        let data;
        if (contentType && contentType.includes('application/json')) {
            data = await response.json();
            console.log('响应数据:', data);
        } else {
            const text = await response.text();
            console.log('非 JSON 响应内容:', text);
            data = { message: text || '上传失败' };
        }

        if (!response.ok) {
            console.error('上传失败:', data);
            throw new Error(data.message || data.detail || '上传失败');
        }

        console.log('上传成功:', data);
        return data;

    } catch (error) {
        clearTimeout(timeoutId);

        // 处理不同类型的错误
        if (error.name === 'AbortError') {
            console.error('上传超时:', error);
            throw new Error('上传超时，请检查网络连接或后端服务是否运行');
        } else if (error instanceof TypeError && error.message.includes('fetch')) {
            console.error('网络错误:', error);
            throw new Error('网络连接失败，请检查后端服务是否运行');
        } else {
            console.error('上传异常:', error);
            throw error;
        }
    }
}

/**
 * 开始分析 API
 * @param {string} taskId - 任务ID
 * @param {string} targetPlayer - 目标球员选择 ('single_player' | 'left' | 'right' | 'front' | 'back')
 */
export async function startAnalysis(taskId, targetPlayer) {
    // 球员位置直接传递，不做映射（保留 front/back/left/right 的位置语义）
    const mappedPlayer = targetPlayer;

    // 场景类型：单人训练 vs 双人对练
    const sceneType = (targetPlayer === 'single_player')
        ? 'single'
        : 'dual_practice';

    const payload = {
        task_id: taskId,
        target_player: mappedPlayer,
        scene_type: sceneType
    };

    console.log('[DEBUG] 开始分析 API 调用:', payload);
    console.log('[DEBUG] taskId:', taskId, 'typeof:', typeof taskId, 'isEmpty:', !taskId);
    console.log('[DEBUG] targetPlayer:', targetPlayer, 'mappedPlayer:', mappedPlayer, 'sceneType:', sceneType);

    return apiRequest('/api/analyze', {
        method: 'POST',
        body: JSON.stringify(payload),
    });
}

/**
 * 预处理视频 API - 检测目标运动员
 */
export async function preprocessVideo(taskId) {
    return apiRequest(`/api/preprocess/${taskId}`);
}

/**
 * 获取分析结果 API
 */
export async function getAnalysisResult(taskId) {
    return apiRequest(`/api/results/${taskId}`);
}

/**
 * 获取历史任务列表 API
 */
export async function getHistoryTasks(page = 1, limit = 20, status = null) {
    const params = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString(),
    });
    if (status) {
        params.append('status', status);
    }
    return apiRequest(`/api/history?${params.toString()}`);
}

/**
 * 获取任务队列 API
 */
export async function getTaskQueue() {
    return apiRequest('/api/queue');
}

/**
 * 刷新任务状态 API
 */
export async function refreshTaskStatus(taskId) {
    return apiRequest(`/api/tasks/${taskId}/status`);
}

/**
 * 删除任务 API
 */
export async function deleteTask(taskId) {
    return apiRequest(`/api/tasks/${taskId}`, {
        method: 'DELETE',
    });
}

/**
 * 设置任务为公开分享状态 API
 * @param {string} taskId - 任务 ID
 */
export async function shareTask(taskId) {
    return apiRequest(`/api/tasks/${taskId}/share`, {
        method: 'POST',
    });
}

/**
 * WebSocket 连接 - 实时接收任务状态更新
 */
export function connectTaskWebSocket(taskId, onMessage, onError) {
    // 构造 WebSocket URL
    // 1. 生产环境使用相对路径：VITE_API_URL=/api -> ws://.../ws/tasks/...
    // 2. 本地开发使用绝对路径：VITE_API_URL=http://... -> ws://...
    let wsUrl;
    if (API_BASE_URL.startsWith('/')) {
        // 相对路径：使用当前页面的协议和主机
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        wsUrl = `${protocol}//${host}/ws/tasks/${taskId}`;
    } else {
        // 绝对路径：替换协议
        wsUrl = `${API_BASE_URL.replace('http:', 'ws:').replace('https:', 'wss:')}/ws/tasks/${taskId}`;
    }

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket 连接已建立');
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            onMessage(data);
        } catch (error) {
            console.error('WebSocket 消息解析错误:', error);
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket 错误:', error);
        onError?.(error);
    };

    ws.onclose = () => {
        console.log('WebSocket 连接已关闭');
    };

    return ws;
}

// ============ 管理后台 API ============

export async function adminGetUsers(page = 1, limit = 20) {
    return apiRequest(`/admin/users?page=${page}&limit=${limit}`);
}

export async function adminCreateUser(username, password, role = 'user') {
    return apiRequest('/admin/users', {
        method: 'POST',
        body: JSON.stringify({ username, password, role }),
    });
}

export async function adminUpdateUser(userId, updates) {
    return apiRequest(`/admin/users/${userId}`, {
        method: 'PUT',
        body: JSON.stringify(updates),
    });
}

export async function adminDeleteUser(userId) {
    return apiRequest(`/admin/users/${userId}`, { method: 'DELETE' });
}

export async function adminGetTasks(page = 1, limit = 20) {
    return apiRequest(`/admin/tasks?page=${page}&limit=${limit}`);
}

export async function adminDeleteTask(taskId) {
    return apiRequest(`/admin/tasks/${taskId}`, { method: 'DELETE' });
}

export async function adminGetStats() {
    return apiRequest('/admin/stats');
}

export async function adminGetConfig() {
    return apiRequest('/admin/config');
}

export async function adminUpdateConfig(key, value, description = null) {
    return apiRequest(`/admin/config/${key}`, {
        method: 'PUT',
        body: JSON.stringify({ value, description }),
    });
}

export { API_BASE_URL, getApiBaseUrl };

export default {
    login,
    register,
    fetchCurrentUser,
    uploadVideo,
    preprocessVideo,
    startAnalysis,
    getAnalysisResult,
    getHistoryTasks,
    getTaskQueue,
    refreshTaskStatus,
    deleteTask,
    connectTaskWebSocket,
    adminGetUsers,
    adminCreateUser,
    adminUpdateUser,
    adminDeleteUser,
    adminGetTasks,
    adminDeleteTask,
    adminGetStats,
    adminGetConfig,
    adminUpdateConfig,
};
