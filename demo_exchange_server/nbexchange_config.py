from nbexchange.handlers.auth.user_handler import BaseUserHandler


class MyUserHandler(BaseUserHandler):
    def get_current_user(self, request):
        return {
            "name": "myname",
            "course_id": "cool_course_id",
            "course_title": "cool course",
            "course_role": "Instructor",
            "org_id": 1,
        }


c.NbExchange.user_plugin_class = MyUserHandler

c.NbExchange.base_url = "/services/exchange"
c.NbExchange.base_storage_location = "/tmp/exchange/"
c.NbExchange.db_url = "sqlite://tmp/nbexchange.sqlite"
# c.NbExchange.db_url = mysql://username:password@my.msql.server.host:3306/db_name
