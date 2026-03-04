/**
 * 登录/注册页面
 */

import { login, register } from '../api/client.js';
import { setUserInfo } from '../utils/userCookie.js';

export class LoginPage {
    constructor(onLoginSuccess) {
        this.onLoginSuccess = onLoginSuccess;
        this.isRegisterMode = false;
        this.loading = false;
    }

    render() {
        const app = document.getElementById('app');
        app.innerHTML = `
            <div class="login-page" style="
                background: var(--bg-primary, #1a1a1a);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            ">
                <div class="login-card" style="
                    background: var(--bg-card, #2a2a2a);
                    border-radius: 16px;
                    padding: 40px 32px;
                    max-width: 400px;
                    width: 100%;
                    border: 1px solid var(--divider, #333);
                ">
                    <h1 style="
                        color: var(--text-primary, #fff);
                        font-size: 24px;
                        text-align: center;
                        margin-bottom: 8px;
                    ">AI 乒乓球教练</h1>
                    <p style="
                        color: var(--text-secondary, #999);
                        text-align: center;
                        margin-bottom: 32px;
                        font-size: 14px;
                    " id="login-subtitle">登录您的账户</p>

                    <form id="login-form">
                        <div style="margin-bottom: 20px;">
                            <label style="
                                color: var(--text-secondary, #999);
                                font-size: 13px;
                                display: block;
                                margin-bottom: 6px;
                            ">用户名</label>
                            <input type="text" id="login-username" placeholder="请输入用户名" autocomplete="username" style="
                                width: 100%;
                                padding: 12px 16px;
                                background: var(--bg-primary, #1a1a1a);
                                border: 1px solid var(--divider, #333);
                                border-radius: 8px;
                                color: var(--text-primary, #fff);
                                font-size: 15px;
                                outline: none;
                                box-sizing: border-box;
                            " />
                        </div>

                        <div style="margin-bottom: 24px;">
                            <label style="
                                color: var(--text-secondary, #999);
                                font-size: 13px;
                                display: block;
                                margin-bottom: 6px;
                            ">密码</label>
                            <input type="password" id="login-password" placeholder="请输入密码" autocomplete="current-password" style="
                                width: 100%;
                                padding: 12px 16px;
                                background: var(--bg-primary, #1a1a1a);
                                border: 1px solid var(--divider, #333);
                                border-radius: 8px;
                                color: var(--text-primary, #fff);
                                font-size: 15px;
                                outline: none;
                                box-sizing: border-box;
                            " />
                        </div>

                        <div id="login-error" style="
                            color: var(--error, #ef4444);
                            font-size: 13px;
                            margin-bottom: 16px;
                            display: none;
                        "></div>

                        <button type="submit" id="login-btn" style="
                            width: 100%;
                            padding: 12px;
                            background: var(--accent, #FFB800);
                            color: #000;
                            border: none;
                            border-radius: 8px;
                            font-size: 16px;
                            font-weight: 600;
                            cursor: pointer;
                        ">登录</button>
                    </form>

                    <div style="
                        text-align: center;
                        margin-top: 20px;
                    ">
                        <span style="color: var(--text-secondary, #999); font-size: 13px;">
                            <span id="login-toggle-text">还没有账户？</span>
                            <a href="#" id="login-toggle" style="
                                color: var(--accent, #FFB800);
                                text-decoration: none;
                            ">注册</a>
                        </span>
                    </div>

                    <div style="
                        text-align: center;
                        margin-top: 16px;
                    ">
                        <a href="#/" id="login-skip" style="
                            color: var(--text-secondary, #999);
                            font-size: 13px;
                            text-decoration: none;
                        ">跳过登录，以访客身份使用</a>
                    </div>
                </div>
            </div>
        `;

        this.bindEvents();
    }

    bindEvents() {
        const form = document.getElementById('login-form');
        const toggle = document.getElementById('login-toggle');

        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleSubmit();
        });

        toggle.addEventListener('click', (e) => {
            e.preventDefault();
            this.toggleMode();
        });
    }

    toggleMode() {
        this.isRegisterMode = !this.isRegisterMode;
        const subtitle = document.getElementById('login-subtitle');
        const btn = document.getElementById('login-btn');
        const toggleText = document.getElementById('login-toggle-text');
        const toggleLink = document.getElementById('login-toggle');

        if (this.isRegisterMode) {
            subtitle.textContent = '创建新账户';
            btn.textContent = '注册';
            toggleText.textContent = '已有账户？';
            toggleLink.textContent = '登录';
        } else {
            subtitle.textContent = '登录您的账户';
            btn.textContent = '登录';
            toggleText.textContent = '还没有账户？';
            toggleLink.textContent = '注册';
        }

        // 清除错误
        const errorEl = document.getElementById('login-error');
        errorEl.style.display = 'none';
    }

    async handleSubmit() {
        if (this.loading) return;

        const username = document.getElementById('login-username').value.trim();
        const password = document.getElementById('login-password').value;
        const errorEl = document.getElementById('login-error');
        const btn = document.getElementById('login-btn');

        if (!username || !password) {
            errorEl.textContent = '请输入用户名和密码';
            errorEl.style.display = 'block';
            return;
        }

        this.loading = true;
        btn.disabled = true;
        btn.textContent = '请稍候...';
        errorEl.style.display = 'none';

        try {
            if (this.isRegisterMode) {
                await register(username, password);
            } else {
                await login(username, password);
            }

            // 登录/注册成功，获取用户信息
            const { fetchCurrentUser } = await import('../api/client.js');
            const userInfo = await fetchCurrentUser();
            setUserInfo(userInfo);

            // 跳转到主页
            window.location.hash = '#/';
            if (this.onLoginSuccess) {
                this.onLoginSuccess(userInfo);
            }
        } catch (error) {
            errorEl.textContent = error.message;
            errorEl.style.display = 'block';
        } finally {
            this.loading = false;
            btn.disabled = false;
            btn.textContent = this.isRegisterMode ? '注册' : '登录';
        }
    }
}
