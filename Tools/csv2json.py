import panda as pd
import json

# Example data (replace with pd.read_csv('your_file.csv'))
data = "maplist.csv"

df = pd.read_csv(data)

# 1. Group by wsid (keep maps list)
by_wsid = {}
for wsid, group in df.groupby('wsid'):
    by_wsid[wsid] = {
        "package_name": group['package_name'].iloc[0],
        "maps": group[['map_name', 'map_id']].to_dict(orient='records')
    }

# 2. Group by map_name (note: same map_name may have multiple wsids)
by_map_name = {}
for map_name, group in df.groupby('map_name'):
    # Each entry contains wsid, package_name, map_id (map_name already as key, can be omitted)
    entries = group[['wsid', 'package_name', 'map_id']].to_dict(orient='records')
    by_map_name[map_name] = entries

# Merge into a top-level dict
output = {
    "by_wsid": by_wsid,
    "by_map_name": by_map_name
}

# Write to JSON
with open('output_dual_index.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("Generated dual-index JSON file")