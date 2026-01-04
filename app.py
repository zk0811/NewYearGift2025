import os

# ============ 【智能代理设置】 ============
# 逻辑：如果没有检测到是在 Vercel 环境下运行，就使用本地代理
# 这样你本地测试依然能通，传上去也不会报错
if not os.environ.get('VERCEL'):
    # 这里填你刚才测试成功的那个端口 (比如 10809 或 7890)
    proxy_address = "http://127.0.0.1:10809"
    os.environ['HTTP_PROXY'] = proxy_address
    os.environ['HTTPS_PROXY'] = proxy_address
    print(f"检测到本地环境，已开启代理: {proxy_address}")
else:
    print("检测到 Vercel 环境，已自动关闭代理")
# ========================================

import uuid
from flask import Flask, render_template, request, redirect
from supabase import create_client

app = Flask(__name__)

# ... 下面保持你原来的配置和代码不变 ...
app = Flask(__name__)

# ================= 配置区域 =================
# 把你的 Supabase URL 和 Key 填在这里
SUPABASE_URL = "https://ryqhjxokcjlhdfxmqzjm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ5cWhqeG9rY2psaGRmeG1xemptIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc1Mjk4NjMsImV4cCI6MjA4MzEwNTg2M30.8ofjF_8g0wtkTZJKAcVd44mp0OS9RKQFCGC7YB5C_4g"
BUCKET_NAME = "images"  # 你刚才建的桶的名字
# ===========================================

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


@app.route('/')
def index():
    # 首页显示上传页面
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    # 1. 生成一个唯一的订单号 (Order ID)
    order_id = str(uuid.uuid4())[:8]  # 比如 "a1b2c3d4"

    uploaded_files = request.files.getlist("photos")

    if not uploaded_files:
        return "没有选择文件", 400

    # 2. 遍历上传的文件并存到 Supabase
    for file in uploaded_files:
        if file.filename == '':
            continue

        file_bytes = file.read()
        file_path = f"{order_id}/{file.filename}"  # 存放在 folders/文件名
        content_type = file.content_type

        # 上传到 Supabase Storage
        supabase.storage.from_(BUCKET_NAME).upload(
            file_path,
            file_bytes,
            {"content-type": content_type}
        )

    # 3. 上传完成，跳转到展示页
    return redirect(f"/tree/{order_id}")


@app.route('/tree/<order_id>')
def show_tree(order_id):
    # 1. 去 Supabase 查询这个订单号下的所有图片
    # 注意：这里我们列出该文件夹下的所有文件
    try:
        files = supabase.storage.from_(BUCKET_NAME).list(order_id)
    except Exception as e:
        return f"找不到订单或网络错误: {e}"

    image_urls = []
    if files:
        for f in files:
            # 拼接公开访问链接
            # 格式通常是: ProjectURL/storage/v1/object/public/BucketName/Path
            public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(f"{order_id}/{f['name']}")
            image_urls.append(public_url)

    # 2. 把图片链接列表传给 tree.html
    return render_template('tree.html', photo_list=image_urls)


if __name__ == '__main__':
    app.run(debug=True, port=5000)