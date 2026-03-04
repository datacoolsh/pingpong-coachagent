/**
 * 管理后台页面
 */

import {
    adminGetUsers,
    adminCreateUser,
    adminUpdateUser,
    adminDeleteUser,
    adminGetTasks,
    adminDeleteTask,
    adminGetStats,
    adminGetConfig,
    adminUpdateConfig,
} from '../api/client.js';

export class AdminPage {
    constructor() {
        this.currentTab = 'stats';
        this.users = [];
        this.tasks = [];
        this.stats = null;
        this.configs = [];
    }

    async render() {
        const app = document.getElementById('app');
        app.innerHTML = `
            <div class="admin-page" style="
                background: var(--bg-primary, #1a1a1a);
                min-height: 100vh;
                color: var(--text-primary, #fff);
            ">
                <header style="
                    background: var(--bg-card, #2a2a2a);
                    border-bottom: 1px solid var(--divider, #333);
                    padding: 16px 24px;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                ">
                    <div style="display: flex; align-items: center; gap: 16px;">
                        <a href="#/" style="color: var(--text-secondary, #999); text-decoration: none; font-size: 14px;">< 返回首页</a>
                        <h1 style="font-size: 20px; margin: 0;">管理后台</h1>
                    </div>
                </header>

                <nav style="
                    background: var(--bg-card, #2a2a2a);
                    padding: 0 24px;
                    display: flex;
                    gap: 0;
                    border-bottom: 1px solid var(--divider, #333);
                ">
                    <button class="admin-tab active" data-tab="stats" style="
                        padding: 12px 20px;
                        background: none;
                        border: none;
                        border-bottom: 2px solid var(--accent, #FFB800);
                        color: var(--accent, #FFB800);
                        cursor: pointer;
                        font-size: 14px;
                    ">统计概览</button>
                    <button class="admin-tab" data-tab="users" style="
                        padding: 12px 20px;
                        background: none;
                        border: none;
                        border-bottom: 2px solid transparent;
                        color: var(--text-secondary, #999);
                        cursor: pointer;
                        font-size: 14px;
                    ">用户管理</button>
                    <button class="admin-tab" data-tab="tasks" style="
                        padding: 12px 20px;
                        background: none;
                        border: none;
                        border-bottom: 2px solid transparent;
                        color: var(--text-secondary, #999);
                        cursor: pointer;
                        font-size: 14px;
                    ">任务管理</button>
                    <button class="admin-tab" data-tab="config" style="
                        padding: 12px 20px;
                        background: none;
                        border: none;
                        border-bottom: 2px solid transparent;
                        color: var(--text-secondary, #999);
                        cursor: pointer;
                        font-size: 14px;
                    ">系统配置</button>
                </nav>

                <div id="admin-content" style="padding: 24px; max-width: 1200px; margin: 0 auto;">
                    <div style="text-align: center; padding: 40px; color: var(--text-secondary, #999);">加载中...</div>
                </div>
            </div>
        `;

        this.bindTabEvents();
        this.loadTab('stats');
    }

