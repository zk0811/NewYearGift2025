import os
import uuid
from flask import Flask, render_template, request, redirect
from supabase import create_client

# ============ 【智能代理设置】 ============
# 只有在本地运行且不是 Vercel 环境时才启用代理
# 如果你关闭了翻墙软件，请把这段暂时注释掉，否则会报错
if not os.environ.get('VERCEL'):
    proxy_address = "http://127.0.0.1:10809"
    os.environ['HTTP_PROXY'] = proxy_address
    os.environ['HTTPS_PROXY'] = proxy_address
    print(f"检测到本地环境，已开启代理: {proxy_address}")
else:
    print("检测到 Vercel 环境，已自动关闭代理")
# ========================================

app = Flask(__name__)

# ================= 配置区域 =================
SUPABASE_URL = "https://ryqhjxokcjlhdfxmqzjm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ5cWhqeG9rY2psaGRmeG1xemptIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc1Mjk4NjMsImV4cCI6MjA4MzEwNTg2M30.8ofjF_8g0wtkTZJKAcVd44mp0OS9RKQFCGC7YB5C_4g"
BUCKET_NAME = "images"
# ===========================================

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


@app.route('/')
def index():
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    # 生成短 ID
    order_id = str(uuid.uuid4())[:8]
    uploaded_files = request.files.getlist("photos")

    if not uploaded_files:
        return "没有选择文件", 400

    print(f"正在上传订单: {order_id}, 文件数量: {len(uploaded_files)}")

    for file in uploaded_files:
        if file.filename == '':
            continue

        file_bytes = file.read()
        # 为了防止中文文件名出错，这里也可以只用 uuid 命名，但目前保持你原来的写法
        file_path = f"{order_id}/{file.filename}"
        content_type = file.content_type

        try:
            supabase.storage.from_(BUCKET_NAME).upload(
                file_path,
                file_bytes,
                {"content-type": content_type}
            )
        except Exception as e:
            print(f"上传单个文件失败: {e}")

    return redirect(f"/tree/{order_id}")


@app.route('/tree/<order_id>')
def show_tree(order_id):
    print(f"正在查询订单: {order_id}")
    image_urls = []

    try:
        # 获取文件列表
        files = supabase.storage.from_(BUCKET_NAME).list(order_id)

        # 确保 files 不是 None 且有内容
        if files:
            for f in files:
                # 过滤掉系统生成的隐藏文件（如果有的话）
                if f['name'] != '.emptyFolderPlaceholder':
                    public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(f"{order_id}/{f['name']}")
                    image_urls.append(public_url)
    except Exception as e:
        print(f"获取图片列表失败: {e}")
        # 如果出错，给一个空列表，防止网页报错白屏
        image_urls = []

    print(f"找到图片数量: {len(image_urls)}")

    # 这里 photo_list 会传递给摇钱树页面
    return render_template('tree.html', photo_list=image_urls)


if __name__ == '__main__':
    # 【重点修改】端口改为 5001，避免冲突
    print("服务正在启动，请访问 http://127.0.0.1:5001")
    app.run(debug=True, port=5001)