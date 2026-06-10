#!/usr/bin/env python3
"""
day09/lab/chatbot_server.py
A premium, self-contained chatbot web UI and API server to test the Multi-Agent RAG project.
No external dependencies required (uses built-in http.server, json, and urllib).

To run:
    python chatbot_server.py [port]
"""

import http.server
import json
import os
import sys
import traceback
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Add parent directory to sys.path so we can import graph.py and workers
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from graph import run_graph, save_trace
except ImportError as e:
    print(f"Error importing graph.py: {e}")
    print("Make sure to run this script from the day09/lab directory.")
    sys.exit(1)

# Gorgeous embedded HTML/CSS/JS page with Outfit font, glassmorphism, and neon gradients.
INDEX_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VinAI RAG Multi-Agent Chatbot Tester</title>
    <!-- Modern Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-gradient: linear-gradient(135deg, #0b0f19 0%, #111827 50%, #1e1b4b 100%);
            --panel-bg: rgba(30, 41, 59, 0.45);
            --panel-border: rgba(255, 255, 255, 0.08);
            --accent-primary: #6366f1; /* Indigo */
            --accent-secondary: #a855f7; /* Purple */
            --accent-success: #10b981; /* Emerald */
            --accent-warning: #f59e0b; /* Amber */
            --accent-danger: #ef4444; /* Rose */
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --font-display: 'Outfit', sans-serif;
            --font-body: 'Inter', sans-serif;
            --font-mono: 'Fira Code', monospace;
            --shadow-neon: 0 0 20px rgba(99, 102, 241, 0.15);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: var(--font-body);
            background: var(--bg-gradient);
            background-attachment: fixed;
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }

        /* Header block */
        header {
            background: rgba(15, 23, 42, 0.6);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--panel-border);
            padding: 1.25rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .logo-container {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .logo-icon {
            width: 2.5rem;
            height: 2.5rem;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            border-radius: 0.75rem;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: var(--font-display);
            font-weight: 800;
            font-size: 1.25rem;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
            animation: pulse-glow 3s infinite alternate;
        }

        @keyframes pulse-glow {
            0% { box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4); }
            100% { box-shadow: 0 4px 25px rgba(168, 85, 247, 0.6); }
        }

        .logo-text h1 {
            font-family: var(--font-display);
            font-size: 1.25rem;
            font-weight: 700;
            background: linear-gradient(to right, #ffffff, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .logo-text p {
            font-size: 0.75rem;
            color: var(--text-muted);
            letter-spacing: 0.05em;
        }

        .status-badge {
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: #34d399;
            padding: 0.35rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            background: var(--accent-success);
            border-radius: 50%;
            animation: blink 1.5s infinite;
        }

        @keyframes blink {
            0%, 100% { opacity: 0.4; }
            50% { opacity: 1; }
        }

        /* Layout Grid */
        .workspace {
            display: grid;
            grid-template-columns: 320px 1fr;
            flex-grow: 1;
            height: calc(100vh - 73px);
            overflow: hidden;
        }

        /* Sidebar for controls */
        .sidebar {
            background: rgba(15, 23, 42, 0.3);
            border-right: 1px solid var(--panel-border);
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
            overflow-y: auto;
        }

        .sidebar-title {
            font-family: var(--font-display);
            font-size: 0.875rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .preset-buttons {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }

        .preset-btn {
            background: var(--panel-bg);
            border: 1px solid var(--panel-border);
            color: var(--text-main);
            padding: 0.75rem 1rem;
            border-radius: 0.75rem;
            font-size: 0.825rem;
            text-align: left;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .preset-btn:hover {
            border-color: var(--accent-primary);
            background: rgba(99, 102, 241, 0.08);
            transform: translateX(4px);
        }

        /* Chat container styling */
        .chat-container {
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            height: 100%;
            background: rgba(15, 23, 42, 0.1);
            position: relative;
        }

        .chat-messages {
            flex-grow: 1;
            overflow-y: auto;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        /* Message components */
        .message-row {
            display: flex;
            gap: 1rem;
            max-width: 85%;
            animation: slide-up 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards;
        }

        @keyframes slide-up {
            from { opacity: 0; transform: translateY(12px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .message-row.user {
            align-self: flex-end;
            flex-direction: row-reverse;
        }

        .message-row.bot {
            align-self: flex-start;
        }

        .avatar {
            width: 2.25rem;
            height: 2.25rem;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 0.875rem;
            flex-shrink: 0;
            font-family: var(--font-display);
        }

        .user .avatar {
            background: var(--accent-primary);
            color: #ffffff;
        }

        .bot .avatar {
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            color: #ffffff;
        }

        .message-bubble {
            padding: 1rem 1.25rem;
            border-radius: 1.25rem;
            line-height: 1.6;
            font-size: 0.95rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }

        .user .message-bubble {
            background: var(--accent-primary);
            color: #ffffff;
            border-bottom-right-radius: 0.25rem;
        }

        .bot .message-bubble {
            background: var(--panel-bg);
            border: 1px solid var(--panel-border);
            color: var(--text-main);
            border-bottom-left-radius: 0.25rem;
            width: 100%;
        }

        /* Citation markers */
        .citation-badge {
            background: rgba(99, 102, 241, 0.15);
            border: 1px solid rgba(99, 102, 241, 0.3);
            color: #a5b4fc;
            padding: 0.1rem 0.4rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-family: var(--font-mono);
            margin-left: 0.25rem;
            display: inline-block;
        }

        /* Debug details layout */
        .debug-panel {
            margin-top: 1rem;
            border-top: 1px solid var(--panel-border);
            padding-top: 0.75rem;
        }

        .debug-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            user-select: none;
            padding: 0.25rem 0;
            color: var(--text-muted);
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            transition: color 0.2s;
        }

        .debug-header:hover {
            color: var(--accent-secondary);
        }

        .debug-content {
            display: none;
            margin-top: 0.75rem;
            font-size: 0.85rem;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            animation: expand-down 0.25s ease-out;
        }

        @keyframes expand-down {
            from { opacity: 0; max-height: 0; overflow: hidden; }
            to { opacity: 1; max-height: 1000px; }
        }

        /* Badge groups */
        .badge-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: 0.5rem;
        }

        .debug-badge {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--panel-border);
            padding: 0.4rem 0.6rem;
            border-radius: 0.5rem;
            display: flex;
            flex-direction: column;
            gap: 0.15rem;
        }

        .debug-badge-label {
            font-size: 0.65rem;
            text-transform: uppercase;
            color: var(--text-muted);
            letter-spacing: 0.03em;
        }

        .debug-badge-val {
            font-weight: 600;
            color: var(--text-main);
            font-size: 0.8rem;
        }

        .debug-badge-val.success { color: var(--accent-success); }
        .debug-badge-val.warning { color: var(--accent-warning); }
        .debug-badge-val.danger { color: var(--accent-danger); }
        .debug-badge-val.primary { color: var(--accent-primary); }

        /* Document citations block */
        .sources-block {
            background: rgba(0, 0, 0, 0.15);
            border: 1px solid var(--panel-border);
            border-radius: 0.5rem;
            padding: 0.75rem;
        }

        .sources-title {
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.25rem;
        }

        .source-item {
            margin-bottom: 0.5rem;
            border-bottom: 1px dashed rgba(255, 255, 255, 0.05);
            padding-bottom: 0.5rem;
        }

        .source-item:last-child {
            margin-bottom: 0;
            border-bottom: none;
            padding-bottom: 0;
        }

        .source-name {
            font-family: var(--font-mono);
            font-size: 0.75rem;
            color: #a5b4fc;
            display: flex;
            justify-content: space-between;
        }

        .source-score {
            color: var(--text-muted);
        }

        .source-snippet {
            font-size: 0.775rem;
            color: #cbd5e1;
            margin-top: 0.25rem;
            font-style: italic;
            white-space: pre-wrap;
            border-left: 2px solid var(--accent-primary);
            padding-left: 0.5rem;
        }

        /* Timeline trace flow */
        .trace-timeline {
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
            border-left: 1px solid rgba(255, 255, 255, 0.08);
            padding-left: 0.75rem;
            margin-left: 0.25rem;
        }

        .trace-step {
            font-family: var(--font-mono);
            font-size: 0.725rem;
            color: var(--text-muted);
            position: relative;
        }

        .trace-step::before {
            content: '';
            position: absolute;
            left: -15px;
            top: 5px;
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--accent-secondary);
        }

        /* Input Container styling */
        .chat-input-container {
            padding: 1.5rem 2rem 2rem 2rem;
            background: linear-gradient(to top, rgba(15, 23, 42, 0.8) 70%, rgba(15, 23, 42, 0));
            border-top: 1px solid var(--panel-border);
        }

        .input-wrapper {
            background: rgba(30, 41, 59, 0.6);
            border: 1px solid var(--panel-border);
            border-radius: 1rem;
            padding: 0.5rem 0.75rem 0.5rem 1.25rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            box-shadow: var(--shadow-neon);
            transition: border-color 0.2s, box-shadow 0.2s;
        }

        .input-wrapper:focus-within {
            border-color: var(--accent-primary);
            box-shadow: 0 0 25px rgba(99, 102, 241, 0.3);
        }

        .chat-input {
            flex-grow: 1;
            background: transparent;
            border: none;
            color: var(--text-main);
            font-size: 0.95rem;
            outline: none;
            font-family: var(--font-body);
            padding: 0.5rem 0;
        }

        .chat-input::placeholder {
            color: var(--text-muted);
        }

        .send-btn {
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            border: none;
            color: #ffffff;
            width: 2.5rem;
            height: 2.5rem;
            border-radius: 0.75rem;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: transform 0.2s, opacity 0.2s;
        }

        .send-btn:hover {
            transform: scale(1.05);
        }

        .send-btn:active {
            transform: scale(0.95);
        }

        .send-btn svg {
            width: 1.25rem;
            height: 1.25rem;
            fill: currentColor;
            transform: rotate(-45deg) translate(2px, -2px);
        }

        /* Typing indicator */
        .typing-indicator {
            display: flex;
            gap: 4px;
            align-items: center;
            padding: 0.25rem 0.5rem;
        }

        .typing-dot {
            width: 6px;
            height: 6px;
            background: var(--text-muted);
            border-radius: 50%;
            animation: bounce 1.4s infinite ease-in-out both;
        }

        .typing-dot:nth-child(1) { animation-delay: -0.32s; }
        .typing-dot:nth-child(2) { animation-delay: -0.16s; }

        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }

        /* Scrollbar styling */
        ::-webkit-scrollbar {
            width: 6px;
        }
        ::-webkit-scrollbar-track {
            background: transparent;
        }
        ::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 9999px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.2);
        }
    </style>
