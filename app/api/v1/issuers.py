# -*- coding: utf-8 -*-

import re
import falcon

from sqlalchemy.orm.exc import NoResultFound
from cerberus import Validator, ValidationError

from app import log
from app.api.common import BaseResource
from app.model import Issuer
from app.errors import AppError, InvalidParameterError, UserNotExistsError, PasswordNotMatch

LOG = log.get_logger()


FIELDS = {
    'eth_address': {
        'type': 'string',
        'required': True,
        'minlength': 42,
        'maxlength': 42
    },
    'user_name': {
        'type': 'string',
        'required': True,
        'minlength': 4,
        'maxlength': 20
    }
}

def validate_user_create(req, res, resource, params):
    schema = {
        'eth_address': FIELDS['eth_address'],
        'user_name': FIELDS['user_name']
    }

    v = Validator(schema)
    try:
        if not v.validate(req.context['data']):
            raise InvalidParameterError(v.errors)
    except ValidationError:
        raise InvalidParameterError('Invalid Request %s' % req.context)


class Collection(BaseResource):
    """
    Handle for endpoint: /v1/issuers
    """
    @falcon.before(validate_user_create)
    def on_post(self, req, res):
        session = req.context['session']
        user_req = req.context['data']
        if user_req:
            user = Issuer()
            user.eth_address = user_req['eth_address']
            user.user_name = user_req['user_name']
            user.token = "1234567" # To-Do
            session.add(user)
            self.on_success(res)
        else:
            raise InvalidParameterError(req.context['data'])


class Item(BaseResource):
    """
    Handle for endpoint: /v1/issuers/{user_id}
    """
    def on_get(self, req, res, user_id):
        session = req.context['session']
        try:
            user_db = User.find_one(session, user_id)
            self.on_success(res, user_db.to_dict())
        except NoResultFound:
            raise UserNotExistsError('user id: %s' % user_id)
