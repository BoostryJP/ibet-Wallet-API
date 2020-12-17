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

import urllib.request
import os
import csv
import zipfile
import json
import shutil
import ssl
import datetime
import logging
log_fmt = '[Update Jigyosyo] [%(asctime)s] [%(process)d] [%(levelname)s] %(message)s'
logging.basicConfig(level="DEBUG", format=log_fmt)


"""
日本郵政HPから最新の事業所個別郵便番号データを取得する
https://www.post.japanpost.jp/zipcode/dl/jigyosyo/index-zip.html
"""

# 設定
ssl._create_default_https_context = ssl._create_unverified_context
download_url = "https://www.post.japanpost.jp/zipcode/dl/jigyosyo/zip/jigyosyo.zip"
in_file = "jigyosyo.zip"
base_dir = os.getcwd()
out_file = os.path.join(base_dir, 'data', 'zip_code_jigyosyo.zip')


# 入力ファイルダウンロード
def download_file(work_dir):
    logging.info('[START] file_download')
    try:
        urllib.request.urlretrieve(download_url, os.path.join(work_dir, in_file))
    except Exception as e:
        logging.error(e, 'マスタデータの取得に失敗しました郵政HPを確認してください。')
        raise
    logging.info('[END] file_download')
    return os.path.getsize(os.path.join(work_dir, in_file))


# バージョンチェック
def check_version(file_size):
    logging.info('[START] check_version')
    with open(os.path.join(base_dir, 'data', 'zip_code_jigyosyo_version')) as f:
        reader = csv.reader(f)
        for row in reader:
            if int(row[1]) == file_size:  # バージョン一致
                logging.info('現在のファイルは最新バージョンです。')
                check_result = False
            else:  # バージョン不一致
                logging.info('現在のファイルは古いバージョンです。')
                check_result = True
    logging.info('[END] check_version')
    return check_result


# JSONファイル作成
def create_json(work_dir):
    logging.info('[START] create_json')
    try:
        with zipfile.ZipFile(os.path.join(work_dir, in_file)) as zip_file:
            zip_file.extract('JIGYOSYO.CSV', work_dir)
        logging.info('マスタデータを解凍しました。')
    except Exception as e:
        logging.error(e, 'マスタデータの解凍に失敗しました。')
        raise

    # 個別JSONファイル出力
    try:
        with open(os.path.join(work_dir, 'JIGYOSYO.CSV'), encoding='cp932') as f:
            reader = csv.reader(f)
            code_list = []
            for row in reader:
                code_list.append(row)
            code_list.sort(key=lambda x: x[2])

        for item in code_list:
            json_data = [{
                'jis_code': item[0],  # 大口事業所の所在地のJISコード
                'zip_code': item[7],  # 大口事業所個別番号
                'corporate_name_kana': item[1],  # 大口事業所名（かな）
                'corporate_name': item[2],  # 大口事業所名（漢字）
                'prefecture_name_kana': '',  # 都道府県名（かな）
                'city_name_kana': '',  # 市区町村名（かな）
                'town_name_kana': '',  # 町域名（かな）
                'prefecture_name': item[3],  # 都道府県名（漢字）
                'city_name': item[4],  # 市区町村名（漢字）
                'town_name': item[5]  # 町域名（漢字）
            }]
            # 郵便番号の上3桁ごとにディレクトリを作成する
            zip_code_head = item[7][0:3]
            if not os.path.exists(os.path.join(work_dir, 'zip_code_jigyosyo', zip_code_head)):
                os.makedirs(os.path.join(work_dir, 'zip_code_jigyosyo', zip_code_head))
            # JSONファイルを作成
            fw = open(os.path.join(work_dir, 'zip_code_jigyosyo', zip_code_head, item[7] + '.json'), 'w')
            json.dump(json_data, fw, indent=2, ensure_ascii=False)
        logging.info('JSONファイルの作成に成功しました。')
    except Exception as e:
        logging.error(e, 'JSONファイルの作成に失敗しました。')
        raise
    logging.info('[END] create_json')


# バージョンファイルの更新
def update_version(base_path, version):
    with open(os.path.join(base_path, 'data', 'zip_code_jigyosyo_version'), 'w') as f:
        writer = csv.writer(f)
        dt = datetime.date.today().strftime('%Y%m%d')
        writer.writerow([dt, version])


# メイン処理
if __name__ == "__main__":
    # 作業ディレクトリ作成
    tmp_dir = os.path.join(base_dir, "scripts", 'tmp')
    os.makedirs(tmp_dir, exist_ok=True)

    try:
        # ファイルダウンロード
        file_size = download_file(tmp_dir)
        if check_version(file_size):  # バージョンに差分がない場合は処理をスキップ
            # JSONファイル作成
            create_json(tmp_dir)
            # アーカイブファイル作成
            shutil.make_archive(
                os.path.join(tmp_dir, "zip_code_jigyosyo"),
                'zip',
                root_dir=tmp_dir,
                base_dir="zip_code_jigyosyo"
            )
            # 出力ファイルを移動
            shutil.move(os.path.join(tmp_dir, "zip_code_jigyosyo.zip"), out_file)
            update_version(base_dir, file_size)
        else:
            logging.info('マスタデータに変更はありませんでした。')
    except Exception as err:
        logging.error(err, "処理中にエラーが発生しました。")
    finally:
        # 作業ディレクトリの削除
        shutil.rmtree(tmp_dir)
        logging.info('正常終了しました。')
