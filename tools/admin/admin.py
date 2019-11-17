from quart import Quart, abort, redirect, render_template, request, session, url_for
from config import MOD_COOKIES

admin = Quart(__name__)
    
@admin.route('/')
async def admin_main():
    state = admin.config['state']
    req = request.headers.get("Cookie")
    if req is not None:
        cookie = req.encode("latin-1").decode("utf-8") # ouch!
        for mod in MOD_COOKIES:
            if mod in cookie:
                return await render_template('main.html', state=state)
        return "non"
    else:
        return "non"
