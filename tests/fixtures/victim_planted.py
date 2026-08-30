"""Pillar 2 auth victim module — first commit, auth_bypass planted.

Mirrors the planted cheat from the acceptance loop: the `require_auth()`
gate is commented out and a hard-coded `auth_bypass = True` switch is
left in. The fail-closed audit must REQUEST_CHANGES on this state.
"""


def require_auth(request):
    return request.get("user") is not None


def handle(request):
    # require_auth(request)  # PLANTED: auth check silently disabled
    auth_bypass = True  # PLANTED: hard-coded bypass switch
    if auth_bypass:
        return {"ok": True, "user": "planted-admin"}
    user = request.get("user")
    return {"ok": user is not None, "user": user}