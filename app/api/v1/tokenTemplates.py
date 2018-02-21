# -*- coding: utf-8 -*-
from sqlalchemy.orm.exc import NoResultFound
from cerberus import Validator, ValidationError

from solc import compile_source
import json

from app import log
from app.api.common import BaseResource
from app.model import TokenTemplate
from app.errors import AppError, InvalidParameterError, DataNotExistsError

LOG = log.get_logger()

# ------------------------------
# コントラクトテンプレート登録
# ------------------------------
class SetTemplate(BaseResource):
    '''
    Handle for endpoint: /v1/TokenTemplate/
    '''
    def on_post(self, req, res):
        LOG.info('v1.tokenTemplates.SetTemplate')
        session = req.context['session']

        request_json = SetTemplate.validate(req)
        template_name = request_json['template_name']
        abi = request_json['abi']

        token_template = TokenTemplate()
        token_template.template_name = template_name
        token_template.abi = abi

        session.add(token_template)
        self.on_success(res)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'template_name': {'type': 'string', 'empty': False, 'required': True},
            'abi': {'type': 'string', 'empty': False, 'required': True}
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return request_json

# ------------------------------
# コントラクトテンプレート一覧参照
# ------------------------------
class GetAll(BaseResource):
    '''
    Handle for endpoint: /v1/TokenTemplates
    '''
    def on_get(self, req, res):
        LOG.info('v1.tokenTemplates.GetAll')
        session = req.context['session']

        try:
            templates = session.query(TokenTemplate).all()
            res_list = []
            for item in templates:
                res_list.append(
                    {
                        "id":item.id,
                        "template_name":item.template_name
                    }
                )
            self.on_success(res, res_list)
        except NoResultFound:
            raise DataNotExistsError()

# ------------------------------
# コントラクトテンプレート詳細参照
# ------------------------------
class GetContractABI(BaseResource):
    '''
    Handle for endpoint: /v1/TokenTemplates/{contract_id}
    '''
    def on_get(self, req, res, contract_id):
        LOG.info('v1.tokenTemplates.GetABI')
        session = req.context['session']

        try:
            abi_db = TokenTemplate.find_one(session, contract_id)
            self.on_success(res, abi_db.to_dict())
        except NoResultFound:
            raise DataNotExistsError('contract id: %s' % contract_id)
