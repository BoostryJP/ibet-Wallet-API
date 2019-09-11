# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from locust import HttpLocust, TaskSet, task

import json
from app import config

# テスト用のアカウント
eth_address = "0x3509Ef81bAb3cf3B8d031119098871B56F08E80b"

# Basic認証
basic_auth_user = config.BASIC_AUTH_USER
basic_auth_pass = config.BASIC_AUTH_PASS


class LoadTestTaskSet(TaskSet):
    def on_start(self):
        self.client.get(
            "/",
            auth=(basic_auth_user, basic_auth_pass),
            verify=False
        )

    @task
    def v1_jdr_mytokens(self):
        headers = {'content-type': 'application/json'}
        response = self.client.post(
            "/v1/JDR/MyTokens/",
            json.dumps({'account_address_list': [eth_address]}),
            headers=headers,
            auth=(basic_auth_user, basic_auth_pass),
            verify=False
        )
        print(response.content)

    @task
    def v1_mrf_mytokens(self):
        headers = {'content-type': 'application/json'}
        response = self.client.post(
            "/v1/MRF/MyTokens/",
            json.dumps({'account_address_list': [eth_address]}),
            headers=headers,
            auth=(basic_auth_user, basic_auth_pass),
            verify=False
        )
        print(response.content)

    @task
    def v1_requiredverion(self):
        response = self.client.get(
            "/v1/RequiredVersion/?platform=ios",
            auth=(basic_auth_user, basic_auth_pass),
            verify=False
        )
        print(response.content)

    @task
    def v1_orderlist(self):
        headers = {'content-type': 'application/json'}
        response = self.client.post(
            "v1/OrderList",
            json.dumps({'account_address_list': [eth_address]}),
            headers=headers,
			auth=(basic_auth_user, basic_auth_pass),
			verify=False
        )
        print(response.content)

    @task
    def v1_jdr_lastprice(self):
        headers = {'content-type': 'application/json'}
        response = self.client.post(
            "/v1/JDR/LastPrice",
            json.dumps({'address_list': ["0xA4e577C0fb832a9643237E89e890B3e43F501b9e"]}), # テスト用DRトークン
            headers=headers,
			auth=(basic_auth_user, basic_auth_pass),
			verify=False
        )
        print(response.content)

    @task
    def v1_nodeinfo(self):
        response = self.client.get(
            "/v1/NodeInfo",
            auth=(basic_auth_user, basic_auth_pass),
            verify=False
        )
        print(response.content)

    @task
    def v1_jdr_contracts(self):
        response = self.client.get(
            "/v1/JDR/Contracts?limit=2",
            auth=(basic_auth_user, basic_auth_pass),
            verify=False
        )
        print(response.content)


class Website(HttpLocust):
    task_set = LoadTestTaskSet

    # task実行の最短待ち時間
    min_wait = 1000

    # task実行の最大待ち時間
    max_wait = 1000
