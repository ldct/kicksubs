import os, cgi, urllib, jinja2
from base64 import b64encode

from google.appengine.api import users
from google.appengine.ext import ndb

import webapp2
from webapp2_extras.appengine.users import login_required, admin_required

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'])


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

        template_values = base_template_value(self)
        template = JINJA_ENVIRONMENT.get_template('add_project.html')
        self.response.write(template.render(template_values))

class AddProjectPostedPage(webapp2.RequestHandler):

    def post(self):

        u_title = urllib.unquote(self.request.get('title'))

        project_list_name = self.request.get('project_list_name', DEFAULT_PROJECT_LIST_NAME)
        backing_list_name = self.request.get('backers_list_name', DEFAULT_BACKING_LIST_NAME)
        account_list_name = self.request.get('account_list_name', DEFAULT_ACCOUNT_LIST_NAME)

        #create initial backing
        amount = int(self.request.get('amount_backed'))
        self_backing = Backing(parent=backing_list_key(backing_list_name))
        self_backing.backer = users.get_current_user()
        self_backing.amount_backed = amount
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

        template_values = base_template_value(self)

        #lookup project
        project_list_name = self.request.get('project_list_name', DEFAULT_PROJECT_LIST_NAME)
        projects_query = Project.query(ancestor=project_list_key(project_list_name)).filter(Project.title == title)
        project = projects_query.fetch(10)[0]

        if (project.fufiller):
            template_values['fufiller'] = project.fufiller.submitter.nickname()

        template_values['title'] = project.title
        template_values['quoted_title'] = urllib.quote(project.title)
        template_values['description'] = project.description
        template_values['submissions'] = []
        template_values['backers'] = []

        for s in project.submissions:
            template_values['submissions'].append({'submitter': s.submitter.nickname(),
                                                   'content': b64encode(s.content)})

        for b in project.backers:
            template_values['backers'].append({'name': b.backer.nickname(),
                                               'amount': b.amount_backed})

        template_values['total_amount_backed'] = sum(b.amount_backed for b in project.backers)

        template = JINJA_ENVIRONMENT.get_template('view_project.html')
        self.response.write(template.render(template_values))


class AddSubmissionPage(webapp2.RequestHandler):
    @login_required
    def get(self, title):

        template_values = base_template_value(self)
        template_values["title"] = title

        template = JINJA_ENVIRONMENT.get_template('add_submission.html')
        self.response.write(template.render(template_values))


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
            self.response.write("<p>%s <a href=data:text/plain;base64,%s> download </a>" % (s.submitter.nickname(), b64encode(s.content)))

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

        account_list_name = self.request.get('account_list_name', DEFAULT_ACCOUNT_LIST_NAME)
        account = Account.query(ancestor=account_list_key(account_list_name)).filter(Account.user == chosen_submission.submitter).fetch(1)[0]
        account.balance += sum(b.amount_backed for b in project.backers)
        account.put()

class AddBackingPage(webapp2.RequestHandler):
    def get(self, title):

        template_values = base_template_value(self)

        account_list_name = self.request.get('account_list_name', DEFAULT_ACCOUNT_LIST_NAME)
        account = Account.query(ancestor=account_list_key(account_list_name)).filter(Account.user == users.get_current_user()).fetch(1)[0]

        template_values["title"] = title

        template = JINJA_ENVIRONMENT.get_template('add_backing.html')
        self.response.write(template.render(template_values))


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


def base_template_value(self):
    template_value = {}
    user = users.get_current_user()
    if user:
        account_list_name = self.request.get('account_list_name', DEFAULT_ACCOUNT_LIST_NAME)
        account = Account.query(ancestor=account_list_key(account_list_name)).filter(Account.user == user).fetch(1)[0]

        template_value["user"] = {'name': user.nickname(),
                                   'balance': account.balance,
                                   'url': users.create_logout_url('/')}
    else:
        template_value["login_url"] = users.create_login_url('/')
    return template_value


class MainPage(webapp2.RequestHandler):

    def get(self):

        user = users.get_current_user()

        if user:
            account_list_name = self.request.get('account_list_name', DEFAULT_ACCOUNT_LIST_NAME)
            accounts = Account.query(ancestor=account_list_key(account_list_name)).filter(Account.user == user).fetch(1)

            if len(accounts) == 0:
                new_account = Account(parent=account_list_key(account_list_name))
                new_account.user = user
                new_account.balance = 100
                new_account.put()

            accounts = Account.query(ancestor=account_list_key(account_list_name)).filter(Account.user == user).fetch(1)
            account = accounts[0]

        template_values = base_template_value(self)

        project_list_name = self.request.get('project_list_name', DEFAULT_PROJECT_LIST_NAME)

        projects_query = Project.query(ancestor=project_list_key(project_list_name)).order(-Project.date_created)
        projects = projects_query.fetch(10)

        template_values["projects"] = []

        for p in projects:
            template_values["projects"].append({'author': p.author.nickname(),
                                                'title': p.title,
                                                'url': '/project/' + urllib.quote(p.title),
                                                'description': p.description,
                                                'total_amount_backed': sum(b.amount_backed for b in p.backers),
                                                'num_backers': len(p.backers)})

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))

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