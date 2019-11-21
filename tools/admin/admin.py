from quart import Quart, abort, redirect, render_template, request, session, url_for
from config import MOD_COOKIES
from ..handlers import cookie_check

admin = Quart(__name__)

@admin.route('/')
async def admin_main():
    # maybe this whole block could be replace with @cookie_check(MOD_COOKIES)
    req = request.headers.get("Cookie")
    if req is not None:
        cookie = req.encode("latin-1").decode("utf-8") # ouch!
        for mod in MOD_COOKIES:
            if mod in cookie:
                state = admin.config['state']
                return await render_template('main.html', state=state)
        return "nonnw"
    else:
        return "nonnw"
