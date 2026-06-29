import os
import json
import subprocess
from datetime import datetime, timedelta
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Header, Footer, Button, Static, Label, Select,
    Input, LoadingIndicator, DataTable
)
from textual.message import Message
from textual import work

from core.content_manager import ContentManager
from core.database import QueueManager


def load_config():
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            return json.load(f)
    return {}


# ── Sidebar ──────────────────────────────────────────────────────────────────

class Sidebar(Vertical):
    def compose(self) -> ComposeResult:
        yield Label("⚡ Navigation", id="nav-header")
        yield Button("🏠 Dashboard", id="nav_dashboard", variant="primary")
        yield Button("✏️  Create Post", id="nav_create", variant="primary")
        yield Button("📋 Queue & Drafts", id="nav_queue", variant="primary")
        yield Button("⏻  Quit", id="nav_quit", variant="error")


# ── Dashboard ────────────────────────────────────────────────────────────────

class DashboardView(VerticalScroll):
    def compose(self) -> ComposeResult:
        yield Static("═══════════════════════════════════════", classes="divider")
        yield Static("  LinkedIn Post Automator  ", id="dashboard-title")
        yield Static("═══════════════════════════════════════", classes="divider")
        yield Static("")
        yield Static("  ✅  SQLite-backed post queue")
        yield Static("  ✅  Dynamic AI personas (no generic vibes)")
        yield Static("  ✅  OpenRouter model failover")
        yield Static("  ✅  Premium glassmorphism infographics")
        yield Static("")
        yield Static("  Select [bold cyan]Create Post[/] from the sidebar to begin.", markup=True)


# ── Create Post View ─────────────────────────────────────────────────────────

