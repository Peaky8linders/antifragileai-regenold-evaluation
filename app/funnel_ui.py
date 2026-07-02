"""Lexy sign-up / sign-in funnel landing page (served at ``/``).

A conversion-focused front page for the free Lexy EU AI Act Q&A app.
Reuses the antifragile.ai design language (dark slate surfaces, sky-blue
accent, Inter / Instrument Serif type) so it sits cohesively in front of the Lexy
chat UI (`app/web_ui.py`, now at ``/app``).

Flow: visitor enters an email (sign up) or looks up their key (sign in)
→ the page calls ``/api/v1/regenold/auth/signup`` / ``/signin`` → the
fresh ``lexy_sk_...`` key is shown with a copy button and an "Open Lexy"
CTA that navigates to ``/app#key=<key>``. The chat reads the key from the
URL fragment (never sent to the server) into localStorage. No secret is
ever baked into this HTML.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)


def register_funnel_routes(app: FastAPI) -> None:
    """Mount the sign-up / sign-in funnel at ``/``."""

    @app.get("/", response_class=HTMLResponse)
    def read_funnel() -> str:
        # SECURITY: this page is public; never embed P2P_REGENOLD_API_KEY
        # or any user key. Keys are issued by the API at runtime only.
        return FUNNEL_TEMPLATE


FUNNEL_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lexy · EU AI Act Assistant</title>
    <meta name="description" content="Free, grounded Q&amp;A on the EU AI Act. Every answer cites the exact Articles and Annexes.">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        :root {
            --bg-primary: #f8fafc;
            --bg-secondary: #ffffff;
            --bg-glass: #ffffff;
            --bg-glass-hover: #ffffff;
            --accent-cyan: #0ea5e9;
            --accent-blue: #2563eb;
            --accent-glow: rgba(14, 165, 233, 0.18);
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --text-muted: #94a3b8;
            --border-glass: #e2e8f0;
            --border-glow: rgba(14, 165, 233, 0.35);
            --ok: #059669;
            --err: #dc2626;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', system-ui, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.55;
            overflow-x: hidden;
        }
        body::before {
            content: ""; position: fixed; inset: 0; z-index: 0; pointer-events: none;
            background:
                radial-gradient(900px 600px at 15% -10%, rgba(14, 165, 233,0.10), transparent 60%),
                radial-gradient(800px 600px at 110% 10%, rgba(59,130,246,0.12), transparent 55%);
        }
        .wrap { position: relative; z-index: 1; max-width: 1080px; margin: 0 auto; padding: 32px 24px 64px; }
        header.top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 56px; }
        .brand { display: flex; align-items: center; gap: 12px; }
        .brand-avatar { position: relative; width: 46px; height: 46px; flex-shrink: 0; }
        .brand-avatar img { position: relative; z-index: 1; width: 46px; height: 46px; border-radius: 50%; object-fit: cover; border: 2px solid var(--accent-cyan); box-shadow: 0 0 18px var(--accent-glow); background: var(--bg-secondary); display: block; }
        .brand-avatar-glow { position: absolute; inset: -5px; border-radius: 50%; background: radial-gradient(circle, var(--accent-glow) 0%, transparent 70%); z-index: 0; animation: brand-pulse 3s infinite ease-in-out; pointer-events: none; }
        .brand-status-dot { position: absolute; z-index: 2; bottom: 1px; right: 1px; width: 11px; height: 11px; background: #10b981; border: 2px solid var(--bg-primary); border-radius: 50%; box-shadow: 0 0 6px #10b981; }
        @keyframes brand-pulse { 0%, 100% { opacity: .45; transform: scale(1); } 50% { opacity: .8; transform: scale(1.08); } }
        .brand .wordmark { font-family: 'Instrument Serif', Georgia, serif; font-weight: 400; font-size: 26px; letter-spacing: -0.01em; }
        .brand .wordmark span { color: var(--accent-cyan); }
        .brand-text { display: flex; flex-direction: column; gap: 2px; }
        .brand-tag { font-size: 12px; color: var(--text-muted); font-weight: 500; letter-spacing: 0.01em; }
        .pill { font-size: 12px; color: var(--text-secondary); border: 1px solid var(--border-glass); padding: 6px 12px; border-radius: 999px; background: var(--bg-glass); }
        .hero { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 48px; align-items: start; }
        @media (max-width: 880px) { .hero { grid-template-columns: 1fr; gap: 32px; } header.top { margin-bottom: 36px; } }
        .eyebrow { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 600; color: var(--accent-cyan); background: rgba(14, 165, 233,0.08); border: 1px solid var(--border-glow); padding: 6px 14px; border-radius: 999px; margin-bottom: 20px; }
        h1 { font-family: 'Instrument Serif', Georgia, serif; font-weight: 400; font-size: clamp(36px, 5vw, 54px); line-height: 1.05; letter-spacing: -0.01em; margin-bottom: 18px; }
        h1 .grad { background: linear-gradient(120deg, var(--accent-cyan), var(--accent-blue)); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
        .powered-by { font-size: 15px; font-weight: 500; color: var(--text-secondary); margin: -6px 0 18px; }
        .powered-by a { color: var(--accent-cyan); font-weight: 700; text-decoration: none; }
        .powered-by a:hover { text-decoration: underline; }
        .sub { font-size: 17px; color: var(--text-secondary); max-width: 520px; margin-bottom: 28px; }
        .features { list-style: none; display: grid; gap: 14px; margin-top: 8px; }
        .features li { display: flex; gap: 12px; align-items: flex-start; font-size: 15px; color: var(--text-secondary); }
        .features li i { color: var(--accent-cyan); flex-shrink: 0; margin-top: 2px; }
        .features li strong { color: var(--text-primary); font-weight: 600; }

        .card { background: var(--bg-glass); backdrop-filter: blur(18px); border: 1px solid var(--border-glass); border-radius: 20px; padding: 28px; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08); }
        .tabs { display: flex; gap: 6px; background: rgba(15, 23, 42,0.04); border-radius: 12px; padding: 5px; margin-bottom: 22px; }
        .tab { flex: 1; text-align: center; padding: 10px 12px; border-radius: 9px; font-size: 14px; font-weight: 600; color: var(--text-secondary); cursor: pointer; border: none; background: transparent; transition: all .2s; }
        .tab.active { background: var(--bg-glass-hover); color: var(--text-primary); box-shadow: inset 0 0 0 1px var(--border-glow); }
        .card h2 { font-family: 'Instrument Serif', Georgia, serif; font-size: 23px; font-weight: 400; margin-bottom: 6px; }
        .card .lead { font-size: 14px; color: var(--text-secondary); margin-bottom: 20px; }
        label { display: block; font-size: 13px; font-weight: 600; color: var(--text-secondary); margin: 14px 0 6px; }
        input[type=email], input[type=text] {
            width: 100%; padding: 12px 14px; font-size: 15px; font-family: inherit;
            background: #ffffff; border: 1px solid var(--border-glass); border-radius: 10px; color: var(--text-primary); transition: border-color .2s, box-shadow .2s;
        }
        input:focus { outline: none; border-color: var(--border-glow); box-shadow: 0 0 0 3px var(--accent-glow); }
        .btn { width: 100%; margin-top: 22px; padding: 13px 18px; font-size: 15px; font-weight: 700; font-family: 'Inter', sans-serif; border: none; border-radius: 11px; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 8px; transition: transform .12s, box-shadow .2s, opacity .2s; }
        .btn-primary { background: var(--accent-cyan); color: #ffffff; box-shadow: 0 8px 20px var(--accent-glow); }
        .btn-primary:hover { background: #38bdf8; transform: translateY(-1px); box-shadow: 0 12px 30px var(--accent-glow); }
        .btn:disabled { opacity: .55; cursor: progress; }
        .btn-ghost { background: rgba(15, 23, 42,0.05); color: var(--text-primary); border: 1px solid var(--border-glass); }
        .btn-ghost:hover { background: rgba(15, 23, 42,0.09); }
        .hint { font-size: 12px; color: var(--text-muted); margin-top: 14px; text-align: center; }
        .hint a { color: var(--accent-cyan); text-decoration: none; cursor: pointer; }
        .msg { font-size: 13px; margin-top: 14px; padding: 10px 12px; border-radius: 9px; display: none; }
        .msg.err { display: block; background: rgba(251,113,133,0.10); border: 1px solid rgba(251,113,133,0.35); color: var(--err); }

        .keybox { display: none; }
        .keybox.show { display: block; animation: rise .3s ease; }
        @keyframes rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
        .keybox .ok-badge { display: inline-flex; align-items: center; gap: 8px; color: var(--ok); font-weight: 600; font-size: 14px; margin-bottom: 14px; }
        .key-field { display: flex; gap: 8px; align-items: stretch; }
        .key-field code { flex: 1; font-family: 'JetBrains Mono', monospace; font-size: 13px; background: #f0f9ff; border: 1px solid var(--border-glow); border-radius: 10px; padding: 13px 14px; color: var(--accent-cyan); word-break: break-all; }
        .copy-btn { flex-shrink: 0; padding: 0 14px; border-radius: 10px; border: 1px solid var(--border-glass); background: rgba(15, 23, 42,0.05); color: var(--text-primary); cursor: pointer; display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; }
        .copy-btn:hover { background: rgba(15, 23, 42,0.1); }
        .keybox .save-note { font-size: 12px; color: var(--text-muted); margin: 12px 0 4px; }
        .divider { display: flex; align-items: center; gap: 12px; margin: 22px 0; color: var(--text-muted); font-size: 12px; }
        .divider::before, .divider::after { content: ""; flex: 1; height: 1px; background: var(--border-glass); }
        .site-footer { margin-top: 64px; padding-top: 40px; border-top: 1px solid var(--border-glass); }
        .footer-grid { display: grid; grid-template-columns: 1.6fr 1fr 1.3fr; gap: 40px; }
        @media (max-width: 720px) { .footer-grid { grid-template-columns: 1fr; gap: 28px; } }
        .footer-logo { display: inline-flex; align-items: center; gap: 8px; font-family: 'Instrument Serif', Georgia, serif; font-size: 21px; letter-spacing: -0.01em; }
        .footer-logo i, .footer-logo .dot { color: var(--accent-cyan); }
        .footer-tagline { font-size: 13px; color: var(--text-muted); margin: 12px 0 18px; max-width: 340px; line-height: 1.55; }
        .footer-social { display: flex; gap: 10px; }
        .footer-social a { display: inline-flex; align-items: center; justify-content: center; width: 36px; height: 36px; border-radius: 10px; border: 1px solid var(--border-glass); background: var(--bg-glass); color: var(--text-secondary); transition: color .2s, border-color .2s, box-shadow .2s, transform .12s; }
        .footer-social a:hover { color: var(--accent-cyan); border-color: var(--border-glow); box-shadow: 0 0 14px var(--accent-glow); transform: translateY(-1px); }
        .footer-social svg { width: 17px; height: 17px; fill: currentColor; }
        .footer-col h3 { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: var(--text-secondary); margin-bottom: 14px; }
        .footer-col ul { list-style: none; display: grid; gap: 10px; }
        .footer-col a { font-size: 14px; color: var(--text-muted); text-decoration: none; transition: color .2s; }
        .footer-col a:hover { color: var(--accent-cyan); }
        .footer-bottom { margin-top: 36px; padding-top: 20px; border-top: 1px solid var(--border-glass); font-size: 12px; color: var(--text-muted); }
        .footer-bottom .disc { max-width: 660px; line-height: 1.5; margin-bottom: 14px; }
        .footer-bottom-row { display: flex; flex-wrap: wrap; gap: 8px 20px; justify-content: space-between; align-items: center; }
        .trust { display: flex; flex-wrap: wrap; gap: 10px 22px; justify-content: center; margin-top: 24px; font-size: 12px; color: var(--text-muted); }
        .trust span { display: inline-flex; align-items: center; gap: 6px; }
        .trust i { width: 14px; height: 14px; color: var(--accent-cyan); }
    </style>
</head>
<body>
    <div class="wrap">
        <header class="top">
            <div class="brand">
                <div class="brand-avatar">
                    <span class="brand-avatar-glow" aria-hidden="true"></span>
                    <img src="/lexy_avatar.png" alt="Lexy" onerror="this.parentElement.style.display='none'">
                    <span class="brand-status-dot" aria-hidden="true"></span>
                </div>
                <div class="brand-text">
                    <div class="wordmark">Lex<span>y</span></div>
                    <div class="brand-tag">EU AI Act Virtual Assistant</div>
                </div>
            </div>
            <div class="pill">EU AI Act · Regulation (EU) 2024/1689</div>
        </header>

        <section class="hero">
            <div>
                <h1>EU AI Act <span class="grad">Q&amp;A RAG</span> system</h1>
                <p class="powered-by">Powered by <a href="https://antifragile-ai.net" target="_blank" rel="noopener noreferrer">Antifragile.AI</a></p>
                <p class="sub">Ask any EU AI Act question. Get a plain-language answer, cited to the exact Articles and Annexes.</p>
                <ul class="features">
                    <li><i data-lucide="scale" style="width:18px;height:18px"></i><span><strong>Grounded in the regulation.</strong> Every answer cites the operative Articles &amp; Annexes.</span></li>
                    <li><i data-lucide="zap" style="width:18px;height:18px"></i><span><strong>Risk classification and obligations.</strong> Prohibited, high-risk, or limited, and who must do what.</span></li>
                    <li><i data-lucide="key-round" style="width:18px;height:18px"></i><span><strong>Your own API key.</strong> Use Lexy in the chat or call the Q&amp;A API directly.</span></li>
                </ul>
            </div>

            <div class="card" aria-live="polite">
                <div class="tabs" id="tabs">
                    <button class="tab active" data-tab="signup" type="button">Get free access</button>
                    <button class="tab" data-tab="signin" type="button">Sign in</button>
                </div>

                <!-- SIGN UP -->
                <form id="signup-form" class="pane">
                    <h2>Create your free account</h2>
                    <p class="lead">Get your API key in seconds.</p>
                    <label for="su-email">Work email</label>
                    <input id="su-email" type="email" autocomplete="email" placeholder="you@company.com" required>
                    <label for="su-name">Name <span style="color:var(--text-muted);font-weight:400">(optional)</span></label>
                    <input id="su-name" type="text" autocomplete="name" placeholder="Jane Doe">
                    <label for="su-company">Company <span style="color:var(--text-muted);font-weight:400">(optional)</span></label>
                    <input id="su-company" type="text" autocomplete="organization" placeholder="Acme GmbH">
                    <button class="btn btn-primary" type="submit"><i data-lucide="rocket" style="width:17px;height:17px"></i> Get my free key</button>
                    <div class="msg" id="su-msg"></div>
                    <p class="hint">Already have an account? <a id="to-signin">Sign in</a></p>
                </form>

                <!-- SIGN IN -->
                <form id="signin-form" class="pane" style="display:none">
                    <h2>Welcome back</h2>
                    <p class="lead">Enter your email to get your key.</p>
                    <label for="si-email">Email</label>
                    <input id="si-email" type="email" autocomplete="email" placeholder="you@company.com" required>
                    <button class="btn btn-primary" type="submit"><i data-lucide="log-in" style="width:17px;height:17px"></i> Get my key</button>
                    <div class="msg" id="si-msg"></div>
                    <div class="divider">or</div>
                    <label for="si-key">Already have a key?</label>
                    <input id="si-key" type="text" placeholder="lexy_sk_..." autocomplete="off" spellcheck="false">
                    <button class="btn btn-ghost" type="button" id="use-key-btn"><i data-lucide="arrow-right" style="width:17px;height:17px"></i> Open Lexy</button>
                    <p class="hint">New here? <a id="to-signup">Create a free account</a></p>
                </form>

                <!-- KEY RESULT -->
                <div class="keybox" id="keybox">
                    <div class="ok-badge"><i data-lucide="check-circle-2" style="width:17px;height:17px"></i> <span id="kb-title">Your account is ready</span></div>
                    <p class="lead" style="margin-bottom:14px">This is your Lexy API key. Keep it safe; it identifies your usage.</p>
                    <div class="key-field">
                        <code id="kb-key">lexy_sk_...</code>
                        <button class="copy-btn" id="kb-copy" type="button"><i data-lucide="copy" style="width:14px;height:14px"></i> Copy</button>
                    </div>
                    <p class="save-note" id="kb-emailed" style="display:none"><i data-lucide="mail" style="width:12px;height:12px;vertical-align:-2px"></i> We also emailed it to you.</p>
                    <button class="btn btn-primary" id="kb-open" type="button" style="margin-top:18px"><i data-lucide="message-square" style="width:17px;height:17px"></i> Open Lexy &rarr;</button>
                    <p class="hint"><a id="kb-back">&larr; Back</a></p>
                </div>
            </div>
        </section>

        <footer class="site-footer">
            <div class="footer-grid">
                <div class="footer-brand">
                    <div class="footer-logo"><i data-lucide="shield-check" style="width:20px;height:20px"></i> Antifragile<span class="dot">.AI</span></div>
                    <p class="footer-tagline">EU AI Act path-to-production compliance. Grounded, cited answers on Regulation (EU) 2024/1689.</p>
                    <div class="footer-social">
                        <a href="https://www.linkedin.com/company/antifragile-ai" target="_blank" rel="noopener noreferrer" aria-label="Antifragile.AI on LinkedIn" title="LinkedIn"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg></a>
                        <a href="https://x.com/antifragileai" target="_blank" rel="noopener noreferrer" aria-label="Antifragile.AI on X" title="X"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg></a>
                        <a href="mailto:support@antifragile-ai.net" aria-label="Email Antifragile.AI" title="Email"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M1.5 8.67v8.58a3 3 0 003 3h15a3 3 0 003-3V8.67l-8.928 5.493a3 3 0 01-3.144 0L1.5 8.67z"/><path d="M22.5 6.908V6.75a3 3 0 00-3-3h-15a3 3 0 00-3 3v.158l9.714 5.978a1.5 1.5 0 001.572 0L22.5 6.908z"/></svg></a>
                    </div>
                </div>
                <div class="footer-col">
                    <h3>Legal</h3>
                    <ul>
                        <li><a href="https://antifragile-ai.net/legal/privacy" target="_blank" rel="noopener noreferrer">Privacy Policy</a></li>
                        <li><a href="https://antifragile-ai.net/legal/terms" target="_blank" rel="noopener noreferrer">Terms of Service</a></li>
                        <li><a href="https://antifragile-ai.net/legal/dpa" target="_blank" rel="noopener noreferrer">Data Processing Addendum</a></li>
                        <li><a href="https://antifragile-ai.net/legal/security" target="_blank" rel="noopener noreferrer">Security</a></li>
                    </ul>
                </div>
                <div class="footer-col">
                    <h3>Contact</h3>
                    <ul>
                        <li><a href="https://antifragile-ai.net/contact" target="_blank" rel="noopener noreferrer">Contact form</a></li>
                        <li><a href="mailto:sales@antifragile-ai.net">sales@antifragile-ai.net</a></li>
                        <li><a href="mailto:compliance@antifragile-ai.net">compliance@antifragile-ai.net</a></li>
                        <li><a href="mailto:privacy@antifragile-ai.net">privacy@antifragile-ai.net</a></li>
                    </ul>
                </div>
            </div>
            <div class="footer-bottom">
                <p class="disc">Lexy provides general guidance on the EU AI Act, not legal advice. Consult qualified counsel for binding compliance decisions.</p>
                <div class="footer-bottom-row">
                    <span>&copy; <span id="footer-year">2026</span> Antifragile.AI &middot; Lexy</span>
                    <span>Regulation (EU) 2024/1689 &middot; Grounded Q&amp;A</span>
                </div>
            </div>
        </footer>
    </div>

    <script>
        const API = '/api/v1/regenold/auth';

        function $(id) { return document.getElementById(id); }
        function showMsg(el, text) { el.textContent = text; el.className = 'msg err'; }
        function clearMsg(el) { el.textContent = ''; el.className = 'msg'; }

        // Tabs
        const panes = { signup: $('signup-form'), signin: $('signin-form') };
        function selectTab(name) {
            $('keybox').classList.remove('show');
            document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
            panes.signup.style.display = name === 'signup' ? 'block' : 'none';
            panes.signin.style.display = name === 'signin' ? 'block' : 'none';
        }
        document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => selectTab(t.dataset.tab)));
        $('to-signin').addEventListener('click', () => selectTab('signin'));
        $('to-signup').addEventListener('click', () => selectTab('signup'));

        // Key result panel
        function showKey(data, isReturning) {
            panes.signup.style.display = 'none';
            panes.signin.style.display = 'none';
            $('kb-title').textContent = isReturning ? 'Welcome back' : 'Your account is ready';
            $('kb-key').textContent = data.api_key;
            $('kb-emailed').style.display = data.email_sent ? 'block' : 'none';
            const box = $('keybox');
            box.classList.add('show');
            $('kb-open').onclick = () => openLexy(data.api_key);
            if (window.lucide) lucide.createIcons();
        }
        function openLexy(key) {
            // Hand the key to the chat via the URL fragment (never sent to
            // the server) — the chat stores it in localStorage and strips it.
            window.location.href = '/app#key=' + encodeURIComponent(key);
        }

        $('kb-copy').addEventListener('click', async () => {
            try { await navigator.clipboard.writeText($('kb-key').textContent); $('kb-copy').innerHTML = 'Copied'; setTimeout(() => { $('kb-copy').innerHTML = '<i data-lucide=copy style=\\'width:14px;height:14px\\'></i> Copy'; lucide.createIcons(); }, 1500); } catch (e) {}
        });
        $('kb-back').addEventListener('click', () => { $('keybox').classList.remove('show'); selectTab('signup'); });

        async function postJSON(path, payload) {
            const res = await fetch(API + path, {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
            });
            let data = {};
            try { data = await res.json(); } catch (e) {}
            return { ok: res.ok, status: res.status, data };
        }
        function errText(data, fallback) {
            if (data && data.detail) {
                if (typeof data.detail === 'string') return data.detail;
                if (data.detail.message) return data.detail.message;
            }
            return fallback;
        }

        // Sign up
        $('signup-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const msg = $('su-msg'); clearMsg(msg);
            const email = $('su-email').value.trim();
            if (!email) { showMsg(msg, 'Please enter your email.'); return; }
            const btn = e.submitter || $('signup-form').querySelector('button[type=submit]');
            btn.disabled = true;
            const r = await postJSON('/signup', { email, name: $('su-name').value.trim(), company: $('su-company').value.trim() });
            btn.disabled = false;
            if (r.ok) { showKey(r.data, r.data.returning); }
            else { showMsg(msg, errText(r.data, 'Something went wrong. Please try again.')); }
        });

        // Sign in (by email)
        $('signin-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const msg = $('si-msg'); clearMsg(msg);
            const email = $('si-email').value.trim();
            if (!email) { showMsg(msg, 'Please enter your email.'); return; }
            const btn = e.submitter || $('signin-form').querySelector('button[type=submit]');
            btn.disabled = true;
            const r = await postJSON('/signin', { email });
            btn.disabled = false;
            if (r.ok) { showKey(r.data, true); }
            else if (r.status === 404) { showMsg(msg, 'No account for that email. Switch to "Get free access" to create one.'); }
            else { showMsg(msg, errText(r.data, 'Something went wrong. Please try again.')); }
        });

        // Use an existing pasted key
        $('use-key-btn').addEventListener('click', () => {
            const msg = $('si-msg'); clearMsg(msg);
            const key = $('si-key').value.trim();
            if (!key) { showMsg(msg, 'Paste your API key first.'); return; }
            openLexy(key);
        });

        // Footer copyright year
        var _fy = document.getElementById('footer-year');
        if (_fy) _fy.textContent = new Date().getFullYear();

        if (window.lucide) lucide.createIcons();
    </script>
</body>
</html>"""
