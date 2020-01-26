# 日本郵政HPから最新の郵便番号-住所のデータを取得する
import urllib.request
import sys
import os
import re
import csv
import zipfile
import json
import filecmp
import subprocess
import shutil
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
import time
import datetime

# 設定
class Config():
    yuseiUrl = "https://www.post.japanpost.jp/zipcode/dl/kogaki/zip/ken_all.zip"
    basePath = os.getcwd()
    targetZip = os.path.join(basePath, 'data', 'zip_code.zip')

def getRawFile(yuseiUrl, basePath):
    try:
        fileName = yuseiUrl.split("/")[len(yuseiUrl.split("/"))-1]
        urllib.request.urlretrieve(yuseiUrl, os.path.join(basePath, fileName))
        # 待たないとzipファイル取得しきれない
        # fuzzy
        time.sleep(5)
        return fileName, os.path.getsize(os.path.join(basePath, fileName))
    except:
        print('マスタデータの取得に失敗しました郵政HPを確認してください')
        raise

def checkVersion(basePath, fileSize):
    with open(os.path.join(basePath, 'data', 'zip_code_version')) as f:
        reader = csv.reader(f)
        for row in reader:
            if int(row[1]) == fileSize:
                return False
            else:
                return True

def createJson(basePath, fileName):
    try:
        with zipfile.ZipFile(os.path.join(basePath, fileName)) as zf:
            zf.extract('KEN_ALL.CSV', basePath)
        print('マスタデータを解凍しました')
    except:
        print('マスタデータの解凍に失敗しました')
        raise
    try:
        with open(os.path.join(basePath, 'KEN_ALL.CSV'), encoding='shift_jis') as f:
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
                # 特殊な町域
                # お探しの町域が見つからない場合、市区町村名の後ろに町域名がなく番地がくる住所、町域名がない市区町村
                if '以下に掲載がない場合' in item[8] or 'の次に番地がくる場合' in item[8] or '一円' in item[8]:
                    townName = ''
                    townNameKana = ''
                else:
                    townName = item[8]
                    townNameKana = item[5]

                jsonData = {
                    'jis_code': item[0],
                    'zip_code': item[2],
                    'prefecture_name_kana': item[3],
                    'city_name_kana': item[4],
                    'town_name_kana': townNameKana,
                    'prefecture_name': item[6],
                    'city_name': item[7],
                    'town_name': townName
                    }
                if preZipJson['zip_code'] == jsonData['zip_code']:
                    zipArray.append(jsonData)
                else:
                    if not os.path.exists(os.path.join(basePath, 'zip_code', preZipJson['zip_code'][0:3])):
                        os.makedirs(os.path.join(basePath, 'zip_code', preZipJson['zip_code'][0:3]))
                    fw = open(os.path.join(basePath, 'zip_code', preZipJson['zip_code'][0:3], preZipJson['zip_code'] + '.json'),'w')
                    json.dump(zipArray, fw, indent=2, ensure_ascii=False)
                    preZipJson = jsonData
                    zipArray = [jsonData]
    except:
        print('JSONファイル作成に失敗しました')
        raise


def checkDiff(before, after):
    command = 'diff -r ' + before + ' ' + after
    ret = subprocess.run(command.split(), stdout=subprocess.PIPE)
    output = ret.stdout.decode()
    lines = output.splitlines()
    for i, line in enumerate(lines):
        print('-----------------diff start----------------')
        print(i, line)
        print('-----------------diff end----------------')

def updateVersion(basePath, version):
    with open(os.path.join(basePath, 'data', 'zip_code_version'), 'w') as f:
        writer = csv.writer(f)
        dt = datetime.date.today().strftime('%Y%m%d')
        writer.writerow([dt, version])

if __name__ == "__main__":
    tmpdir = os.path.join(Config.basePath, "scripts", 'tmp')
    os.makedirs(tmpdir, exist_ok=True)
    try:
        fileName, fileSize = getRawFile(Config.yuseiUrl, tmpdir)
        print('マスタデータを取得しました')
        if checkVersion(Config.basePath, fileSize):
            createJson(tmpdir, fileName)
            print('JSONファイルを作成しました')
            shutil.copyfile(Config.targetZip, os.path.join(tmpdir, "zip_code.zip"))
            with zipfile.ZipFile(os.path.join(tmpdir, "zip_code.zip")) as zf:
                zf.extractall(os.path.join(tmpdir, "zip_code_old"))
            checkDiff(os.path.join(tmpdir, "zip_code_old"), os.path.join(tmpdir, "zip_code"))
            shutil.make_archive(os.path.join(tmpdir, "zip_code"), 'zip', root_dir=os.path.join(tmpdir, "zip_code"))
            shutil.move(os.path.join(tmpdir, "zip_code.zip"), Config.targetZip)
            updateVersion(Config.basePath, fileSize)
        else:
            print('マスタデータに変更はありませんでした')
    except Exception as err:
        print(err)
        print('エラー発生')
    finally:
        print('処理が終わりました')
        shutil.rmtree(tmpdir)

