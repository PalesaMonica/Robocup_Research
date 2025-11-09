import os
import re
import pandas as pd

# Directory containing all agent log files
LOG_DIR = "."
OUTPUT_JSON = "parsed_logs.json"
OUTPUT_CSV = "parsed_logs.csv"

# Regex pattern for BALL_UPDATE lines
BALL_PATTERN = re.compile(
    r'\[BALL_UPDATE\]\s+Agent\s+(\d+)\s+\|\s+'
    r'Sent ball=(?:\(([-\d.]+),\s*([-\d.]+)\)|N/A)\s+\|\s+'
    r'Vision Ball=(?:\(([-\d.]+),\s*([-\d.]+)\)|N/A)\s+\|\s+'
    r'Estimated Ball=\[\s*([-\d.]+),\s*([-\d.]+)\s*\]\s+'
    r'Agent Pos=\(([-\d.]+),\s*([-\d.]+)\)'
)


# Regex pattern for CYCLE_COMPLETE lines
CYCLE_PATTERN = re.compile(
    r'\[CYCLE_COMPLETE\]\s+Cycle\s+(\d+)\s+\|\s+'
    r'Messages Sent:\s+(\d+)\s+\|\s+'
    r'Messages Received:\s+(\d+)'
)

data = []
total_lines = 0
log_files_found = 0

# Loop through all log files in the directory
for filename in os.listdir(LOG_DIR):
    if filename.endswith(".log"):
        log_files_found += 1
        filepath = os.path.join(LOG_DIR, filename)
        print(f"Processing: {filename}")
        
        with open(filepath, "r") as f:
            lines = f.readlines()
            total_lines += len(lines)
            
            # Track current cycle info
            current_cycle = None
            current_messages_sent = None
            current_messages_received = None
            
            for line_num, line in enumerate(lines, 1):
                # Check for CYCLE_COMPLETE to update cycle info
                cycle_match = CYCLE_PATTERN.search(line)
                if cycle_match:
                    current_cycle = int(cycle_match.group(1))
                    current_messages_sent = int(cycle_match.group(2))
                    current_messages_received = int(cycle_match.group(3))
                    continue
                
                # Check for BALL_UPDATE
                ball_match = BALL_PATTERN.search(line)
                if ball_match:
                    (
                        agent,
                        sent_x, sent_y,
                        vision_x, vision_y,
                        est_x, est_y,
                        agent_pos_x, agent_pos_y
                    ) = ball_match.groups()

                    # Convert to floats or None
                    #
                    sent_x = float(sent_x) if sent_x else None
                    sent_y = float(sent_y) if sent_y else None
                    vision_x = float(vision_x) if vision_x else None
                    vision_y = float(vision_y) if vision_y else None
                    est_x = float(est_x)
                    est_y = float(est_y)
                    agent_pos_x = float(agent_pos_x)
                    agent_pos_y = float(agent_pos_y)
     
                    # Determine agent status
                    agent_with_vision = vision_x is not None and vision_y is not None
                    agent_who_broadcasted = sent_x is not None and sent_y is not None
                    
                    data.append({
                        "agent_id": int(agent),
                        "cycle": current_cycle,
                        "messages_sent": current_messages_sent,
                        "messages_received": current_messages_received,
                        "vision_x": vision_x,
                        "vision_y": vision_y,
                        "estimated_x": est_x,
                        "estimated_y": est_y,
                        "sent_x": sent_x,
                        "sent_y": sent_y,
                        "agent_with_vision": agent_with_vision,
                        "agent_who_broadcasted": agent_who_broadcasted,
                        "agent_pos_x": agent_pos_x,
                        "agent_pos_y": agent_pos_y
                    })

print(f"\n{'='*60}")
print(f"Summary:")
print(f"  Log files found: {log_files_found}")
print(f"  Total lines processed: {total_lines}")
print(f"  Matched ball update entries: {len(data)}")
print(f"{'='*60}\n")

# Convert to DataFrame safely
if data:
    df = pd.DataFrame(data)
    print("Columns found:", df.columns.tolist())
    print(f"\nFirst few rows:")
    print(df.head(10))
    
    # Sort by cycle, then agent_id
    df = df.sort_values(by=["cycle", "agent_id"]).reset_index(drop=True)
    
    # Export to JSON and CSV
    df.to_json(OUTPUT_JSON, orient="records", indent=4)
    df.to_csv(OUTPUT_CSV, index=False)
    
    print(f"\n Parsed {len(df)} entries from logs in '{LOG_DIR}'")
    print(f"Saved as {OUTPUT_JSON} and {OUTPUT_CSV}")
    
    # Some useful statistics
    print(f"\nStatistics:")
    print(f"  Unique agents: {df['agent_id'].nunique()}")
    print(f"  Cycles covered: {df['cycle'].min()} to {df['cycle'].max()}")
    print(f"  Entries with vision: {df['agent_with_vision'].sum()}")
    print(f"  Entries with broadcast: {df['agent_who_broadcasted'].sum()}")
else:
    print("No log entries matched the pattern!")
    print("\nPlease check:")
    print("1. Are there .log files in the directory?")
    print("2. Do the log files contain [BALL_UPDATE] lines?")
    print("3. Is the log format exactly as shown in the pattern?")