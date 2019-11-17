from quart import Quart, abort, redirect, render_template, request, session, url_for

from config import MOD_COOKIES

#admin interace
admin = Quart(__name__)
    
@admin.route('/')
async def admin_main():
    cookie = request.headers.get("Cookie").encode("latin-1").decode("utf-8") # ouch!
    print(cookie)
    for mod in MOD_COOKIES:
        print(mod in cookie)
        if mod in cookie:
            return "authorized"
    return "non"