</head>
<body>
    <header>
        <div class="logo-container">
            <div class="logo-icon">V</div>
            <div class="logo-text">
                <h1>VinAI Agentic RAG</h1>
                <p>Day 09 & Day 10 System Tester</p>
            </div>
        </div>
        <div class="status-badge">
            <span class="status-dot"></span>
            Agent Engine Ready
        </div>
    </header>

    <div class="workspace">
        <!-- Preset and information panel -->
        <div class="sidebar">
            <div>
                <h2 class="sidebar-title">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-help-circle"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                    Câu Hỏi Mẫu
                </h2>
                <div class="preset-buttons">
                    <button class="preset-btn" onclick="sendPreset('SLA xử lý ticket P1 là bao lâu?')">SLA xử lý ticket P1 là bao lâu?</button>
                    <button class="preset-btn" onclick="sendPreset('Khách hàng Flash Sale yêu cầu hoàn tiền vì lỗi sản phẩm — được không?')">Hoàn tiền đơn hàng Flash Sale?</button>
                    <button class="preset-btn" onclick="sendPreset('Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp. Quy trình là gì?')">Quy trình cấp quyền Level 3?</button>
                    <button class="preset-btn" onclick="sendPreset('Tài khoản bị khóa sau bao nhiêu lần đăng nhập sai?')">Tài khoản bị khóa sau mấy lần nhập sai?</button>
                    <button class="preset-btn" onclick="sendPreset('Làm remote tối đa mấy ngày mỗi tuần?')">Chính sách làm remote thế nào?</button>
                    <button class="preset-btn" onclick="sendPreset('Gặp lỗi ERR-403-AUTH thì giải quyết thế nào?')">Mã lỗi hệ thống ERR-403-AUTH?</button>
                    <button class="preset-btn" onclick="sendPreset('Đơn hàng mua ngày 31/01/2026 yêu cầu hoàn tiền, áp dụng chính sách nào?')">Hoàn tiền đơn hàng 31/01/2026?</button>
                </div>
            </div>

            <div style="margin-top: auto;">
                <h2 class="sidebar-title" style="color: #a5b4fc;">Chỉ dẫn kiểm thử</h2>
                <p style="font-size: 0.75rem; color: var(--text-muted); line-height: 1.5;">
                    Giao diện này gọi trực tiếp đến module <strong>graph.py</strong>. Mỗi phản hồi của Agent sẽ đi kèm trace log đầy đủ chứa các quyết định của Supervisor, thông tin MCP Tools đã gọi, độ trễ và danh sách chunk tri thức được retrieve từ ChromaDB.
                </p>
            </div>
        </div>

        <!-- Main Chat Box -->
        <div class="chat-container">
            <div class="chat-messages" id="chatMessages">
                <!-- Welcome Message -->
                <div class="message-row bot">
                    <div class="avatar">AI</div>
                    <div class="message-bubble">
                        Xin chào! Tôi là Trợ lý IT & CS Helpdesk của VinAI. Hệ thống của chúng ta đang sử dụng mô hình <strong>Multi-Agent Supervisor-Worker</strong>. 
                        <br><br>
                        Bạn có thể chọn một câu hỏi mẫu ở thanh bên trái hoặc tự nhập câu hỏi để kiểm tra khả năng định tuyến của Supervisor, gọi MCP tools, và làm sạch dữ liệu tri thức của hệ thống.
                    </div>
                </div>
            </div>

            <!-- Input bar -->
            <div class="chat-input-container">
                <form id="chatForm" onsubmit="handleChatSubmit(event)">
                    <div class="input-wrapper">
                        <input type="text" id="userInput" class="chat-input" placeholder="Nhập câu hỏi của bạn tại đây..." autocomplete="off" required>
                        <button type="submit" class="send-btn" id="sendBtn">
                            <svg viewBox="0 0 24 24">
                                <path d="M2,21L23,12L2,3V10L17,12L2,14V21Z" />
                            </svg>
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <script>
        const chatMessages = document.getElementById('chatMessages');
        const userInput = document.getElementById('userInput');
        const sendBtn = document.getElementById('sendBtn');

        function sendPreset(text) {
            userInput.value = text;
            chatForm.requestSubmit();
        }

        function toggleDebug(header) {
            const content = header.nextElementSibling;
            const isVisible = content.style.display === 'flex';
            content.style.display = isVisible ? 'none' : 'flex';
            header.querySelector('.arrow').innerText = isVisible ? '▶' : '▼';
        }

        function appendMessage(sender, text, data = null) {
            const row = document.createElement('div');
            row.className = `message-row ${sender}`;
            
            const avatar = document.createElement('div');
            avatar.className = 'avatar';
            avatar.innerText = sender === 'user' ? 'U' : 'AI';

            const bubble = document.createElement('div');
            bubble.className = 'message-bubble';
            
            // Format citations within text e.g. [policy_refund_v4.txt]
            let formattedText = text.replace(/\\\[([\\w\\.-]+)\\\]/g, '<span class="citation-badge">$1</span>');
            bubble.innerHTML = `<div>${formattedText}</div>`;

            if (data) {
                // Generate Debug Details Panel for Bot Answers
                const debugPanel = document.createElement('div');
                debugPanel.className = 'debug-panel';
                
                const debugHeader = document.createElement('div');
                debugHeader.className = 'debug-header';
                debugHeader.onclick = function() { toggleDebug(this); };
                debugHeader.innerHTML = `<span>Trace log chi tiết <span class="arrow">▶</span></span> <span>ID: ${data.run_id || 'N/A'}</span>`;
                
                const debugContent = document.createElement('div');
                debugContent.className = 'debug-content';
                debugContent.style.display = 'none';

                // Badges
                const routeClass = data.supervisor_route === 'human_review' ? 'danger' : (data.supervisor_route === 'policy_tool_worker' ? 'warning' : 'success');
                const riskClass = data.risk_high ? 'danger' : 'success';
                const toolClass = data.needs_tool ? 'warning' : 'primary';

                let badgeGridHtml = `
                    <div class="badge-grid">
                        <div class="debug-badge">
                            <span class="debug-badge-label">Supervisor Route</span>
                            <span class="debug-badge-val ${routeClass}">${data.supervisor_route || 'None'}</span>
                        </div>
                        <div class="debug-badge">
                            <span class="debug-badge-label">Risk High?</span>
                            <span class="debug-badge-val ${riskClass}">${data.risk_high ? 'YES' : 'NO'}</span>
                        </div>
                        <div class="debug-badge">
                            <span class="debug-badge-label">Needs MCP?</span>
                            <span class="debug-badge-val ${toolClass}">${data.needs_tool ? 'YES' : 'NO'}</span>
                        </div>
                        <div class="debug-badge">
                            <span class="debug-badge-label">Confidence</span>
                            <span class="debug-badge-val">${data.confidence !== undefined ? data.confidence : 'N/A'}</span>
                        </div>
                        <div class="debug-badge">
                            <span class="debug-badge-label">Latency</span>
                            <span class="debug-badge-val primary">${data.latency_ms || 0}ms</span>
                        </div>
                    </div>
                `;
                debugContent.innerHTML += badgeGridHtml;

                // Route Reason
                debugContent.innerHTML += `
                    <div style="font-size: 0.775rem; background: rgba(255,255,255,0.02); padding: 0.5rem; border-radius: 4px; border-left: 2px solid var(--accent-secondary);">
                        <strong style="color: var(--text-muted); font-size: 0.65rem; text-transform: uppercase;">Routing Reason:</strong>
                        <div style="margin-top: 0.15rem;">${data.route_reason || 'N/A'}</div>
                    </div>
                `;

                // Trace Timeline
                if (data.history && data.history.length > 0) {
                    let timelineHtml = `
                        <div>
                            <div class="sources-title">Graph Execution Steps</div>
                            <div class="trace-timeline">
                    `;
                    data.history.forEach(step => {
                        timelineHtml += `<div class="trace-step">${step}</div>`;
                    });
                    timelineHtml += `
                            </div>
                        </div>
                    `;
                    debugContent.innerHTML += timelineHtml;
                }

                // MCP Tools Used
                if (data.mcp_tools_used && data.mcp_tools_used.length > 0) {
                    debugContent.innerHTML += `
                        <div style="font-size: 0.775rem; background: rgba(168, 85, 247, 0.05); padding: 0.5rem; border-radius: 4px; border: 1px solid rgba(168, 85, 247, 0.2);">
                            <strong style="color: #d8b4fe; font-size: 0.65rem; text-transform: uppercase;">MCP Tools Called:</strong>
                            <div style="margin-top: 0.25rem; font-family: var(--font-mono);">${data.mcp_tools_used.join(', ')}</div>
                        </div>
                    `;
                }

                // Sources
                if (data.retrieved_chunks && data.retrieved_chunks.length > 0) {
                    let sourcesHtml = `
                        <div class="sources-block">
                            <div class="sources-title">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-database"><polyline points="22 12 16 12 14 15 10 15 8 12 2 12"></polyline><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0 -1.79 1.11z"></path></svg>
                                ChromaDB Context (Dense Semantic Chunks)
                            </div>
                    `;
                    data.retrieved_chunks.forEach((c, idx) => {
                        sourcesHtml += `
                            <div class="source-item">
                                <div class="source-name">
                                    <span>[${idx+1}] ${c.source || 'unknown'}</span>
                                    <span class="source-score">relevance: ${(c.score !== undefined ? c.score : 0.00).toFixed(2)}</span>
                                </div>
                                <div class="source-snippet">${c.text || ''}</div>
                            </div>
                        `;
                    });
                    sourcesHtml += '</div>';
                    debugContent.innerHTML += sourcesHtml;
                }

                debugPanel.appendChild(debugHeader);
                debugPanel.appendChild(debugContent);
                bubble.appendChild(debugPanel);
            }

            row.appendChild(avatar);
            row.appendChild(bubble);
            chatMessages.appendChild(row);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function handleChatSubmit(event) {
            event.preventDefault();
            const text = userInput.value.trim();
            if (!text) return;

            // Append User Message
            appendMessage('user', text);
            userInput.value = '';

            // Append Bot Typing State
            const typingRow = document.createElement('div');
            typingRow.className = 'message-row bot typing-container';
            typingRow.innerHTML = `
                <div class="avatar">AI</div>
                <div class="message-bubble" style="width: auto;">
                    <div class="typing-indicator">
                        <span class="typing-dot"></span>
                        <span class="typing-dot"></span>
                        <span class="typing-dot"></span>
                    </div>
                </div>
            `;
            chatMessages.appendChild(typingRow);
            chatMessages.scrollTop = chatMessages.scrollHeight;

            // Call API
            fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            })
            .then(res => {
                if (!res.ok) throw new Error('API server returned error');
                return res.json();
            })
            .then(data => {
                // Remove Typing Indicator
                const indicators = chatMessages.querySelectorAll('.typing-container');
                indicators.forEach(i => i.remove());

                // Append Bot Answer
                appendMessage('bot', data.final_answer, data);
            })
            .catch(err => {
                console.error(err);
                const indicators = chatMessages.querySelectorAll('.typing-container');
                indicators.forEach(i => i.remove());
                appendMessage('bot', '❌ Đã xảy ra lỗi kết nối với Agent Backend. Vui lòng kiểm tra console server hoặc chạy lại script.');
            });
        }
    </script>
