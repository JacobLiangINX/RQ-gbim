from flask import Flask
#from flask import render_template, redirect, url_for, request,flash
#from flask_login import UserMixin, LoginManager, login_required, current_user, login_user, logout_user

app = Flask("project")

from project.controllers import *
