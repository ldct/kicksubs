import cgi
from google.appengine.api import users
from google.appengine.ext import ndb
import webapp2
import urllib

NEW_PROJECT_FORM_HTML = """\
    <form action="/new_project_post" method="post">
      <div><textarea name="title" rows="1"></textarea></div>
      <div><textarea name="description" rows="3" cols="60"></textarea></div>
      <div><textarea name="amount_backed" rows="1"></textarea></div>
      <div><input type="submit" value="Submit Project"></div>
    </form>
"""

ADD_BACKING_FORM_HTML = """\
    <form action="/add_backing_post" method="post">
      <div><textarea name="title" rows="1">%s</textarea></div>
      <div><textarea name="amount_to_back" rows="1">50</textarea></div>
      <div><input type="submit" value="Confirm Backing"></div>
    </form>
"""



DEFAULT_PROJECT_LIST_NAME = 'default_project_list'
def project_list_key(project_list_name = DEFAULT_PROJECT_LIST_NAME):
    return ndb.Key('Project_List', project_list_name)

DEFAULT_BACKING_LIST_NAME = 'default_backing_list'
def backing_list_key(backing_list_name = DEFAULT_BACKING_LIST_NAME):
    return ndb.Key('Backing_List', backing_list_name)

DEFAULT_ACCOUNT_LIST_NAME = 'default_account_list'
def account_list_key(account_list_name = DEFAULT_ACCOUNT_LIST_NAME):
    return ndb.Key('Account_List', account_list_name)

class Backing(ndb.Model):
    backer = ndb.UserProperty()
    amount_backed = ndb.IntegerProperty()

class Account(ndb.Model):
    user = ndb.UserProperty()
    balance = ndb.IntegerProperty(default=0)

class Project(ndb.Model):
    author = ndb.UserProperty()
    title = ndb.StringProperty()
    description = ndb.StringProperty()
    date_created = ndb.DateTimeProperty(auto_now_add=True)
    backers = ndb.StructuredProperty(Backing, repeated=True)

class NewProjectPostedPage(webapp2.RequestHandler):
    def post(self):
        self.response.write('<html><body>')

        project_list_name = self.request.get('project_list_name', DEFAULT_PROJECT_LIST_NAME)
        backing_list_name = self.request.get('backers_list_name', DEFAULT_BACKING_LIST_NAME)
        account_list_name = self.request.get('account_list_name', DEFAULT_ACCOUNT_LIST_NAME)
        project = Project(parent=project_list_key(project_list_name))

        if not(users.get_current_user()):
            self.response.write("Error: Not signed in!")
            return

        project.author = users.get_current_user()
        project.title = self.request.get('title')
        project.description = self.request.get('description')

        amount = int(self.request.get('amount_backed'))
        self_backing = Backing(parent=backing_list_key(backing_list_name), backer = users.get_current_user(), amount_backed = amount)
        project.backers = [self_backing]
        project.put()

        self.response.write('</body></html>')

class ProjectPage(webapp2.RequestHandler):
    def get(self, title):
        self.response.write('<html><body>')
        u_title = urllib.unquote(title)

        project_list_name = self.request.get('project_list_name', DEFAULT_PROJECT_LIST_NAME)
        projects_query = Project.query(ancestor=project_list_key(project_list_name)).filter(Project.title == u_title)
        projects = projects_query.fetch(10)

        self.response.write('%i projects found' % len(projects))

        if (len(projects) == 0):
            self.response.write("Error: no projects found with title %s" % u_title)

        for p in projects:
            self.response.write("<h1>%s</h1>" % p.title)
            self.response.write("<p>%s" % p.description)
            self.response.write("<p>Backers: %s" % str(p.backers))

class AddBackingPage(webapp2.RequestHandler):
    def get(self, title):
        self.response.write('<html><body>')

        account_list_name = self.request.get('account_list_name', DEFAULT_ACCOUNT_LIST_NAME)
        accounts = Account.query(ancestor=account_list_key(account_list_name)).filter(Account.user == users.get_current_user()).fetch(1)
        account = accounts[0]

        self.response.write('Are you sure you want to back %s? You have %s credits left' % (title, account.balance))

        self.response.write(ADD_BACKING_FORM_HTML % title)

class AddBackingPostedPage(webapp2.RequestHandler):
    
    def post(self):

        user = users.get_current_user()

        u_title = urllib.unquote(self.request.get('title'))
        amount_to_back = int(self.request.get('amount_to_back'))

        project_list_name = self.request.get('project_list_name', DEFAULT_PROJECT_LIST_NAME)
        projects_query = Project.query(ancestor=project_list_key(project_list_name)).filter(Project.title == u_title)
        project = projects_query.fetch(1)[0]

        backing_list_name = self.request.get('backers_list_name', DEFAULT_BACKING_LIST_NAME)
        account_list_name = self.request.get('account_list_name', DEFAULT_ACCOUNT_LIST_NAME)

        new_backing = Backing(parent=backing_list_key(backing_list_name), backer = user, amount_backed = amount_to_back)
        project.backers.append(new_backing)
        project.put()

        account_list_name = self.request.get('account_list_name', DEFAULT_ACCOUNT_LIST_NAME)
        account = Account.query(ancestor=account_list_key(account_list_name)).filter(Account.user == user).fetch(1)[0]

        account.balance -= amount_to_back
        account.put()

        self.response.write('</body></html>')


class MainPage(webapp2.RequestHandler):

    def get(self):

        self.response.write('<html><title>Main Page</title><body>')
        user = users.get_current_user()

        if user:
            account_list_name = self.request.get('account_list_name', DEFAULT_ACCOUNT_LIST_NAME)
            accounts = Account.query(ancestor=account_list_key(account_list_name)).filter(Account.user == user).fetch(1)

            if len(accounts) == 0:
                new_account = Account(parent=account_list_key(account_list_name))
                new_account.user = user
                new_account.balance = 0
                new_account.put()

            accounts = Account.query(ancestor=account_list_key(account_list_name)).filter(Account.user == user).fetch(1)
            account = accounts[0]

            greeting = ('Welcome, %s! You have %s credits. (<a href="%s">sign out</a>)' %
                        (user.nickname(), account.balance, users.create_logout_url('/')))
        else:
            greeting = ('<a href="%s">Sign in or register</a>.' %
                        users.create_login_url('/'))
        self.response.write(greeting)

        project_list_name = self.request.get('project_list_name', DEFAULT_PROJECT_LIST_NAME)

        projects_query = Project.query(ancestor=project_list_key(project_list_name)).order(-Project.date_created)
        projects = projects_query.fetch(10)

        self.response.write('<p> Latest %i Projects:' % len(projects))

        for p in projects:
            author_nick = p.author.nickname()
            description = cgi.escape(p.description)
            title = cgi.escape(p.title)

            self.response.write(
                '<p> <b> %s </b> by %s <br> %s' % (title, author_nick, description))

        if user: #refactor this away
            self.response.write('<p> Hello, ' + user.nickname())
            self.response.write(NEW_PROJECT_FORM_HTML)
        else:
            self.redirect(users.create_login_url(self.request.uri))



application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/add_backing/(.*)', AddBackingPage),
    ('/add_backing_post', AddBackingPostedPage),
    ('/new_project_post', NewProjectPostedPage),
    ('/project/(.*)',ProjectPage)
], debug=True)