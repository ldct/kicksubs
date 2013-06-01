import cgi
from google.appengine.api import users
from google.appengine.ext import ndb
import webapp2

MAIN_PAGE_HTML = """\
    <form action="/new_project" method="post">
      <div><textarea name="content" rows="3" cols="60"></textarea></div>
      <div><input type="submit" value="Sign Guestbook"></div>
    </form>
"""

DEFAULT_PROJECT_LIST_NAME = 'default_project_list'

def project_list_key(project_list_name = DEFAULT_PROJECT_LIST_NAME):
    return ndb.Key('Project_List', project_list_name)

class Project(ndb.Model):
    author = ndb.UserProperty()
    description = ndb.StringProperty()
    date_created = ndb.DateTimeProperty(auto_now_add=True)

class NewProjectPostedPage(webapp2.RequestHandler):
    def post(self):
        self.response.write('<html><body>You wrote:')
        self.response.write(cgi.escape(self.request.get('content')))
        
        project_list_name = self.request.get('project_list_name', DEFAULT_PROJECT_LIST_NAME)
        project = Project(parent=project_list_key(project_list_name))

        if users.get_current_user():
            project.author = users.get_current_user()
        else:
            self.response.write("no user!")
        project.description = self.request.get('content')
        project.put()

        self.response.write('</body></html>')

class MainPage(webapp2.RequestHandler):

    def get(self):

        self.response.write('<html><body>')
        project_list_name = self.request.get('project_list_name', DEFAULT_PROJECT_LIST_NAME)

        projects_query = Project.query(ancestor=project_list_key(project_list_name)).order(-Project.date_created)
        projects = projects_query.fetch(10)

        self.response.write('<p> Latest %i Projects:' % len(projects))

        for p in projects:
            self.response.write('<p> author: %s description: %s' % (p.author.nickname(), cgi.escape(p.description)))

    	user = users.get_current_user()

        if user:
            self.response.write('<p> Hello, ' + user.nickname())

            self.response.write(MAIN_PAGE_HTML)
        else:
            self.redirect(users.create_login_url(self.request.uri))

application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/new_project', NewProjectPostedPage),
], debug=True)