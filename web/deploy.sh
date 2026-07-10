#!/bin/bash
# deploy.sh — 一键部署自助兑换 Web 服务到服务器
# 用法: bash web/deploy.sh
# 注意: 需要设置 DEPLOY_SERVER 和 DEPLOY_USER 环境变量

set -e

SERVER="${DEPLOY_SERVER:?请设置 DEPLOY_SERVER 环境变量（IP 地址）}"
PORT="${DEPLOY_PORT:-9000}"
USER="${DEPLOY_USER:?请设置 DEPLOY_USER 环境变量（SSH 用户名）}"

SERVER="${DEPLOY_SERVER:-}"
PORT="9000"
USER="${DEPLOY_USER:-}"

echo "🚀 部署 Bounty Plaza 兑换系统到 $SERVER:$PORT"

# 1. 打包本地文件
echo "📦 打包文件..."
tar czf /tmp/bounty-plaza-web.tar.gz \
  web/app.py \
  web/requirements.txt \
  scripts/coin.py \
  BOUNTY_CONFIG.json \
  data/

# 2. 上传到服务器
echo "📤 上传到服务器..."
scp /tmp/bounty-plaza-web.tar.gz $USER@$SERVER:/opt/bounty-plaza/
ssh $USER@$SERVER "mkdir -p /opt/bounty-plaza && tar xzf /opt/bounty-plaza/bounty-plaza-web.tar.gz -C /opt/bounty-plaza"

# 3. 安装依赖
echo "📦 安装 Python 依赖..."
ssh $USER@$SERVER "cd /opt/bounty-plaza/web && pip install -r requirements.txt -q"

# 4. 创建 systemd 服务
echo "⚙️ 注册 systemd 服务..."
ssh $USER@$SERVER "cat > /etc/systemd/system/bounty-plaza.service << 'SERVICEEOF'
[Unit]
Description=Bounty Plaza Redemption API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/bounty-plaza/web
ExecStart=$(which python3) app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICEEOF"

# 5. 启动服务
echo "🚀 启动服务..."
ssh $USER@$SERVER "systemctl daemon-reload && systemctl enable bounty-plaza && systemctl restart bounty-plaza"

# 6. 开放防火墙
echo "🔓 开放端口 $PORT..."
ssh $USER@$SERVER "ufw allow $PORT/tcp 2>/dev/null || firewall-cmd --add-port=$PORT/tcp --permanent 2>/dev/null || echo '防火墙配置跳过'"

echo ""
echo "✅ 部署完成！"
echo "   API: http://$SERVER:$PORT"
echo "   Swagger UI: http://$SERVER:$PORT/docs"
echo "   查看日志: ssh $USER@$SERVER 'journalctl -u bounty-plaza -f'"
