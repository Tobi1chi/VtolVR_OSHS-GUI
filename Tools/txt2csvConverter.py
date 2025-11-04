import re
import csv
import os
import time

def parse_and_save_to_csv(input_file, output_file):
    # 正则：匹配所有地图包（包括 WSID=0）
    main_pattern = re.compile(
        r'Name:\s*"([^"]+)"\s+ID:\s*"([^"]+)"\s+(?:True|False)\s+WSID:\s*(\d+)'
    )
    sub_pattern = re.compile(
        r'-\s+([^"]+?)\s+ID:\s*"([^"]+)"'
    )

    all_rows = []  # 存储 CSV 行数据

    current_package = None

    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                

            # 检查是否为主包行
            main_match = main_pattern.search(line)
            if main_match:
                package_name = main_match.group(1)
                #package_id = main_match.group(2)
                wsid = int(main_match.group(3))
                # 如果 WSID 为 0，用 package_name 代替
                wsid_or_name = package_name if wsid == 0 else str(wsid)
                current_package = {
                    "package_name": package_name,
                    #"package_id": package_id,
                    "wsid": wsid_or_name
                }
                continue

            # 匹配子地图
            if current_package is not None:
                sub_match = sub_pattern.search(line)
                if sub_match:
                    map_name = sub_match.group(1).strip()
                    map_id = sub_match.group(2)
                    all_rows.append({
                        "package_name": current_package["package_name"],
                        #"package_id": current_package["package_id"],
                        "wsid": current_package["wsid"],
                        "map_name": map_name,
                        "map_id": map_id
                    })

    # 写入 CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ["package_name", "wsid", "map_name", "map_id"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"✅ 已保存 {len(all_rows)} 条地图记录到 {output_file}")
    print(f"📁 文件路径: {os.path.abspath(output_file)}")

# ===== 使用 =====
if __name__ == "__main__":
    now = time.time()
    parse_and_save_to_csv("List.txt", "maplist.csv")
    print(time.time()-now)