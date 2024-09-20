from flask import Blueprint, Flask, request, render_template, redirect, session, jsonify, flash
from flask_wtf.csrf import CSRFProtect
from dotenv import dotenv_values
import os


# os.system("npm run")
config = dotenv_values('.env')

app = Flask(__name__)

# Use when implementing module
# budgets = Blueprint('budgets', __name__,
#                            template_folder='templates',
#                            static_folder='static',
#                            static_url_path='/static/budgets')

# initialize CSRF protection
csrf = CSRFProtect(app)

# checks if working in local development environment or production environment
if 'PUBLIC' in os.environ:
    # if connection string is not in local environment variables then we are working in local environment
    #db = BudgetDb(config['LOCAL_DB'])
    app.secret_key = config['SECRET_KEY']
else:
    # production
    print('Loading config.production.')

    # conn_str = current_app.config.get('CONN_STRING')

    #db = BudgetDb(os.environ['CONN_STRING'])
    ...

@app.route('/')
def hello_world():  # put application's code here
    return render_template('news_page.html')


if __name__ == '__main__':
    app.run()
