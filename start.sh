#!/bin/bash
# 进化竞技场启动脚本
# 同时启动Python后端和前端开发服务器

echo "🧬 Evolution Arena 启动中..."
echo ""

# 检查环境变量
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "⚠️  警告: DEEPSEEK_API_KEY 环境变量未设置"
    echo "   请设置后重新启动: export DEEPSEEK_API_KEY=your_key_here"
    echo ""
fi

# 启动Python后端（后台）
echo "🐍 启动Python后端 (端口8000)..."
cd python_backend
python3 main.py &
PYTHON_PID=$!
cd ..

# 等待Python启动
sleep 2

# 启动前端
echo "⚛️  启动前端开发服务器 (端口3000)..."
npm run dev &
NODE_PID=$!

echo ""
echo "✅ 系统已启动！"
echo "   前端: http://localhost:3000"
echo "   后端: http://localhost:8000"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo ""

# 捕获退出信号
trap "echo '正在停止服务...'; kill $PYTHON_PID $NODE_PID 2>/dev/null; exit 0" INT TERM

wait
