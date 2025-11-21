import queue
from aider.io import InputOutput

class ServerIO(InputOutput):
    def __init__(self, pretty=False, yes=True, dry_run=False, encoding="utf-8"):
        super().__init__(pretty=pretty, yes=yes, dry_run=dry_run, encoding=encoding)
        self.output_queue = queue.Queue()

    def tool_output(self, *messages, log_only=False, bold=False):
        if not log_only:
            # Join messages with space as per base class logic
            msg = " ".join(str(m) for m in messages) if messages else ""
            self.output_queue.put({"type": "tool_output", "content": msg})
        super().tool_output(*messages, log_only=log_only, bold=bold)

    def tool_error(self, msg, strip=True):
        self.output_queue.put({"type": "tool_error", "content": msg})
        super().tool_error(msg, strip=strip)

    def tool_warning(self, msg, strip=True):
        self.output_queue.put({"type": "tool_warning", "content": msg})
        super().tool_warning(msg, strip=strip)

    def assistant_output(self, message, pretty=None):
        # We don't capture this here because we stream the LLM response directly
        # from the Coder generator in the API endpoint.
        # However, for non-streaming responses (if any), we might need it.
        pass
        
    def get_captured_lines(self):
        lines = []
        while not self.output_queue.empty():
            lines.append(self.output_queue.get())
        return lines
