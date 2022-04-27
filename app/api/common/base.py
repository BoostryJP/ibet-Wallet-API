"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

import falcon
import json
from falcon import Request, Response

try:
    from collections import OrderedDict
except ImportError:
    OrderedDict = dict

from app import log
from app.utils.alchemy import new_alchemy_encoder
from app.config import BRAND_NAME
from app.errors import NotSupportedError

LOG = log.get_logger()


class BaseResource(object):
    HELLO_WORLD = {
        'server': '%s' % BRAND_NAME
    }

    def to_json(self, body_dict):
        return json.dumps(body_dict)

    def from_db_to_json(self, db):
        return json.dumps(db, cls=new_alchemy_encoder())

    def on_error(self, res, error=None):
        res.status = error['status']
        meta = OrderedDict()
        meta['code'] = error['code']
        meta['message'] = error['message']

        obj = OrderedDict()
        obj['meta'] = meta
        res.text = self.to_json(obj)

    def on_success(self, res, data=None):
        res.status = falcon.HTTP_200
        meta = OrderedDict()
        meta['code'] = 200
        meta['message'] = 'OK'

        obj = OrderedDict()
        obj['meta'] = meta
        obj['data'] = data
        res.text = self.to_json(obj)

    def on_get(self, req: Request, res: Response, *args, **kwargs):
        if req.path == '/':
            res.status = falcon.HTTP_200
            res.text = self.to_json(self.HELLO_WORLD)
        else:
            raise NotSupportedError(method='GET', url=req.path)

    def on_post(self, req: Request, res: Response, *args, **kwargs):
        raise NotSupportedError(method='POST', url=req.path)

    def on_put(self, req: Request, res: Response, *args, **kwargs):
        raise NotSupportedError(method='PUT', url=req.path)

    def on_delete(self, req: Request, res: Response, *args, **kwargs):
        raise NotSupportedError(method='DELETE', url=req.path)