    bindTabEvents() {
        document.querySelectorAll('.admin-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.admin-tab').forEach(t => {
                    t.style.borderBottomColor = 'transparent';
                    t.style.color = 'var(--text-secondary, #999)';
                });
                tab.style.borderBottomColor = 'var(--accent, #FFB800)';
                tab.style.color = 'var(--accent, #FFB800)';
                this.loadTab(tab.dataset.tab);
            });
        });
    }

    async loadTab(tab) {
        this.currentTab = tab;
        const content = document.getElementById('admin-content');
        content.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-secondary, #999);">加载中...</div>';

        try {
            switch (tab) {
                case 'stats': await this.renderStats(content); break;
                case 'users': await this.renderUsers(content); break;
                case 'tasks': await this.renderTasks(content); break;
                case 'config': await this.renderConfig(content); break;
            }
        } catch (error) {
            content.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--error, #ef4444);">加载失败: ${error.message}</div>`;
        }
    }

    async renderStats(container) {
        const stats = await adminGetStats();
        container.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px;">
                ${this._statCard('总用户数', stats.total_users)}
                ${this._statCard('活跃用户', stats.active_users)}
                ${this._statCard('总任务数', stats.total_tasks)}
                ${this._statCard('已完成', stats.completed_tasks)}
                ${this._statCard('失败任务', stats.failed_tasks)}
            </div>
        `;
    }

    _statCard(label, value) {
        return `
            <div style="
                background: var(--bg-card, #2a2a2a);
                border-radius: 12px;
                padding: 24px;
                border: 1px solid var(--divider, #333);
            ">
                <div style="color: var(--text-secondary, #999); font-size: 13px; margin-bottom: 8px;">${label}</div>
                <div style="font-size: 32px; font-weight: 700; color: var(--accent, #FFB800);">${value}</div>
            </div>
        `;
    }

    async renderUsers(container) {
        const data = await adminGetUsers();
        this.users = data.users;

        container.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                <h2 style="margin: 0; font-size: 18px;">用户列表 (${data.total})</h2>
                <button id="admin-add-user-btn" style="
                    padding: 8px 16px;
                    background: var(--accent, #FFB800);
                    color: #000;
                    border: none;
                    border-radius: 8px;
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: 600;
                ">+ 新增用户</button>
            </div>
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="border-bottom: 1px solid var(--divider, #333);">
                            <th style="padding: 12px; text-align: left; color: var(--text-secondary, #999); font-size: 13px;">用户名</th>
                            <th style="padding: 12px; text-align: left; color: var(--text-secondary, #999); font-size: 13px;">角色</th>
                            <th style="padding: 12px; text-align: left; color: var(--text-secondary, #999); font-size: 13px;">状态</th>
                            <th style="padding: 12px; text-align: left; color: var(--text-secondary, #999); font-size: 13px;">创建时间</th>
                            <th style="padding: 12px; text-align: right; color: var(--text-secondary, #999); font-size: 13px;">操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${this.users.map(u => `
                            <tr style="border-bottom: 1px solid var(--divider, #333);">
                                <td style="padding: 12px; font-size: 14px;">${u.username}</td>
                                <td style="padding: 12px;"><span style="
                                    padding: 2px 8px;
                                    border-radius: 4px;
                                    font-size: 12px;
                                    background: ${u.role === 'admin' ? 'var(--accent, #FFB800)' : '#555'};
                                    color: ${u.role === 'admin' ? '#000' : '#fff'};
                                ">${u.role}</span></td>
                                <td style="padding: 12px; font-size: 14px; color: ${u.is_active ? '#22c55e' : '#ef4444'};">${u.is_active ? '活跃' : '禁用'}</td>
                                <td style="padding: 12px; font-size: 13px; color: var(--text-secondary, #999);">${u.created_at?.slice(0, 10) || '-'}</td>
                                <td style="padding: 12px; text-align: right;">
                                    <button class="admin-toggle-user" data-id="${u.id}" data-active="${u.is_active}" style="
                                        padding: 4px 10px; background: none; border: 1px solid var(--divider, #333);
                                        border-radius: 4px; color: var(--text-secondary, #999); cursor: pointer; font-size: 12px; margin-right: 4px;
                                    ">${u.is_active ? '禁用' : '启用'}</button>
                                    <button class="admin-delete-user" data-id="${u.id}" style="
                                        padding: 4px 10px; background: none; border: 1px solid var(--error, #ef4444);
                                        border-radius: 4px; color: var(--error, #ef4444); cursor: pointer; font-size: 12px;
                                    ">删除</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;

        // 绑定事件
        document.getElementById('admin-add-user-btn')?.addEventListener('click', () => this.showAddUserDialog());
        document.querySelectorAll('.admin-toggle-user').forEach(btn => {
            btn.addEventListener('click', async () => {
                const isActive = btn.dataset.active === 'true';
                await adminUpdateUser(btn.dataset.id, { is_active: !isActive });
                this.loadTab('users');
            });
        });
        document.querySelectorAll('.admin-delete-user').forEach(btn => {
            btn.addEventListener('click', async () => {
                if (confirm('确定删除此用户？')) {
                    await adminDeleteUser(btn.dataset.id);
                    this.loadTab('users');
                }
            });
        });
    }

    showAddUserDialog() {
        const dialog = document.createElement('div');
        dialog.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:1000;';
        dialog.innerHTML = `
            <div style="background: var(--bg-card, #2a2a2a); border-radius: 12px; padding: 24px; width: 360px; border: 1px solid var(--divider, #333);">
                <h3 style="margin: 0 0 20px; color: var(--text-primary, #fff);">新增用户</h3>
                <input id="new-username" placeholder="用户名" style="width:100%;padding:10px;margin-bottom:12px;background:var(--bg-primary,#1a1a1a);border:1px solid var(--divider,#333);border-radius:6px;color:var(--text-primary,#fff);box-sizing:border-box;">
                <input id="new-password" type="password" placeholder="密码" style="width:100%;padding:10px;margin-bottom:12px;background:var(--bg-primary,#1a1a1a);border:1px solid var(--divider,#333);border-radius:6px;color:var(--text-primary,#fff);box-sizing:border-box;">
                <select id="new-role" style="width:100%;padding:10px;margin-bottom:16px;background:var(--bg-primary,#1a1a1a);border:1px solid var(--divider,#333);border-radius:6px;color:var(--text-primary,#fff);box-sizing:border-box;">
                    <option value="user">普通用户</option>
                    <option value="admin">管理员</option>
                </select>
                <div id="new-user-error" style="color:var(--error,#ef4444);font-size:13px;margin-bottom:12px;display:none;"></div>
                <div style="display:flex;gap:8px;justify-content:flex-end;">
                    <button id="new-user-cancel" style="padding:8px 16px;background:none;border:1px solid var(--divider,#333);border-radius:6px;color:var(--text-secondary,#999);cursor:pointer;">取消</button>
                    <button id="new-user-submit" style="padding:8px 16px;background:var(--accent,#FFB800);color:#000;border:none;border-radius:6px;cursor:pointer;font-weight:600;">创建</button>
                </div>
            </div>
        `;
        document.body.appendChild(dialog);

        dialog.querySelector('#new-user-cancel').addEventListener('click', () => dialog.remove());
        dialog.querySelector('#new-user-submit').addEventListener('click', async () => {
            const username = dialog.querySelector('#new-username').value.trim();
            const password = dialog.querySelector('#new-password').value;
            const role = dialog.querySelector('#new-role').value;
            const errorEl = dialog.querySelector('#new-user-error');

            if (!username || !password) {
                errorEl.textContent = '请填写用户名和密码';
                errorEl.style.display = 'block';
                return;
            }
            try {
                await adminCreateUser(username, password, role);
                dialog.remove();
                this.loadTab('users');
            } catch (e) {
                errorEl.textContent = e.message;
                errorEl.style.display = 'block';
            }
        });
    }

    async renderTasks(container) {
        const data = await adminGetTasks();
        container.innerHTML = `
            <h2 style="margin: 0 0 16px; font-size: 18px;">所有任务 (${data.total})</h2>
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="border-bottom: 1px solid var(--divider, #333);">
                            <th style="padding: 12px; text-align: left; color: var(--text-secondary, #999); font-size: 13px;">任务ID</th>
                            <th style="padding: 12px; text-align: left; color: var(--text-secondary, #999); font-size: 13px;">名称</th>
                            <th style="padding: 12px; text-align: left; color: var(--text-secondary, #999); font-size: 13px;">用户</th>
                            <th style="padding: 12px; text-align: left; color: var(--text-secondary, #999); font-size: 13px;">状态</th>
                            <th style="padding: 12px; text-align: left; color: var(--text-secondary, #999); font-size: 13px;">公开</th>
                            <th style="padding: 12px; text-align: left; color: var(--text-secondary, #999); font-size: 13px;">创建时间</th>
                            <th style="padding: 12px; text-align: right; color: var(--text-secondary, #999); font-size: 13px;">操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.tasks.map(t => `
                            <tr style="border-bottom: 1px solid var(--divider, #333);">
                                <td style="padding: 12px; font-size: 13px; font-family: monospace;">${t.task_id}</td>
                                <td style="padding: 12px; font-size: 14px;">${t.name}</td>
                                <td style="padding: 12px; font-size: 13px; color: var(--text-secondary, #999);">${t.user_id || '-'}</td>
                                <td style="padding: 12px;"><span style="
                                    padding: 2px 8px; border-radius: 4px; font-size: 12px;
                                    background: ${t.status === 'completed' ? '#22c55e33' : t.status === 'failed' ? '#ef444433' : '#FFB80033'};
                                    color: ${t.status === 'completed' ? '#22c55e' : t.status === 'failed' ? '#ef4444' : '#FFB800'};
                                ">${t.status}</span></td>
                                <td style="padding: 12px; font-size: 13px;">${t.is_public ? '是' : '否'}</td>
                                <td style="padding: 12px; font-size: 13px; color: var(--text-secondary, #999);">${t.created_at?.slice(0, 10) || '-'}</td>
                                <td style="padding: 12px; text-align: right;">
                                    <button class="admin-delete-task" data-id="${t.task_id}" style="
                                        padding: 4px 10px; background: none; border: 1px solid var(--error, #ef4444);
                                        border-radius: 4px; color: var(--error, #ef4444); cursor: pointer; font-size: 12px;
                                    ">删除</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;

        document.querySelectorAll('.admin-delete-task').forEach(btn => {
            btn.addEventListener('click', async () => {
                if (confirm('确定删除此任务？')) {
                    await adminDeleteTask(btn.dataset.id);
                    this.loadTab('tasks');
                }
            });
        });
    }

    async renderConfig(container) {
        const configs = await adminGetConfig();
        container.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                <h2 style="margin: 0; font-size: 18px;">系统配置</h2>
                <button id="admin-add-config-btn" style="
                    padding: 8px 16px; background: var(--accent, #FFB800); color: #000;
                    border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600;
                ">+ 新增配置</button>
            </div>
            ${configs.length === 0 ? '<p style="color: var(--text-secondary, #999);">暂无配置项</p>' : ''}
            <div style="display: flex; flex-direction: column; gap: 12px;">
                ${configs.map(c => `
                    <div style="
                        background: var(--bg-card, #2a2a2a);
                        border: 1px solid var(--divider, #333);
                        border-radius: 8px;
                        padding: 16px;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    ">
                        <div>
                            <div style="font-weight: 600; font-size: 14px; margin-bottom: 4px;">${c.key}</div>
                            <div style="font-size: 13px; color: var(--text-secondary, #999);">${c.description || ''}</div>
                            <div style="font-size: 13px; font-family: monospace; margin-top: 4px; color: var(--accent, #FFB800);">${c.value}</div>
                        </div>
                        <button class="admin-edit-config" data-key="${c.key}" data-value="${c.value}" data-desc="${c.description || ''}" style="
                            padding: 4px 10px; background: none; border: 1px solid var(--divider, #333);
                            border-radius: 4px; color: var(--text-secondary, #999); cursor: pointer; font-size: 12px;
                        ">编辑</button>
                    </div>
                `).join('')}
            </div>
        `;

        document.getElementById('admin-add-config-btn')?.addEventListener('click', () => this.showConfigDialog());
        document.querySelectorAll('.admin-edit-config').forEach(btn => {
            btn.addEventListener('click', () => {
                this.showConfigDialog(btn.dataset.key, btn.dataset.value, btn.dataset.desc);
            });
        });
    }

    showConfigDialog(key = '', value = '', description = '') {
        const isEdit = !!key;
        const dialog = document.createElement('div');
        dialog.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:1000;';
        dialog.innerHTML = `
            <div style="background: var(--bg-card, #2a2a2a); border-radius: 12px; padding: 24px; width: 400px; border: 1px solid var(--divider, #333);">
                <h3 style="margin: 0 0 20px; color: var(--text-primary, #fff);">${isEdit ? '编辑配置' : '新增配置'}</h3>
                <input id="cfg-key" placeholder="配置键" value="${key}" ${isEdit ? 'disabled' : ''} style="width:100%;padding:10px;margin-bottom:12px;background:var(--bg-primary,#1a1a1a);border:1px solid var(--divider,#333);border-radius:6px;color:var(--text-primary,#fff);box-sizing:border-box;">
                <input id="cfg-value" placeholder="配置值" value="${value}" style="width:100%;padding:10px;margin-bottom:12px;background:var(--bg-primary,#1a1a1a);border:1px solid var(--divider,#333);border-radius:6px;color:var(--text-primary,#fff);box-sizing:border-box;">
                <input id="cfg-desc" placeholder="描述（可选）" value="${description}" style="width:100%;padding:10px;margin-bottom:16px;background:var(--bg-primary,#1a1a1a);border:1px solid var(--divider,#333);border-radius:6px;color:var(--text-primary,#fff);box-sizing:border-box;">
                <div style="display:flex;gap:8px;justify-content:flex-end;">
                    <button id="cfg-cancel" style="padding:8px 16px;background:none;border:1px solid var(--divider,#333);border-radius:6px;color:var(--text-secondary,#999);cursor:pointer;">取消</button>
                    <button id="cfg-submit" style="padding:8px 16px;background:var(--accent,#FFB800);color:#000;border:none;border-radius:6px;cursor:pointer;font-weight:600;">保存</button>
                </div>
            </div>
        `;
        document.body.appendChild(dialog);

        dialog.querySelector('#cfg-cancel').addEventListener('click', () => dialog.remove());
        dialog.querySelector('#cfg-submit').addEventListener('click', async () => {
            const k = dialog.querySelector('#cfg-key').value.trim();
            const v = dialog.querySelector('#cfg-value').value;
            const d = dialog.querySelector('#cfg-desc').value || null;
            if (!k) return;
            await adminUpdateConfig(k, v, d);
            dialog.remove();
            this.loadTab('config');
        });
    }
}
