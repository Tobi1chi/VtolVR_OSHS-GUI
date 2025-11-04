import pandas as pd
import json

# 示例数据（替换为 pd.read_csv('your_file.csv')）
data = "maplist.csv"

df = pd.read_csv(data)

# 1. 按 wsid 分组（保留 maps 列表）
by_wsid = {}
for wsid, group in df.groupby('wsid'):
    by_wsid[wsid] = {
        "package_name": group['package_name'].iloc[0],
        "maps": group[['map_name', 'map_id']].to_dict(orient='records')
    }

# 2. 按 map_name 分组（注意：同一个 map_name 可能有多个 wsid）
by_map_name = {}
for map_name, group in df.groupby('map_name'):
    # 每个条目包含 wsi d、package_name、map_id（map_name 已作为键，可省略）
    entries = group[['wsid', 'package_name', 'map_id']].to_dict(orient='records')
    by_map_name[map_name] = entries

# 合并到一个顶层 dict
output = {
    "by_wsid": by_wsid,
    "by_map_name": by_map_name
}

# 写入 JSON
with open('output_dual_index.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("已生成 dual-index JSON 文件")