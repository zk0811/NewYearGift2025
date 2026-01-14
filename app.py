import os
import json
import random
import string
from flask import Flask, render_template, request, redirect, url_for, jsonify
from supabase import create_client, Client

app = Flask(__name__)

# --- 配置 Supabase ---
# 请确保你的 .env 文件或 Vercel 环境变量里填了这两个
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# 生成随机 ID 的小工具
def generate_short_id(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


# 1. 首页：上传照片
@app.route('/')
def index():
    return render_template('upload.html')  # 确保你的上传页面叫 upload.html (或者 index.html)


# 2. 处理上传接口
@app.route('/upload', methods=['POST'])
def upload_files():
    if 'photos' not in request.files:
        return jsonify({"error": "No files"}), 400

    files = request.files.getlist('photos')
    if not files:
        return jsonify({"error": "No files selected"}), 400

    # 生成一个本次的订单号 (Tree ID)
    tree_id = generate_short_id()

    # 上传到 Supabase
    uploaded_urls = []
    bucket_name = "images"  # 你的存储桶名字

    for file in files:
        if file.filename == '':
            continue

        # 为了不重名，给文件名加个时间戳
        # file_path = f"{tree_id}/{int(time.time())}_{file.filename}"
        # 简单点，直接用 tree_id 文件夹
        file_ext = file.filename.split('.')[-1]
        file_path = f"{tree_id}/{generate_short_id(4)}.{file_ext}"

        try:
            file_bytes = file.read()
            supabase.storage.from_(bucket_name).upload(
                path=file_path,
                file=file_bytes,
                file_options={"content-type": file.content_type}
            )
            # 获取公开链接
            public_url = supabase.storage.from_(bucket_name).get_public_url(file_path)
            uploaded_urls.append(public_url)
        except Exception as e:
            print(f"Upload failed: {e}")

    # 将链接存入数据库 (Table: trees)
    # 如果你还没有建数据库表，可以先跳过存库，直接把 URL 传给页面（但刷新会消失）
    # 这里我们用最简单的方法：把 URL 存到 Supabase 的数据库里

    try:
        data = {
            "id": tree_id,
            "photos": uploaded_urls
        }
        supabase.table("trees").insert(data).execute()
    except Exception as e:
        print(f"DB Error: {e}")
        # 如果没建表，暂时忽略错误，不影响演示

    # 上传成功，返回跳转链接
    return jsonify({"redirect_url": f"/tree/{tree_id}"})


# 3. 展示页：摇钱树
@app.route('/tree/<tree_id>')
def show_tree(tree_id):
    photo_list = []

    try:
        # 从数据库里查照片
        response = supabase.table("trees").select("*").eq("id", tree_id).execute()
        if response.data and len(response.data) > 0:
            photo_list = response.data[0].get("photos", [])
        else:
            # 如果没查到（可能没建表），我们尝试直接去 Storage 也就是存储桶里找找看
            # (这是一个备用方案，防止你没建数据库表)
            files = supabase.storage.from_("images").list(tree_id)
            if files:
                for f in files:
                    public_url = supabase.storage.from_("images").get_public_url(f"{tree_id}/{f['name']}")
                    photo_list.append(public_url)

    except Exception as e:
        print(f"Error fetching tree: {e}")
        photo_list = []

    # 关键点：把 photo_list 传给网页！
    return render_template('tree.html', photo_list=photo_list)


if __name__ == '__main__':
    app.run(debug=True, port=5001)