class CreatePostView(VerticalScroll):
    current_text: str = ""
    current_img: str = ""

    class PostGenerated(Message):
        def __init__(self, text, image_path):
            self.text = text
            self.image_path = image_path
            super().__init__()

    class GenerationError(Message):
        def __init__(self, msg):
            self.msg = msg
            super().__init__()

    class PostPublished(Message):
        def __init__(self, msg):
            self.msg = msg
            super().__init__()

    def compose(self) -> ComposeResult:
        yield Static("[bold underline]Create New Post[/]", markup=True)
        yield Static("")

        with Horizontal(classes="form-row"):
            yield Label("Text Provider:", classes="form-label")
            yield Select(
                [("Auto (try all)", "auto"), ("OpenRouter", "openrouter"),
                 ("Gemini", "gemini"), ("OpenAI", "openai")],
                id="text_provider", value="auto"
            )
        with Horizontal(classes="form-row"):
            yield Label("Image Generator:", classes="form-label")
            yield Select(
                [("Auto (infographic first)", "auto"), ("Infographic Only", "infographic"),
                 ("Pollinations (AI art)", "pollinations"), ("Gemini", "gemini"),
                 ("DALL-E 3", "dall-e-3")],
                id="image_generator", value="auto"
            )

        yield Static("")
        yield Button("⚡ Generate Post", id="btn_generate", variant="success")
        yield Static("[dim]Generates text + infographic image using selected providers.[/]", markup=True)
        yield LoadingIndicator(id="loading", classes="hidden")

        # ── Result area ──
        yield Static("", id="result_divider", classes="hidden")

        # Post text in a scrollable container
        yield VerticalScroll(
            Static("", id="post_preview_text"),
            id="post_scroll_box",
            classes="hidden"
        )

        # Image info + open button
        yield Static("", id="image_info", classes="hidden")
        with Horizontal(id="image_buttons", classes="hidden"):
            yield Button("👁  View Image", id="btn_view_image", variant="primary")

        # Action buttons
        yield Static("", id="actions_divider", classes="hidden")
        with Horizontal(id="action_buttons", classes="hidden"):
            yield Button("🚀 Post Now", id="btn_post_now", variant="success")
            yield Button("⏰ Queue (1h)", id="btn_queue_1h", variant="primary")
            yield Button("⏰ Queue (6h)", id="btn_queue_6h", variant="primary")
            yield Button("💾 Save Draft", id="btn_draft", variant="default")
            yield Button("🔄 Regenerate", id="btn_regenerate", variant="warning")

        with Horizontal(id="custom_schedule", classes="hidden"):
            yield Label("Custom delay (minutes):", classes="form-label")
            yield Input(placeholder="e.g. 120", id="custom_minutes", type="integer")
            yield Button("Queue", id="btn_queue_custom", variant="primary")

        yield Static("", id="status_msg", classes="hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id

        if bid in ("btn_generate", "btn_regenerate"):
            self.query_one("#loading").remove_class("hidden")
            for wid in ("#result_divider", "#post_scroll_box", "#image_info",
                         "#image_buttons", "#actions_divider", "#action_buttons",
                         "#custom_schedule", "#status_msg"):
                self.query_one(wid).add_class("hidden")

            tp = self.query_one("#text_provider").value or "auto"
            ig = self.query_one("#image_generator").value or "auto"
            self.generate_content(str(tp), str(ig))

        elif bid == "btn_view_image":
            if self.current_img and os.path.exists(self.current_img):
                abs_path = os.path.abspath(self.current_img)
                try:
                    subprocess.Popen(["xdg-open", abs_path],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    self.app.notify(f"Open manually: {abs_path}", severity="warning")

        elif bid == "btn_post_now":
            self._post_now()
        elif bid == "btn_queue_1h":
            self._queue_post(60)
        elif bid == "btn_queue_6h":
            self._queue_post(360)
        elif bid == "btn_queue_custom":
            try:
                mins = int(self.query_one("#custom_minutes").value)
                self._queue_post(mins)
            except (ValueError, TypeError):
                self.app.notify("Enter a valid number of minutes.", severity="error")
        elif bid == "btn_draft":
            db = QueueManager()
            db.add_post(self.current_text, self.current_img, "DRAFT")
            self._show_status("💾 Saved as Draft!")
            self.app.notify("Post saved as Draft.", severity="information")

    @work(exclusive=True, thread=True)
    def generate_content(self, text_provider: str, image_generator: str) -> None:
        try:
            cfg = load_config()
            cm = ContentManager(cfg)

            tsuccess, text = cm.generate_draft_text(provider=text_provider)
            if not tsuccess:
                self.post_message(self.GenerationError(f"Text generation failed:\n{text}"))
                return

            isuccess, img = cm.generate_draft_image(text, image_model=image_generator)
            if not isuccess:
                self.post_message(self.PostGenerated(text, ""))
                self.app.call_from_thread(
                    self.app.notify,
                    f"Image failed: {img[:80]}",
                    severity="warning"
                )
                return

            self.post_message(self.PostGenerated(text, img))
        except Exception as e:
            self.post_message(self.GenerationError(str(e)))

    def on_create_post_view_post_generated(self, msg: PostGenerated) -> None:
        self.query_one("#loading").add_class("hidden")
        self.current_text = msg.text
        self.current_img = msg.image_path

        # Show full post text
        self.query_one("#post_preview_text", Static).update(msg.text)
        self.query_one("#post_scroll_box").remove_class("hidden")

        self.query_one("#result_divider", Static).update(
            "[bold green]━━━━━━━━━━━━━━━━━ Generated Post ━━━━━━━━━━━━━━━━━[/]"
        )
        self.query_one("#result_divider").remove_class("hidden")

        # Show image info
        img_info = self.query_one("#image_info", Static)
        if msg.image_path and os.path.exists(msg.image_path):
            size_kb = os.path.getsize(msg.image_path) / 1024
            abs_path = os.path.abspath(msg.image_path)
            img_info.update(
                f"[bold cyan]🖼  Image Ready:[/] {abs_path} [dim]({size_kb:.1f} KB)[/]\n"
                f"[dim]Click 'View Image' below to open it in your image viewer.[/]"
            )
            img_info.remove_class("hidden")
            self.query_one("#image_buttons").remove_class("hidden")
        else:
            img_info.update("[yellow]⚠  No image was generated.[/]")
            img_info.remove_class("hidden")

        # Show actions
        self.query_one("#actions_divider", Static).update(
            "[bold]━━━━━━━━━━━━━━━━━━━ Actions ━━━━━━━━━━━━━━━━━━━━[/]"
        )
        self.query_one("#actions_divider").remove_class("hidden")
        self.query_one("#action_buttons").remove_class("hidden")
        self.query_one("#custom_schedule").remove_class("hidden")

        self.app.notify("Post generated successfully!", severity="information")

    def on_create_post_view_generation_error(self, msg: GenerationError) -> None:
        self.query_one("#loading").add_class("hidden")
        self.query_one("#result_divider", Static).update(
            "[bold red]━━━━━━━━━━━━━━━━━ Error ━━━━━━━━━━━━━━━━━━━━━━[/]"
        )
        self.query_one("#result_divider").remove_class("hidden")
        self.query_one("#post_preview_text", Static).update(f"[red]{msg.msg}[/]")
        self.query_one("#post_scroll_box").remove_class("hidden")

    def _post_now(self):
        if not self.current_text:
            self.app.notify("No post to publish!", severity="error")
            return
        self._show_status("[yellow]🚀 Publishing to LinkedIn...[/]")
        self._do_post()

    @work(exclusive=True, thread=True)
    def _do_post(self):
        try:
            cfg = load_config()
            cm = ContentManager(cfg)
            success, msg = cm.publish_post(self.current_text, self.current_img)
            if success:
                db = QueueManager()
                db.add_post(self.current_text, self.current_img, "POSTED")
                self.post_message(self.PostPublished("✅ Posted to LinkedIn successfully!"))
            else:
                self.post_message(self.PostPublished(f"❌ Failed to post: {msg}"))
        except Exception as e:
            self.post_message(self.PostPublished(f"❌ Error: {e}"))

    def on_create_post_view_post_published(self, msg: PostPublished) -> None:
        self._show_status(msg.msg)
        self.app.notify(msg.msg, severity="information")

    def _queue_post(self, minutes):
        if not self.current_text:
            self.app.notify("No post to queue!", severity="error")
            return
        db = QueueManager()
        scheduled = (datetime.now() + timedelta(minutes=minutes)).isoformat()
        db.add_post(self.current_text, self.current_img, "QUEUED", scheduled)
        self._show_status(f"⏰ Queued for {minutes} minutes from now.")
        self.app.notify(f"Post queued for {minutes}min from now.", severity="information")

    def _show_status(self, text):
        s = self.query_one("#status_msg", Static)
        s.update(text)
        s.remove_class("hidden")


# ── Queue View ───────────────────────────────────────────────────────────────

class QueueView(VerticalScroll):
    def compose(self) -> ComposeResult:
        yield Static("[bold underline]Queue & History[/]", markup=True)
        yield Static("")
        yield DataTable(id="queue_table")
        yield Static("")
        yield Button("🔄 Refresh", id="btn_refresh_queue", variant="primary")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("ID", "Status", "Scheduled", "Preview")
        self.refresh_table()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_refresh_queue":
            self.refresh_table()

    def refresh_table(self):
        table = self.query_one(DataTable)
        table.clear()
        db = QueueManager()
        for p in db.get_all_posts():
            preview = (p['content'] or "")[:60].replace("\n", " ") + "..."
            table.add_row(
                str(p['id']),
                p['status'],
                p['scheduled_time'] or "N/A",
                preview
            )


# ── Main App ─────────────────────────────────────────────────────────────────

class AutomatorApp(App):
    TITLE = "LinkedIn Post Automator"
    SUB_TITLE = "Enterprise Edition"

    CSS = """
    Screen { layout: horizontal; }

    Sidebar {
        width: 28;
        background: $panel;
        padding: 1;
        border-right: thick $primary;
    }
    Sidebar Button { width: 100%; margin-bottom: 1; }
    #nav-header {
        padding-bottom: 1;
        text-style: bold;
        color: $accent;
        text-align: center;
    }

    .main-content {
        width: 1fr;
        padding: 1 2;
        overflow-y: auto;
    }

    .hidden { display: none; }

    .form-row {
        height: auto;
        margin-bottom: 1;
        align: left middle;
    }
    .form-label {
        width: 22;
        margin-top: 1;
    }
    Select { width: 40; margin-left: 1; }

    #post_scroll_box {
        height: 16;
        border: solid $success;
        background: $panel;
        padding: 1 2;
        margin: 1 0;
    }

    #image_info {
        padding: 1 2;
        margin: 1 0;
        border: solid $accent;
        background: $panel;
    }
    #image_buttons {
        height: auto;
        margin: 0 0 1 0;
    }

    #action_buttons {
        height: auto;
        margin: 1 0;
    }
    #action_buttons Button {
        margin-right: 1;
    }

    #custom_schedule {
        height: auto;
        margin: 0 0 1 0;
        align: left middle;
    }
    #custom_schedule Input {
        width: 16;
        margin: 0 1;
    }

    #status_msg {
        padding: 1;
        margin: 1 0;
        background: $panel;
        border: solid $accent;
    }

    #dashboard-title {
        text-align: center;
        text-style: bold;
        color: $accent;
    }
    .divider { color: $primary; text-align: center; }

    DataTable { height: auto; max-height: 20; }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Sidebar()
        yield Container(
            DashboardView(id="view_dashboard"),
            CreatePostView(id="view_create", classes="hidden"),
            QueueView(id="view_queue", classes="hidden"),
            classes="main-content"
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "nav_quit":
            self.exit()
        elif event.button.id.startswith("nav_"):
            view_name = event.button.id.replace("nav_", "view_")
            for view in ["view_dashboard", "view_create", "view_queue"]:
                if view == view_name:
                    self.query_one(f"#{view}").remove_class("hidden")
                    if view == "view_queue":
                        self.query_one(QueueView).refresh_table()
                else:
                    self.query_one(f"#{view}").add_class("hidden")


if __name__ == "__main__":
    app = AutomatorApp()
    app.run()
