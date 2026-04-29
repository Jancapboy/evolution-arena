#!/bin/bash
# 进化竞技场生产环境启动脚本
# 同时启动Python后端和Node生产服务器

set -e

echo "🧬 Evolution Arena 生产模式启动中..."
echo ""

# 加载环境配置
if [ -f "python_backend/.env" ]; then
    echo "📝 加载 python_backend/.env..."
    set -a
    source python_backend/.env
    set +a
fi

# 检查必要环境变量
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "❌ 错误: DEEPSEEK_API_KEY 未设置"
    echo "   请在 python_backend/.env 中配置 DEEPSEEK_API_KEY=***"
    exit 1
fi

echo "✅ API配置: $DEEPSEEK_API_URL"
echo "   模型: $DEEPSEEK_MODEL"
echo ""

# 检查Python依赖
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "📦 安装Python依赖..."
    cd python_backend
    pip install -r requirements.txt -q
    cd ..
fi

# 检查Node依赖
if [ ! -d "node_modules" ]; then
    echo "📦 安装Node依赖..."
    npm ci
fi

# 构建前端
if [ ! -d "dist/public" ]; then
    echo "🛠️  构建前端..."
    npm run build
fi

# 启动Python后端（后台）
echo "🐍 启动Python FastAPI后端 (端口8000)..."
cd python_backend
python3 main.py &
PYTHON_PID=$!
cd ..

# 等待Python启动
sleep 3

# 检查Python是否启动成功
if ! kill -0 $PYTHON_PID 2>/dev/null; then
    echo "❌ Python后端启动失败"
    exit 1
fi

echo "✅ Python后端已启动 (PID: $PYTHON_PID)"

# 启动Node生产服务器
echo "⚛️  启动Node生产服务器 (端口3000)..."
NODE_ENV=production PORT=3000 npm run start &
NODE_PID=$!

sleep 2

if ! kill -0 $NODE_PID 2>/dev/null; then
    echo "❌ Node服务器启动失败"
    kill $PYTHON_PID 2>/dev/null || true
    exit 1
fi

echo ""
echo "✅ 生产环境已启动！"
echo "   主服务: http://localhost:3000"
echo "   Python API: http://localhost:8000"
echo "   健康检查: http://localhost:3000/api/health"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo ""

# 捕获退出信号
trap "echo '正在停止服务...'; kill $PYTHON_PID $NODE_PID 2>/dev/null; exit 0" INT TERM

wait
