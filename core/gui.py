"""
core/gui.py — Premium Textual TUI for LinkedIn Post Automator v2.5.

Features:
- Dynamic ASCII banner (theme-aware)
- Live dashboard with animated stats
- Post editor with character counter + AI actions
- Template selector with confidence display
- Theme selector with preview
- Queue manager with status badges
- Settings with secret source tracking
- Keyboard shortcuts + modal confirmations
- Loading spinners and status feedback
"""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button, DataTable, Footer, Header, Input, Label,
    LoadingIndicator, Select, Static, TextArea,
)
from textual import work

from core.config import load_config
from core.constants import LINKEDIN_CHAR_LIMIT, PostStatus
from core.database import QueueManager
from core.llm.gateway import LLMGateway
from core.services.text_generator import TextGenerator
from core.services.image_generator import ImageGenerator
from core.services.publisher import Publisher
from core.infographic import InfographicEngine
from core.infographic.themes import list_themes
from core.infographic.templates import list_templates
from core.logger import get_logger

logger = get_logger(__name__)


# ── ASCII Banner ─────────────────────────────────────────────────────────────

ASCII_BANNER = r"""
    __    ___ 
   / /   /   |
  / /   / /| |
 / /___/ ___ |
/_____/_/  |_|
""".strip()

# ── Theme CSS ────────────────────────────────────────────────────────────────

APP_CSS = """
$accent: rgb(124, 58, 237);
$cyan: rgb(6, 182, 212);
$green: rgb(16, 185, 129);
$pink: rgb(236, 72, 153);
$amber: rgb(245, 158, 11);
$red: rgb(239, 68, 68);
$bg: rgb(10, 14, 24);
$surface: rgb(14, 20, 36);
$card: rgb(20, 28, 48);
$border: rgb(30, 44, 68);
$muted: rgb(100, 116, 150);

Screen {
    layout: horizontal;
    background: $bg;
}

/* ── Sidebar ── */
Sidebar {
    width: 28;
    background: $surface;
    padding: 0;
    border-right: tall $border;
}

#ascii-banner {
    color: $cyan;
    text-style: bold;
    padding: 1 1 0 1;
    text-align: center;
}

#version-tag {
    color: $muted;
    text-align: center;
    padding: 0 1 1 1;
}

.nav-sep {
    color: $border;
    padding: 0 1;
}

Sidebar Button {
    width: 100%;
    margin: 0 1;
    background: transparent;
    color: $muted;
    border: none;
    text-style: bold;
    padding: 0 2;
}

Sidebar Button:hover {
    background: $card;
    color: $cyan;
}

Sidebar Button.active {
    background: $card;
    color: $cyan;
    border-left: tall $cyan;
}

Sidebar #btn_quit {
    color: $red;
    margin-top: 1;
}

Sidebar #btn_quit:hover {
    background: rgba(239, 68, 68, 0.12);
}

/* ── Main ── */
.main-panel {
    width: 1fr;
    padding: 1 2;
    overflow-y: auto;
}

.hidden { display: none; }

/* ── Stats ── */
.stat-row {
    height: auto;
    margin-bottom: 1;
}

.stat-box {
    width: 1fr;
    height: auto;
    border: tall $border;
    background: $card;
    padding: 1 2;
    margin: 0 1;
    text-align: center;
}

.stat-num {
    color: $cyan;
    text-style: bold;
    text-align: center;
}

.stat-lbl {
    color: $muted;
    text-align: center;
}

.section-hdr {
    text-style: bold;
    color: $accent;
    padding: 1 0;
}

.health-line {
    padding: 0 1;
    color: $muted;
}

.sep-line {
    color: $border;
    margin: 1 0;
}

/* ── Create ── */
.form-group {
    height: auto;
    margin-bottom: 1;
    align: left middle;
}

.form-lbl {
    width: 22;
    margin-top: 1;
    color: $muted;
}

Select {
    width: 42;
    margin-left: 1;
}

#post_editor {
    height: 14;
    border: tall $border;
    background: $card;
    margin: 1 0;
}

#char_counter {
    text-align: right;
    padding: 0 1;
    color: $muted;
}

#image_info {
    padding: 1 2;
    margin: 1 0;
    border: tall $border;
    background: $card;
}

#selection_info {
    padding: 0 1;
    color: $muted;
    margin: 0 0 1 0;
}

.btn-row {
    height: auto;
    margin: 1 0;
}

.btn-row Button {
    margin-right: 1;
}

#schedule_row {
    height: auto;
    margin: 0 0 1 0;
    align: left middle;
}

#schedule_row Input {
    width: 14;
    margin: 0 1;
}

#status_bar {
    padding: 1;
    margin: 1 0;
    background: $card;
    border: tall $accent;
}

/* ── Queue ── */
DataTable {
    height: auto;
    max-height: 22;
}

.queue-btns {
    height: auto;
    margin: 1 0;
}

.queue-btns Button {
    margin-right: 1;
}

.filter-group {
    height: auto;
    margin-bottom: 1;
    align: left middle;
}

/* ── Settings ── */
.settings-block {
    border: tall $border;
    background: $card;
    padding: 1 2;
    margin: 0 0 1 0;
}

/* ── Modal ── */
ConfirmModal {
    align: center middle;
}

#modal-box {
    width: 50;
    height: auto;
    background: $card;
    border: tall $accent;
    padding: 2 3;
}

#modal-box Label {
    width: 100%;
    text-align: center;
    margin-bottom: 1;
}

#modal-btns {
    height: auto;
    align: center middle;
}

#modal-btns Button {
    margin: 0 1;
}
"""


