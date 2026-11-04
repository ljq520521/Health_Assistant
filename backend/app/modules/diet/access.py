"""Diet-local adoption of member A's real authorization dependencies."""
from fastapi import Depends, HTTPException, Request
import re
from app.modules.profile.auth import optional_user, bearer_scheme

def private_access(request:Request,credentials=Depends(bearer_scheme)):
    if request.url.path == '/api/diet/config': return
    user=optional_user(request,credentials)
    if user is None: raise HTTPException(401,'请先在健康档案页面登录',headers={'WWW-Authenticate':'Bearer'})
    if not user['consent_health_data']: raise HTTPException(403,'尚未授权处理健康数据')
    if user['role']!='admin' and user['mask_sensitive']:
        raise HTTPException(403,'当前隐私设置隐藏敏感资料，暂不提供可能推断禁忌的个人饮食数据')
    preview_paths = ('/api/diet/recipe-recommendations/preview', '/api/diet/weekly-plans/preview')
    read_only=request.method=='GET' or (request.method=='POST' and
        (request.url.path in preview_paths or re.fullmatch(r'/api/diet/weekly-plans/[0-9]+/refresh-preview',request.url.path)))
    if not read_only and user['role']!='admin': raise HTTPException(403,'仅管理员可以修改个人饮食数据')
