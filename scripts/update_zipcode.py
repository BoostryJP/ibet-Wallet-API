"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed onan "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

import sys
import os
import csv
import zipfile
import json
import shutil
import ssl
import datetime
import logging
log_fmt = '[Update Zipcode] [%(asctime)s] [%(process)d] [%(levelname)s] %(message)s'
logging.basicConfig(level="DEBUG", format=log_fmt)

"""
株式会社アイビス社提供の加工済み郵便番号データを利用
http://zipcloud.ibsnet.co.jp/
"""

# 設定
ssl._create_default_https_context = ssl._create_unverified_context
base_dir = os.getcwd()
input_dir = os.path.join(base_dir, 'scripts', 'input_file')
out_file = os.path.join(base_dir, 'data', 'zip_code.zip')


# 共通部品: JSONファイル出力
def write_json(data, path_with_file):
    fw = open(path_with_file, 'w')
    json.dump(data, fw, indent=2, ensure_ascii=False)


# バージョンチェック
def check_version(file_size):
    logging.info('[START] check_version')
    with open(os.path.join(base_dir, 'data', 'zip_code_version')) as f:
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


# 入力ファイルを作業ディレクトリにコピー
def move_to_temp_dir(in_path, tmp_path):
    logging.info('[START] move_to_temp_dir')
    try:
        shutil.copyfile(in_path, tmp_path)
        logging.info('作業ディレクトリへのコピーに成功しました。')
    except Exception as e:
        logging.error(e, '作業ディレクトリへのコピーに失敗しました。')
        raise
    logging.info('[END] move_to_temp_dir')


# 入力ファイル（Zip）の解凍
def unzip(path, file_name):
    logging.info('[START] unzip')
    try:
        with zipfile.ZipFile(os.path.join(path, file_name)) as zip_file:
            zip_file.extract('x-ken-all.csv', path)
        logging.info('Zipファイルの解凍に成功しました。')
    except Exception as e:
        logging.error(e, 'Zipファイルの解凍に失敗しました。')
        raise
    logging.info('[END] unzip')


# JSONファイル作成
def create_json(base_path):
    logging.info('[START] create_json')
    try:
        with open(os.path.join(base_path, 'x-ken-all.csv'), encoding='shift_jis') as f:
            reader = csv.reader(f)
            codeList = []
            for row in reader:
                codeList.append(row)
            codeList.sort(key=lambda x: x[2])
        zipArray = []
        preZipJson = {
            'jis_code': codeList[0][0],
            'zip_code': codeList[0][2],
            'prefecture_name_kana': codeList[0][3],
            'city_name_kana': codeList[0][4],
            'town_name_kana': codeList[0][5],
            'prefecture_name': codeList[0][6],
            'city_name': codeList[0][7],
            'town_name': codeList[0][8]
        }
        for item in codeList:
            jsonData = {
                'jis_code': item[0],
                'zip_code': item[2],
                'prefecture_name_kana': item[3],
                'city_name_kana': item[4],
                'town_name_kana': item[5],
                'prefecture_name': item[6],
                'city_name': item[7],
                'town_name': item[8]
            }
            if preZipJson['zip_code'] == jsonData['zip_code']:
                zipArray.append(jsonData)
            else:
                # 郵便番号の上3桁ごとにディレクトリを作成する
                if not os.path.exists(os.path.join(base_path, 'zip_code', preZipJson['zip_code'][0:3])):
                    os.makedirs(os.path.join(base_path, 'zip_code', preZipJson['zip_code'][0:3]))
                # JSONファイルを作成
                write_json(
                    zipArray,
                    os.path.join(base_path, 'zip_code', preZipJson['zip_code'][0:3], preZipJson['zip_code'] + '.json')
                )
                preZipJson = jsonData
                zipArray = [jsonData]
        if zipArray:
            write_json(
                zipArray,
                os.path.join(base_path, 'zip_code', preZipJson['zip_code'][0:3], preZipJson['zip_code'] + '.json')
            )
        logging.info('JSONファイルの作成に成功しました。')
    except Exception as e:
        logging.error(e, 'JSONファイルの作成に失敗しました。')
        raise

    logging.info('[END] create_json')


# バージョンファイルの更新
def update_version(base_path, version):
    with open(os.path.join(base_path, 'data', 'zip_code_version'), 'w') as f:
        writer = csv.writer(f)
        dt = datetime.date.today().strftime('%Y%m%d')
        writer.writerow([dt, version])


# メイン処理
if __name__ == "__main__":
    args = sys.argv

    # 入力ファイル
    # NOTE:事前にサイトからダウンロードして、input_fileディレクトリに格納しておく
    in_file_name = args[1]
    in_file = os.path.join(input_dir, in_file_name)

    # 作業ディレクトリの作成
    tmp_dir = os.path.join(base_dir, "scripts", 'tmp')
    os.makedirs(tmp_dir, exist_ok=True)

    try:
        # ファイルサイズを取得
        file_size = os.path.getsize(in_file)
        if check_version(file_size):  # バージョンに差分が存在する場合は後続処理をおこなう
            # 入力ファイルを作業ディレクトリにコピー
            move_to_temp_dir(in_file, os.path.join(tmp_dir, in_file_name))
            # Zipファイルの解凍
            unzip(tmp_dir, in_file_name)
            # JSONファイルを作成
            create_json(tmp_dir)
            # アーカイブファイルを作成
            shutil.make_archive(os.path.join(tmp_dir, "zip_code"), 'zip', root_dir=tmp_dir, base_dir="zip_code")
            # 出力ファイルを移動
            shutil.move(os.path.join(tmp_dir, "zip_code.zip"), out_file)
            update_version(base_dir, file_size)
        else:
            logging.info('マスタデータに変更はありませんでした。')
    except Exception as err:
        logging.error(err, "処理中にエラーが発生しました。")
    finally:
        shutil.rmtree(tmp_dir)
        logging.info('正常終了しました。')