# ── Confirmation Modal ───────────────────────────────────────────────────────

class ConfirmModal(ModalScreen[bool]):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__()

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-box"):
            yield Label(f"[bold]{self.message}[/]")
            with Horizontal(id="modal-btns"):
                yield Button("✅ Yes", id="cfm_yes", variant="success")
                yield Button("❌ No", id="cfm_no", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "cfm_yes")


# ── Sidebar ──────────────────────────────────────────────────────────────────

class Sidebar(Vertical):
    def compose(self) -> ComposeResult:
        yield Static(ASCII_BANNER, id="ascii-banner")
        yield Static("[dim]v2.5 · Enterprise[/]", id="version-tag", markup=True)
        yield Static("─" * 30, classes="nav-sep")
        yield Button("📊  Dashboard", id="nav_dashboard", classes="active")
        yield Button("✏️   Create Post", id="nav_create")
        yield Button("📦  Queue", id="nav_queue")
        yield Button("⚙️   Settings", id="nav_settings")
        yield Static("─" * 30, classes="nav-sep")
        yield Button("⏻   Quit", id="btn_quit")


# ── Dashboard ────────────────────────────────────────────────────────────────

class DashboardView(VerticalScroll):
    def compose(self) -> ComposeResult:
        yield Static("📊  [bold]Dashboard[/bold]", classes="section-hdr", markup=True)
        with Horizontal(classes="stat-row"):
            with Vertical(classes="stat-box"):
                yield Static("0", id="s_today", classes="stat-num")
                yield Static("Today", classes="stat-lbl")
            with Vertical(classes="stat-box"):
                yield Static("0", id="s_queued", classes="stat-num")
                yield Static("Queued", classes="stat-lbl")
            with Vertical(classes="stat-box"):
                yield Static("0", id="s_drafts", classes="stat-num")
                yield Static("Drafts", classes="stat-lbl")
            with Vertical(classes="stat-box"):
                yield Static("—", id="s_rate", classes="stat-num")
                yield Static("Success", classes="stat-lbl")
        yield Static("─" * 60, classes="sep-line")
        yield Static("📡  [bold]System Health[/bold]", classes="section-hdr", markup=True)
        yield Static("", id="health_out")
        yield Static("─" * 60, classes="sep-line")
        yield Static("🎨  [bold]Engine Status[/bold]", classes="section-hdr", markup=True)
        yield Static("", id="engine_out")
        yield Static("─" * 60, classes="sep-line")
        yield Static("📜  [bold]Recent Activity[/bold]", classes="section-hdr", markup=True)
        yield Static("", id="activity_out")

    def on_mount(self) -> None:
        self.refresh_data()

    def refresh_data(self) -> None:
        try:
            db = QueueManager()
            stats = db.get_stats()
            self.query_one("#s_today", Static).update(str(stats.get("today", 0)))
            self.query_one("#s_queued", Static).update(str(stats.get("queued", 0)))
            self.query_one("#s_drafts", Static).update(str(stats.get("draft", 0)))
            posted = stats.get("posted", 0)
            total = stats.get("total", 0)
            rate = f"{int(posted / total * 100)}%" if total > 0 else "N/A"
            self.query_one("#s_rate", Static).update(rate)

            # Health
            config = load_config()
            h = []
            for name, ok in [
                ("OpenAI", config.has_openai), ("Gemini", config.has_gemini),
                ("OpenRouter", config.has_openrouter), ("LinkedIn", config.has_linkedin),
            ]:
                icon = "[green]●[/]" if ok else "[red]●[/]"
                src = config.get_secret_source(
                    {"OpenAI": "open_ai_api_key", "Gemini": "gemini_api_key",
                     "OpenRouter": "openrouter_api_key"}.get(name, "")
                )
                suffix = f" [dim](from {src})[/]" if src != "not set" and ok else ""
                h.append(f"  {icon} {name}{suffix}")
            h.append(f"  [green]●[/] Database ({stats.get('total', 0)} posts)")

            insecure = config.secrets_in_config_json()
            if insecure:
                h.append("")
                h.append("  [bold red]⚠ Secrets in config.json:[/]")
                for k in insecure:
                    h.append(f"    [red]· {k} — move to .env[/]")

            self.query_one("#health_out", Static).update("\n".join(h))

            # Engine status
            templates = InfographicEngine.available_templates()
            themes = InfographicEngine.available_themes()
            e = [
                f"  📐 Templates: {len(templates)} available",
                f"  🎨 Themes: {len(themes)} available",
                f"  ⚡ Mode: Template-first (deterministic)",
            ]
            self.query_one("#engine_out", Static).update("\n".join(e))

            # Activity
            recent = db.get_post_summaries(limit=5)
            if recent:
                lines = []
                for p in recent:
                    s = p["status"]
                    icon = {"POSTED": "✅", "QUEUED": "⏰", "DRAFT": "📝", "FAILED": "❌"}.get(s, "•")
                    preview = (p.get("preview") or "")[:45].replace("\n", " ")
                    lines.append(f"  {icon} [{s}] {preview}…")
                self.query_one("#activity_out", Static).update("\n".join(lines))
            else:
                self.query_one("#activity_out", Static).update("  No posts yet.")
        except Exception as e:
            logger.error("Dashboard error: %s", e)


