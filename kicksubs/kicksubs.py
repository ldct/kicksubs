import cgi

from google.appengine.api import users
from google.appengine.ext import ndb

import webapp2
from webapp2_extras.appengine.users import login_required, admin_required

import urllib
from base64 import b64encode

NEW_PROJECT_FORM_HTML = """\
    <form action="/add_project_post" method="post">
      <div>Title: <input name="title" rows="1"></input></div>
      Description: <div><textarea name="description"3"  rows="cols="60"></textarea></div>
      <p> Want to put up some of your own money to back this project? 
      <div>Amount: <input name="amount_backed" value=10></input></div>
      <div><input type="submit" value="Submit Project"></div>
    </form>
"""

ADD_BACKING_FORM_HTML = """\
    <form action="/add_backing_post" method="post">
      <div><input name="title" value='%s'></input></div>
      <div><textarea name="amount_to_back" rows="1">50</textarea></div>
      <div><input type="submit" value="Confirm Backing"></div>
    </form>
"""

ADD_SUBMISSION_FORM_HTML = """\
    <form action="/add_submission_post" method="post">
      <div><input name="title" value='%s'></input></div>
      Content: <div><textarea name="content" rows="3"></textarea></div>
      <div><input type="submit" value="Confirm Submission"></div>
    </form>
"""

