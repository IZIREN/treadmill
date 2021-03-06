"""
Treadmill App monitor REST api.
"""


import flask
import flask_restplus as restplus
from flask_restplus import fields

# Disable E0611: No 'name' in module
from treadmill import webutils  # pylint: disable=E0611


# Old style classes, no init method.
#
# pylint: disable=W0232
def init(api, cors, impl):
    """Configures REST handlers for app monitor resource."""

    namespace = webutils.namespace(
        api, __name__, 'Application monitor REST operations'
    )

    model = {
        '_id': fields.String(description='Name'),
        'count': fields.Integer(description='Count', required=True),
    }

    app_monitor_model = api.model(
        'AppMonitor', model
    )

    match_parser = api.parser()
    match_parser.add_argument('match', help='A glob match on an app monitor',
                              location='args', required=False,)

    @namespace.route(
        '/',
    )
    class _AppMonitorList(restplus.Resource):
        """Treadmill App monitor resource"""

        @webutils.get_api(api, cors,
                          marshal=api.marshal_list_with,
                          resp_model=app_monitor_model,
                          parser=match_parser)
        def get(self):
            """Returns list of configured app monitors."""
            args = match_parser.parse_args()
            return impl.list(args.get('match'))

    @namespace.route('/<app_monitor>')
    @api.doc(params={'app_monitor': 'Application Monitor ID/name'})
    class _AppMonitorResource(restplus.Resource):
        """Treadmill App monitor resource."""

        @webutils.get_api(api, cors,
                          marshal=api.marshal_with,
                          resp_model=app_monitor_model)
        def get(self, app_monitor):
            """Return Treadmill application monitor configuration."""
            return impl.get(app_monitor)

        @webutils.post_api(api, cors,
                           req_model=app_monitor_model,
                           resp_model=app_monitor_model)
        def post(self, app_monitor):
            """Creates Treadmill application."""
            return impl.create(app_monitor, flask.request.json)

        @webutils.put_api(api, cors,
                          req_model=app_monitor_model,
                          resp_model=app_monitor_model)
        def put(self, app_monitor):
            """Updates Treadmill application configuration."""
            return impl.update(app_monitor, flask.request.json)

        @webutils.delete_api(api, cors)
        def delete(self, app_monitor):
            """Deletes Treadmill application monitor."""
            return impl.delete(app_monitor)
