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
import json

from app.errors import InvalidParameterError


class JSONTranslator(object):
    def process_request(self, req, res):
        if self.__get_content_type(req) == 'application/json':
            try:
                raw_json = req.bounded_stream.read()
            except Exception:
                raise InvalidParameterError('Content-Length is not set correctly')
            try:
                req.context['raw_data'] = raw_json.decode('utf-8')
                req.context['data'] = json.loads(raw_json.decode('utf-8'))
            except ValueError:
                raise InvalidParameterError('No JSON object could be decoded or Malformed JSON')
            except UnicodeDecodeError:
                raise InvalidParameterError('Cannot be decoded by utf-8')
        else:
            req.context['data'] = None

    def __get_content_type(self, req):
        """
        Content-Typeヘッダからtype/subtype部分を抜き出します。
        例) 
          "application/json; charset=utf-8" => "application/json"
          "application/json" => "application/json"
          None => None
        """
        
        content_type = req.content_type
        if content_type is None:
            return None
        else:
            return content_type.split(";")[0]
