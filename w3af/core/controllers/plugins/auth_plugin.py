"""
auth_plugin.py

Copyright 2011 Andres Riancho

This file is part of w3af, http://w3af.org/ .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""
import w3af.core.controllers.output_manager as om
import w3af.core.data.kb.knowledge_base as kb

from w3af.core.controllers.plugins.plugin import Plugin
from w3af.core.data.kb.info import Info
from w3af.core.data.fuzzer.utils import rand_alnum
from w3af.core.data.url.helpers import is_no_content_response


class AuthPlugin(Plugin):
    """
    This is the base class for auth plugins, all auth plugins should inherit
    from it and implement the following methods:
        1. login(...)
        2. logout(...)
        2. has_active_session(...)

    :author: Dmitriy V. Simonov ( dsimonov@yandex-team.com )
    """

    MAX_FAILED_LOGIN_COUNT = 3

    def __init__(self):
        Plugin.__init__(self)

        self._uri_opener = None
        self._debugging_id = None
        self._http_response_ids = []
        self._log_messages = []
        self._attempt_login = True
        self._failed_login_count = 0

    def login(self):
        """
        Login user into web application.

        It is called in the begging of w3afCore::_discover_and_bruteforce() method
        if current user session is not valid.

        """
        raise NotImplementedError('Plugin is not implementing required method login')

    def logout(self):
        """
        Logout user from web application.

        TODO: need to add calling of this method to w3afCore::_end()

        """
        raise NotImplementedError('Plugin is not implementing required method logout')

    def has_active_session(self):
        """
        Check if current session is still valid.

        It is called in the begging of w3afCore::_discover_and_bruteforce() method.
        """
        raise NotImplementedError('Plugin is not implementing required method isLogged')

    def _log_http_response(self, http_response):
        if is_no_content_response(http_response):
            return False

        self._http_response_ids.append(http_response.id)
        return True

    def _clear_log(self):
        self._http_response_ids = []
        self._log_messages = []

    def _log_debug(self, message):
        self._log_messages.append(message)

        formatted_message = self._format_message(message)
        om.out.debug(formatted_message)

    def _log_error(self, message):
        self._log_messages.append(message)

        # Send the message to the output without adding any formatting
        om.out.error(message)

        # This is here just for me to be able to quickly find all the activity
        # of a specific auth plugin by grepping by its name
        self._log_debug(message)

    def _format_message(self, message):
        message_fmt = '[auth.%s] %s (did: %s)'
        return message_fmt % (self.get_name(), message, self._debugging_id)

    def _new_debugging_id(self):
        self._debugging_id = rand_alnum(8)

    def _get_main_authentication_url(self):
        """
        :return: The main authentication URL, this can be the URL where the
                 credentials are sent to, the location where the login form
                 should be found, or any other URL which identifies the
                 authentication.
        """
        raise NotImplementedError

    def _handle_authentication_failure(self):
        self._failed_login_count += 1

        if self._failed_login_count == self.MAX_FAILED_LOGIN_COUNT:
            msg = ('The authentication plugin failed %s consecutive times to'
                   ' get a valid application session using the user-provided'
                   ' configuration settings. Disabling the `%s` authentication'
                   ' plugin.')
            args = (self._failed_login_count, self.get_name())
            self._log_error(msg % args)

            self._log_info_to_kb()

            self._attempt_login = False

    def end(self):
        if self._failed_login_count:
            msg = ('The `%s` authentication plugin failed %i times to get'
                   ' a valid application session using the user-provided'
                   ' configuration settings')
            args = (self.get_name(), self._failed_login_count,)

            self._log_error(msg % args)

            self._log_info_to_kb()

    def _handle_authentication_success(self):
        self._failed_login_count = 0

    def _log_info_to_kb(self):
        """
        This method creates an Info object containing information about failed
        authentication attempts and stores it in the knowledge base.

        The information stored in the Info object is:

            * The log messages from self._log_messages
            * HTTP response IDs from self._htp_response_ids

        :return: None
        """
        desc = ('The authentication plugin failed to get a valid application'
                ' session using the user-provided configuration settings.\n'
                '\n'
                'The plugin generated the following log messages:\n'
                '\n')
        desc += '\n'.join(self._log_messages)

        i = Info('Authentication failure',
                 desc,
                 self._http_response_ids,
                 self.get_name())

        i.set_uri(self._get_main_authentication_url())

        kb.kb.append('authentication', 'error', i)

    def get_type(self):
        return 'auth'
