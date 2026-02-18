import json
import os
import sys

# ANSI Escape Sequences for coloring
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

LOG_FILE = "/home/natsuki/multi-agent-phantom/memory/daily_log.jsonl"

def print_header():
    title = "PHANTOM LOG VIEWER"
    print(f"\n{Colors.BOLD}{Colors.RED}{'=' * 20} {title} {'=' * 20}{Colors.RESET}")
    header = f"{'DATE':<11} | {'TIME':<6} | {'EXECUTOR':<10} | {'RESULT':<7} | {'SUMMARY'}"
    print(f"{Colors.BOLD}{header}{Colors.RESET}")
    print(f"{Colors.RED}{'-' * 75}{Colors.RESET}")

def format_row(entry):
    res = entry.get('result', '').lower()
    res_str = entry.get('result', 'N/A').upper()
    res_color = Colors.GREEN if res in ['pass', 'success'] else Colors.RED
    
    date = entry.get('date', 'YYYY-MM-DD')
    time = entry.get('time', 'HH:MM')
    executor = entry.get('executor', 'unknown')
    summary = entry.get('summary', '')
    
    # Character specific colors
    exec_map = {
        'joker': Colors.RED,
        'skull': Colors.YELLOW,
        'panther': Colors.MAGENTA,
        'fox': Colors.BLUE,
        'queen': Colors.CYAN,
        'mona': Colors.GREEN,
        'oracle': Colors.YELLOW,
        'noir': Colors.MAGENTA,
        'violet': Colors.MAGENTA,
        'wolf': Colors.BLUE,
        'crow': Colors.WHITE
    }
    exec_color = exec_map.get(executor.lower(), Colors.WHITE)
    
    row = f"{date:<11} | {time:<6} | {exec_color}{executor.upper():<10}{Colors.RESET} | {res_color}{res_str:<7}{Colors.RESET} | {summary}"
    return row

def main():
    if not os.path.exists(LOG_FILE):
        print(f"{Colors.RED}Error: Target log not found: {LOG_FILE}{Colors.RESET}")
        return

    logs = []
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"{Colors.RED}Error reading file: {e}{Colors.RESET}")
        return

    # Default to show latest 10
    display_count = 10
    if len(sys.argv) > 1:
        try:
            display_count = int(sys.argv[1])
        except ValueError:
            pass

    latest_logs = logs[-display_count:] if len(logs) > 0 else []

    print_header()
    if not latest_logs:
        print(f"{Colors.YELLOW}No records found.{Colors.RESET}")
    else:
        for log in latest_logs:
            print(format_row(log))
    
    print(f"{Colors.RED}{'-' * 75}{Colors.RESET}")
    print(f" Showing {len(latest_logs)} of {len(logs)} entries.\n")

if __name__ == "__main__":
    main()