# ── Create Post ──────────────────────────────────────────────────────────────

class CreatePostView(VerticalScroll):
    current_text: str = ""
    current_img: str = ""
    current_persona: str = ""

    def compose(self) -> ComposeResult:
        yield Static("✏️   [bold]Create New Post[/bold]", classes="section-hdr", markup=True)

        with Horizontal(classes="form-group"):
            yield Label("Text Provider:", classes="form-lbl")
            yield Select(
                [("Auto (failover)", "auto"), ("Gemini", "gemini"),
                 ("OpenRouter", "openrouter"), ("OpenAI", "openai")],
                id="sel_provider", value="auto",
            )

        with Horizontal(classes="form-group"):
            yield Label("Image Mode:", classes="form-lbl")
            yield Select(
                [("Template Only (default)", "template_only"),
                 ("Hybrid (template+AI)", "hybrid"),
                 ("AI Only", "ai_only"),
                 ("DALL-E 3", "dall-e-3"), ("Gemini", "gemini"),
                 ("Pollinations", "pollinations")],
                id="sel_imgmode", value="template_only",
            )

        # Template + Theme selectors
        tpl_options = [("Auto-detect", "auto")] + [
            (t.display_name, t.name) for t in list_templates()
        ]
        theme_options = [("Random", "random")] + [
            (t.display_name, t.name) for t in list_themes()
        ]

        with Horizontal(classes="form-group"):
            yield Label("Template:", classes="form-lbl")
            yield Select(tpl_options, id="sel_template", value="auto")

        with Horizontal(classes="form-group"):
            yield Label("Theme:", classes="form-lbl")
            yield Select(theme_options, id="sel_theme", value="random")

        yield Button("⚡ Generate Post", id="btn_gen", variant="success")
        yield LoadingIndicator(id="loader", classes="hidden")

        yield Static("", id="gen_divider", classes="hidden")
        yield TextArea("", id="post_editor", classes="hidden", language=None)
        yield Static("0 / 3000", id="char_counter", classes="hidden")
        yield Static("", id="selection_info", classes="hidden")

        with Horizontal(id="ai_btns", classes="btn-row hidden"):
            yield Button("✨ Improve", id="btn_improve")
            yield Button("🔥 Viral", id="btn_viral")
            yield Button("📏 Shorten", id="btn_shorten")
            yield Button("📖 Expand", id="btn_expand")

        yield Static("", id="image_info", classes="hidden")
        with Horizontal(id="img_btns", classes="btn-row hidden"):
            yield Button("👁  View Image", id="btn_view_img", variant="primary")
            yield Button("🔄 Regen Image", id="btn_regen_img", variant="warning")

        yield Static("", id="act_divider", classes="hidden")
        with Horizontal(id="act_btns", classes="btn-row hidden"):
            yield Button("🚀 Post Now", id="btn_post", variant="success")
            yield Button("⏰ Queue", id="btn_queue", variant="primary")
            yield Button("💾 Draft", id="btn_draft")
            yield Button("🔄 Regenerate All", id="btn_regen", variant="warning")

        with Horizontal(id="schedule_row", classes="hidden"):
            yield Label("Minutes from now:", classes="form-lbl")
            yield Input(placeholder="60", id="in_minutes", type="integer", value="60")

        yield Static("", id="status_bar", classes="hidden")

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if event.text_area.id == "post_editor":
            self.current_text = event.text_area.text
            n = len(self.current_text)
            ctr = self.query_one("#char_counter", Static)
            if n <= 2000:
                ctr.update(f"[green]{n}[/] / {LINKEDIN_CHAR_LIMIT}")
            elif n <= 2800:
                ctr.update(f"[yellow]{n}[/] / {LINKEDIN_CHAR_LIMIT}")
            else:
                ctr.update(f"[bold red]{n}[/] / {LINKEDIN_CHAR_LIMIT}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid in ("btn_gen", "btn_regen"):
            self._start_gen()
        elif bid == "btn_regen_img":
            self._regen_image()
        elif bid == "btn_view_img":
            self._open_img()
        elif bid == "btn_post":
            self._confirm_post()
        elif bid == "btn_queue":
            self._queue()
        elif bid == "btn_draft":
            self._draft()
        elif bid in ("btn_improve", "btn_viral", "btn_shorten", "btn_expand"):
            self._ai_action(bid.replace("btn_", ""))

    def _start_gen(self) -> None:
        self.query_one("#loader").remove_class("hidden")
        for wid in ("#gen_divider", "#post_editor", "#char_counter",
                     "#selection_info", "#ai_btns", "#image_info", "#img_btns",
                     "#act_divider", "#act_btns", "#schedule_row", "#status_bar"):
            self.query_one(wid).add_class("hidden")
        tp = str(self.query_one("#sel_provider", Select).value or "auto")
        im = str(self.query_one("#sel_imgmode", Select).value or "template_only")
        tpl = str(self.query_one("#sel_template", Select).value or "auto")
        thm = str(self.query_one("#sel_theme", Select).value or "random")
        self._do_gen(tp, im, tpl, thm)

    @work(exclusive=True, thread=True)
    def _do_gen(self, provider: str, img_mode: str, template: str, theme: str) -> None:
        try:
            config = load_config()
            llm = LLMGateway(config)
            text_gen = TextGenerator(llm, config)
            img_gen = ImageGenerator(llm)

            ok, text, persona = text_gen.generate(provider=provider)
            if not ok:
                self.app.call_from_thread(self._show_err, f"Text generation failed:\n{text}")
                return

            iok, img_path, img_type = img_gen.generate(
                text, image_model=img_mode, template=template, theme=theme,
            )
            if not iok:
                self.app.call_from_thread(self._show_result, text, "", persona, "", "")
                self.app.call_from_thread(
                    self.app.notify, f"Image: {img_path[:80]}", severity="warning"
                )
                return

            self.app.call_from_thread(self._show_result, text, img_path, persona, img_type, template)
        except Exception as e:
            self.app.call_from_thread(self._show_err, str(e))

    def _show_result(self, text: str, img_path: str, persona: str, img_type: str, template: str) -> None:
        self.query_one("#loader").add_class("hidden")
        self.current_text = text
        self.current_img = img_path
        self.current_persona = persona

        editor = self.query_one("#post_editor", TextArea)
        editor.load_text(text)
        editor.remove_class("hidden")

        self.query_one("#gen_divider", Static).update(
            f"[bold cyan]━━━ Generated ━━━[/]  [dim]Persona: {persona}[/]"
        )
        self.query_one("#gen_divider").remove_class("hidden")

        n = len(text)
        color = "green" if n <= 2000 else ("yellow" if n <= 2800 else "bold red")
        self.query_one("#char_counter", Static).update(f"[{color}]{n}[/] / {LINKEDIN_CHAR_LIMIT}")
        self.query_one("#char_counter").remove_class("hidden")

        # Selection info
        if img_type and "template:" in img_type:
            tpl = img_type.replace("template:", "")
            self.query_one("#selection_info", Static).update(
                f"[dim]🎯 Template: [cyan]{tpl}[/] · Image type: {img_type}[/]"
            )
            self.query_one("#selection_info").remove_class("hidden")

        self.query_one("#ai_btns").remove_class("hidden")

        info = self.query_one("#image_info", Static)
        if img_path and os.path.exists(img_path):
            kb = os.path.getsize(img_path) / 1024
            info.update(f"[bold cyan]🖼  Image:[/] {os.path.abspath(img_path)} [dim]({kb:.0f}KB, {img_type})[/]")
            info.remove_class("hidden")
            self.query_one("#img_btns").remove_class("hidden")
        else:
            info.update("[yellow]⚠ No image generated[/]")
            info.remove_class("hidden")

        self.query_one("#act_divider", Static).update("[bold]━━━ Actions ━━━[/]")
        self.query_one("#act_divider").remove_class("hidden")
        self.query_one("#act_btns").remove_class("hidden")
        self.query_one("#schedule_row").remove_class("hidden")
        self.app.notify("✅ Post generated!", severity="information")

    def _show_err(self, msg: str) -> None:
        self.query_one("#loader").add_class("hidden")
        self.query_one("#gen_divider", Static).update("[bold red]━━━ Error ━━━[/]")
        self.query_one("#gen_divider").remove_class("hidden")
        self.query_one("#status_bar", Static).update(f"[red]{msg}[/]")
        self.query_one("#status_bar").remove_class("hidden")

    def _regen_image(self) -> None:
        if not self.current_text:
            self.app.notify("Generate a post first.", severity="error")
            return
        self.query_one("#loader").remove_class("hidden")
        im = str(self.query_one("#sel_imgmode", Select).value or "template_only")
        tpl = str(self.query_one("#sel_template", Select).value or "auto")
        thm = str(self.query_one("#sel_theme", Select).value or "random")
        self._do_regen_img(im, tpl, thm)

    @work(exclusive=True, thread=True)
    def _do_regen_img(self, img_mode: str, template: str, theme: str) -> None:
        try:
            config = load_config()
            llm = LLMGateway(config)
            img_gen = ImageGenerator(llm)
            iok, img_path, img_type = img_gen.generate(
                self.current_text, image_model=img_mode, template=template, theme=theme,
            )
            if iok:
                self.current_img = img_path
                self.app.call_from_thread(self._update_img_info, img_path, img_type)
            else:
                self.app.call_from_thread(self.app.notify, f"Image failed: {img_path[:80]}", severity="error")
                self.app.call_from_thread(lambda: self.query_one("#loader").add_class("hidden"))
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Error: {e}", severity="error")
            self.app.call_from_thread(lambda: self.query_one("#loader").add_class("hidden"))

    def _update_img_info(self, path: str, img_type: str) -> None:
        self.query_one("#loader").add_class("hidden")
        info = self.query_one("#image_info", Static)
        if path and os.path.exists(path):
            kb = os.path.getsize(path) / 1024
            info.update(f"[bold cyan]🖼  Image:[/] {os.path.abspath(path)} [dim]({kb:.0f}KB, {img_type})[/]")
        self.app.notify("🖼 Image regenerated!", severity="information")

    def _ai_action(self, action: str) -> None:
        if not self.current_text:
            self.app.notify("Generate first.", severity="error")
            return
        self.query_one("#loader").remove_class("hidden")
        self._do_ai(action)

    @work(exclusive=True, thread=True)
    def _do_ai(self, action: str) -> None:
        try:
            config = load_config()
            llm = LLMGateway(config)
            tg = TextGenerator(llm, config)
            ok, res = tg.improve(self.current_text, action)
            if ok:
                self.app.call_from_thread(self._set_text, res)
            else:
                self.app.call_from_thread(self.app.notify, f"Failed: {res[:60]}", severity="error")
                self.app.call_from_thread(lambda: self.query_one("#loader").add_class("hidden"))
        except Exception as e:
            self.app.call_from_thread(self.app.notify, str(e), severity="error")
            self.app.call_from_thread(lambda: self.query_one("#loader").add_class("hidden"))

    def _set_text(self, text: str) -> None:
        self.query_one("#loader").add_class("hidden")
        self.current_text = text
        self.query_one("#post_editor", TextArea).load_text(text)
        n = len(text)
        color = "green" if n <= 2000 else ("yellow" if n <= 2800 else "bold red")
        self.query_one("#char_counter", Static).update(f"[{color}]{n}[/] / {LINKEDIN_CHAR_LIMIT}")
        self.app.notify("✨ Text updated!", severity="information")

    def _confirm_post(self) -> None:
        if not self.current_text:
            self.app.notify("Nothing to post.", severity="error")
            return
        def cb(ok: bool) -> None:
            if ok:
                self._status("[yellow]🚀 Publishing…[/]")
                self._do_post()
        self.app.push_screen(ConfirmModal("Post to LinkedIn now?"), cb)

    @work(exclusive=True, thread=True)
    def _do_post(self) -> None:
        try:
            config = load_config()
            pub = Publisher(config.cookies)
            ok, msg = pub.publish(self.current_text, self.current_img)
            if ok:
                db = QueueManager()
                db.add_post(self.current_text, self.current_img, PostStatus.POSTED,
                            persona=self.current_persona)
                self.app.call_from_thread(self._status, "[green]✅ Posted successfully![/]")
            else:
                self.app.call_from_thread(self._status, f"[red]❌ {msg}[/]")
        except Exception as e:
            self.app.call_from_thread(self._status, f"[red]❌ {e}[/]")

    def _queue(self) -> None:
        if not self.current_text:
            self.app.notify("Nothing to queue.", severity="error")
            return
        try:
            mins = int(self.query_one("#in_minutes", Input).value or "60")
        except (ValueError, TypeError):
            self.app.notify("Enter a valid number.", severity="error")
            return
        sched = (datetime.now() + timedelta(minutes=mins)).strftime("%Y-%m-%dT%H:%M:%S")
        db = QueueManager()
        db.add_post(self.current_text, self.current_img, PostStatus.QUEUED,
                     scheduled_time=sched, persona=self.current_persona)
        self._status(f"[cyan]⏰ Queued for {mins} minutes.[/]")
        self.app.notify(f"Queued ({mins}min).", severity="information")

    def _draft(self) -> None:
        if not self.current_text:
            self.app.notify("Nothing to save.", severity="error")
            return
        db = QueueManager()
        db.add_post(self.current_text, self.current_img, PostStatus.DRAFT,
                     persona=self.current_persona)
        self._status("[green]💾 Draft saved![/]")

    def _open_img(self) -> None:
        if self.current_img and os.path.exists(self.current_img):
            try:
                subprocess.Popen(["xdg-open", os.path.abspath(self.current_img)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                self.app.notify(f"Open: {os.path.abspath(self.current_img)}", severity="warning")

    def _status(self, text: str) -> None:
        s = self.query_one("#status_bar", Static)
        s.update(text)
        s.remove_class("hidden")


# ── Queue View ───────────────────────────────────────────────────────────────

class QueueView(VerticalScroll):
    selected_id: int | None = None

    def compose(self) -> ComposeResult:
        yield Static("📦  [bold]Queue & History[/bold]", classes="section-hdr", markup=True)
        with Horizontal(classes="filter-group"):
            yield Label("Filter:", classes="form-lbl")
            yield Select(
                [("All", "all"), ("Queued", "QUEUED"), ("Drafts", "DRAFT"),
                 ("Posted", "POSTED"), ("Failed", "FAILED")],
                id="q_filter", value="all",
            )
            yield Button("🔄 Refresh", id="btn_q_refresh", variant="primary")
        yield DataTable(id="q_table")
        yield Static("", id="q_count")
        with Horizontal(classes="queue-btns"):
            yield Button("🗑  Delete", id="btn_q_del", variant="error")
            yield Button("🔁 Retry", id="btn_q_retry", variant="warning")

    def on_mount(self) -> None:
        tbl = self.query_one("#q_table", DataTable)
        tbl.cursor_type = "row"
        tbl.add_columns("ID", "Status", "Scheduled", "Chars", "Preview")
        self._load()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "q_filter":
            self._load()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_q_refresh":
            self._load()
        elif event.button.id == "btn_q_del":
            self._delete()
        elif event.button.id == "btn_q_retry":
            self._retry()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row = self.query_one("#q_table", DataTable).get_row(event.row_key)
        try:
            self.selected_id = int(row[0])
        except (ValueError, IndexError):
            self.selected_id = None

    def _load(self) -> None:
        tbl = self.query_one("#q_table", DataTable)
        tbl.clear()
        fv = self.query_one("#q_filter", Select).value
        status = None if fv == "all" else str(fv)
        db = QueueManager()
        posts = db.get_post_summaries(limit=100, status=status)
        for p in posts:
            s = p["status"]
            badge = {"POSTED": "[green]● POSTED[/]", "QUEUED": "[cyan]● QUEUED[/]",
                     "DRAFT": "[yellow]● DRAFT[/]", "FAILED": "[red]● FAILED[/]"}.get(s, s)
            preview = (p.get("preview") or "")[:45].replace("\n", " ")
            sched = p.get("scheduled_time") or "—"
            chars = str(p.get("char_count") or "?")
            tbl.add_row(str(p["id"]), badge, sched, chars, preview)
        self.query_one("#q_count", Static).update(f"[dim]{len(posts)} post{'s' if len(posts)!=1 else ''}[/]")

    def _delete(self) -> None:
        if not self.selected_id:
            self.app.notify("Select a post.", severity="warning")
            return
        def cb(ok):
            if ok and self.selected_id:
                QueueManager().delete_post(self.selected_id)
                self._load()
                self.app.notify("Deleted.", severity="information")
        self.app.push_screen(ConfirmModal(f"Delete post #{self.selected_id}?"), cb)

    def _retry(self) -> None:
        if not self.selected_id:
            self.app.notify("Select a post.", severity="warning")
            return
        db = QueueManager()
        post = db.get_post(self.selected_id)
        if not post or post["status"] != "FAILED":
            self.app.notify("Only FAILED posts can retry.", severity="warning")
            return
        db.update_status(self.selected_id, PostStatus.QUEUED)
        self._load()
        self.app.notify("Re-queued.", severity="information")


# ── Settings View ────────────────────────────────────────────────────────────

class SettingsView(VerticalScroll):
    def compose(self) -> ComposeResult:
        yield Static("⚙️   [bold]Settings[/bold]", classes="section-hdr", markup=True)
        yield Static("", id="cfg_out")
        yield Static("─" * 60, classes="sep-line")
        yield Static("", id="prov_out")

    def on_mount(self) -> None:
        self._load()

    def _load(self) -> None:
        config = load_config()
        lines = [
            "[bold]Configuration[/bold]", "",
            f"  Bio: [cyan]{config.bio[:60]}{'…' if len(config.bio)>60 else ''}[/]",
            f"  Token Limit: [cyan]{config.gpt_token_limit}[/]",
            f"  API Provider: [cyan]{config.api_provider}[/]",
            f"  Post History: [cyan]{config.num_recent_posts} posts[/]",
            "",
            "[bold]API Keys[/bold] (masked, source shown)", "",
        ]
        for label, key in [
            ("OpenAI", "open_ai_api_key"),
            ("Gemini", "gemini_api_key"),
            ("OpenRouter", "openrouter_api_key"),
        ]:
            val = getattr(config, key, "")
            masked = config.mask_key(val)
            src = config.get_secret_source(key)
            src_tag = f"[green]{src}[/]" if src == ".env" else (f"[red]{src}[/]" if src == "config.json" else f"[dim]{src}[/]")
            lines.append(f"  {label}: [cyan]{masked}[/] from {src_tag}")

        lines += [
            "", "[bold]LinkedIn[/bold]", "",
            f"  li_at: [cyan]{config.mask_key(config.cookies.get('li_at', ''))}[/]"
            f" from {config.get_secret_source('li_at')}",
            f"  JSESSIONID: [cyan]{config.mask_key(config.cookies.get('JSESSIONID', ''))}[/]",
            "", f"[bold]Websites[/bold] ({len(config.websites)})", "",
        ]
        for u in config.websites[:5]:
            lines.append(f"  • {u}")
        self.query_one("#cfg_out", Static).update("\n".join(lines))

        # Provider status
        st = [
            "[bold]Provider Status[/bold]", "",
            f"  {'[green]●[/]' if config.has_openai else '[red]●[/]'} OpenAI",
            f"  {'[green]●[/]' if config.has_gemini else '[red]●[/]'} Gemini",
            f"  {'[green]●[/]' if config.has_openrouter else '[red]●[/]'} OpenRouter",
            f"  {'[green]●[/]' if config.has_linkedin else '[red]●[/]'} LinkedIn",
        ]
        errors = config.validate()
        if errors:
            st += ["", "[bold red]⚠ Issues:[/]"] + [f"  [red]· {e}[/]" for e in errors]
        self.query_one("#prov_out", Static).update("\n".join(st))


# ── Main App ─────────────────────────────────────────────────────────────────

class AutomatorApp(App):
    TITLE = "LinkedIn Post Automator"
    SUB_TITLE = "v2.5 · Enterprise"
    CSS = APP_CSS

    BINDINGS = [
        Binding("d", "go('dashboard')", "Dashboard", show=True),
        Binding("c", "go('create')", "Create", show=True),
        Binding("q", "go('queue')", "Queue", show=True),
        Binding("s", "go('settings')", "Settings", show=True),
        Binding("ctrl+q", "quit", "Quit", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Sidebar()
        yield Container(
            DashboardView(id="v_dashboard"),
            CreatePostView(id="v_create", classes="hidden"),
            QueueView(id="v_queue", classes="hidden"),
            SettingsView(id="v_settings", classes="hidden"),
            classes="main-panel",
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_quit":
            self.exit()
        elif event.button.id and event.button.id.startswith("nav_"):
            self.action_go(event.button.id.replace("nav_", ""))

    def action_go(self, name: str) -> None:
        views = {"dashboard": "v_dashboard", "create": "v_create",
                 "queue": "v_queue", "settings": "v_settings"}
        target = views.get(name)
        if not target:
            return
        for k, vid in views.items():
            w = self.query_one(f"#{vid}")
            b = self.query_one(f"#nav_{k}", Button)
            if vid == target:
                w.remove_class("hidden")
                b.add_class("active")
                if k == "dashboard":
                    self.query_one(DashboardView).refresh_data()
                elif k == "queue":
                    self.query_one(QueueView)._load()
                elif k == "settings":
                    self.query_one(SettingsView)._load()
            else:
                w.add_class("hidden")
                b.remove_class("active")


if __name__ == "__main__":
    AutomatorApp().run()
