class PomodoroSession:
    def __init__(self, user_id: int, focus_len: int = 25, break_len: int = 5):
        self.user_id = user_id
        self.focus_len = focus_len
        self.break_len = break_len
        self.cycle_count = 0  # Completed focus cycles
        self.state = "IDLE"   # IDLE, FOCUS, BREAK

    def next_state(self) -> tuple:
        """Determines next cycle intervals. Returns (state_string, duration_minutes)"""
        if self.state == "IDLE" or self.state == "BREAK":
            self.state = "FOCUS"
            return "FOCUS", self.focus_len
        else:
            self.cycle_count += 1
            if self.cycle_count % 4 == 0:
                self.state = "BREAK"
                return "LONG_BREAK", 15
            else:
                self.state = "BREAK"
                return "SHORT_BREAK", self.break_len

