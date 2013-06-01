import cgi
from google.appengine.api import users
from google.appengine.ext import ndb
import webapp2
import urllib

MAIN_PAGE_HTML = """\
    <form action="/new_project" method="post">
      <div><textarea name="title" rows="1"></textarea></div>
      <div><textarea name="description" rows="3" cols="60"></textarea></div>
      <div><textarea name="amount_in_cents" rows="1"></textarea></div>
      <div><input type="submit" value="Submit Project"></div>
    </form>
"""

DEFAULT_PROJECT_LIST_NAME = 'default_project_list'
def project_list_key(project_list_name = DEFAULT_PROJECT_LIST_NAME):
    return ndb.Key('Project_List', project_list_name)

DEFAULT_BACKING_LIST_NAME = 'default_backing_list'
def backing_list_key(backing_list_name = DEFAULT_BACKING_LIST_NAME):
    return ndb.Key('Backing_List', backing_list_name)

class Backing(ndb.Model):
    backer = ndb.UserProperty()
    amount_in_cents = ndb.IntegerProperty()

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
        project = Project(parent=project_list_key(project_list_name))

        if not(users.get_current_user()):
            self.response.write("Error: Not signed in!")
            return

        project.author = users.get_current_user()
        project.title = self.request.get('title')
        project.description = self.request.get('description')

        amount = int(self.request.get('amount_in_cents'))
        self_backing = Backing(parent=backing_list_key(backing_list_name), backer = users.get_current_user(), amount_in_cents = amount)
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


class MainPage(webapp2.RequestHandler):

    def get(self):

        self.response.write('<html><body>')
        project_list_name = self.request.get('project_list_name', DEFAULT_PROJECT_LIST_NAME)

        projects_query = Project.query(ancestor=project_list_key(project_list_name)).order(-Project.date_created)
        projects = projects_query.fetch(10)

        self.response.write('<p> Latest %i Projects:' % len(projects))

        for p in projects:
            self.response.write(
                '<p> <b> author: </b> %s <b> description: </b> %s <b> title: %s</b>' % (p.author.nickname(), cgi.escape(p.description), cgi.escape(p.title)))

    	user = users.get_current_user()

        if user:
            self.response.write('<p> Hello, ' + user.nickname())

            self.response.write(MAIN_PAGE_HTML)
        else:
            self.redirect(users.create_login_url(self.request.uri))

application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/new_project', NewProjectPostedPage),
    ('/project/(.*)',ProjectPage)
], debug=True)