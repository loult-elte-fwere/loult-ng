from quart import Quart, abort, redirect, render_template, request, session, url_for
from config import MOD_COOKIES
from ..handlers import cookie_check

admin = Quart(__name__)

# @cookie_check(MOD_COOKIES)
@admin.route('/')
async def admin_main():
    state = admin.config['state']
    req = request.headers.get("Cookie")
    return await render_template('main.html', state=state)    
