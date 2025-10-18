# server.py
import socket
import json
import os

HOST = '127.0.0.1'  # localhost
PORT = 23232
JSON_FILE_PATH = 'state_machine1.json'  # 替换为你的 JSON 文件路径


def stream_json_file(client_socket, file_path):
    """以流式方式发送 JSON 文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
        #     # 方式1：按行发送（适合 JSONL 格式：每行一个 JSON 对象）
        #     for line in f:
        #         line = line.strip()
        #         if not line:
        #             continue
        #         # 可选：验证是否为有效 JSON（可省略以提高性能）
        #         # json.loads(line)  # 如果格式错误会抛出异常
        #         client_socket.sendall((line + '\n').encode('utf-8'))

        # 或者方式2：按固定块发送（适合任意 JSON 文件）
            f.seek(0)
            while True:
                chunk = f.read(4096)  # 4KB 块
                if not chunk:
                    break
                client_socket.sendall(chunk.encode('utf-8'))

    except FileNotFoundError:
        error_msg = json.dumps({"error": "JSON file not found"}) + '\n'
        client_socket.sendall(error_msg.encode('utf-8'))
    except Exception as e:
        error_msg = json.dumps({"error": str(e)}) + '\n'
        client_socket.sendall(error_msg.encode('utf-8'))


def main():
    if not os.path.exists(JSON_FILE_PATH):
        print(f"警告: {JSON_FILE_PATH} 不存在，客户端连接时会收到错误。")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        print(f"服务端启动，监听 {HOST}:{PORT}...")

        while True:
            try:
                client_socket, addr = server_socket.accept()
                print(f"客户端 {addr} 已连接")
                try:
                    stream_json_file(client_socket, JSON_FILE_PATH)
                finally:
                    client_socket.close()
                    print(f"客户端 {addr} 连接已关闭")
            except KeyboardInterrupt:
                print("\n服务端被用户中断")
                break
            except Exception as e:
                print(f"处理客户端时出错: {e}")


if __name__ == '__main__':
    main()