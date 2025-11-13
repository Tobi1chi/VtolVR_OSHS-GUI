from pathlib import Path
import shutil

def zip_folder(folder: Path, out_zip: Path):
    shutil.make_archive(str(out_zip), "zip", str(folder.parent), folder.name)

def copy_folder(src: Path, dst: Path):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

def rename_folder(folder: Path, new_name: str) -> Path:
    new_path = folder.with_name(new_name)
    folder.rename(new_path)
    return new_path

def delete_folder(folder: Path):
    if folder.exists() and folder.is_dir():
        shutil.rmtree(folder)

if __name__ == "__main__":
    base = Path(r"C:\Users\28262\AppData\Roaming\Boundless Dynamics, LLC\VTOLVR\SaveData\Replays")
    f = base / "AutoSave1"

    # 压缩
    zip_folder(f, base / "AutoSave1.zip")

    # 拷贝
    copy_folder(f, base / "AutoSave1_copy")

    # 重命名
    f2 = rename_folder(f, "AutoSave1_renamed")

    # 删除
    delete_folder(f2)
