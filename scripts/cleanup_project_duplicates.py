import json
import subprocess
import argparse
import sys

def run_command(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return None
    return result.stdout

def main():
    parser = argparse.ArgumentParser(description='Cleanup duplicate project items.')
    parser.add_argument('--dry-run', action='store_true', help='Display items to be archived without executing.')
    args = parser.parse_args()

    owner = "nayasuda"
    project_number = 1

    print(f"Fetching items for project {project_number} (owner: {owner})...")
    cmd = f"gh project item-list {project_number} --owner {owner} --format json --limit 1000"
    output = run_command(cmd)
    if not output:
        return

    try:
        data = json.loads(output)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        return

    items = data.get("items", [])
    
    # Group by title
    groups = {}
    for item in items:
        title = item.get("title")
        if not title:
            continue
        if title not in groups:
            groups[title] = []
        groups[title].append(item)

    archive_list = []
    
    for title, group in groups.items():
        if len(group) <= 1:
            continue
        
        # Priority for keeping:
        # 1. Status is NOT "Done"
        # 2. ID is larger (newer)
        
        non_done_items = [i for i in group if i.get("status") != "Done"]
        
        if non_done_items:
            # Keep the newest non-done item
            non_done_items.sort(key=lambda x: x.get("id", ""), reverse=True)
            keep_item = non_done_items[0]
        else:
            # All are Done, keep the newest one
            group.sort(key=lambda x: x.get("id", ""), reverse=True)
            keep_item = group[0]
            
        for item in group:
            if item["id"] != keep_item["id"]:
                archive_list.append(item)

    if not archive_list:
        print("\nNo duplicates found.")
        return

    print(f"\nFound {len(archive_list)} items to archive:")
    for item in archive_list:
        print(f"- [{item.get('status')}] {item.get('title')} (ID: {item.get('id')})")

    print(f"\nTotal items to archive: {len(archive_list)}")

    if args.dry_run:
        print("\n[Dry Run] No items were actually archived.")
    else:
        print("\nArchiving items...")
        for item in archive_list:
            item_id = item.get("id")
            print(f"Archiving {item_id}...")
            archive_cmd = f"gh project item-archive {project_number} --owner {owner} --id {item_id}"
            run_command(archive_cmd)
        print("Done.")

if __name__ == "__main__":
    main()
