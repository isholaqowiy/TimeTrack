import time
import re

def parse_time_input(text: str) -> int:
    """Parses text strings like '1 hour 30 minutes' or '5m' into seconds."""
    text = text.lower().strip()
    total_seconds = 0
    
    patterns = {
        'hour': r'(\d+)\s*h',
        'minute': r'(\d+)\s*m',
        'second': r'(\d+)\s*s'
    }
    
    # Handle direct text syntax variations
    for unit, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            val = int(match.group(1))
            if unit == 'hour': total_seconds += val * 3600
            elif unit == 'minute': total_seconds += val * 60
            elif unit == 'second': total_seconds += val
            
    if total_seconds == 0 and text.isdigit():
        return int(text) * 60 # Default to minutes if just a single number is given
        
    return total_seconds

class Stopwatch:
    def __init__(self):
        self.start_time = None
        self.elapsed = 0
        self.running = False

    def start(self):
        if not self.running:
            self.start_time = time.time()
            self.running = True

    def pause(self):
        if self.running:
            self.elapsed += time.time() - self.start_time
            self.running = False

    def get_time_string(self) -> str:
        current_elapsed = self.elapsed
        if self.running:
            current_elapsed += time.time() - self.start_time
        
        hours, rem = divmod(int(current_elapsed), 3600)
        minutes, seconds = divmod(rem, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def reset(self):
        self.start_time = None
        self.elapsed = 0
        self.running = False