</body>
</html>
"""


class ChatbotHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override to suppress default HTTP logging noise in console
        pass

    def do_OPTIONS(self):
        # Handle CORS
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(INDEX_HTML.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/chat":
            try:
                # Read content length
                content_length = int(self.headers.get("Content-Length", 0))
                post_data = self.rfile.read(content_length)
                req_data = json.loads(post_data.decode("utf-8"))
                query = req_data.get("message", "")

                print(f"[API] Processing Query: '{query}'")

                # Execute graph logic
                state = run_graph(query)

                # Save trace log
                save_trace(state)

                # Format response payload
                response_data = {
                    "final_answer": state.get("final_answer", ""),
                    "supervisor_route": state.get("supervisor_route", ""),
                    "route_reason": state.get("route_reason", ""),
                    "risk_high": state.get("risk_high", False),
                    "needs_tool": state.get("needs_tool", False),
                    "confidence": state.get("confidence", 0.0),
                    "latency_ms": state.get("latency_ms", 0),
                    "history": state.get("history", []),
                    "retrieved_chunks": [
                        {"text": c.get("text", ""), "source": c.get("source", ""), "score": c.get("score", 0.0)}
                        for c in state.get("retrieved_chunks", [])
                    ],
                    "mcp_tools_used": state.get("mcp_tools_used", []),
                    "run_id": state.get("run_id", "")
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode("utf-8"))

            except Exception as e:
                traceback.print_exc()
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                err_response = {"error": str(e), "traceback": traceback.format_exc()}
                self.wfile.write(json.dumps(err_response).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def run(port=8000):
    server_address = ("", port)
    httpd = http.server.HTTPServer(server_address, ChatbotHTTPRequestHandler)
    print("=" * 60)
    print(f"VinAI Chatbot Test Engine started successfully!")
    print(f"Local URL: http://localhost:{port}")
    print("Press Ctrl+C to stop the server.")
    print("=" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Chatbot server...")
        httpd.server_close()
        print("Server stopped.")


if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run(port)
