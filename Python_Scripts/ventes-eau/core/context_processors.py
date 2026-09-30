def roles(request):
    is_boss = False
    if request.user.is_authenticated:
        is_boss = request.user.is_superuser or request.user.groups.filter(name="Chef").exists()
    return {"is_boss": is_boss}