import os
import uuid
import json
from flask import Flask, render_template, request, redirect, jsonify
from supabase import create_client

app = Flask(__name__)

# ================= 配置区域 =================
# 建议：如果以后要长期用，最好把这些 Key 放到 Vercel 的 Environment Variables 里
# 但现在为了调试，直接填在这里没问题
SUPABASE_URL = "https://ryqhjxokcjlhdfxmqzjm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ5cWhqeG9rY2psaGRmeG1xemptIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc1Mjk4NjMsImV4cCI6MjA4MzEwNTg2M30.8ofjF_8g0wtkTZJKAcVd44mp0OS9RKQFCGC7YB5C_4g"
BUCKET_NAME = "images"
# ===========================================

# 初始化 Supabase (不带任何代理参数)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


@app.route('/')
def index():
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    # 1. 生成订单号
    order_id = str(uuid.uuid4())[:8]

    # 2. 获取文件
    if 'photos' not in request.files:
        return "No photos field", 400

    uploaded_files = request.files.getlist("photos")

    if not uploaded_files or uploaded_files[0].filename == '':
        return "请选择至少一张照片", 400

    print(f"开始上传订单: {order_id}，文件数: {len(uploaded_files)}")

    # 3. 循环上传
    success_count = 0
    for file in uploaded_files:
        if file.filename == '':
            continue

        try:
            file_bytes = file.read()
            # 使用 uuid 作为文件名，防止中文乱码问题
            file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
            random_filename = f"{str(uuid.uuid4())[:6]}.{file_ext}"
            file_path = f"{order_id}/{random_filename}"

            # 上传到 Supabase
            supabase.storage.from_(BUCKET_NAME).upload(
                file_path,
                file_bytes,
                {"content-type": file.content_type}
            )
            success_count += 1
        except Exception as e:
            # 打印错误但不中断整个程序
            print(f"Error uploading file: {e}")

    print(f"上传完成，成功: {success_count} 张")

    # 4. 关键修改：兼容两种跳转方式
    # 如果前端是用 fetch/ajax 请求的（带 loading 转圈那种），它需要 JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json:
        return jsonify({"redirect_url": f"/tree/{order_id}", "status": "success"})

    # 如果是普通表单提交，直接跳转
    return redirect(f"/tree/{order_id}")


@app.route('/tree/<order_id>')
def show_tree(order_id):
    image_urls = []
    try:
        # 获取文件列表
        files = supabase.storage.from_(BUCKET_NAME).list(order_id)

        if files:
            for f in files:
                # 过滤系统文件
                if f['name'] != '.emptyFolderPlaceholder':
                    public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(f"{order_id}/{f['name']}")
                    image_urls.append(public_url)
    except Exception as e:
        print(f"获取列表失败: {e}")

    # 如果没图，或者出错了，给一个空列表，防止网页崩溃
    if not image_urls:
        print("未找到图片，将使用默认空列表")

    return render_template('tree.html', photo_list=image_urls)


if __name__ == '__main__':
    # 本地运行端口改为 5001
    app.run(debug=True, port=5001)