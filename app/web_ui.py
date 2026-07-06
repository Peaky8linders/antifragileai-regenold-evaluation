from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse

logger = logging.getLogger(__name__)

def register_web_routes(app: FastAPI) -> None:
    """Mounts the interactive Lexy chat UI + avatar routes.

    The chat UI now lives at ``/app`` (the sign-up funnel owns ``/`` —
    see :func:`app.funnel_ui.register_funnel_routes`). After a sign-up /
    sign-in the funnel redirects to ``/app#key=<lexy_sk_...>``; the chat
    reads the key from the URL fragment (never sent to the server) into
    ``localStorage['regenold_api_key']`` and strips the URL.
    """

    # Absolute path to the lexy_avatar.png image in the workspace root
    avatar_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lexy_avatar.png"))

    @app.get("/app", response_class=HTMLResponse)
    def read_web_ui() -> str:
        # SECURITY: never inject the partner API key into the served HTML.
        # This page is reachable unauthenticated on the public endpoint, so
        # baking ``P2P_REGENOLD_API_KEY`` into the markup would leak it to
        # every visitor. The user's own funnel-issued key arrives via the
        # ``#key=`` URL fragment (or is pasted into the config field) and is
        # persisted client-side in localStorage; the browser sends it as the
        # ``X-Regenold-Api-Key`` header on the same-origin ``/api/v1`` call.
        # The template ships with an EMPTY key field.
        return HTML_TEMPLATE

    @app.get("/lexy_avatar.png")
    def get_lexy_avatar() -> FileResponse:
        if not os.path.exists(avatar_path):
            logger.warning("Lexy avatar image not found at expected path: %s", avatar_path)
        return FileResponse(avatar_path)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lexy · Compliance Assistant</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <!-- Lucide Icons -->
    <script src="https://unpkg.com/lucide@latest"></script>
    <!-- Marked.js for Markdown parsing -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <!-- DOMPurify — sanitize model/user markdown before innerHTML (XSS guard, R104) -->
    <script src="https://cdn.jsdelivr.net/npm/dompurify@3.1.7/dist/purify.min.js"></script>
    <style>
        :root {
            --bg-primary: #f8fafc;
            --bg-secondary: #ffffff;
            --bg-glass: #ffffff;
            --bg-glass-hover: #ffffff;
            --accent-cyan: #0ea5e9;
            --accent-cyan-rgb: 14, 165, 233;
            --accent-blue: #3b82f6;
            --accent-glow: rgba(14, 165, 233, 0.18);
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --text-muted: #94a3b8;
            --border-glass: #e2e8f0;
            --border-glow: rgba(14, 165, 233, 0.35);
            --transition-speed: 0.3s;
            --sidebar-width: 320px;
            --rail-width: 252px;
            --rail-collapsed: 72px;
            --drawer-width: 420px;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', system-ui, sans-serif;
            background-color: var(--bg-primary);
            background-image:
                radial-gradient(circle at 0% 0%, rgba(14, 165, 233, 0.06) 0%, transparent 40%),
                radial-gradient(circle at 100% 100%, rgba(59, 130, 246, 0.08) 0%, transparent 50%),
                radial-gradient(circle at 50% 50%, #f1f5f9 0%, #f8fafc 100%);
            background-attachment: fixed;
            color: var(--text-primary);
            height: 100vh;
            display: flex;
            overflow: hidden;
            -webkit-font-smoothing: antialiased;
        }

        /* Scrollbar styles */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: rgba(15, 23, 42, 0.01);
        }
        ::-webkit-scrollbar-thumb {
            background: rgba(15, 23, 42, 0.1);
            border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(14, 165, 233, 0.3);
        }

        /* Layout */
        .sidebar {
            width: var(--sidebar-width);
            background: rgba(255, 255, 255, 0.8);
            border-right: 1px solid var(--border-glass);
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
            z-index: 10;
            backdrop-filter: blur(20px);
        }

        .main-workspace {
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            height: 100%;
            position: relative;
            background: transparent;
        }

        .detail-drawer {
            width: var(--drawer-width);
            background: rgba(255, 255, 255, 0.85);
            border-left: 1px solid var(--border-glass);
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
            z-index: 10;
            backdrop-filter: blur(20px);
            transition: transform var(--transition-speed) cubic-bezier(0.16, 1, 0.3, 1),
                        width var(--transition-speed) cubic-bezier(0.16, 1, 0.3, 1);
            overflow: hidden;
        }

        .detail-drawer.collapsed {
            width: 0;
            transform: translateX(100%);
            border-left: none;
        }

        /* Sidebar content */
        .sidebar-header {
            padding: 24px;
            border-bottom: 1px solid var(--border-glass);
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .logo-container {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .logo-text {
            font-family: 'Instrument Serif', Georgia, serif;
            font-size: 18px;
            font-weight: 700;
            letter-spacing: 0.5px;
            background: linear-gradient(135deg, #0f172a 0%, #0ea5e9 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .logo-badge {
            background: rgba(14, 165, 233, 0.1);
            border: 1px solid rgba(14, 165, 233, 0.3);
            color: var(--accent-cyan);
            font-size: 10px;
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 4px;
            text-transform: uppercase;
        }

        .avatar-widget {
            padding: 24px;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            border-bottom: 1px solid var(--border-glass);
        }

        .avatar-container {
            position: relative;
            margin-bottom: 16px;
        }

        .avatar-glow {
            position: absolute;
            top: -6px;
            left: -6px;
            right: -6px;
            bottom: -6px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(14, 165, 233, 0.22) 0%, transparent 70%);
            z-index: -1;
            animation: pulse-glow 3s infinite ease-in-out;
        }

        .avatar-img {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            border: 2px solid var(--accent-cyan);
            object-fit: cover;
            box-shadow: 0 0 20px rgba(14, 165, 233, 0.2);
            background-color: var(--bg-secondary);
        }

        .status-dot {
            position: absolute;
            bottom: 6px;
            right: 6px;
            width: 12px;
            height: 12px;
            background-color: #10b981;
            border: 2px solid var(--bg-secondary);
            border-radius: 50%;
            box-shadow: 0 0 8px #10b981;
        }

        .avatar-name {
            font-family: 'Instrument Serif', Georgia, serif;
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 4px;
            color: var(--text-primary);
        }

        .avatar-title {
            font-size: 12px;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }

        .system-status {
            padding: 20px;
            flex-grow: 1;
            overflow-y: auto;
        }

        /* Sidebar footer — contact / social / legal */
        .sidebar-footer {
            padding: 16px 20px;
            border-top: 1px solid var(--border-glass);
            display: flex;
            flex-direction: column;
            gap: 12px;
            flex-shrink: 0;
        }
        .sidebar-social {
            display: flex;
            gap: 8px;
        }
        .sidebar-social a {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 30px;
            height: 30px;
            border-radius: 8px;
            border: 1px solid var(--border-glass);
            background: rgba(15, 23, 42, 0.04);
            color: var(--text-muted);
            transition: var(--transition-speed);
        }
        .sidebar-social a:hover {
            color: var(--accent-cyan);
            border-color: var(--border-glow);
        }
        .sidebar-social svg {
            width: 15px;
            height: 15px;
            fill: currentColor;
        }
        .sidebar-legal {
            display: flex;
            flex-wrap: wrap;
            gap: 4px 10px;
        }
        .sidebar-legal a {
            font-size: 11px;
            color: var(--text-muted);
            text-decoration: none;
            transition: color var(--transition-speed);
        }
        .sidebar-legal a:hover {
            color: var(--accent-cyan);
        }

        .section-title {
            font-family: 'Inter', sans-serif;
            font-size: 11px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .diagnostics-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-bottom: 24px;
        }

        .diagnostic-item {
            background: rgba(15, 23, 42, 0.02);
            border: 1px solid var(--border-glass);
            border-radius: 8px;
            padding: 10px 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 12px;
            transition: var(--transition-speed);
        }

        .diagnostic-item:hover {
            background: rgba(15, 23, 42, 0.04);
            border-color: rgba(14, 165, 233, 0.15);
        }

        .diag-label {
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .diag-value {
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .badge-ok {
            color: #10b981;
            background: rgba(16, 185, 129, 0.1);
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid rgba(16, 185, 129, 0.2);
            font-size: 10px;
            font-weight: 600;
        }

        .badge-err {
            color: #ef4444;
            background: rgba(239, 68, 68, 0.1);
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid rgba(239, 68, 68, 0.2);
            font-size: 10px;
            font-weight: 600;
        }

        .badge-loading {
            color: var(--accent-cyan);
            background: rgba(14, 165, 233, 0.1);
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid rgba(14, 165, 233, 0.2);
            font-size: 10px;
            font-weight: 600;
            animation: pulse-glow 1.5s infinite ease-in-out;
        }

        /* Config Widget */
        .config-panel {
            background: rgba(15, 23, 42, 0.02);
            border: 1px solid var(--border-glass);
            border-radius: 8px;
            padding: 14px;
            margin-bottom: 12px;
        }

        .form-group {
            margin-bottom: 12px;
        }

        .form-group:last-child {
            margin-bottom: 0;
        }

        .form-label {
            font-size: 11px;
            color: var(--text-secondary);
            margin-bottom: 6px;
            display: block;
            font-weight: 500;
        }

        .form-checkbox-label {
            font-size: 12px;
            color: var(--text-secondary);
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            user-select: none;
        }

        .form-input {
            width: 100%;
            background: rgba(255, 255, 255, 0.7);
            border: 1px solid var(--border-glass);
            border-radius: 6px;
            padding: 8px 10px;
            color: var(--text-primary);
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            outline: none;
            transition: var(--transition-speed);
        }

        .form-input:focus {
            border-color: var(--accent-cyan);
            box-shadow: 0 0 10px rgba(14, 165, 233, 0.15);
        }

        .checkbox-input {
            appearance: none;
            width: 16px;
            height: 16px;
            border: 1px solid var(--border-glass);
            border-radius: 4px;
            background: rgba(255, 255, 255, 0.7);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: var(--transition-speed);
        }

        .checkbox-input:checked {
            border-color: var(--accent-cyan);
            background: rgba(14, 165, 233, 0.15);
        }

        .checkbox-input:checked::after {
            content: '';
            width: 8px;
            height: 8px;
            background: var(--accent-cyan);
            border-radius: 2px;
            box-shadow: 0 0 5px var(--accent-cyan);
        }

        /* Workspace main */
        .workspace-header {
            padding: 20px 24px;
            border-bottom: 1px solid var(--border-glass);
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(255, 255, 255, 0.5);
            backdrop-filter: blur(10px);
        }

        .workspace-title-block {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .workspace-title {
            font-family: 'Inter', sans-serif;
            font-size: 16px;
            font-weight: 600;
        }

        .workspace-actions {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .btn-action {
            background: rgba(15, 23, 42, 0.04);
            border: 1px solid var(--border-glass);
            color: var(--text-secondary);
            width: 36px;
            height: 36px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: var(--transition-speed);
            outline: none;
        }

        .btn-action:hover, .btn-action.active {
            background: rgba(14, 165, 233, 0.08);
            border-color: var(--accent-cyan);
            color: var(--accent-cyan);
            box-shadow: 0 0 10px rgba(14, 165, 233, 0.1);
        }

        /* Chat view */
        .chat-scroller {
            flex-grow: 1;
            overflow-y: auto;
            padding: 32px 24px;
            display: flex;
            flex-direction: column;
            gap: 24px;
        }

        .message-row {
            display: flex;
            gap: 16px;
            max-width: 800px;
            width: 100%;
        }

        .message-row.user-row {
            align-self: flex-end;
            flex-direction: row-reverse;
        }

        .message-row.assistant-row {
            align-self: flex-start;
        }

        .msg-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            flex-shrink: 0;
            overflow: hidden;
            border: 1px solid var(--border-glass);
            background: var(--bg-secondary);
        }

        .msg-avatar img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .assistant-row .msg-avatar {
            border-color: var(--accent-cyan);
            box-shadow: 0 0 8px rgba(14, 165, 233, 0.2);
        }

        .msg-bubble-container {
            display: flex;
            flex-direction: column;
            gap: 6px;
            max-width: calc(100% - 52px);
        }

        .msg-bubble {
            padding: 14px 18px;
            border-radius: 12px;
            font-size: 14px;
            line-height: 1.5;
            position: relative;
        }

        .user-row .msg-bubble {
            background: #e0f2fe;
            border: 1px solid var(--border-glass);
            border-bottom-right-radius: 2px;
            color: var(--text-primary);
        }

        .assistant-row .msg-bubble {
            background: rgba(255, 255, 255, 0.65);
            border: 1px solid var(--border-glass);
            border-bottom-left-radius: 2px;
            color: var(--text-primary);
        }

        .assistant-row .msg-bubble::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, var(--accent-cyan) 0%, transparent 100%);
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        }

        .msg-meta {
            font-size: 11px;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .user-row .msg-meta {
            justify-content: flex-end;
        }

        /* Markdown formatting inside bubble */
        .msg-bubble p {
            margin-bottom: 10px;
        }

        .msg-bubble p:last-child {
            margin-bottom: 0;
        }

        .msg-bubble ul, .msg-bubble ol {
            margin-left: 20px;
            margin-bottom: 10px;
        }

        .msg-bubble li {
            margin-bottom: 4px;
        }

        .msg-bubble code {
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            background: rgba(15, 23, 42, 0.05);
            padding: 2px 4px;
            border-radius: 4px;
            color: #f43f5e;
        }

        .cite-badge {
            display: inline-block;
            background: rgba(14, 165, 233, 0.15);
            color: var(--accent-cyan);
            border: 1px solid rgba(14, 165, 233, 0.3);
            border-radius: 6px;
            padding: 1px 6px;
            font-size: 12px;
            font-weight: 500;
            margin: 0 2px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .cite-badge:hover {
            background: rgba(14, 165, 233, 0.25);
            border-color: rgba(14, 165, 233, 0.5);
            box-shadow: 0 0 8px rgba(14, 165, 233, 0.2);
        }

        /* Welcome layout */
        .welcome-container {
            max-width: 680px;
            margin: 15px auto auto auto;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            padding: 10px 20px 30px 20px;
        }

        .welcome-icon {
            font-size: 40px;
            margin-bottom: 20px;
            animation: float 4s infinite ease-in-out;
        }

        .welcome-title {
            font-family: 'Instrument Serif', Georgia, serif;
            font-size: 28px;
            font-weight: 800;
            margin-bottom: 12px;
            background: linear-gradient(120deg, #0f172a 0%, #0369a1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .welcome-desc {
            font-size: 14px;
            color: var(--text-secondary);
            margin-bottom: 32px;
            line-height: 1.6;
        }

        .suggestion-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            width: 100%;
        }

        .suggestion-card {
            background: rgba(255, 255, 255, 0.45);
            border: 1px solid var(--border-glass);
            border-radius: 12px;
            padding: 16px;
            text-align: left;
            cursor: pointer;
            transition: var(--transition-speed);
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .suggestion-card:hover {
            background: rgba(255, 255, 255, 0.6);
            border-color: var(--accent-cyan);
            box-shadow: 0 0 15px rgba(14, 165, 233, 0.1);
            transform: translateY(-2px);
        }

        .sug-title {
            font-family: 'Inter', sans-serif;
            font-size: 13px;
            font-weight: 600;
            color: var(--accent-cyan);
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .sug-prompt {
            font-size: 12px;
            color: var(--text-secondary);
            line-height: 1.4;
        }

        /* Input area */
        .input-area {
            padding: 24px;
            border-top: 1px solid var(--border-glass);
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(10px);
        }

        .input-wrapper {
            position: relative;
            max-width: 800px;
            margin: auto;
            display: flex;
            align-items: center;
            background: rgba(255, 255, 255, 0.8);
            border: 1px solid var(--border-glass);
            border-radius: 14px;
            padding: 6px 6px 6px 16px;
            transition: var(--transition-speed);
        }

        .input-wrapper:focus-within {
            border-color: var(--accent-cyan);
            box-shadow: 0 0 20px rgba(14, 165, 233, 0.15);
        }

        .chat-input {
            flex-grow: 1;
            background: transparent;
            border: none;
            color: var(--text-primary);
            font-size: 14px;
            outline: none;
            padding: 10px 0;
            resize: none;
            height: 40px;
            font-family: inherit;
        }

        .btn-send {
            background: linear-gradient(135deg, var(--accent-cyan) 0%, var(--accent-blue) 100%);
            border: none;
            color: #fff;
            width: 40px;
            height: 40px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: var(--transition-speed);
            box-shadow: 0 0 15px rgba(14, 165, 233, 0.3);
            outline: none;
        }

        .btn-send:hover {
            box-shadow: 0 0 25px rgba(14, 165, 233, 0.5);
            transform: scale(1.05);
        }

        .btn-send:disabled {
            background: rgba(15, 23, 42, 0.05);
            color: var(--text-muted);
            box-shadow: none;
            cursor: not-allowed;
            transform: none;
        }

        /* Detail Drawer Content */
        .drawer-header {
            padding: 20px;
            border-bottom: 1px solid var(--border-glass);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .drawer-title {
            font-family: 'Inter', sans-serif;
            font-size: 15px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .drawer-tabs {
            display: flex;
            border-bottom: 1px solid var(--border-glass);
            background: rgba(255, 255, 255, 0.3);
        }

        .drawer-tab {
            flex-grow: 1;
            padding: 12px;
            text-align: center;
            font-size: 12px;
            font-weight: 500;
            color: var(--text-secondary);
            cursor: pointer;
            border-bottom: 2px solid transparent;
            transition: var(--transition-speed);
        }

        .drawer-tab:hover {
            color: var(--text-primary);
            background: rgba(15, 23, 42, 0.01);
        }

        .drawer-tab.active {
            color: var(--accent-cyan);
            border-bottom-color: var(--accent-cyan);
            background: rgba(14, 165, 233, 0.02);
        }

        .drawer-body {
            flex-grow: 1;
            overflow-y: auto;
            padding: 20px;
        }

        .tab-content {
            display: none;
            height: 100%;
        }

        .tab-content.active {
            display: block;
        }

        /* References tab */
        .references-container {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .ref-card {
            background: rgba(15, 23, 42, 0.02);
            border: 1px solid var(--border-glass);
            border-radius: 8px;
            padding: 14px;
            transition: var(--transition-speed);
        }

        .ref-card:hover {
            border-color: rgba(14, 165, 233, 0.15);
            background: rgba(15, 23, 42, 0.03);
        }

        .ref-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
        }

        .ref-title {
            font-family: 'Inter', sans-serif;
            font-size: 13px;
            font-weight: 600;
            color: var(--accent-cyan);
        }

        .ref-badge {
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.2);
            color: var(--accent-blue);
            font-size: 9px;
            padding: 1px 4px;
            border-radius: 3px;
            text-transform: uppercase;
        }

        .ref-desc {
            font-size: 12px;
            color: var(--text-secondary);
            line-height: 1.4;
        }

        /* Reasoning tab — rich structured display */
        .reasoning-scroller {
            height: 100%;
            display: flex;
            flex-direction: column;
            gap: 10px;
            overflow-y: auto;
        }

        .reasoning-header-bar {
            background: rgba(14, 165, 233, 0.05);
            border: 1px solid rgba(14, 165, 233, 0.2);
            border-radius: 8px;
            padding: 10px 14px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-shrink: 0;
        }

        .reasoning-header-bar .schema-ver {
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            color: var(--text-muted);
        }

        .reasoning-model-badge {
            font-family: 'Inter', sans-serif;
            font-size: 11px;
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 20px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .reasoning-model-badge.sonnet {
            background: rgba(14, 165, 233, 0.1);
            border: 1px solid rgba(14, 165, 233, 0.25);
            color: var(--accent-cyan);
        }

        .reasoning-model-badge.opus {
            background: rgba(251, 191, 36, 0.1);
            border: 1px solid rgba(251, 191, 36, 0.3);
            color: #fbbf24;
        }

        .reasoning-model-badge.groq {
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.25);
            color: #10b981;
        }

        .reasoning-model-badge.gemini {
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.25);
            color: #3b82f6;
        }

        .reasoning-section {
            background: rgba(15, 23, 42, 0.02);
            border: 1px solid var(--border-glass);
            border-radius: 8px;
            overflow: hidden;
            flex-shrink: 0;
        }

        .reasoning-section-header {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            font-size: 10px;
            font-family: 'Inter', sans-serif;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 1px solid var(--border-glass);
        }

        .reasoning-section-header.scope-hdr { color: #34d399; background: rgba(52,211,153,0.05); }
        .reasoning-section-header.intent-hdr { color: #60a5fa; background: rgba(96,165,250,0.05); }
        .reasoning-section-header.retrieval-hdr { color: var(--accent-cyan); background: rgba(14, 165, 233,0.04); }
        .reasoning-section-header.graph-hdr { color: #a78bfa; background: rgba(167,139,250,0.05); }
        .reasoning-section-header.guards-hdr { color: #fb923c; background: rgba(251,146,60,0.05); }
        .reasoning-section-header.model-hdr { color: #c084fc; background: rgba(192,132,252,0.05); }
        .reasoning-section-header.subq-hdr { color: #38bdf8; background: rgba(56,189,248,0.05); }
        .reasoning-section-header.notes-hdr { color: #94a3b8; background: rgba(148,163,184,0.03); }

        .reasoning-section-body {
            padding: 10px 14px;
            font-size: 12px;
            line-height: 1.6;
            color: var(--text-secondary);
        }

        .rlog-kv {
            display: flex;
            gap: 8px;
            margin-bottom: 4px;
            align-items: flex-start;
        }

        .rlog-key {
            color: var(--text-muted);
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            min-width: 90px;
            flex-shrink: 0;
            padding-top: 1px;
        }

        .rlog-val {
            color: var(--text-secondary);
            font-size: 12px;
            word-break: break-word;
        }

        .rlog-val.highlight { color: var(--text-primary); }
        .rlog-val.ok { color: #34d399; }
        .rlog-val.warn { color: #fbbf24; }

        .rlog-tag {
            display: inline-block;
            padding: 1px 6px;
            border-radius: 4px;
            font-size: 10px;
            font-family: 'JetBrains Mono', monospace;
            margin: 1px 3px 1px 0;
            background: rgba(15, 23, 42, 0.05);
            border: 1px solid var(--border-glass);
            color: var(--text-secondary);
        }

        .rlog-subq-card {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 6px;
            padding: 8px 10px;
            margin-bottom: 8px;
            border-left: 2px solid rgba(56, 189, 248, 0.4);
        }

        .rlog-subq-card:last-child { margin-bottom: 0; }

        .rlog-subq-q {
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            color: #38bdf8;
            margin-bottom: 6px;
            white-space: pre-wrap;
            word-break: break-word;
        }

        .rlog-note-line {
            font-size: 11px;
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-secondary);
            padding: 3px 0;
            border-bottom: 1px solid rgba(15, 23, 42,0.03);
            word-break: break-word;
            white-space: pre-wrap;
        }

        .rlog-note-line:last-child { border-bottom: none; }

        .rlog-empty {
            color: var(--text-muted);
            font-size: 13px;
            text-align: center;
            margin-top: 40px;
        }

        .reasoning-log-container {
            display: none; /* kept for backward compat but hidden */
        }

        /* Stats tab */
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 14px;
        }

        .stat-card {
            background: rgba(15, 23, 42, 0.02);
            border: 1px solid var(--border-glass);
            border-radius: 10px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .stat-label {
            font-size: 11px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .stat-value {
            font-family: 'Inter', sans-serif;
            font-size: 20px;
            font-weight: 700;
            color: var(--text-primary);
        }

        .stat-value.highlight {
            color: var(--accent-cyan);
            text-shadow: 0 0 10px rgba(14, 165, 233, 0.2);
        }

        .progress-bar-bg {
            background: rgba(15, 23, 42, 0.05);
            height: 4px;
            border-radius: 2px;
            overflow: hidden;
            margin-top: 4px;
        }

        .progress-bar-fill {
            background: linear-gradient(90deg, var(--accent-cyan), var(--accent-blue));
            height: 100%;
            border-radius: 2px;
            width: 0%;
            transition: width 1s ease-out;
        }

        /* Thinking pipeline — animated answer-path progress (ChatGPT / Gemini style).
           Each stage is revealed in turn, held >= 1s, with a shimmering active
           label and a checkmark on completion. */
        .thinking-panel {
            display: flex;
            flex-direction: column;
            min-width: 250px;
        }

        .thinking-head {
            display: flex;
            align-items: center;
            gap: 9px;
            font-family: 'Inter', sans-serif;
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
            letter-spacing: 0.3px;
            margin-bottom: 12px;
        }

        .think-steps {
            display: flex;
            flex-direction: column;
            gap: 3px;
        }

        .think-step {
            display: flex;
            align-items: center;
            gap: 11px;
            padding: 4px 0;
            font-size: 13px;
            opacity: 0;
            transform: translateY(5px);
            transition: opacity 0.4s ease, transform 0.4s ease;
        }

        .think-step.visible {
            opacity: 1;
            transform: none;
        }

        .think-icon {
            width: 16px;
            height: 16px;
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--accent-cyan);
        }

        .thinking-panel .dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--text-muted);
        }

        .thinking-panel .ring,
        .thinking-head .head-ring {
            width: 14px;
            height: 14px;
            border-radius: 50%;
            border: 2px solid rgba(14, 165, 233, 0.18);
            border-top-color: var(--accent-cyan);
            animation: spin 0.7s linear infinite;
        }

        .thinking-head .head-ring {
            width: 13px;
            height: 13px;
            flex-shrink: 0;
        }

        .think-icon .check {
            width: 15px;
            height: 15px;
        }

        .think-label {
            color: var(--text-secondary);
            transition: color 0.3s;
        }

        .think-step.done .think-label {
            color: var(--text-muted);
        }

        .think-step.active .think-label {
            background: linear-gradient(90deg, var(--text-muted) 0%, #f8fafc 30%, var(--accent-cyan) 50%, #f8fafc 70%, var(--text-muted) 100%);
            background-size: 200% auto;
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: shimmer 1.5s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        @keyframes shimmer {
            to { background-position: -200% center; }
        }

        /* Animations */
        @keyframes pulse-glow {
            0%, 100% { opacity: 0.5; transform: scale(1); }
            50% { opacity: 0.8; transform: scale(1.05); }
        }

        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-8px); }
        }

        /* ══════════════════════════════════════════════════════════════
           Antifragile OS shell — fixed pinnable/hideable nav rail,
           multi-view workspace, onboarding + personalized workflow.
           ══════════════════════════════════════════════════════════════ */

        /* ── Fixed side menu (nav rail) ─────────────────────────────── */
        .railnav {
            width: var(--rail-width);
            flex-shrink: 0;
            background: rgba(255, 255, 255, 0.82);
            border-right: 1px solid var(--border-glass);
            backdrop-filter: blur(20px);
            display: flex;
            flex-direction: column;
            z-index: 40;
            position: relative;
            transition: width var(--transition-speed) cubic-bezier(0.16, 1, 0.3, 1);
        }
        .railnav.collapsed { width: var(--rail-collapsed); }
        /* Unpinned + collapsed: expand as an overlay on hover (classic pin behaviour) */
        .railnav.collapsed:not(.pinned):hover {
            width: var(--rail-width);
            box-shadow: 24px 0 48px -24px rgba(15, 23, 42, 0.18);
        }
        .railnav.hidden { width: 0; border-right: none; overflow: hidden; }

        .rail-head {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 18px 16px;
            border-bottom: 1px solid var(--border-glass);
            min-height: 65px;
        }
        .rail-brand { display: flex; align-items: center; gap: 9px; overflow: hidden; flex-grow: 1; min-width: 0; }
        .rail-brand-ico {
            width: 34px; height: 34px; flex-shrink: 0; border-radius: 9px;
            display: flex; align-items: center; justify-content: center;
            background: linear-gradient(135deg, rgba(14,165,233,0.15), rgba(59,130,246,0.12));
            border: 1px solid rgba(14,165,233,0.25);
        }
        .rail-wordmark {
            display: flex; flex-direction: column; line-height: 1.15; white-space: nowrap;
            transition: opacity 0.2s;
        }
        .rail-wordmark .wm-title {
            font-family: 'Instrument Serif', Georgia, serif; font-size: 17px; font-weight: 600;
            letter-spacing: 0.2px; color: var(--text-primary);
        }
        .rail-wordmark .wm-title span { color: var(--accent-cyan); }
        .rail-wordmark .wm-sub { font-size: 10px; font-weight: 600; letter-spacing: 1.4px; text-transform: uppercase; color: var(--text-muted); }
        .rail-collapse {
            flex-shrink: 0; width: 30px; height: 30px; border-radius: 8px; cursor: pointer;
            display: flex; align-items: center; justify-content: center;
            border: 1px solid var(--border-glass); background: rgba(15,23,42,0.02); color: var(--text-muted);
            transition: var(--transition-speed);
        }
        .rail-collapse:hover { color: var(--accent-cyan); border-color: var(--border-glow); }

        .rail-scroll { flex-grow: 1; overflow-y: auto; overflow-x: hidden; padding: 14px 12px; }
        .rail-group-label {
            font-size: 10px; font-weight: 700; letter-spacing: 1.4px; text-transform: uppercase;
            color: var(--text-muted); padding: 6px 12px 8px; white-space: nowrap;
        }
        .rail-nav { display: flex; flex-direction: column; gap: 4px; }
        .nav-item {
            display: flex; align-items: center; gap: 12px;
            padding: 10px 12px; border-radius: 10px; cursor: pointer;
            color: var(--text-secondary); border: 1px solid transparent;
            transition: background 0.18s, color 0.18s, border-color 0.18s;
            position: relative; white-space: nowrap; user-select: none;
        }
        .nav-item:hover { background: rgba(15,23,42,0.04); color: var(--text-primary); }
        .nav-item.active {
            background: rgba(14,165,233,0.10); color: var(--accent-cyan);
            border-color: rgba(14,165,233,0.22); font-weight: 600;
        }
        .nav-item.active::before {
            content: ''; position: absolute; left: -12px; top: 50%; transform: translateY(-50%);
            width: 3px; height: 20px; border-radius: 0 3px 3px 0; background: var(--accent-cyan);
        }
        .nav-ico { width: 20px; height: 20px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; }
        .nav-label { font-size: 13.5px; flex-grow: 1; overflow: hidden; text-overflow: ellipsis; }
        .nav-badge {
            font-size: 10px; font-weight: 700; padding: 1px 7px; border-radius: 999px;
            background: rgba(14,165,233,0.12); color: var(--accent-cyan); flex-shrink: 0;
        }
        .nav-divider { height: 1px; background: var(--border-glass); margin: 12px 6px; }

        /* Collapsed rail: hide labels + center icons. Unpinned peeks on hover;
           pinned stays a locked icon rail with per-item tooltips. */
        .railnav.collapsed .rail-wordmark,
        .railnav.collapsed .rail-group-label,
        .railnav.collapsed .nav-label,
        .railnav.collapsed .nav-badge,
        .railnav.collapsed .rail-lexy-text { display: none; }
        .railnav.collapsed .nav-item { justify-content: center; padding: 10px; }
        .railnav.collapsed .rail-collapse { display: none; }
        .railnav.collapsed .rail-head { justify-content: center; padding: 18px 10px; }
        .railnav.collapsed .rail-brand { justify-content: center; }
        .railnav.collapsed .rail-pin { justify-content: center; }
        .railnav.collapsed .rail-lexy { justify-content: center; padding: 8px; }

        .railnav.collapsed:not(.pinned):hover .rail-wordmark { display: flex; }
        .railnav.collapsed:not(.pinned):hover .rail-group-label { display: block; }
        .railnav.collapsed:not(.pinned):hover .nav-label { display: block; }
        .railnav.collapsed:not(.pinned):hover .nav-badge { display: inline-block; }
        .railnav.collapsed:not(.pinned):hover .rail-lexy-text { display: flex; }
        .railnav.collapsed:not(.pinned):hover .nav-item { justify-content: flex-start; padding: 10px 12px; }
        .railnav.collapsed:not(.pinned):hover .rail-collapse { display: flex; }
        .railnav.collapsed:not(.pinned):hover .rail-head { justify-content: space-between; padding: 18px 16px; }
        .railnav.collapsed:not(.pinned):hover .rail-brand { justify-content: flex-start; }
        .railnav.collapsed:not(.pinned):hover .rail-pin { justify-content: flex-start; }
        .railnav.collapsed:not(.pinned):hover .rail-lexy { justify-content: flex-start; padding: 8px 10px; }

        .railnav.collapsed.pinned .nav-item[data-tip]:hover::after {
            content: attr(data-tip); position: absolute; left: calc(100% + 12px); top: 50%;
            transform: translateY(-50%); background: #0f172a; color: #fff; font-size: 12px; font-weight: 500;
            padding: 5px 10px; border-radius: 7px; white-space: nowrap; z-index: 60;
            box-shadow: 0 8px 20px rgba(15,23,42,0.25); pointer-events: none;
        }

        .rail-foot { padding: 12px; border-top: 1px solid var(--border-glass); display: flex; flex-direction: column; gap: 6px; }
        .rail-lexy {
            display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 10px;
            background: rgba(14,165,233,0.05); border: 1px solid rgba(14,165,233,0.12);
        }
        .rail-lexy-avatar { position: relative; width: 32px; height: 32px; flex-shrink: 0; }
        .rail-lexy-avatar img { width: 32px; height: 32px; border-radius: 50%; object-fit: cover; border: 1.5px solid var(--accent-cyan); }
        .rail-lexy-avatar .dot { position: absolute; bottom: -1px; right: -1px; width: 9px; height: 9px; background: #10b981; border: 2px solid #fff; border-radius: 50%; }
        .rail-lexy-text { display: flex; flex-direction: column; line-height: 1.2; white-space: nowrap; overflow: hidden; }
        .rail-lexy-text .n { font-size: 12.5px; font-weight: 600; color: var(--text-primary); }
        .rail-lexy-text .s { font-size: 10.5px; color: #10b981; font-weight: 500; }
        .rail-pin {
            display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-radius: 9px;
            font-size: 12px; color: var(--text-muted); cursor: pointer; border: 1px solid transparent;
            transition: var(--transition-speed);
        }
        .rail-pin:hover { background: rgba(15,23,42,0.04); color: var(--text-secondary); }
        .rail-pin.on { color: var(--accent-cyan); }
        .rail-pin .pin-state { margin-left: auto; font-weight: 600; font-size: 11px; }

        /* Floating reveal button when the rail is fully hidden */
        .rail-reveal {
            position: fixed; left: 14px; top: 14px; z-index: 50;
            width: 40px; height: 40px; border-radius: 11px; cursor: pointer; display: none;
            align-items: center; justify-content: center; color: var(--accent-cyan);
            background: rgba(255,255,255,0.92); border: 1px solid var(--border-glow);
            box-shadow: 0 8px 22px rgba(15,23,42,0.14); backdrop-filter: blur(10px);
        }
        .rail-reveal.show { display: flex; }

        /* ── Multi-view workspace ───────────────────────────────────── */
        .view { display: none; flex-direction: column; height: 100%; flex-grow: 1; min-width: 0; }
        .view.active { display: flex; }
        .view-head {
            padding: 18px 26px; border-bottom: 1px solid var(--border-glass);
            background: rgba(255,255,255,0.5); backdrop-filter: blur(10px);
            display: flex; align-items: center; justify-content: space-between; gap: 16px;
        }
        .view-head-title { display: flex; align-items: center; gap: 13px; min-width: 0; }
        .view-head-ico {
            width: 38px; height: 38px; border-radius: 10px; flex-shrink: 0;
            display: flex; align-items: center; justify-content: center;
            background: linear-gradient(135deg, rgba(14,165,233,0.12), rgba(59,130,246,0.10));
            border: 1px solid rgba(14,165,233,0.2); color: var(--accent-cyan);
        }
        .view-head h2 { font-family: 'Instrument Serif', Georgia, serif; font-size: 21px; font-weight: 600; line-height: 1.1; }
        .view-head .sub { font-size: 12.5px; color: var(--text-muted); margin-top: 1px; }
        .view-scroll { flex-grow: 1; overflow-y: auto; padding: 26px; }
        .view-inner { max-width: 920px; margin: 0 auto; }

        .panel {
            background: rgba(255,255,255,0.6); border: 1px solid var(--border-glass);
            border-radius: 16px; padding: 22px; margin-bottom: 18px;
        }
        .panel-title { font-size: 13px; font-weight: 700; letter-spacing: 0.4px; color: var(--text-primary); display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
        .panel-lead { font-size: 13px; color: var(--text-secondary); margin-bottom: 16px; line-height: 1.55; }

        .btn-pill {
            display: inline-flex; align-items: center; gap: 7px; padding: 9px 15px; border-radius: 10px;
            font-size: 13px; font-weight: 600; font-family: inherit; cursor: pointer; border: 1px solid var(--border-glass);
            background: rgba(15,23,42,0.03); color: var(--text-secondary); transition: var(--transition-speed);
        }
        .btn-pill:hover { border-color: var(--accent-cyan); color: var(--accent-cyan); background: rgba(14,165,233,0.06); }
        .btn-pill.primary { background: linear-gradient(135deg, var(--accent-cyan), var(--accent-blue)); color: #fff; border: none; box-shadow: 0 8px 20px rgba(14,165,233,0.25); }
        .btn-pill.primary:hover { transform: translateY(-1px); box-shadow: 0 12px 26px rgba(14,165,233,0.35); color: #fff; }

        /* ── Classify & Assess view ─────────────────────────────────── */
        .cls-q {
            border: 1px solid var(--border-glass); border-radius: 12px; padding: 14px 16px; margin-bottom: 10px;
            background: rgba(255,255,255,0.5); transition: var(--transition-speed);
        }
        .cls-q .q-text { font-size: 13.5px; color: var(--text-primary); line-height: 1.5; margin-bottom: 12px; font-weight: 500; }
        .cls-q .q-opts { display: flex; gap: 8px; }
        .seg { display: inline-flex; border: 1px solid var(--border-glass); border-radius: 9px; overflow: hidden; }
        .seg button {
            border: none; background: transparent; padding: 7px 16px; font-size: 12.5px; font-weight: 600; font-family: inherit;
            color: var(--text-muted); cursor: pointer; transition: var(--transition-speed);
        }
        .seg button + button { border-left: 1px solid var(--border-glass); }
        .seg button.yes.on { background: rgba(239,68,68,0.12); color: #dc2626; }
        .seg button.no.on { background: rgba(16,185,129,0.12); color: #059669; }
        .cls-result {
            border-radius: 14px; padding: 20px; margin-top: 4px;
            border: 1px solid var(--border-glow); background: linear-gradient(135deg, rgba(14,165,233,0.06), rgba(59,130,246,0.04));
        }
        .tier-chip {
            display: inline-flex; align-items: center; gap: 7px; padding: 6px 13px; border-radius: 999px;
            font-size: 13px; font-weight: 700; margin-bottom: 12px;
        }
        .tier-prohibited { background: rgba(239,68,68,0.14); color: #dc2626; border: 1px solid rgba(239,68,68,0.3); }
        .tier-high { background: rgba(245,158,11,0.16); color: #d97706; border: 1px solid rgba(245,158,11,0.3); }
        .tier-limited { background: rgba(14,165,233,0.14); color: #0284c7; border: 1px solid rgba(14,165,233,0.3); }
        .tier-minimal { background: rgba(16,185,129,0.14); color: #059669; border: 1px solid rgba(16,185,129,0.3); }
        .tier-gpai { background: rgba(139,92,246,0.14); color: #7c3aed; border: 1px solid rgba(139,92,246,0.3); }
        .cls-result .r-summary { font-size: 13.5px; color: var(--text-primary); line-height: 1.6; margin-bottom: 14px; }
        .obl-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }
        .obl-item { display: flex; gap: 10px; align-items: flex-start; font-size: 13px; color: var(--text-secondary); line-height: 1.5; }
        .obl-item i { color: var(--accent-cyan); flex-shrink: 0; margin-top: 2px; }
        .cls-actions { display: flex; flex-wrap: wrap; gap: 10px; }

        /* ── Agents Hub view ────────────────────────────────────────── */
        .agents-summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
        @media (max-width: 720px) { .agents-summary { grid-template-columns: repeat(2, 1fr); } }
        .sum-card { background: rgba(255,255,255,0.6); border: 1px solid var(--border-glass); border-radius: 13px; padding: 15px; }
        .sum-card .n { font-family: 'Instrument Serif', Georgia, serif; font-size: 27px; font-weight: 600; line-height: 1; color: var(--text-primary); }
        .sum-card .l { font-size: 11.5px; color: var(--text-muted); margin-top: 6px; display: flex; align-items: center; gap: 6px; }
        .agent-card {
            background: rgba(255,255,255,0.62); border: 1px solid var(--border-glass); border-radius: 14px;
            padding: 16px 18px; margin-bottom: 12px; transition: var(--transition-speed);
        }
        .agent-card:hover { border-color: rgba(14,165,233,0.3); box-shadow: 0 6px 18px rgba(15,23,42,0.05); }
        .agent-top { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
        .agent-name { font-size: 15px; font-weight: 600; color: var(--text-primary); display: flex; align-items: center; gap: 9px; }
        .agent-name .a-ico { width: 30px; height: 30px; border-radius: 8px; background: rgba(14,165,233,0.1); display: flex; align-items: center; justify-content: center; color: var(--accent-cyan); flex-shrink: 0; }
        .gov-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px 18px; margin-bottom: 14px; }
        .gov-field { display: flex; flex-direction: column; gap: 3px; }
        .gov-field .k { font-size: 10.5px; font-weight: 600; letter-spacing: 0.4px; text-transform: uppercase; color: var(--text-muted); }
        .gov-field .v { font-size: 13px; color: var(--text-primary); font-weight: 500; }
        .gov-field .v.ok { color: #059669; }
        .gov-field .v.warn { color: #d97706; }
        .gov-field .v.miss { color: #dc2626; }
        .agent-actions { display: flex; flex-wrap: wrap; gap: 8px; padding-top: 12px; border-top: 1px solid var(--border-glass); }
        .link-graph { display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; font-weight: 600; color: var(--accent-cyan); cursor: pointer; padding: 6px 10px; border-radius: 8px; transition: var(--transition-speed); }
        .link-graph:hover { background: rgba(14,165,233,0.08); }

        /* ── Settings view ──────────────────────────────────────────── */
        .settings-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
        @media (max-width: 720px) { .settings-grid { grid-template-columns: 1fr; } }
        .set-links { display: flex; flex-wrap: wrap; gap: 8px 18px; }
        .set-links a { font-size: 13px; color: var(--text-muted); text-decoration: none; transition: color 0.2s; }
        .set-links a:hover { color: var(--accent-cyan); }
        .set-social { display: flex; gap: 8px; margin-bottom: 14px; }
        .set-social a { width: 32px; height: 32px; border-radius: 8px; border: 1px solid var(--border-glass); background: rgba(15,23,42,0.03); color: var(--text-muted); display: inline-flex; align-items: center; justify-content: center; transition: var(--transition-speed); }
        .set-social a:hover { color: var(--accent-cyan); border-color: var(--border-glow); }
        .set-social svg { width: 15px; height: 15px; fill: currentColor; }

        /* ── Onboarding + workflow (rendered inside the Lexy chat) ──── */
        .onb-card { margin-top: 6px; }
        .onb-q { font-size: 14px; color: var(--text-primary); font-weight: 500; margin-bottom: 12px; line-height: 1.5; }
        .chip-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 9px; }
        @media (max-width: 560px) { .chip-grid { grid-template-columns: 1fr; } }
        .chip {
            display: flex; align-items: center; gap: 10px; text-align: left;
            padding: 12px 14px; border-radius: 11px; cursor: pointer; font-family: inherit;
            border: 1px solid var(--border-glass); background: rgba(255,255,255,0.6); transition: var(--transition-speed);
        }
        .chip:hover { border-color: var(--accent-cyan); background: rgba(14,165,233,0.06); transform: translateY(-1px); box-shadow: 0 6px 16px rgba(14,165,233,0.1); }
        .chip .c-ico { width: 34px; height: 34px; border-radius: 9px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; background: rgba(14,165,233,0.1); color: var(--accent-cyan); }
        .chip .c-text { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
        .chip .c-title { font-size: 13.5px; font-weight: 600; color: var(--text-primary); }
        .chip .c-blurb { font-size: 11.5px; color: var(--text-muted); line-height: 1.4; }
        .chip-mini {
            display: inline-flex; align-items: center; gap: 7px; padding: 8px 13px; border-radius: 999px; cursor: pointer;
            font-family: inherit; font-size: 12.5px; font-weight: 600; color: var(--text-secondary);
            border: 1px solid var(--border-glass); background: rgba(255,255,255,0.6); transition: var(--transition-speed);
        }
        .chip-mini:hover { border-color: var(--accent-cyan); color: var(--accent-cyan); background: rgba(14,165,233,0.06); }
        .chip-mini i { color: var(--accent-cyan); }
        .chip-row { display: flex; flex-wrap: wrap; gap: 8px; }

        .workflow-card {
            border: 1px solid var(--border-glow); border-radius: 14px; overflow: hidden;
            background: rgba(255,255,255,0.7); margin-top: 4px;
        }
        .wf-head { padding: 16px 18px; background: linear-gradient(135deg, rgba(14,165,233,0.1), rgba(59,130,246,0.06)); border-bottom: 1px solid var(--border-glass); }
        .wf-mission-label { font-size: 10.5px; font-weight: 700; letter-spacing: 1.4px; text-transform: uppercase; color: var(--accent-cyan); display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
        .wf-mission { font-size: 14.5px; color: var(--text-primary); font-weight: 500; line-height: 1.5; }
        .wf-meta { font-size: 12px; color: var(--text-muted); margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px 12px; }
        .wf-meta b { color: var(--text-secondary); font-weight: 600; }
        .wf-steps { padding: 8px; }
        .wf-step { display: flex; gap: 13px; padding: 12px 12px; border-radius: 11px; transition: var(--transition-speed); }
        .wf-step:hover { background: rgba(14,165,233,0.04); }
        .wf-step + .wf-step { border-top: 1px solid var(--border-glass); }
        .wf-num {
            width: 26px; height: 26px; flex-shrink: 0; border-radius: 8px; font-size: 12.5px; font-weight: 700;
            display: flex; align-items: center; justify-content: center;
            background: rgba(14,165,233,0.12); color: var(--accent-cyan); margin-top: 1px;
        }
        .wf-body { flex-grow: 1; min-width: 0; }
        .wf-title { font-size: 13.5px; font-weight: 600; color: var(--text-primary); margin-bottom: 3px; }
        .wf-detail { font-size: 12.5px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 8px; }
        .wf-refs { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 8px; }
        .wf-actions { display: flex; flex-wrap: wrap; gap: 7px; }
        .wf-btn {
            display: inline-flex; align-items: center; gap: 6px; padding: 5px 11px; border-radius: 8px; cursor: pointer;
            font-family: inherit; font-size: 12px; font-weight: 600; color: var(--accent-cyan);
            border: 1px solid rgba(14,165,233,0.25); background: rgba(14,165,233,0.06); transition: var(--transition-speed);
        }
        .wf-btn:hover { background: rgba(14,165,233,0.14); }
        .wf-btn.ghost { color: var(--text-muted); border-color: var(--border-glass); background: transparent; }
        .wf-btn.ghost:hover { color: var(--text-secondary); background: rgba(15,23,42,0.03); }

        /* Mission banner atop the Lexy view */
        .mission-banner {
            display: none; align-items: center; gap: 12px; margin: 0 auto 4px; max-width: 800px;
            padding: 11px 16px; border-radius: 12px; border: 1px solid var(--border-glow);
            background: linear-gradient(135deg, rgba(14,165,233,0.08), rgba(59,130,246,0.05));
        }
        .mission-banner.show { display: flex; }
        .mission-banner .mb-ico { width: 30px; height: 30px; flex-shrink: 0; border-radius: 8px; display: flex; align-items: center; justify-content: center; background: rgba(14,165,233,0.14); color: var(--accent-cyan); }
        .mission-banner .mb-text { flex-grow: 1; min-width: 0; font-size: 12.5px; color: var(--text-secondary); }
        .mission-banner .mb-text b { color: var(--text-primary); font-weight: 600; }


        /* Floating Lexy Widget */
        #view-lexy {
            position: fixed;
            bottom: 24px;
            right: 24px;
            width: 400px;
            height: 600px;
            max-height: calc(100vh - 48px);
            background: rgba(255, 255, 255, 0.95);
            border: 1px solid var(--border-glass);
            border-radius: 16px;
            box-shadow: 0 12px 40px rgba(0,0,0,0.15);
            z-index: 1000;
            display: flex;
            flex-direction: column;
            transform: translateY(0);
            transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.3s ease;
            opacity: 1;
        }

        #view-lexy.hidden-popup {
            transform: translateY(20px) scale(0.95);
            opacity: 0;
            pointer-events: none;
        }

        .lexy-fab {
            position: fixed;
            bottom: 24px;
            right: 24px;
            width: 60px;
            height: 60px;
            border-radius: 30px;
            background: var(--bg-surface);
            border: 2px solid var(--accent-cyan);
            box-shadow: 0 4px 12px rgba(14, 165, 233, 0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 999;
            transition: transform 0.2s;
        }
        .lexy-fab:hover {
            transform: scale(1.05);
        }
        .lexy-fab img {
            width: 40px;
            height: 40px;
            border-radius: 20px;
        }

        /* ── Responsive ─────────────────────────────────────────────── */
        @media (max-width: 1024px) {
            .rail { transform: translateX(-100%); }
            .rail.pinned { transform: translateX(0); }
            .detail-drawer { position: fixed; top: 0; right: 0; bottom: 0; }
            #view-lexy { width: 100%; height: 100%; bottom: 0; right: 0; border-radius: 0; max-height: none; }
        }
        @media (max-width: 860px) {
            .detail-drawer { position: fixed; top: 0; right: 0; bottom: 0; }
        }
    </style>
</head>
<body>
    <!-- Floating reveal button (shown only when the rail is fully hidden) -->
    <div class="rail-reveal" id="rail-reveal" onclick="showRail()" title="Show menu">
        <i data-lucide="panel-left-open" style="width:18px;height:18px;"></i>
    </div>

    <!-- Fixed side menu (nav rail) -->
    <button class="lexy-fab" onclick="toggleLexy()"><img src="/lexy_avatar.png" alt="Chat"></button>
    <nav class="railnav" id="railnav">
        <div class="rail-head">
            <div class="rail-brand">
                <span class="rail-brand-ico"><i data-lucide="shield-check" style="color: var(--accent-cyan); width: 19px; height: 19px;"></i></span>
                <span class="rail-wordmark">
                    <span class="wm-title">Antifragile<span> OS</span></span>
                    <span class="wm-sub">EU AI Act</span>
                </span>
            </div>
            <div class="rail-collapse" id="rail-collapse" onclick="toggleCollapse()" title="Collapse menu">
                <i data-lucide="panel-left-close" style="width:16px;height:16px;"></i>
            </div>
        </div>

        <div class="rail-scroll">
            <div class="rail-group-label">Workspace</div>
            <div class="rail-nav">
                <div class="nav-item" data-view="lexy" data-tip="Lexy" onclick="switchView('lexy')">
                    <span class="nav-ico"><i data-lucide="sparkles" style="width:19px;height:19px;"></i></span>
                    <span class="nav-label">Lexy</span>
                </div>
                <div class="nav-item active" data-view="classify" data-tip="Classify &amp; Assess" onclick="switchView('classify')">
                    <span class="nav-ico"><i data-lucide="scan-search" style="width:19px;height:19px;"></i></span>
                    <span class="nav-label">Classify &amp; Assess</span>
                </div>
                <div class="nav-item" data-view="agents" data-tip="Agents Hub" onclick="switchView('agents')">
                    <span class="nav-ico"><i data-lucide="boxes" style="width:19px;height:19px;"></i></span>
                    <span class="nav-label">Agents Hub</span>
                </div>
            </div>

            <div class="nav-divider" id="wf-divider" style="display:none;"></div>
            <div class="rail-nav">
                <div class="nav-item" id="nav-workflow" data-tip="My Workflow" style="display:none;" onclick="openMyWorkflow()">
                    <span class="nav-ico"><i data-lucide="route" style="width:19px;height:19px;"></i></span>
                    <span class="nav-label">My Workflow</span>
                    <span class="nav-badge" id="wf-nav-badge"></span>
                </div>
            </div>
        </div>

        <div class="rail-foot">
            <div class="rail-lexy">
                <div class="rail-lexy-avatar">
                    <img src="/lexy_avatar.png" alt="Lexy">
                    <span class="dot"></span>
                </div>
                <div class="rail-lexy-text">
                    <span class="n">Lexy</span>
                    <span class="s" id="rail-status">Online</span>
                </div>
            </div>
            <div class="nav-item" data-view="settings" data-tip="Settings" onclick="switchView('settings')">
                <span class="nav-ico"><i data-lucide="settings" style="width:19px;height:19px;"></i></span>
                <span class="nav-label">Settings</span>
            </div>
            <div class="rail-pin" id="rail-pin" onclick="togglePin()" title="Pin the menu open">
                <span id="rail-pin-ico" style="display:inline-flex;"><i data-lucide="pin" style="width:15px;height:15px;"></i></span>
                <span class="nav-label">Pin menu</span>
                <span class="pin-state" id="pin-state">Off</span>
            </div>
        </div>
    </nav>

    <!-- Main Workspace -->
    <div class="main-workspace">

        <!-- ═══════════════ Lexy view (chat) ═══════════════ -->
        <div class="view hidden-popup" id="view-lexy">
        <div class="workspace-header">
            <div class="workspace-title-block">
                <i data-lucide="sparkles" style="color: var(--accent-cyan); width: 20px; height: 20px;"></i>
                <span class="workspace-title">Lexy</span>
                <span id="lexy-subtitle" style="font-size:12px;color:var(--text-muted);font-weight:500;">EU AI Act Compliance Assistant</span>
            </div>
            <div class="workspace-actions">
                <button id="btn-clear" class="btn-action" title="New conversation">
                    <i data-lucide="plus" style="width: 18px; height: 18px;"></i>
                </button>
                
                <button onclick="toggleLexy()" class="btn-action" title="Close Chat">
                    <i data-lucide="x" style="width: 16px; height: 16px;"></i>
                </button>
                <button id="btn-toggle-drawer" class="btn-action active" title="Toggle Detail Panel">
                    <i data-lucide="panel-right-open" style="width: 16px; height: 16px;"></i>
                </button>
            </div>
        </div>

        <div class="mission-banner" id="mission-banner" style="margin-top:12px;">
            <span class="mb-ico"><i data-lucide="route" style="width:16px;height:16px;"></i></span>
            <span class="mb-text" id="mission-banner-text"></span>
            <button class="btn-pill" style="padding:6px 12px;flex-shrink:0;" onclick="openMyWorkflow()">
                <i data-lucide="list-checks" style="width:14px;height:14px;"></i> View workflow
            </button>
        </div>

        <!-- Chat View -->
        <div class="chat-scroller" id="chat-container">
            <div class="welcome-container" id="welcome-message">
                <h1 class="welcome-title">EU AI Act Workspace</h1>
                <p class="welcome-desc">
                    I am Lexy, your EU AI Act compliance assistant. Ask a question and I will answer with citations to the exact Articles and Annexes.
                </p>
                <div class="suggestion-grid">
                    <div class="suggestion-card" onclick="selectSuggestion('Is a remote biometric identification system prohibited under Article 5?')">
                        <div class="sug-title">
                            <i data-lucide="shield-alert" style="width: 14px; height: 14px;"></i>
                            Prohibitions
                        </div>
                        <div class="sug-prompt">Is a remote biometric identification system prohibited under Article 5?</div>
                    </div>
                    <div class="suggestion-card" onclick="selectSuggestion('What obligations do providers of high-risk systems have under Article 16?')">
                        <div class="sug-title">
                            <i data-lucide="book-open" style="width: 14px; height: 14px;"></i>
                            High-Risk Systems
                        </div>
                        <div class="sug-prompt">What obligations do providers of high-risk systems have under Article 16?</div>
                    </div>
                    <div class="suggestion-card" onclick="selectSuggestion('What are the penalties for non-compliance with the EU AI Act according to Article 99?')">
                        <div class="sug-title">
                            <i data-lucide="gavel" style="width: 14px; height: 14px;"></i>
                            Sanctions
                        </div>
                        <div class="sug-prompt">What are the penalties for non-compliance with the Act under Article 99?</div>
                    </div>
                    <div class="suggestion-card" onclick="selectSuggestion('Does the EU AI Act apply to AI systems used solely for scientific research?')">
                        <div class="sug-title">
                            <i data-lucide="microscope" style="width: 14px; height: 14px;"></i>
                            Exemptions
                        </div>
                        <div class="sug-prompt">Does the EU AI Act apply to systems used solely for scientific research?</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Input Area -->
        <div class="input-area">
            <div class="input-wrapper">
                <input type="text" id="user-input" class="chat-input" placeholder="Ask Lexy a compliance question..." autocomplete="off">
                <button id="btn-send" class="btn-send" disabled>
                    <i data-lucide="send" style="width: 16px; height: 16px;"></i>
                </button>
            </div>
        </div>
        </div><!-- /view-lexy -->

        <!-- ═══════════════ Classify & Assess view ═══════════════ -->
        <div class="view active" id="view-classify">
            <div class="view-head">
                <div class="view-head-title">
                    <span class="view-head-ico"><i data-lucide="scan-search" style="width:20px;height:20px;"></i></span>
                    <div>
                        <h2>Classify &amp; Assess</h2>
                        <div class="sub">Determine your system's risk tier and the obligations that follow</div>
                    </div>
                </div>
                <button class="btn-pill" onclick="resetClassify()"><i data-lucide="rotate-ccw" style="width:15px;height:15px;"></i> Reset</button>
            </div>
            <div class="view-scroll">
                <div class="view-inner">
                    <div class="panel">
                        <div class="panel-title"><i data-lucide="file-text" style="width:16px;height:16px;color:var(--accent-cyan);"></i> Your AI system</div>
                        <div class="panel-lead" id="classify-intro">Answer a few questions about the system's intended purpose. Lexy maps each answer to the operative Articles of Regulation (EU) 2024/1689 and returns a risk tier with the obligations that apply.</div>
                        <input type="text" id="cls-name" class="form-input" style="font-family:inherit;font-size:13px;padding:11px 13px;" placeholder="Name your AI system (e.g. CV screening assistant)">
                    </div>
                    <div class="panel">
                        <div class="panel-title"><i data-lucide="git-branch" style="width:16px;height:16px;color:var(--accent-cyan);"></i> Risk questions</div>
                        <div id="cls-questions"></div>
                    </div>
                    <div id="cls-result-wrap"></div>
                </div>
            </div>
        </div>

        <!-- ═══════════════ Agents Hub view ═══════════════ -->
        <div class="view" id="view-agents">
            <div class="view-head">
                <div class="view-head-title">
                    <span class="view-head-ico"><i data-lucide="boxes" style="width:20px;height:20px;"></i></span>
                    <div>
                        <h2>Agents Hub</h2>
                        <div class="sub">Inventory and governance for every AI system you operate</div>
                    </div>
                </div>
                <button class="btn-pill primary" onclick="switchView('classify')"><i data-lucide="plus" style="width:15px;height:15px;"></i> Classify a system</button>
            </div>
            <div class="view-scroll">
                <div class="view-inner">
                    <div class="agents-summary" id="agents-summary"></div>
                    <div id="agents-list"></div>
                </div>
            </div>
        </div>

        <!-- ═══════════════ Settings view ═══════════════ -->
        <div class="view" id="view-settings">
            <div class="view-head">
                <div class="view-head-title">
                    <span class="view-head-ico"><i data-lucide="settings" style="width:20px;height:20px;"></i></span>
                    <div>
                        <h2>Settings</h2>
                        <div class="sub">Diagnostics, session options and your API key</div>
                    </div>
                </div>
            </div>
            <div class="view-scroll">
                <div class="view-inner">
                    <div class="settings-grid">
                        <div class="panel" style="margin-bottom:0;">
                            <div class="panel-title"><i data-lucide="activity" style="width:16px;height:16px;color:var(--accent-cyan);"></i> System Diagnostics</div>
                            <div class="panel-lead">Live health of the services backing Lexy.</div>
                            <div class="diagnostics-list">
                                <div class="diagnostic-item">
                                    <span class="diag-label"><i data-lucide="server" style="width: 14px; height: 14px;"></i> Core API Status</span>
                                    <span id="diag-api" class="diag-value"><span class="badge-loading">Checking</span></span>
                                </div>
                                <div class="diagnostic-item">
                                    <span class="diag-label"><i data-lucide="brain-circuit" style="width: 14px; height: 14px;"></i> LLM Provider</span>
                                    <span id="diag-llm" class="diag-value"><span class="badge-loading">Checking</span></span>
                                </div>
                                <div class="diagnostic-item">
                                    <span class="diag-label"><i data-lucide="database" style="width: 14px; height: 14px;"></i> Knowledge Graph</span>
                                    <span id="diag-graph" class="diag-value"><span class="badge-loading">Checking</span></span>
                                </div>
                            </div>
                        </div>

                        <div class="panel" style="margin-bottom:0;">
                            <div class="panel-title"><i data-lucide="sliders" style="width:16px;height:16px;color:var(--accent-cyan);"></i> Session Options</div>
                            <div class="panel-lead">Control what the API returns for each answer.</div>
                            <div class="config-panel" style="margin-bottom:0;">
                                <div class="form-group">
                                    <label class="form-checkbox-label">
                                        <input type="checkbox" id="opt-reasoning" class="checkbox-input" checked>
                                        Include Reasoning Trace
                                    </label>
                                </div>
                                <div class="form-group">
                                    <label class="form-checkbox-label">
                                        <input type="checkbox" id="opt-telemetry" class="checkbox-input" checked>
                                        Include Telemetry metrics
                                    </label>
                                </div>
                                <div class="form-group" style="margin-top: 14px;">
                                    <label class="form-label">API Key Header (X-Regenold-Api-Key)</label>
                                    <input type="password" id="cfg-api-key" class="form-input" value="" placeholder="Paste your lexy_sk_... key" autocomplete="off">
                                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 6px; line-height: 1.4;">Stored only in this browser (localStorage). Never sent anywhere except this API.</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="panel" style="margin-top:18px;">
                        <div class="panel-title"><i data-lucide="compass" style="width:16px;height:16px;color:var(--accent-cyan);"></i> Onboarding</div>
                        <div class="panel-lead">Restart the role assessment to generate a fresh personalized workflow.</div>
                        <button class="btn-pill" onclick="restartOnboarding()"><i data-lucide="refresh-cw" style="width:15px;height:15px;"></i> Restart role assessment</button>
                    </div>

                    <div class="panel" style="margin-top:18px;">
                        <div class="set-social">
                            <a href="https://www.linkedin.com/company/antifragile-ai" target="_blank" rel="noopener noreferrer" aria-label="LinkedIn" title="LinkedIn"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg></a>
                            <a href="https://x.com/antifragileai" target="_blank" rel="noopener noreferrer" aria-label="X" title="X"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg></a>
                            <a href="mailto:support@antifragile-ai.net" aria-label="Email" title="Email"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M1.5 8.67v8.58a3 3 0 003 3h15a3 3 0 003-3V8.67l-8.928 5.493a3 3 0 01-3.144 0L1.5 8.67z"/><path d="M22.5 6.908V6.75a3 3 0 00-3-3h-15a3 3 0 00-3 3v.158l9.714 5.978a1.5 1.5 0 001.572 0L22.5 6.908z"/></svg></a>
                        </div>
                        <div class="set-links">
                            <a href="https://antifragile-ai.net/legal/privacy" target="_blank" rel="noopener noreferrer">Privacy</a>
                            <a href="https://antifragile-ai.net/legal/terms" target="_blank" rel="noopener noreferrer">Terms</a>
                            <a href="https://antifragile-ai.net/legal/dpa" target="_blank" rel="noopener noreferrer">DPA</a>
                            <a href="https://antifragile-ai.net/legal/security" target="_blank" rel="noopener noreferrer">Security</a>
                            <a href="https://antifragile-ai.net/contact" target="_blank" rel="noopener noreferrer">Contact</a>
                        </div>
                        <div style="font-size:11px;color:var(--text-muted);margin-top:14px;line-height:1.5;">Lexy provides general guidance on the EU AI Act, not legal advice. Consult qualified counsel for binding compliance decisions.</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Detail Drawer -->
    <div class="detail-drawer" id="detail-drawer">
        <div class="drawer-header">
            <span class="drawer-title">
                <i data-lucide="terminal" style="color: var(--accent-cyan); width: 16px; height: 16px;"></i>
                Execution Diagnostics
            </span>
        </div>

        <div class="drawer-tabs">
            <div class="drawer-tab active" onclick="switchTab('citations')">Citations</div>
            <div class="drawer-tab" onclick="switchTab('reasoning')">Reasoning Log</div>
            <div class="drawer-tab" onclick="switchTab('telemetry')">Telemetry</div>
        </div>

        <div class="drawer-body">
            <!-- Citations Tab -->
            <div id="tab-citations" class="tab-content active">
                <div class="references-container" id="citations-container">
                    <p style="color: var(--text-muted); font-size: 13px; text-align: center; margin-top: 40px;">
                        No citations available. Submit a question to retrieve grounding data.
                    </p>
                </div>
            </div>

            <!-- Reasoning Tab -->
            <div id="tab-reasoning" class="tab-content">
                <div class="reasoning-scroller" id="reasoning-container">
                    <p class="rlog-empty">No reasoning trace captured. Enable "Include Reasoning Trace" before sending.</p>
                </div>
            </div>

            <!-- Telemetry Tab -->
            <div id="tab-telemetry" class="tab-content">
                <div class="references-container">
                    <div class="stats-grid">
                        <div class="stat-card">
                            <span class="stat-label">Confidence Score</span>
                            <span class="stat-value highlight" id="stat-confidence">N/A</span>
                            <div class="progress-bar-bg">
                                <div class="progress-bar-fill" id="gauge-confidence"></div>
                            </div>
                        </div>
                        <div class="stat-card">
                            <span class="stat-label">Retrieval Path</span>
                            <span class="stat-value" id="stat-path" style="font-size: 13px; text-transform: uppercase; color: var(--accent-blue);">N/A</span>
                        </div>
                        <div class="stat-card">
                            <span class="stat-label">Nodes Traversed</span>
                            <span class="stat-value" id="stat-nodes">N/A</span>
                        </div>
                        <div class="stat-card">
                            <span class="stat-label">KB Version</span>
                            <span class="stat-value" id="stat-kb" style="font-size: 12px; font-family: 'JetBrains Mono', monospace;">N/A</span>
                        </div>
                        <div class="stat-card">
                            <span class="stat-label">Obligations Match</span>
                            <span class="stat-value" id="stat-obligations">N/A</span>
                        </div>
                        <div class="stat-card">
                            <span class="stat-label">Gaps Detected</span>
                            <span class="stat-value" id="stat-gaps">N/A</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Init Lucide
        lucide.createIcons();

        // State
        const messages = [];
        let isProcessing = false;

        // Elements
        const chatContainer = document.getElementById('chat-container');
        const userInput = document.getElementById('user-input');
        const btnSend = document.getElementById('btn-send');
        const btnClear = document.getElementById('btn-clear');
        const btnToggleDrawer = document.getElementById('btn-toggle-drawer');
        const detailDrawer = document.getElementById('detail-drawer');
        const welcomeMessage = document.getElementById('welcome-message');

        const cfgApiKey = document.getElementById('cfg-api-key');
        const optReasoning = document.getElementById('opt-reasoning');
        const optTelemetry = document.getElementById('opt-telemetry');

        // R104 — XSS guards. The model `answer`, the user's own input, the
        // references list, and the healthz fields all flow into the DOM. The
        // partner API key lives in localStorage on this same origin, so any
        // unsanitized HTML sink would let injected markup exfiltrate it.
        // escapeHtml() neutralises every interpolated server/user string;
        // renderMarkdown() runs marked through DOMPurify and fails safe to
        // plain text if the sanitizer didn't load.
        function escapeHtml(s) {
            const d = document.createElement('div');
            d.textContent = (s === undefined || s === null) ? '' : String(s);
            return d.innerHTML;
        }
        function renderMarkdown(text) {
            const raw = marked.parse(text || '');
            let safeHtml = window.DOMPurify ? DOMPurify.sanitize(raw) : escapeHtml(text || '');
            
            // Post-process to render citations as interactive badges
            // Match exactly Article N or Annex X with word boundaries
            safeHtml = safeHtml.replace(/\\b(Article\\s+[0-9]+(?:\\.[0-9a-zA-Z]+)?|Annex\\s+[IVXLCDM]+(?:\\.[0-9a-zA-Z]+)?)\\b/gi, '<span class="cite-badge">$1</span>');
            return safeHtml;
        }

        // Persist the partner API key client-side only (localStorage), so the
        // server never has to inject it into the HTML. Restore it on load and
        // save on every edit. Wrapped in try/catch because localStorage can
        // throw in private-browsing / sandboxed iframes.
        const API_KEY_STORAGE = 'regenold_api_key';
        try {
            // R104 — prefer the URL *fragment* (#key=...) over the query
            // string (?key=...). Fragments are never sent to the server, so
            // the partner key cannot land in Railway/uvicorn access logs.
            // Query-param support is kept for backward-compat with existing
            // shared links; in both cases the URL is cleaned immediately.
            const hashParams = new URLSearchParams(window.location.hash.slice(1));
            const urlParams = new URLSearchParams(window.location.search);
            const keyParam = hashParams.get('key') || urlParams.get('key');
            if (keyParam) {
                cfgApiKey.value = keyParam.trim();
                localStorage.setItem(API_KEY_STORAGE, keyParam.trim());
                // Strip both query and fragment so the key isn't shown in the
                // address bar or left behind in browser history.
                window.history.replaceState({}, document.title, window.location.pathname);
            } else {
                const savedKey = localStorage.getItem(API_KEY_STORAGE);
                if (savedKey) cfgApiKey.value = savedKey;
            }
        } catch (e) { /* localStorage unavailable — field stays empty */ }
        cfgApiKey.addEventListener('change', () => {
            try { localStorage.setItem(API_KEY_STORAGE, cfgApiKey.value.trim()); } catch (e) {}
        });

        // References lookup for beautiful details
        const articlesSummary = {
            "Article 5": "Prohibited AI Practices — Catalogues systems presenting unacceptable risks such as cognitive behavioral manipulation, biometric categorization, and real-time biometric identification.",
            "Article 6": "Classification Rules for High-Risk AI Systems — Establishes criteria for systems requiring pre-market conformity assessment based on safety components and Annex III lists.",
            "Article 13": "Transparency and Provision of Information — Mandates high-risk systems to operate with sufficient transparency to enable deployers to interpret outputs and use the system appropriately.",
            "Article 16": "Obligations of Providers of High-Risk Systems — Details core duties including quality management systems, logging, conformity assessments, and CE marking.",
            "Article 26": "Obligations of Deployers of High-Risk Systems — Requires compliance with instructions for use, human oversight, logging, and monitoring of system operations.",
            "Article 52": "Transparency Obligations for Certain AI Systems — Imposes specific notice duties for systems interacting with humans (chatbots), emotion recognition, biometric categorization, and deepfakes.",
            "Article 99": "Penalties and Administrative Fines — Establishes financial sanctions for infringements of prohibitions (up to €35M / 7% turnover) and general obligations.",
            "Annex III": "High-Risk AI Systems — Explicit lists of applications deemed high-risk, including biometrics, critical infrastructure, education, employment, and law enforcement.",
            "Annex IV": "Technical Documentation — Details the required documentation for high-risk systems, including system architecture, risk management, data governance, and monitoring schemes."
        };

        // Event Listeners
        userInput.addEventListener('input', () => {
            btnSend.disabled = userInput.value.trim() === '' || isProcessing;
        });

        userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !btnSend.disabled) {
                sendMessage();
            }
        });

        btnSend.addEventListener('click', sendMessage);

        btnClear.addEventListener('click', () => {
            if (confirm('Clear entire conversation history?')) {
                messages.length = 0;
                chatContainer.innerHTML = '';
                chatContainer.appendChild(welcomeMessage);
                resetDiagnostics();
            }
        });

        btnToggleDrawer.addEventListener('click', () => {
            detailDrawer.classList.toggle('collapsed');
            btnToggleDrawer.classList.toggle('active');
        });

        // Initialize Diagnostics
        checkSystemHealth();

        // Functions
        async function checkSystemHealth() {
            // Healthz Check
            try {
                const res = await fetch('/healthz');
                if (res.ok) {
                    const data = await res.json();
                    document.getElementById('diag-api').innerHTML = `<span class="badge-ok">OK (v${escapeHtml(data.version || '1.0.0')})</span>`;
                } else {
                    document.getElementById('diag-api').innerHTML = '<span class="badge-err">Error</span>';
                }
            } catch (e) {
                document.getElementById('diag-api').innerHTML = '<span class="badge-err">Offline</span>';
            }

            // LLM Check
            try {
                const res = await fetch('/healthz/llm');
                if (res.ok) {
                    const data = await res.json();
                    if (data.llm_ok) {
                        document.getElementById('diag-llm').innerHTML = `<span class="badge-ok" title="${escapeHtml(data.detail || '')}">${escapeHtml(data.provider || 'Ready')}</span>`;
                    } else {
                        document.getElementById('diag-llm').innerHTML = `<span class="badge-err" title="${escapeHtml(data.detail || '')}">Fail</span>`;
                    }
                } else {
                    document.getElementById('diag-llm').innerHTML = '<span class="badge-err">Error</span>';
                }
            } catch (e) {
                document.getElementById('diag-llm').innerHTML = '<span class="badge-err">Offline</span>';
            }

            // Graph Check
            try {
                const res = await fetch('/healthz/graph');
                if (res.ok) {
                    const data = await res.json();
                    if (data.graph_ok) {
                        document.getElementById('diag-graph').innerHTML = `<span class="badge-ok" title="${escapeHtml(data.detail || '')}">Neo4j</span>`;
                    } else {
                        document.getElementById('diag-graph').innerHTML = `<span class="badge-err" title="${escapeHtml(data.detail || '')}">No Conn</span>`;
                    }
                } else {
                    document.getElementById('diag-graph').innerHTML = '<span class="badge-err">Error</span>';
                }
            } catch (e) {
                document.getElementById('diag-graph').innerHTML = '<span class="badge-err">Offline</span>';
            }
        }

        function selectSuggestion(text) {
            userInput.value = text;
            btnSend.disabled = false;
            sendMessage();
        }

        function resetDiagnostics() {
            document.getElementById('citations-container').innerHTML = `
                <p style="color: var(--text-muted); font-size: 13px; text-align: center; margin-top: 40px;">
                    No citations available. Submit a question to retrieve grounding data.
                </p>`;
            document.getElementById('reasoning-container').innerHTML = '<p class="rlog-empty">No reasoning trace captured. Enable "Include Reasoning Trace" before sending.</p>';
            document.getElementById('stat-confidence').innerText = 'N/A';
            document.getElementById('gauge-confidence').style.width = '0%';
            document.getElementById('stat-path').innerText = 'N/A';
            document.getElementById('stat-nodes').innerText = 'N/A';
            document.getElementById('stat-kb').innerText = 'N/A';
            document.getElementById('stat-obligations').innerText = 'N/A';
            document.getElementById('stat-gaps').innerText = 'N/A';
        }

        function switchTab(tabId) {
            document.querySelectorAll('.drawer-tab').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));

            // Activate current
            const tabElements = document.querySelectorAll('.drawer-tab');
            if (tabId === 'citations') tabElements[0].classList.add('active');
            if (tabId === 'reasoning') tabElements[1].classList.add('active');
            if (tabId === 'telemetry') tabElements[2].classList.add('active');

            document.getElementById(`tab-${tabId}`).classList.add('active');
        }

        async function sendMessage() {
            const text = userInput.value.trim();
            if (text === '' || isProcessing) return;

            // Onboarding interception — while Lexy is running the setup session
            // in the chat window, typed input is the user's GOAL, not an API call.
            if (typeof ONB !== 'undefined' && ONB.state === 'awaiting-goal') {
                userInput.value = '';
                btnSend.disabled = true;
                onbGoalText(text);
                return;
            }
            if (typeof ONB !== 'undefined' && ONB.state === 'awaiting-role') {
                userInput.value = '';
                btnSend.disabled = true;
                appendMessage('user', text);
                appendLexyHTML('<div class="onb-q">First, pick the role that fits best so I can tailor everything to you.</div>' + roleChipsHTML());
                return;
            }

            // Remove welcome if present
            if (welcomeMessage.parentNode) {
                welcomeMessage.parentNode.removeChild(welcomeMessage);
            }

            isProcessing = true;
            userInput.value = '';
            btnSend.disabled = true;

            // Append User Bubble
            appendMessage('user', text);
            messages.push({ role: 'user', content: text });

            // Show the animated "thinking" pipeline — a visualisation of the
            // real answer path (input -> scope -> classify -> retrieve -> graph
            // -> ground -> synthesise -> polish -> output). Each stage is held
            // for at least one second so the journey is legible, ChatGPT /
            // Gemini "thinking" style. The request fires in parallel below.
            const pipeline = appendThinkingPipeline();
            chatContainer.scrollTop = chatContainer.scrollHeight;

            // Prepare Request parameters
            const apiKey = cfgApiKey.value.trim();
            if (apiKey) {
                try { localStorage.setItem(API_KEY_STORAGE, apiKey); } catch (e) {}
            }
            const reasoningOpt = optReasoning.checked;
            const telemetryOpt = optTelemetry.checked;

            let url = '/api/v1/regenold/eu-ai-act/ask';
            const params = [];
            if (reasoningOpt) params.push('include_reasoning=true');
            if (telemetryOpt) params.push('include_telemetry=true');
            if (params.length > 0) url += '?' + params.join('&');

            const headers = { 'Content-Type': 'application/json' };
            if (apiKey) {
                headers['X-Regenold-Api-Key'] = apiKey;
            }

            // Fire the request in parallel with the animation. ``settled`` never
            // rejects — it resolves once the request has settled (success OR
            // failure) so the pipeline knows when the answer is ready and the
            // final "Polishing" stage can complete.
            const fetchPromise = fetch(url, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    messages: messages.map(m => ({ role: m.role, content: m.content }))
                })
            });
            const settled = fetchPromise.then(
                (r) => ({ ok: true, response: r }),
                (e) => ({ ok: false, error: e })
            );

            try {
                // Play the full path: resolves after every stage has shown
                // (>= 1s each) AND the response has arrived.
                await pipeline.run(settled);
                pipeline.remove();

                const outcome = await settled;
                if (!outcome.ok) {
                    appendMessage('assistant', `❌ **Connection Failed**: Unable to communicate with the FastAPI backend. Check that the service is running locally.\\n\\n*Detail: ${outcome.error.message}*`);
                } else {
                    const response = outcome.response;
                    if (response.ok) {
                        const data = await response.json();

                        // Render response
                        appendMessage('assistant', data.answer);
                        messages.push({ role: 'assistant', content: data.answer });

                        // Update diagnostics panel
                        updateDiagnostics(data);
                    } else {
                        let errMessage = 'Internal Server Error';
                        try {
                            const errData = await response.json();
                            errMessage = errData.detail?.message || errData.detail || response.statusText;
                        } catch (e) {}
                        appendMessage('assistant', `⚠️ **Error ${response.status}**: ${errMessage}\\n\\nPlease verify your local backend configuration and ensure uvicorn is running.`);
                    }
                }
            } catch (e) {
                pipeline.remove();
                appendMessage('assistant', `❌ **Connection Failed**: Unable to communicate with the FastAPI backend. Check that the service is running locally.\\n\\n*Detail: ${e.message}*`);
            } finally {
                isProcessing = false;
                userInput.focus();
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
        }

        function appendMessage(role, text) {
            const row = document.createElement('div');
            row.className = `message-row ${role}-row`;

            // Avatar
            const avatar = document.createElement('div');
            avatar.className = 'msg-avatar';
            if (role === 'user') {
                avatar.innerHTML = '<i data-lucide="user" style="width: 20px; height: 20px; margin: 7px; color: var(--text-secondary);"></i>';
            } else {
                avatar.innerHTML = '<img src="/lexy_avatar.png" alt="Lexy">';
            }

            const bubbleContainer = document.createElement('div');
            bubbleContainer.className = 'msg-bubble-container';

            const bubble = document.createElement('div');
            bubble.className = 'msg-bubble';
            bubble.innerHTML = renderMarkdown(text);  // R104 — sanitized markdown

            const meta = document.createElement('div');
            meta.className = 'msg-meta';
            const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            meta.innerHTML = `<span>${role === 'user' ? 'You' : 'Lexy'}</span> &bull; <span>${timeStr}</span>`;

            bubbleContainer.appendChild(bubble);
            bubbleContainer.appendChild(meta);
            row.appendChild(avatar);
            row.appendChild(bubbleContainer);
            chatContainer.appendChild(row);

            // Re-render Lucide icons
            lucide.createIcons();
        }

        // PIPELINE_STEPS — the human-readable stages of the real answer path
        // the backend walks for every question: flatten history + parse the
        // question (input) -> scope / jurisdiction gate -> deterministic risk
        // & role classification -> BM25 + KB retrieval -> Neo4j knowledge-graph
        // expansion -> citation grounding -> Stage-2 LLM synthesis -> normalise
        // + tone (polish) -> output. Rendered ChatGPT / Gemini "thinking"
        // style, each stage visible for at least one second.
        const PIPELINE_STEPS = [
            'Reading your question',
            'Checking scope & jurisdiction',
            'Classifying risk & role',
            'Searching the EU AI Act',
            'Traversing the knowledge graph',
            'Grounding citations',
            'Synthesising the answer',
            'Polishing & formatting'
        ];

        // Minimum on-screen time per stage. The spec requires >= 1 second;
        // 1100ms lets the shimmer read as deliberate rather than a flicker.
        const PIPELINE_STEP_MS = 1100;

        // Inline SVG checkmark (no Lucide re-render needed mid-animation).
        // Uses currentColor so the active accent (cyan) flows through.
        const _CHECK_SVG = '<svg class="check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>';

        // Build the animated "thinking" pipeline that replaces the plain typing
        // dots. Returns a controller: ``run(donePromise)`` plays each stage in
        // turn (>= PIPELINE_STEP_MS each) and holds on the final "Polishing"
        // stage until ``donePromise`` settles, so slow Stage-2 LLM requests keep
        // the panel spinning; ``remove()`` tears the row down.
        function appendThinkingPipeline() {
            const row = document.createElement('div');
            row.className = 'message-row assistant-row';

            const avatar = document.createElement('div');
            avatar.className = 'msg-avatar';
            avatar.innerHTML = '<img src="/lexy_avatar.png" alt="Lexy">';

            const bubbleContainer = document.createElement('div');
            bubbleContainer.className = 'msg-bubble-container';

            const bubble = document.createElement('div');
            bubble.className = 'msg-bubble';

            const panel = document.createElement('div');
            panel.className = 'thinking-panel';

            const head = document.createElement('div');
            head.className = 'thinking-head';
            head.innerHTML = '<span class="head-ring"></span><span>Reasoning over the EU AI Act…</span>';

            const stepsWrap = document.createElement('div');
            stepsWrap.className = 'think-steps';

            const stepEls = PIPELINE_STEPS.map((label) => {
                const el = document.createElement('div');
                el.className = 'think-step';
                el.innerHTML = '<span class="think-icon"><span class="dot"></span></span>'
                    + '<span class="think-label">' + escapeHtml(label) + '</span>';
                stepsWrap.appendChild(el);
                return el;
            });

            panel.appendChild(head);
            panel.appendChild(stepsWrap);
            bubble.appendChild(panel);
            bubbleContainer.appendChild(bubble);
            row.appendChild(avatar);
            row.appendChild(bubbleContainer);
            chatContainer.appendChild(row);

            const sleep = (ms) => new Promise((res) => setTimeout(res, ms));

            function setState(el, state) {
                el.classList.add('visible');
                el.classList.remove('active', 'done');
                const icon = el.querySelector('.think-icon');
                if (state === 'active') {
                    el.classList.add('active');
                    icon.innerHTML = '<span class="ring"></span>';
                } else if (state === 'done') {
                    el.classList.add('done');
                    icon.innerHTML = _CHECK_SVG;
                }
            }

            async function run(donePromise) {
                let answered = false;
                Promise.resolve(donePromise).then(() => { answered = true; }, () => { answered = true; });
                for (let i = 0; i < stepEls.length; i++) {
                    setState(stepEls[i], 'active');
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                    await sleep(PIPELINE_STEP_MS);
                    // Hold the final "Polishing" stage until the answer lands so
                    // the panel keeps spinning through slow Stage-2 LLM requests
                    // instead of stalling on a finished checklist.
                    if (i === stepEls.length - 1) {
                        while (!answered) { await sleep(120); }
                    }
                    setState(stepEls[i], 'done');
                }
            }

            function remove() {
                if (row.parentNode) row.parentNode.removeChild(row);
            }

            return { row, run, remove };
        }

        // ── renderReasoningLog ─────────────────────────────────────────────
        // Builds a rich structured display from the JSON reasoning trace payload.
        // Each field gets a dedicated colour-coded section card; notes are shown
        // in full (no truncation) as a timeline log.
        function renderReasoningLog(container, rawReasoning) {
            if (!rawReasoning) {
                container.innerHTML = '<p class="rlog-empty">No detailed reasoning logs returned. Enable "Include Reasoning Trace" in the sidebar.</p>';
                return;
            }

            let trace;
            try { trace = JSON.parse(rawReasoning); }
            catch (e) {
                container.innerHTML = '<p class="rlog-empty">Reasoning payload is not valid JSON.</p>';
                return;
            }

            // Detect which Stage-2 model was used from the notes array.
            // The engine records e.g. "stage2_model=claude-opus-4-8 complex=true"
            // or "stage2_model=claude-sonnet-5 complex=false" in notes.
            let detectedModel = '';
            let isComplex = false;
            (trace.notes || []).forEach(n => {
                const m = n.match(/stage2_model[=:]\\s*(\\S+)/i);
                if (m) detectedModel = m[1];
                if (/complex[=:]?\\s*true/i.test(n)) isComplex = true;
            });
            // Also check stage2_polish landed + complex inference from guards/notes
            if (!detectedModel && trace.stage2_polish) {
                // Fall back to reading the note that records which model was used
                (trace.notes || []).forEach(n => {
                    if (/opus.?4/i.test(n)) detectedModel = 'claude-opus-4';
                    else if (/sonnet/i.test(n)) detectedModel = 'claude-sonnet-5';
                    else if (/groq|llama|qwen/i.test(n)) detectedModel = 'groq';
                });
            }
            if (!detectedModel && trace.stage2_polish === true) detectedModel = 'claude-opus-4-8'; // default
            if (!detectedModel && trace.stage2_polish === false) detectedModel = 'claude-sonnet-5';

            function modelClass(m) {
                if (!m) return 'sonnet';
                if (/opus/i.test(m)) return 'opus';
                if (/groq|llama|qwen|gpt-oss/i.test(m)) return 'groq';
                if (/gemini/i.test(m)) return 'gemini';
                return 'sonnet';
            }

            // R264 — the Stage-2 answer model is Sonnet 5 (simple) or Opus 4.8
            // (complex); Sonnet 4.6 is retired. The prior fallthrough returned
            // 'Sonnet 4.6' for ANY unrecognised string, so the correctly-recorded
            // 'claude-sonnet-5' note rendered as "Sonnet 4.6" in the UI.
            function modelLabel(m) {
                if (!m) return 'Sonnet 5';
                if (/opus.*4.*8/i.test(m)) return '★ Opus 4.8';
                if (/opus/i.test(m)) return '★ Opus';
                if (/sonnet.*4/i.test(m)) return 'Sonnet 4.6';
                if (/sonnet/i.test(m)) return 'Sonnet 5';
                if (/gpt-oss/i.test(m)) return '⚡ Groq GPT-OSS';
                if (/qwen/i.test(m)) return '⚡ Groq Qwen 3.6';
                if (/groq|llama/i.test(m)) return '⚡ Groq';
                if (/gemini/i.test(m)) return '✨ Gemini 3.1';
                return 'Sonnet 5';
            }

            function section(hdrClass, icon, title, bodyHTML) {
                return `<div class="reasoning-section">
                    <div class="reasoning-section-header ${hdrClass}">${icon} ${escapeHtml(title)}</div>
                    <div class="reasoning-section-body">${bodyHTML}</div>
                </div>`;
            }

            function kv(key, valHTML) {
                return `<div class="rlog-kv"><span class="rlog-key">${escapeHtml(key)}</span><span class="rlog-val">${valHTML}</span></div>`;
            }

            function tags(arr) {
                return (arr || []).map(t => `<span class="rlog-tag">${escapeHtml(t)}</span>`).join('');
            }

            const parts = [];

            // ── Header bar ───────────────────────────────────────────────────
            const schemaVer = trace.schema_version || '?';
            const mClass = modelClass(detectedModel);
            const mLabel = modelLabel(detectedModel);
            const complexBadge = isComplex ? ' <span style="font-size:10px;color:#a78bfa">(complex routing)</span>' : '';
            // An LLM model only PRODUCED this answer when Stage-2 actually landed
            // (trace.stage2_polish === true). The "stage2_model=…" note records the
            // model the engine *selected/attempted* BEFORE the call — so when Stage-2
            // fails (provider down / wrapper outage / truncation) the deterministic
            // pipeline produced the answer. Pre-R141 the header always showed the
            // attempted model, so an outage read as "★ Opus 4.8 answered" when Opus
            // never ran. Show the honest answer source instead.
            const stage2Landed = trace.stage2_polish === true;
            let answerBadge;
            if (stage2Landed) {
                answerBadge = `<span class="reasoning-model-badge ${mClass}">${escapeHtml(mLabel)}${complexBadge}</span>`;
            } else {
                const attempted = (trace.stage2_polish === false && detectedModel)
                    ? ` <span style="font-size:10px;color:var(--text-muted)">(Stage-2 ${escapeHtml(mLabel)} did not land)</span>`
                    : '';
                answerBadge = `<span class="reasoning-model-badge" style="background:#3f3f46;color:#d4d4d8">Deterministic</span>${attempted}`;
            }
            parts.push(`<div class="reasoning-header-bar">
                <span class="schema-ver">schema ${escapeHtml(schemaVer)}</span>
                ${answerBadge}
            </div>`);

            // ── Scope ────────────────────────────────────────────────────────
            if (trace.scope && Object.keys(trace.scope).length > 0) {
                const sc = trace.scope;
                const vclass = sc.verdict === 'in_scope' ? 'ok' : sc.verdict === 'out_of_scope' ? 'warn' : '';
                let body = kv('verdict', `<span class="rlog-val ${vclass} highlight">${escapeHtml(sc.verdict || '—')}</span>`);
                if (sc.evidence) body += kv('evidence', escapeHtml(sc.evidence));
                if (sc.near_oos_framework) body += kv('near-oos', `<span class="rlog-val warn">${escapeHtml(sc.near_oos_framework)}</span>`);
                parts.push(section('scope-hdr', '🔍', 'Scope Gate', body));
            }

            // ── Intent ───────────────────────────────────────────────────────
            if (trace.intent_label || trace.compound_roles?.length || trace.query_denoiser?.fired !== undefined) {
                let body = '';
                if (trace.intent_label) body += kv('intent', `<span class="rlog-val highlight">${escapeHtml(trace.intent_label)}</span>`);
                if (trace.compound_roles?.length) body += kv('roles', tags(trace.compound_roles));
                const qd = trace.query_denoiser;
                if (qd && Object.keys(qd).length) {
                    body += kv('denoiser', `<span class="rlog-val ${qd.fired ? 'ok' : ''}">${qd.fired ? 'fired' : 'skipped'}${qd.fallback_reason ? ' (' + escapeHtml(qd.fallback_reason) + ')' : ''}</span>`);
                    if (qd.rewritten_chars) body += kv('rewritten', escapeHtml(String(qd.rewritten_chars)) + ' chars');
                    if (qd.model) body += kv('model', escapeHtml(qd.model));
                }
                if (body) parts.push(section('intent-hdr', '🎯', 'Intent & Query', body));
            }

            // ── Retrieval ────────────────────────────────────────────────────
            if (trace.retrieval_path || trace.anchors_used?.length || trace.references?.length || trace.top_k_bm25?.length) {
                let body = '';
                if (trace.retrieval_path) body += kv('path', `<span class="rlog-val highlight">${escapeHtml(trace.retrieval_path)}</span>`);
                if (trace.anchors_used?.length) body += kv('anchors', tags(trace.anchors_used));
                // R131 — the FINAL wire citations (Article 26 / Article 3.1 /
                // Annex IV.2 — sub-points included), recorded after every
                // reference pass, so the reasoning log shows the exact refs the
                // answer ships, not just the input anchors.
                if (trace.references?.length) body += kv('citations', tags(trace.references));
                if (trace.xref_expand_added?.length) body += kv('xrefs', tags(trace.xref_expand_added));
                if (trace.top_k_bm25?.length) {
                    const hits = trace.top_k_bm25.map(h => `<span class="rlog-tag">${escapeHtml(h.ref || '')} <span style="color:var(--text-muted)">${h.score != null ? h.score.toFixed(1) : ''}</span></span>`).join('');
                    body += kv('BM25 top-k', hits);
                }
                if (trace.engine_confidence != null) body += kv('confidence', `<span class="rlog-val highlight">${trace.engine_confidence.toFixed(3)}</span>`);
                if (trace.cache_hit != null) body += kv('cache', `<span class="rlog-val ${trace.cache_hit ? 'ok' : ''}">${trace.cache_hit ? 'HIT' : 'miss'}</span>`);
                if (body) parts.push(section('retrieval-hdr', '📚', 'Retrieval', body));
            }

            // ── Graph expansion ──────────────────────────────────────────────
            if (trace.graph_2hop_added?.length) {
                const body = kv('2-hop added', tags(trace.graph_2hop_added));
                parts.push(section('graph-hdr', '🕸', 'Graph Expansion', body));
            }

            // ── Guards fired ─────────────────────────────────────────────────
            if (trace.guards_fired?.length) {
                const body = kv('guards', tags(trace.guards_fired));
                parts.push(section('guards-hdr', '🛡', 'Guards Fired', body));
            }

            // ── Stage-2 model ────────────────────────────────────────────────
            if (trace.stage2_polish !== null && trace.stage2_polish !== undefined) {
                // Distinguish "the LLM was attempted but FAILED" (provider error /
                // wrapper outage / truncation → deterministic fallback) from a plain
                // gate-skip, so a provider outage is VISIBLE here instead of being
                // masked as "Opus 4.8 answered".
                const failNote = (trace.notes || []).find(n => /stage2_failed_both_providers|stage2_call_failed/i.test(n));
                const stage2State = stage2Landed
                    ? 'landed'
                    : (failNote ? 'attempted → FAILED → deterministic fallback' : 'skipped → deterministic');
                let body = kv('stage2', `<span class="rlog-val ${stage2Landed ? 'ok' : 'warn'}">${stage2State}</span>`);
                if (detectedModel) {
                    const lbl = stage2Landed ? 'model used' : 'model attempted';
                    const tail = stage2Landed ? '' : ' <span style="color:var(--text-muted);font-size:10px">— did not produce this answer</span>';
                    body += kv(lbl, `<span class="rlog-val highlight reasoning-model-badge ${mClass}" style="padding:2px 6px;font-size:10px">${escapeHtml(modelLabel(detectedModel))}</span>${tail}`);
                }
                if (failNote) body += kv('failure', `<span class="rlog-val warn">${escapeHtml(failNote)}</span>`);
                if (isComplex) body += kv('gate', '<span class="rlog-val" style="color:#a78bfa">complex routing — question complexity gate fired</span>');
                parts.push(section('model-hdr', '✦', 'LLM Stage-2', body));
            }

            // ── Sub-queries (R110 Sufficient-Context) ────────────────────────
            if (trace.sub_queries?.length) {
                let body = '';
                trace.sub_queries.forEach((sq, i) => {
                    const refs = (sq.refs || []).map(r => `<span class="rlog-tag">${escapeHtml(r)}</span>`).join('');
                    body += `<div class="rlog-subq-card">
                        <div class="rlog-subq-q">[${i+1}] ${escapeHtml(sq.q || '')}</div>
                        ${sq.source ? `<div class="rlog-kv"><span class="rlog-key">source</span><span class="rlog-val">${escapeHtml(sq.source)}</span></div>` : ''}
                        ${sq.reason ? `<div class="rlog-kv"><span class="rlog-key">reason</span><span class="rlog-val">${escapeHtml(sq.reason)}</span></div>` : ''}
                        ${refs ? `<div class="rlog-kv"><span class="rlog-key">refs</span><span class="rlog-val">${refs}</span></div>` : ''}
                    </div>`;
                });
                parts.push(section('subq-hdr', '🔄', `Sub-Queries (${trace.sub_queries.length})`, body));
            }

            // ── Notes timeline ───────────────────────────────────────────────
            if (trace.notes?.length) {
                const lines = trace.notes.map(n => `<div class="rlog-note-line">${escapeHtml(n)}</div>`).join('');
                parts.push(section('notes-hdr', '📝', `Engine Notes (${trace.notes.length})`, lines));
            }

            // ── LLM Thinking ─────────────────────────────────────────────────
            if (trace.llm_thinking) {
                if (typeof trace.llm_thinking === 'string') {
                    const thinkingHtml = `<div class="rlog-note-line" style="white-space: pre-wrap; font-family: monospace; font-size: 0.9em; max-height: 400px; overflow-y: auto;">${escapeHtml(trace.llm_thinking)}</div>`;
                    parts.push(section('model-hdr', '🧠', 'LLM Thinking', thinkingHtml));
                } else {
                    for (const [stage, text] of Object.entries(trace.llm_thinking)) {
                        const thinkingHtml = `<div class="rlog-note-line" style="white-space: pre-wrap; font-family: monospace; font-size: 0.9em; max-height: 400px; overflow-y: auto;">${escapeHtml(text)}</div>`;
                        parts.push(section('model-hdr-' + stage.replace(/\\s+/g, '-'), '🧠', `LLM Thinking (${stage})`, thinkingHtml));
                    }
                }
            }

            if (parts.length === 0) {
                container.innerHTML = '<p class="rlog-empty">Trace received but contains no structured fields.</p>';
            } else {
                container.innerHTML = parts.join('');
            }
            // Switch to Reasoning tab automatically so the user sees it
            switchTab('reasoning');
        }

        function updateDiagnostics(data) {
            // Update Citations Tab
            const citationsContainer = document.getElementById('citations-container');
            if (data.references && data.references.length > 0) {
                citationsContainer.innerHTML = '';
                data.references.forEach(ref => {
                    // Extract base article for summary lookup
                    const baseArticleMatch = ref.match(/^(Article \\d+|Annex [IVXLC]+)/);
                    const baseArticle = baseArticleMatch ? baseArticleMatch[1] : null;
                    const description = (baseArticle && articlesSummary[baseArticle]) || "Official reference citation. Grounding logic extracted from the compliance database.";

                    const card = document.createElement('div');
                    card.className = 'ref-card';
                    card.innerHTML = `
                        <div class="ref-header">
                            <span class="ref-title">${escapeHtml(ref)}</span>
                            <span class="ref-badge">Grounded</span>
                        </div>
                        <div class="ref-desc">${escapeHtml(description)}</div>
                    `;
                    citationsContainer.appendChild(card);
                });
            } else {
                citationsContainer.innerHTML = `
                    <p style="color: var(--text-muted); font-size: 13px; text-align: center; margin-top: 40px;">
                        No citations returned for this response.
                    </p>`;
            }

            // Update Telemetry Tab
            const confidenceVal = data.confidence !== undefined && data.confidence !== null ? data.confidence : null;
            if (confidenceVal !== null) {
                document.getElementById('stat-confidence').innerText = confidenceVal.toFixed(2);
                document.getElementById('gauge-confidence').style.width = `${confidenceVal * 100}%`;
            } else {
                document.getElementById('stat-confidence').innerText = 'N/A';
                document.getElementById('gauge-confidence').style.width = '0%';
            }

            document.getElementById('stat-path').innerText = data.retrieval_path || 'N/A';
            document.getElementById('stat-nodes').innerText = data.nodes_traversed !== null && data.nodes_traversed !== undefined ? data.nodes_traversed : 'N/A';
            document.getElementById('stat-kb').innerText = data.kb_version || 'N/A';
            document.getElementById('stat-obligations').innerText = data.obligations_found !== null && data.obligations_found !== undefined ? data.obligations_found : 'N/A';
            document.getElementById('stat-gaps').innerText = data.gaps_found !== null && data.gaps_found !== undefined ? data.gaps_found : 'N/A';

            // Update Reasoning Tab — rich structured renderer
            renderReasoningLog(document.getElementById('reasoning-container'), data.reasoning);
        }

        /* ══════════════════════════════════════════════════════════════
           Antifragile OS shell — nav rail, views, onboarding + workflow.
           All content grounded in Regulation (EU) 2024/1689 (EU AI Act).
           ══════════════════════════════════════════════════════════════ */

        const LEXY_DATA = {
            roles: [
                { id:"provider", label:"Provider", icon:"factory", blurb:"You develop or place an AI system on the EU market under your own name." },
                { id:"deployer", label:"Deployer", icon:"briefcase", blurb:"You use an AI system under your authority in a professional setting." },
                { id:"importer_distributor", label:"Importer / Distributor", icon:"truck", blurb:"You import or make available a system placed on the market by others." },
                { id:"gpai_provider", label:"GPAI Model Provider", icon:"brain-circuit", blurb:"You provide a general-purpose (foundation) AI model." },
                { id:"compliance_legal", label:"Compliance / Legal", icon:"scale", blurb:"You lead compliance, legal or AI risk for your organisation." },
                { id:"product_engineering", label:"Product / Engineering", icon:"code", blurb:"You build or integrate AI features into a product." }
            ],
            goals: [
                { id:"classify", label:"Classify our system's risk", icon:"scan-search" },
                { id:"obligations", label:"Understand our obligations", icon:"list-checks" },
                { id:"conformity", label:"Prepare for conformity assessment", icon:"clipboard-check" },
                { id:"roadmap", label:"Build a compliance roadmap", icon:"route" },
                { id:"gpai", label:"GPAI model obligations", icon:"brain-circuit" }
            ],
            workflows: {
                "provider::default": { mission:"Here is your provider path to a compliant, market-ready high-risk AI system.", steps:[
                    { title:"Classify the system's risk", detail:"Confirm whether the system is prohibited, high-risk or limited-risk before anything else.", refs:["Article 5","Article 6","Annex III"], ask:"Is our AI system high-risk under Article 6 and Annex III?", action:"classify" },
                    { title:"Stand up a risk management system", detail:"Run a continuous, iterative risk process across the whole lifecycle.", refs:["Article 9"], ask:"What does the Article 9 risk management system require?", action:"ask" },
                    { title:"Govern data and documentation", detail:"Meet data governance and draft the technical documentation the Act requires.", refs:["Article 10","Article 11","Annex IV"], ask:"What must our technical documentation contain under Annex IV?", action:"ask" },
                    { title:"Build in oversight and transparency", detail:"Provide human oversight, logging, transparency, accuracy and cybersecurity by design.", refs:["Article 13","Article 14","Article 15"], ask:"What transparency and human oversight duties apply under Articles 13 and 14?", action:"ask" },
                    { title:"Run conformity assessment and CE mark", detail:"Complete conformity assessment, draw up the EU declaration and affix CE marking.", refs:["Article 43","Article 47","Article 48"], ask:"How do we complete conformity assessment under Article 43?", action:"ask" },
                    { title:"Register and monitor post-market", detail:"Register in the EU database and run post-market monitoring and incident reporting.", refs:["Article 49","Article 72","Article 73"], ask:"What are our post-market monitoring duties under Article 72?", action:"ask" }
                ]},
                "provider::classify": { mission:"Let's pin down exactly which risk tier your system falls into and what follows.", steps:[
                    { title:"Screen for prohibited practices", detail:"Rule out the Article 5 bans first; they override everything else.", refs:["Article 5"], ask:"Does our system fall under any Article 5 prohibition?", action:"classify" },
                    { title:"Check Annex III high-risk uses", detail:"See whether your intended purpose is one of the listed high-risk use cases.", refs:["Article 6","Annex III"], ask:"Is our use case listed in Annex III?", action:"classify" },
                    { title:"Check the Annex I product route", detail:"A safety component of a regulated product can be high-risk too.", refs:["Article 6","Annex I"], ask:"Is our system a safety component under Annex I harmonisation law?", action:"ask" },
                    { title:"Confirm transparency duties", detail:"Even limited-risk systems can trigger Article 50 transparency obligations.", refs:["Article 50"], ask:"Do Article 50 transparency duties apply to our system?", action:"ask" },
                    { title:"Record the classification", detail:"Document the tier and the rationale; it drives every downstream obligation.", refs:["Article 6"], ask:"What obligations follow once our system is high-risk?", action:"ask" }
                ]},
                "provider::conformity": { mission:"Here is the route from a classified high-risk system to CE marking.", steps:[
                    { title:"Confirm high-risk status", detail:"Conformity assessment only applies once the system is high-risk.", refs:["Article 6","Annex III"], ask:"Confirm our system is high-risk under Article 6.", action:"classify" },
                    { title:"Complete the technical documentation", detail:"Assemble the full Annex IV file before assessment.", refs:["Article 11","Annex IV"], ask:"What goes in the Annex IV technical documentation?", action:"ask" },
                    { title:"Choose the assessment route", detail:"Internal control or a notified body, depending on the system.", refs:["Article 43","Annex VI","Annex VII"], ask:"Which conformity assessment route applies under Article 43?", action:"ask" },
                    { title:"Draw up the EU declaration of conformity", detail:"Sign the declaration confirming the system meets the requirements.", refs:["Article 47"], ask:"What must the EU declaration of conformity contain under Article 47?", action:"ask" },
                    { title:"Affix CE marking", detail:"Mark the system to signal conformity across the Union market.", refs:["Article 48"], ask:"What are the CE marking rules under Article 48?", action:"ask" },
                    { title:"Register in the EU database", detail:"Register the high-risk system before placing it on the market.", refs:["Article 49"], ask:"How do we register in the EU database under Article 49?", action:"ask" }
                ]},
                "provider::obligations": { mission:"Here are the core provider obligations, in the order they bite.", steps:[
                    { title:"Provider core duties", detail:"The umbrella set of obligations every high-risk provider carries.", refs:["Article 16"], ask:"What are the core provider obligations under Article 16?", action:"ask" },
                    { title:"Quality management system", detail:"Put a documented QMS in place proportionate to your organisation.", refs:["Article 17"], ask:"What must the Article 17 quality management system cover?", action:"ask" },
                    { title:"Technical documentation and logging", detail:"Keep the Annex IV file and automatically generated logs.", refs:["Article 11","Article 12","Annex IV"], ask:"What record-keeping does Article 12 require?", action:"ask" },
                    { title:"Human oversight and transparency", detail:"Design for meaningful oversight and clear information to deployers.", refs:["Article 13","Article 14"], ask:"What transparency information must we give deployers under Article 13?", action:"ask" },
                    { title:"Post-market monitoring and incidents", detail:"Monitor in the field and report serious incidents to authorities.", refs:["Article 72","Article 73"], ask:"When must we report a serious incident under Article 73?", action:"ask" }
                ]},
                "deployer::default": { mission:"Here is your deployer path to using a high-risk system responsibly.", steps:[
                    { title:"Confirm your role and the tier", detail:"Deployers of high-risk systems carry specific duties; confirm the tier first.", refs:["Article 26","Article 6"], ask:"Is the system we deploy high-risk, and what does that mean for us?", action:"classify" },
                    { title:"Use the system as intended", detail:"Follow the provider's instructions and assign competent human oversight.", refs:["Article 26","Article 14"], ask:"What are deployer obligations under Article 26?", action:"ask" },
                    { title:"Run a fundamental rights impact assessment", detail:"Certain deployers must complete a FRIA before putting the system into use.", refs:["Article 27"], ask:"When must a deployer carry out a FRIA under Article 27?", action:"ask" },
                    { title:"Keep logs and monitor", detail:"Retain the automatically generated logs and monitor operation.", refs:["Article 26","Article 12"], ask:"What logging must a deployer keep under Article 26?", action:"ask" },
                    { title:"Inform affected people", detail:"Tell people when the system informs decisions that affect them.", refs:["Article 26","Article 50"], ask:"When must we inform people affected by an AI decision?", action:"ask" },
                    { title:"Ensure AI literacy", detail:"Make sure staff operating the AI have sufficient AI literacy.", refs:["Article 4"], ask:"What does the Article 4 AI literacy duty require?", action:"ask" }
                ]},
                "importer_distributor::default": { mission:"Here is your path to placing others' AI systems on the market safely.", steps:[
                    { title:"Verify provider compliance", detail:"Check CE marking, the declaration of conformity and documentation before you act.", refs:["Article 23","Article 24"], ask:"What must an importer verify under Article 23?", action:"ask" },
                    { title:"Meet importer duties", detail:"Confirm conformity, keep records and cooperate with authorities.", refs:["Article 23"], ask:"What are importer obligations under Article 23?", action:"ask" },
                    { title:"Meet distributor duties", detail:"Check the marking and act on any non-conformity you find.", refs:["Article 24"], ask:"What are distributor obligations under Article 24?", action:"ask" },
                    { title:"Watch for a role change", detail:"Renaming or substantially modifying a system can make you the provider.", refs:["Article 25"], ask:"When do we become a provider under Article 25?", action:"ask" },
                    { title:"Cooperate and report", detail:"Work with market surveillance authorities and take corrective action.", refs:["Article 23","Article 24"], ask:"What corrective action must we take on a non-conforming system?", action:"ask" }
                ]},
                "gpai_provider::default": { mission:"Here is your path for a general-purpose AI model provider.", steps:[
                    { title:"Confirm GPAI classification", detail:"Determine if your model is general-purpose and whether it carries systemic risk.", refs:["Article 51"], ask:"Is our model a GPAI model with systemic risk under Article 51?", action:"classify" },
                    { title:"Meet GPAI provider obligations", detail:"Documentation, downstream information, a copyright policy and a training-data summary.", refs:["Article 53"], ask:"What obligations apply to GPAI model providers under Article 53?", action:"ask" },
                    { title:"Handle systemic-risk duties", detail:"If systemic, add model evaluation, risk mitigation, incident tracking and cybersecurity.", refs:["Article 55"], ask:"What extra duties apply to GPAI models with systemic risk under Article 55?", action:"ask" },
                    { title:"Follow the codes of practice", detail:"Codes of practice are the primary route to show compliance until standards land.", refs:["Article 56"], ask:"How do the Article 56 codes of practice work?", action:"ask" },
                    { title:"Track the fine-tune threshold", detail:"Downstream modifiers can become the provider once added compute passes one third.", refs:["Article 25"], ask:"When does fine-tuning make us a new provider?", action:"ask" }
                ]},
                "compliance_legal::default": { mission:"Here is an organisation-wide roadmap to EU AI Act readiness.", steps:[
                    { title:"Map your AI portfolio", detail:"Inventory every AI system, its role and its risk tier.", refs:["Article 6"], ask:"How should we classify our AI systems' risk tiers?", action:"classify" },
                    { title:"Establish governance and literacy", detail:"Assign accountability and meet the AI literacy duty across the organisation.", refs:["Article 4"], ask:"What does the Article 4 AI literacy duty require of us?", action:"ask" },
                    { title:"Track the timeline", detail:"Prohibitions, GPAI and high-risk duties apply on staggered dates; plan against them.", refs:["Article 113"], ask:"What are the EU AI Act application dates under Article 113?", action:"ask" },
                    { title:"Close high-risk gaps", detail:"For each high-risk system, verify Articles 9 to 15 are met.", refs:["Article 9","Article 15"], ask:"What are the Chapter III requirements for high-risk systems?", action:"ask" },
                    { title:"Prepare for enforcement", detail:"Understand penalties and set up serious-incident reporting.", refs:["Article 72","Article 73","Article 99"], ask:"What are the penalties for non-compliance under Article 99?", action:"ask" }
                ]},
                "product_engineering::default": { mission:"Here is how to ship an AI feature that meets the Act by design.", steps:[
                    { title:"Classify the feature", detail:"Decide the risk tier of the AI feature you are building.", refs:["Article 6","Annex III"], ask:"What risk tier is our AI feature under Article 6 and Annex III?", action:"classify" },
                    { title:"Govern your data", detail:"Meet training, validation and testing data quality and governance rules.", refs:["Article 10"], ask:"What are the Article 10 data governance requirements?", action:"ask" },
                    { title:"Logging and documentation", detail:"Design in automatic logging and keep the Annex IV file current.", refs:["Article 11","Article 12","Annex IV"], ask:"What logging and documentation must we build in?", action:"ask" },
                    { title:"Oversight, accuracy and security", detail:"Build human oversight and meet accuracy, robustness and cybersecurity.", refs:["Article 14","Article 15"], ask:"What do Articles 14 and 15 require for oversight and robustness?", action:"ask" },
                    { title:"Transparency to users", detail:"Inform users appropriately and label AI-generated content.", refs:["Article 13","Article 50"], ask:"What transparency duties apply to our AI feature?", action:"ask" }
                ]}
            },
            classify: {
                intro:"Answer each question about the system's intended purpose. The result maps to the operative Articles of the EU AI Act.",
                questions:[
                    { id:"prohibited", q:"Does the system perform an Article 5 prohibited practice, for example social scoring, untargeted facial scraping, emotion recognition at work or school, or real-time remote biometric identification in public for law enforcement?", ifYes:{ tier:"Prohibited", refs:["Article 5"] } },
                    { id:"annex3", q:"Is it intended for an Annex III high-risk use, such as biometrics, critical infrastructure, education, employment, essential public or private services, law enforcement, migration, or administration of justice?", ifYes:{ tier:"High-risk", refs:["Article 6","Annex III"] } },
                    { id:"safety", q:"Is it a safety component of, or itself, a product covered by the Annex I Union harmonisation legislation (for example medical devices or machinery) that requires third-party conformity assessment?", ifYes:{ tier:"High-risk", refs:["Article 6","Annex I"] } },
                    { id:"gpai", q:"Is it a general-purpose AI model that can serve many downstream tasks (a foundation model)?", ifYes:{ tier:"GPAI", refs:["Article 51","Article 53"] } },
                    { id:"transparency", q:"Does it interact directly with people, generate synthetic audio, image, video or text, or perform emotion recognition or biometric categorisation?", ifYes:{ tier:"Limited-risk (transparency)", refs:["Article 50"] } }
                ],
                tiers:{
                    "Prohibited":{ cls:"tier-prohibited", summary:"This practice is banned under the EU AI Act. It must not be placed on the market or put into service.", obligations:[
                        "Do not develop, place on the market or use the system (Article 5).",
                        "Re-scope the use case to remove the prohibited element.",
                        "Note the narrow, strictly conditioned law-enforcement exceptions (Article 5)." ] },
                    "High-risk":{ cls:"tier-high", summary:"The system is high-risk. The full Chapter III obligations apply before it can be placed on the market.", obligations:[
                        "Risk management system across the lifecycle (Article 9).",
                        "Data governance for training, validation and testing (Article 10).",
                        "Technical documentation and record-keeping (Article 11, Article 12, Annex IV).",
                        "Transparency, human oversight, accuracy and cybersecurity (Article 13, Article 14, Article 15).",
                        "Conformity assessment, EU declaration and CE marking (Article 43, Article 47, Article 48).",
                        "Registration in the EU database and post-market monitoring (Article 49, Article 72)." ] },
                    "Limited-risk (transparency)":{ cls:"tier-limited", summary:"The system is not high-risk but triggers transparency duties toward the people who interact with it.", obligations:[
                        "Inform people they are interacting with an AI system (Article 50).",
                        "Label synthetic or manipulated content as artificially generated (Article 50).",
                        "Disclose emotion recognition or biometric categorisation to exposed persons (Article 50)." ] },
                    "Minimal-risk":{ cls:"tier-minimal", summary:"The system carries minimal risk. No mandatory obligations apply beyond voluntary measures.", obligations:[
                        "No mandatory obligations under the Act.",
                        "Adopt voluntary codes of conduct as good practice (Article 95).",
                        "Ensure staff AI literacy (Article 4)." ] },
                    "GPAI":{ cls:"tier-gpai", summary:"This is a general-purpose AI model. GPAI provider obligations apply, with extra duties if it carries systemic risk.", obligations:[
                        "Technical documentation and information to downstream providers (Article 53).",
                        "A copyright policy and a training-data summary (Article 53).",
                        "If systemic risk: evaluation, mitigation, incident tracking and cybersecurity (Article 55).",
                        "Follow the codes of practice (Article 56)." ] }
                }
            },
            agents: {
                sampleAgents:[
                    { name:"CV Screening Assistant", riskTier:"High-risk", owner:"People Ops", role:"Provider", oversight:"In place", conformity:"Pending", registration:"Not registered",
                      graphQuery:"Show the obligations for a high-risk employment AI system used to screen job applicants under Annex III." },
                    { name:"Customer Support Chatbot", riskTier:"Limited-risk", owner:"Customer Success", role:"Deployer", oversight:"N/A", conformity:"N/A", registration:"N/A",
                      graphQuery:"What transparency obligations apply to a customer-facing chatbot under Article 50?" },
                    { name:"Fraud Scoring Model", riskTier:"High-risk", owner:"Risk & Fraud", role:"Provider", oversight:"In progress", conformity:"Not started", registration:"Not registered",
                      graphQuery:"What obligations apply to an AI system used for creditworthiness or fraud scoring under Annex III?" }
                ]
            }
        };

        function tierClass(t){ var m={ "Prohibited":"tier-prohibited","High-risk":"tier-high","Limited-risk (transparency)":"tier-limited","Limited-risk":"tier-limited","Minimal-risk":"tier-minimal","GPAI":"tier-gpai" }; return m[t] || "tier-limited"; }
        function refChips(refs){ return (refs||[]).map(function(r){ return '<span class="cite-badge">'+escapeHtml(r)+'</span>'; }).join(' '); }

        /* ── Fixed side menu: pin / hide-collapse ─────────────────────── */
        var RAIL = { collapsed:false, pinned:false };
        var railEl = document.getElementById('railnav');
        var railReveal = document.getElementById('rail-reveal');
        try { var _rs = JSON.parse(localStorage.getItem('lexy_rail') || 'null'); if (_rs) { RAIL.collapsed = !!_rs.collapsed; RAIL.pinned = !!_rs.pinned; } } catch (e) {}

        function applyRailState() {
            railEl.classList.toggle('collapsed', RAIL.collapsed);
            railEl.classList.toggle('pinned', RAIL.pinned);
            document.getElementById('rail-collapse').innerHTML = '<i data-lucide="' + (RAIL.collapsed ? 'panel-left-open' : 'panel-left-close') + '" style="width:16px;height:16px;"></i>';
            document.getElementById('rail-collapse').title = RAIL.collapsed ? 'Expand menu' : 'Hide menu';
            var pinEl = document.getElementById('rail-pin');
            pinEl.classList.toggle('on', RAIL.pinned);
            document.getElementById('pin-state').textContent = RAIL.pinned ? 'On' : 'Off';
            document.getElementById('rail-pin-ico').innerHTML = '<i data-lucide="' + (RAIL.pinned ? 'pin' : 'pin-off') + '" style="width:15px;height:15px;"></i>';
            var narrow = window.innerWidth <= 1024;
            railReveal.classList.toggle('show', narrow && RAIL.collapsed);
            try { localStorage.setItem('lexy_rail', JSON.stringify(RAIL)); } catch (e) {}
            lucide.createIcons();
        }
        function toggleCollapse() { RAIL.collapsed = !RAIL.collapsed; applyRailState(); }
        function togglePin() { RAIL.pinned = !RAIL.pinned; applyRailState(); }
        function showRail() { RAIL.collapsed = false; applyRailState(); }
        window.addEventListener('resize', function () { railReveal.classList.toggle('show', window.innerWidth <= 1024 && RAIL.collapsed); });

        /* ── View switching ───────────────────────────────────────────── */
        function switchView(view) {
            document.querySelectorAll('.nav-item[data-view]').forEach(function (el) {
                el.classList.toggle('active', el.getAttribute('data-view') === view);
            });
            document.querySelectorAll('.view').forEach(function (el) { el.classList.remove('active'); });
            var v = document.getElementById('view-' + view);
            if (v) v.classList.add('active');
            detailDrawer.style.display = (view === 'lexy') ? '' : 'none';
            if (view === 'classify') renderClassify();
            if (view === 'agents') renderAgents();
            if (window.innerWidth <= 1024 && !RAIL.pinned) { RAIL.collapsed = true; applyRailState(); }
            lucide.createIcons();
        }

        /* ── A Lexy chat card with raw (app-controlled) HTML — used for the
              onboarding chips and the workflow card. bare=true drops the
              speech-bubble chrome so a card provides its own frame. ───────── */
        function appendLexyHTML(html, bare) {
            var row = document.createElement('div');
            row.className = 'message-row assistant-row';
            var av = document.createElement('div');
            av.className = 'msg-avatar';
            av.innerHTML = '<img src="/lexy_avatar.png" alt="Lexy">';
            var bc = document.createElement('div');
            bc.className = 'msg-bubble-container';
            if (bare) {
                var wrap = document.createElement('div');
                wrap.style.maxWidth = '100%';
                wrap.innerHTML = html;
                bc.appendChild(wrap);
            } else {
                var b = document.createElement('div');
                b.className = 'msg-bubble';
                b.innerHTML = html;
                bc.appendChild(b);
            }
            var meta = document.createElement('div');
            meta.className = 'msg-meta';
            var t = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            meta.innerHTML = '<span>Lexy</span> &bull; <span>' + t + '</span>';
            bc.appendChild(meta);
            row.appendChild(av);
            row.appendChild(bc);
            chatContainer.appendChild(row);
            lucide.createIcons();
            chatContainer.scrollTop = chatContainer.scrollHeight;
            return row;
        }

        /* ── Onboarding: role assessment → goal session → mission ─────── */
        var ONB = { state: null, roleId: null };

        function roleChipsHTML() {
            var html = '<div class="onb-card"><div class="chip-grid">';
            LEXY_DATA.roles.forEach(function (r) {
                html += '<button class="chip" onclick="onbPickRole(\\'' + r.id + '\\')">'
                    + '<span class="c-ico"><i data-lucide="' + r.icon + '" style="width:18px;height:18px;"></i></span>'
                    + '<span class="c-text"><span class="c-title">' + escapeHtml(r.label) + '</span>'
                    + '<span class="c-blurb">' + escapeHtml(r.blurb) + '</span></span></button>';
            });
            html += '</div></div>';
            return html;
        }
        function goalChipsHTML() {
            var html = '<div class="onb-card"><div class="chip-row">';
            LEXY_DATA.goals.forEach(function (g) {
                html += '<button class="chip-mini" onclick="onbPickGoal(\\'' + g.id + '\\')">'
                    + '<i data-lucide="' + g.icon + '" style="width:14px;height:14px;"></i> ' + escapeHtml(g.label) + '</button>';
            });
            html += '</div></div>';
            return html;
        }

        function startOnboarding() {
            if (welcomeMessage && welcomeMessage.parentNode) welcomeMessage.parentNode.removeChild(welcomeMessage);
            ONB.state = 'awaiting-role';
            appendLexyHTML('<div class="onb-q">Hi, I am <b>Lexy</b>. I will build you a personalized EU AI Act workflow in two quick steps. First, which best describes your role?</div>' + roleChipsHTML());
        }
        function onbPickRole(id) {
            var role = LEXY_DATA.roles.find(function (r) { return r.id === id; });
            if (!role) return;
            ONB.roleId = id;
            ONB.state = 'awaiting-goal';
            appendMessage('user', role.label);
            appendLexyHTML('<div class="onb-q">Great, a <b>' + escapeHtml(role.label) + '</b>. Now tell me what you want to achieve. Pick one, or just type your goal below.</div>' + goalChipsHTML());
            userInput.placeholder = 'Type what you want to achieve...';
            userInput.focus();
        }
        function onbPickGoal(id) {
            var goal = LEXY_DATA.goals.find(function (g) { return g.id === id; });
            if (!goal) return;
            appendMessage('user', goal.label);
            onbFinish(id, goal.label);
        }
        function onbGoalText(text) {
            appendMessage('user', text);
            var matched = LEXY_DATA.goals.find(function (g) { return text.toLowerCase().indexOf(g.id) !== -1 || g.label.toLowerCase().indexOf(text.toLowerCase()) !== -1; });
            onbFinish(matched ? matched.id : 'custom', text);
        }
        function onbFinish(goalId, goalText) {
            ONB.state = 'done';
            userInput.placeholder = 'Ask Lexy a compliance question...';
            var role = LEXY_DATA.roles.find(function (r) { return r.id === ONB.roleId; });
            var wfKey = pickWorkflowKey(ONB.roleId, goalId);
            saveProfile(ONB.roleId, role ? role.label : '', goalId, goalText, wfKey);
            appendLexyHTML('<div class="onb-q" style="margin-bottom:0;">Mission accepted. Based on your role and goal, here is the workflow I recommend. Tap any step and I will take it from there.</div>');
            appendLexyHTML(workflowHTML(wfKey, goalText), true);
            revealWorkflowNav();
            showMissionBanner();
        }

        function pickWorkflowKey(roleId, goalId) {
            var wf = LEXY_DATA.workflows;
            if (wf[roleId + '::' + goalId]) return roleId + '::' + goalId;
            if (wf[roleId + '::default']) return roleId + '::default';
            return 'provider::default';
        }
        function workflowHTML(wfKey, goalText) {
            var wf = LEXY_DATA.workflows[wfKey];
            var role = LEXY_DATA.roles.find(function (r) { return wfKey.indexOf(r.id) === 0; });
            var html = '<div class="workflow-card"><div class="wf-head">'
                + '<div class="wf-mission-label"><i data-lucide="target" style="width:13px;height:13px;"></i> Your mission</div>'
                + '<div class="wf-mission">' + escapeHtml(wf.mission) + '</div>'
                + '<div class="wf-meta"><span><b>Role:</b> ' + escapeHtml(role ? role.label : '') + '</span>'
                + '<span><b>Goal:</b> ' + escapeHtml(goalText || '') + '</span>'
                + '<span><b>Steps:</b> ' + wf.steps.length + '</span></div></div>';
            html += '<div class="wf-steps">';
            wf.steps.forEach(function (s, i) {
                var actLabel = s.action === 'classify' ? 'Open Classify' : 'Ask Lexy';
                var actIco = s.action === 'classify' ? 'scan-search' : 'sparkles';
                html += '<div class="wf-step"><div class="wf-num">' + (i + 1) + '</div><div class="wf-body">'
                    + '<div class="wf-title">' + escapeHtml(s.title) + '</div>'
                    + '<div class="wf-detail">' + escapeHtml(s.detail) + '</div>'
                    + '<div class="wf-refs">' + refChips(s.refs) + '</div>'
                    + '<div class="wf-actions"><button class="wf-btn" onclick="wfStep(\\'' + wfKey + '\\', ' + i + ')">'
                    + '<i data-lucide="' + actIco + '" style="width:13px;height:13px;"></i> ' + actLabel + '</button></div>'
                    + '</div></div>';
            });
            html += '</div></div>';
            return html;
        }
        function wfStep(wfKey, i) {
            var wf = LEXY_DATA.workflows[wfKey];
            if (!wf || !wf.steps[i]) { switchView('lexy'); return; }
            var s = wf.steps[i];
            if (s.action === 'classify') { switchView('classify'); return; }
            document.getElementById('view-lexy').classList.remove('hidden-popup');
            userInput.value = s.ask;
            btnSend.disabled = false;
            sendMessage();
        }

        /* ── Profile persistence + mission surfaces ───────────────────── */
        function saveProfile(roleId, roleLabel, goalId, goalText, wfKey) {
            try { localStorage.setItem('lexy_profile', JSON.stringify({ roleId: roleId, roleLabel: roleLabel, goalId: goalId, goalText: goalText, wfKey: wfKey })); } catch (e) {}
        }
        function getProfile() { try { return JSON.parse(localStorage.getItem('lexy_profile') || 'null'); } catch (e) { return null; } }
        function revealWorkflowNav() {
            var p = getProfile(); if (!p) return;
            var nav = document.getElementById('nav-workflow');
            document.getElementById('wf-divider').style.display = '';
            nav.style.display = '';
            var wf = LEXY_DATA.workflows[p.wfKey];
            document.getElementById('wf-nav-badge').textContent = wf ? wf.steps.length : '';
            lucide.createIcons();
        }
        function showMissionBanner() {
            var p = getProfile(); if (!p) return;
            var el = document.getElementById('mission-banner');
            document.getElementById('mission-banner-text').innerHTML = 'Mission set for a <b>' + escapeHtml(p.roleLabel) + '</b>. Your personalized workflow is ready.';
            el.classList.add('show');
        }
        function openMyWorkflow() {
            var p = getProfile(); if (!p) { switchView('lexy'); return; }
            switchView('lexy');
            if (welcomeMessage && welcomeMessage.parentNode) welcomeMessage.parentNode.removeChild(welcomeMessage);
            appendLexyHTML(workflowHTML(p.wfKey, p.goalText), true);
        }
        function restartOnboarding() {
            try { localStorage.removeItem('lexy_profile'); } catch (e) {}
            document.getElementById('mission-banner').classList.remove('show');
            document.getElementById('nav-workflow').style.display = 'none';
            document.getElementById('wf-divider').style.display = 'none';
            messages.length = 0;
            chatContainer.innerHTML = '';
            switchView('lexy');
            startOnboarding();
        }

        /* ── Classify & Assess view ───────────────────────────────────── */
        var CLS = { answers: {}, built: false };
        function renderClassify() {
            document.getElementById('classify-intro').textContent = LEXY_DATA.classify.intro;
            if (CLS.built) return;
            var wrap = document.getElementById('cls-questions');
            wrap.innerHTML = '';
            LEXY_DATA.classify.questions.forEach(function (q) {
                var el = document.createElement('div');
                el.className = 'cls-q';
                el.innerHTML = '<div class="q-text">' + escapeHtml(q.q) + '</div>'
                    + '<div class="q-opts"><div class="seg">'
                    + '<button class="yes" onclick="clsAnswer(\\'' + q.id + '\\', true, this)">Yes</button>'
                    + '<button class="no" onclick="clsAnswer(\\'' + q.id + '\\', false, this)">No</button>'
                    + '</div></div>';
                wrap.appendChild(el);
            });
            CLS.built = true;
            lucide.createIcons();
        }
        function clsAnswer(id, val, btn) {
            CLS.answers[id] = val;
            var seg = btn.parentElement;
            seg.querySelectorAll('button').forEach(function (b) { b.classList.remove('on'); });
            btn.classList.add('on');
            computeClassify();
        }
        function computeClassify() {
            var qs = LEXY_DATA.classify.questions, tier = null, refs = [];
            for (var i = 0; i < qs.length; i++) { if (CLS.answers[qs[i].id] === true) { tier = qs[i].ifYes.tier; refs = qs[i].ifYes.refs; break; } }
            var allAnswered = qs.every(function (q) { return CLS.answers[q.id] !== undefined; });
            if (!tier) { if (allAnswered) { tier = 'Minimal-risk'; refs = []; } else { document.getElementById('cls-result-wrap').innerHTML = ''; return; } }
            renderClsResult(tier, refs);
        }
        function renderClsResult(tier, refs) {
            var info = LEXY_DATA.classify.tiers[tier] || { cls: tierClass(tier), summary: '', obligations: [] };
            var name = (document.getElementById('cls-name').value || '').trim();
            var obl = info.obligations.map(function (o) { return '<div class="obl-item"><i data-lucide="check-circle-2" style="width:15px;height:15px;"></i><span>' + escapeHtml(o) + '</span></div>'; }).join('');
            var html = '<div class="cls-result">'
                + '<div class="tier-chip ' + (info.cls || tierClass(tier)) + '"><i data-lucide="shield" style="width:15px;height:15px;"></i> ' + escapeHtml(tier) + '</div>'
                + (refs && refs.length ? '<div style="margin-bottom:12px;">' + refChips(refs) + '</div>' : '')
                + '<div class="r-summary">' + escapeHtml(info.summary) + '</div>'
                + '<div class="obl-list">' + obl + '</div>'
                + '<div class="cls-actions">'
                + '<button class="btn-pill primary" onclick="clsAskLexy(\\'' + tier + '\\')"><i data-lucide="sparkles" style="width:15px;height:15px;"></i> Ask Lexy about this</button>'
                + '<button class="btn-pill" onclick="clsAddToHub(\\'' + tier + '\\')"><i data-lucide="plus" style="width:15px;height:15px;"></i> Add to Agents Hub</button>'
                + '</div></div>';
            document.getElementById('cls-result-wrap').innerHTML = html;
            lucide.createIcons();
        }
        function clsAskLexy(tier) {
            var name = (document.getElementById('cls-name').value || '').trim();
            var subject = name ? ('"' + name + '"') : 'our AI system';
            document.getElementById('view-lexy').classList.remove('hidden-popup');
            userInput.value = 'What EU AI Act obligations apply to ' + subject + ' if it is classified as ' + tier + '?';
            btnSend.disabled = false;
            sendMessage();
        }
        function clsAddToHub(tier) {
            var name = (document.getElementById('cls-name').value || '').trim() || 'Untitled AI system';
            var agents = loadUserAgents();
            agents.push({ name: name, riskTier: tier.replace(' (transparency)', ''), owner: 'You', role: 'Provider', oversight: 'To assess', conformity: 'Not started', registration: 'Not registered', graphQuery: 'What obligations apply to ' + name + ' classified as ' + tier + '?' });
            try { localStorage.setItem('lexy_agents', JSON.stringify(agents)); } catch (e) {}
            switchView('agents');
        }
        function resetClassify() {
            CLS.answers = {}; CLS.built = false;
            document.getElementById('cls-name').value = '';
            document.getElementById('cls-result-wrap').innerHTML = '';
            renderClassify();
        }

        /* ── Agents Hub view (inventory + governance) ─────────────────── */
        function loadUserAgents() { try { return JSON.parse(localStorage.getItem('lexy_agents') || '[]'); } catch (e) { return []; } }
        function allAgents() { return LEXY_DATA.agents.sampleAgents.concat(loadUserAgents()); }
        function govClass(v) {
            var s = String(v || '').toLowerCase();
            if (s === 'in place' || s === 'active' || s === 'registered' || s === 'complete') return 'ok';
            if (s === 'pending' || s === 'in progress' || s === 'planned' || s === 'to assess') return 'warn';
            if (s.indexOf('not ') === 0 || s === 'missing') return 'miss';
            return '';
        }
        function renderAgents() {
            var agents = allAgents();
            var total = agents.length;
            var high = agents.filter(function (a) { return /high/i.test(a.riskTier); }).length;
            var conf = agents.filter(function (a) { return /pending|not started|to assess/i.test(a.conformity || ''); }).length;
            var lim = agents.filter(function (a) { return /limited/i.test(a.riskTier); }).length;
            var sum = document.getElementById('agents-summary');
            sum.innerHTML =
                sumCard(total, 'boxes', 'AI systems') +
                sumCard(high, 'shield-alert', 'High-risk') +
                sumCard(conf, 'clipboard-list', 'Conformity open') +
                sumCard(lim, 'eye', 'Transparency');
            var list = document.getElementById('agents-list');
            list.innerHTML = agents.map(function (a, i) { return agentCard(a, i); }).join('');
            lucide.createIcons();
        }
        function sumCard(n, ico, label) {
            return '<div class="sum-card"><div class="n">' + n + '</div><div class="l"><i data-lucide="' + ico + '" style="width:13px;height:13px;"></i> ' + escapeHtml(label) + '</div></div>';
        }
        function govField(k, v) {
            return '<div class="gov-field"><span class="k">' + escapeHtml(k) + '</span><span class="v ' + govClass(v) + '">' + escapeHtml(v || '—') + '</span></div>';
        }
        function agentCard(a, i) {
            return '<div class="agent-card">'
                + '<div class="agent-top"><div class="agent-name"><span class="a-ico"><i data-lucide="cpu" style="width:16px;height:16px;"></i></span>' + escapeHtml(a.name) + '</div>'
                + '<span class="tier-chip ' + tierClass(a.riskTier) + '" style="margin-bottom:0;">' + escapeHtml(a.riskTier) + '</span></div>'
                + '<div class="gov-grid">'
                + govField('Owner', a.owner) + govField('Role', a.role) + govField('Human oversight', a.oversight)
                + govField('Conformity', a.conformity) + govField('EU database', a.registration)
                + '</div>'
                + '<div class="agent-actions">'
                + '<span class="link-graph" onclick="agentGraph(' + i + ')"><i data-lucide="git-fork" style="width:15px;height:15px;"></i> View obligations graph</span>'
                + '<span class="link-graph" onclick="agentAsk(' + i + ')"><i data-lucide="sparkles" style="width:15px;height:15px;"></i> Ask Lexy</span>'
                + '</div></div>';
        }
        function agentGraph(i) {
            var a = allAgents()[i]; if (!a) return;
            document.getElementById('view-lexy').classList.remove('hidden-popup');
            userInput.value = a.graphQuery;
            btnSend.disabled = false;
            sendMessage();
        }
        function agentAsk(i) {
            var a = allAgents()[i]; if (!a) return;
            document.getElementById('view-lexy').classList.remove('hidden-popup');
            userInput.value = 'What EU AI Act obligations apply to ' + a.name + ', a ' + a.riskTier + ' AI system?';
            btnSend.disabled = false;
            sendMessage();
        }

        /* ── Boot ─────────────────────────────────────────────────────── */
        function bootShell() {
            applyRailState();
            var p = getProfile();
            if (p) {
                revealWorkflowNav();
                showMissionBanner();

                if (welcomeMessage) {
                    var d = welcomeMessage.querySelector('.welcome-desc');
                    if (d) d.innerHTML = 'Welcome back. Your workflow for a <b>' + escapeHtml(p.roleLabel) + '</b> is ready, or ask me anything about Regulation (EU) 2024/1689.';
                    var t = welcomeMessage.querySelector('.welcome-title');
                    if (t) t.textContent = 'Welcome back to your workspace';
                }
                var sub = document.getElementById('lexy-subtitle');
                if (sub) sub.textContent = 'ASSISTING: ' + escapeHtml(p.roleLabel).toUpperCase();

            } else {
                startOnboarding();
            }
        }
        bootShell();
    </script>
</body>
</html>
"""
