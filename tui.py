# tui.py - v4 (Added !quit command)

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Log
from textual.binding import Binding

from core import Node

class NodeApp(App):
    TITLE = "MeshMate Node"
    CSS_PATH = "node.css"

    BINDINGS = [
        Binding(key="q", action="quit", description="Quit")
    ]

    def __init__(self, host, port, peers):
        super().__init__()
        self.node = Node(host, port, peers, app_interface=self)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Log(id="log")
        yield Input(placeholder="Type your message and press Enter...", id="input")
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self.node.start_networking, thread=True)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Called when the user presses Enter in the Input widget."""
        message_content = event.value

        # --- NEW QUIT LOGIC ---
        if message_content == '!quit':
            # If the user types !quit, broadcast it to others and exit this node.
            self.node.submit_message(message_content)
            self.exit() # Exit this app immediately.
            return # Stop further processing
        
        if message_content:
            # This is the existing logic for sending regular or !sos messages
            log_widget = self.query_one("#log", Log)
            log_widget.write_line(f"[SENT]: {message_content}")
            self.node.submit_message(message_content)
            
            self.query_one("#input", Input).clear()
    
    def action_quit(self) -> None:
        """The action for the 'q' key binding."""
        self.node.submit_message("!quit") # Also send the quit command on key press
        self.exit()

    def log_message(self, message: str) -> None:
        """A thread-safe method for BACKGROUND THREADS to write to the log."""
        log = self.query_one("#log", Log)
        self.call_from_thread(log.write_line, message)