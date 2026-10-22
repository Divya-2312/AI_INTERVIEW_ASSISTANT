import os

exclude_dirs = {'node_modules', '.git', 'venv', '.venv', 'dist', 'build', '__pycache__', '.pytest_cache'}
binary_exts = {'.gguf', '.zip', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.exe', '.dll', '.so'}

stats_by_ext = {}
loc_by_ext = {}
folder_stats = {}
total_files = 0
total_loc = 0

for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in exclude_dirs]
    rel_root = os.path.relpath(root, '.')
    top_folder = rel_root.split(os.sep)[0] if rel_root != '.' else '.'
    
    if top_folder not in folder_stats:
        folder_stats[top_folder] = {'files': 0, 'loc': 0}
        
    for f in files:
        path = os.path.join(root, f)
        ext = os.path.splitext(f)[1].lower() or '(no ext)'
        if ext in binary_exts:
            continue
            
        lines = 0
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                lines = sum(1 for _ in fp)
        except Exception:
            pass
        
        total_files += 1
        total_loc += lines
        stats_by_ext[ext] = stats_by_ext.get(ext, 0) + 1
        loc_by_ext[ext] = loc_by_ext.get(ext, 0) + lines
        
        folder_stats[top_folder]['files'] += 1
        folder_stats[top_folder]['loc'] += lines

print(f"Total non-binary text files: {total_files}, Total text LOC: {total_loc}")
print("\n--- Text File Counts & LOC by Extension ---")
for ext, count in sorted(stats_by_ext.items(), key=lambda x: x[1], reverse=True):
    print(f"{ext:<12} | Files: {count:<4} | LOC: {loc_by_ext[ext]}")

print("\n--- By Main Folder (Text Files Only) ---")
for fld, data in sorted(folder_stats.items()):
    print(f"{fld:<15} | Files: {data['files']:<4} | LOC: {data['loc']}")
