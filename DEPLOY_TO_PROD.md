# Knowledge Assistant 生产环境部署指南

## 端口分配

| 项目 | 后端 | 前端 |
|------|------|------|
| TravelMind | 8000 | - |
| POD | 8001 | 3002 |
| **Knowledge** | **8002** | **3003** |

## 1. 上传代码

```bash
# 上传到服务器
scp -r knowledge-assistant root@your-server:/opt/
cd /opt/knowledge-assistant
```

## 2. 配置环境

```bash
cp backend/.env.example backend/.env
nano backend/.env
```

**关键配置**:
- `DEFAULT_LLM_PROVIDER` / `DEFAULT_LLM_MODEL`
- `QWEN_API_KEY` 或 `DEEPSEEK_API_KEY`

## 3. 构建并启动

```bash
# 确保 TravelMind 网络存在
docker network ls | grep travelmind-network

# 构建并启动
docker compose -f docker-compose.prod.yml up -d --build

# 查看状态
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f
```

## 4. 配置 Nginx

```bash
# 复制配置
cp deployment/nginx_knowledge.conf /etc/nginx/sites-available/mind-travelmind

# 启用站点
ln -s /etc/nginx/sites-available/mind-travelmind /etc/nginx/sites-enabled/

# 测试并重载
nginx -t && systemctl reload nginx
```

## 5. 配置 SSL (推荐)

```bash
certbot --nginx -d mind.travelmind.cloud
```

## 6. 验证

- 访问: https://mind.travelmind.cloud
- API 文档: https://mind.travelmind.cloud/docs
- 健康检查: https://mind.travelmind.cloud/health

## 常用命令

```bash
# 查看日志
docker compose -f docker-compose.prod.yml logs -f backend

# 重启服务
docker compose -f docker-compose.prod.yml restart

# 停止服务
docker compose -f docker-compose.prod.yml down

# 重新构建
docker compose -f docker-compose.prod.yml up -d --build
```
