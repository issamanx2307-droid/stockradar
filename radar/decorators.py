
from functools import wraps
from rest_framework.response import Response
from django.core.exceptions import PermissionDenied

def pro_required(view_func):
    """
    Decorator สำหรับตรวจสอบว่าผู้ใช้เป็นระดับ PRO หรือไม่
    ใช้กับ API View (Function-based views)
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"error": "กรุณาเข้าสู่ระบบเพื่อใช้งานฟีเจอร์นี้"}, status=401)
        
        if not hasattr(request.user, 'profile') or not request.user.profile.is_pro:
            return Response({
                "error": "ฟีเจอร์นี้เฉพาะสมาชิก PRO เท่านั้น",
                "upgrade_url": "/upgrade"
            }, status=403)
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view

class ProPermissionMiddleware:
    """
    Middleware สำหรับจำกัดการเข้าถึงในระดับ Request (ถ้าจำเป็น)
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ตัวอย่าง: ถ้าเข้าถึง path ที่ขึ้นต้นด้วย /api/pro/ ต้องเป็น PRO เท่านั้น
        if request.path.startswith('/api/backtest/') and request.method == "POST":
            if not request.user.is_authenticated or not request.user.profile.is_pro:
                 # สำหรับ Middleware เราอาจจะ return JSON response โดยตรง
                 from django.http import JsonResponse
                 return JsonResponse({
                     "error": "การทำ Backtest จำกัดเฉพาะสมาชิก PRO เท่านั้น"
                 }, status=403)
        
        response = self.get_response(request)
        return response