FUFILL_PROJECT_FORM_HTML = """\
    <form action="/fufill_project_post" method="post">
    Title: <input name="title" value='%s'></input>
    Chosen user: <input name="chosen_user"></input>
    <input type="submit" value="Fufill Project!"></div>
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

DEFAULT_SUBMISSION_LIST_NAME = 'default_submission_list'
def submission_list_key(submission_list_name = DEFAULT_SUBMISSION_LIST_NAME):
    return ndb.Key('Submission_List', submission_list_name)

class Account(ndb.Model):
    user = ndb.UserProperty()
    balance = ndb.IntegerProperty()

class Backing(ndb.Model):
    backer = ndb.UserProperty()
    amount_backed = ndb.IntegerProperty()

class Submission(ndb.Model):
    submitter = ndb.UserProperty()
    content = ndb.TextProperty()

class Project(ndb.Model):
    author = ndb.UserProperty()
    title = ndb.StringProperty()
    description = ndb.StringProperty()
    date_created = ndb.DateTimeProperty(auto_now_add=True)
    backers = ndb.StructuredProperty(Backing, repeated=True)
    fufiller = ndb.StructuredProperty(Submission)
    submissions = ndb.StructuredProperty(Submission, repeated=True)

class AddProjectPage(webapp2.RequestHandler):
    @login_required
    def get(self):
        user = users.get_current_user()
        self.response.write(NEW_PROJECT_FORM_HTML)

class AddProjectPostedPage(webapp2.RequestHandler):

    def post(self):

        u_title = urllib.unquote(self.request.get('title'))

        project_list_name = self.request.get('project_list_name', DEFAULT_PROJECT_LIST_NAME)
        backing_list_name = self.request.get('backers_list_name', DEFAULT_BACKING_LIST_NAME)
        account_list_name = self.request.get('account_list_name', DEFAULT_ACCOUNT_LIST_NAME)

        #create initial backing
        amount = int(self.request.get('amount_backed'))
        self_backing = Backing(parent=backing_list_key(backing_list_name), backer = users.get_current_user(), amount_backed = amount)

        #remove credits
        account = Account.query(ancestor=account_list_key(account_list_name)).filter(Account.user == users.get_current_user()).fetch(1)[0]
        account.balance -= amount
        account.put()

        #Create new project
        project = Project(parent=project_list_key(project_list_name))
        project.author = users.get_current_user()
        project.title = u_title
        project.description = self.request.get('description')
        project.backers = [self_backing]
        project.fufiller = None
        project.submissions = []
        project.put()

        self.redirect('/project/' + urllib.quote(u_title))

class ProjectPage(webapp2.RequestHandler):
    def get(self, title):

        #lookup project
        project_list_name = self.request.get('project_list_name', DEFAULT_PROJECT_LIST_NAME)
        projects_query = Project.query(ancestor=project_list_key(project_list_name)).filter(Project.title == title)
        project = projects_query.fetch(10)[0]

        self.response.write('<html><body>')
        self.response.write("<h1>%s</h1>" % project.title)
        if (project.fufiller):
            self.response.write("This project has been fufilled by <b>%s</b>" % project.fufiller.submitter.nickname())
        self.response.write("<h2>Description</h2><p>%s" % project.description)

        self.response.write("<h2>Submitters</h2>")
        for s in project.submissions:
            self.response.write("<p>%s submitted <a href=data:text/plain;base64,%s> download </a>" % (s.submitter.nickname(), b64encode(s.content)))

        self.response.write("<h2>Backers</h2>")
        for b in project.backers:
            self.response.write("<p>%s backed %i" % (b.backer.nickname(), b.amount_backed))

        self.response.write("<p>")
        self.response.write("<a href=%s>Back</a> this project! or <br>" % ('/add_backing/' + urllib.quote(title)))
        self.response.write("<a href=%s>Submit</a> something for this project!" % ('/add_submission/' + urllib.quote(title)))

class AddSubmissionPage(webapp2.RequestHandler):
    @login_required
    def get(self, title):
        u_title = urllib.unquote(title)
        self.response.write(ADD_SUBMISSION_FORM_HTML % u_title)

class AddSubmissionPostedPage(webapp2.RequestHandler):
    def post(self):

        user = users.get_current_user()

        title = self.request.get('title')
        content = self.request.get('content')

        submission_list_name = self.request.get('submission_list_name', DEFAULT_SUBMISSION_LIST_NAME)
        new_submission = Submission(parent=submission_list_key(submission_list_name))
        new_submission.submitter = user
        new_submission.content = content

        #lookup project
        project_list_name = self.request.get('project_list_name', DEFAULT_PROJECT_LIST_NAME)
        projects_query = Project.query(ancestor=project_list_key(project_list_name)).filter(Project.title == title)
        project = projects_query.fetch(1)[0]
        project.submissions.append(new_submission)
        project.put()

        self.redirect('/project/' + title)


class FufillProjectPage(webapp2.RequestHandler):
    @admin_required
    def get(self, title):
        u_title = urllib.unquote(title)

        #lookup project
        project_list_name = self.request.get('project_list_name', DEFAULT_PROJECT_LIST_NAME)
        projects_query = Project.query(ancestor=project_list_key(project_list_name)).filter(Project.title == u_title)
        project = projects_query.fetch(10)[0]

        self.response.write('You want to fufill %s. Which submission shall you choose?' % title)

        for s in project.submissions:
            self.response.write("<p> <b> %s: </b> %s" % (s.submitter.nickname(), s.content))

        self.response.write(FUFILL_PROJECT_FORM_HTML % u_title)


class FufillProjectPostedPage(webapp2.RequestHandler):
    def post(self):
        title = self.request.get('title')
        chosen_user = self.request.get('chosen_user')

        #lookup project
        project_list_name = self.request.get('project_list_name', DEFAULT_PROJECT_LIST_NAME)
        projects_query = Project.query(ancestor=project_list_key(project_list_name)).filter(Project.title == title)
        project = projects_query.fetch(10)[0]

        chosen_submission = None
        for s in project.submissions:
            if s.submitter.nickname() ==  chosen_user:
                chosen_submission = s
                break

        project.fufiller = chosen_submission
        project.put()

        #credit account, etc





class AddBackingPage(webapp2.RequestHandler):
    def get(self, title):
        self.response.write('<html><body>')

        account_list_name = self.request.get('account_list_name', DEFAULT_ACCOUNT_LIST_NAME)
        account = Account.query(ancestor=account_list_key(account_list_name)).filter(Account.user == users.get_current_user()).fetch(1)[0]

        self.response.write('Are you sure you want to back %s? You have %s credits left' % (title, account.balance))
        self.response.write(ADD_BACKING_FORM_HTML % title)

class AddBackingPostedPage(webapp2.RequestHandler):
    
    def post(self):

        user = users.get_current_user()

        title = self.request.get('title')
        amount_to_back = int(self.request.get('amount_to_back'))

        project_list_name = self.request.get('project_list_name', DEFAULT_PROJECT_LIST_NAME)
        projects_query = Project.query(ancestor=project_list_key(project_list_name)).filter(Project.title == title)
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

        self.redirect('/project/' + urllib.quote(title))


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
            description = p.description
            title = cgi.escape(p.title)

            self.response.write(
                '<p> <a href=%s> <b> %s </b> </a> by %s <br> %s' % ('/project/' + urllib.quote(title), title, author_nick, description))

application = webapp2.WSGIApplication([
    ('/', MainPage),

    ('/add_project', AddProjectPage),
    ('/add_project_post', AddProjectPostedPage),
    
    ('/add_backing/(.*)', AddBackingPage),
    ('/add_backing_post', AddBackingPostedPage),
    
    ('/add_submission/(.*)', AddSubmissionPage),
    ('/add_submission_post', AddSubmissionPostedPage),

    ('/fufill_project/(.*)', FufillProjectPage),
    ('/fufill_project_post', FufillProjectPostedPage),

    
    ('/project/(.*)',ProjectPage)
], debug=True)