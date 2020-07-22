'''
IMAP4でメールを受信し、結果をJSON形式を返すFlask製APIサーバー。
'''

import datetime
import email
import os
import imaplib
import shutil
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from flask import Flask, jsonify, request
from flask_restful import Resource, Api

DOMAIN = 'xxxxxxxxxxxxxxxxxxxxxxxxxxx'
USER_ID = 'xxxxxxxxxxxxxxxxxxxxxxxxxxx'
PASSWORD = 'xxxxxxxxxxxxxxxxxxxxxxxxxxx'

APP = Flask(__name__)
APP.config['JSON_AS_ASCII'] = False
API = Api(APP)

class CommonUtil():
    '''
    共通処理クラス。
    '''

    def get_header_text(self, msg:email.message.EmailMessage):
        '''
        ヘッダー部をまとめて文字列として返す。
        '''

        text = ''
        for key, value in msg.items():
            text = text + '{}: {}\n'.format(key, value)
        return text


    def get_main_content(self, msg:email.message.EmailMessage):
        '''
        メール本文、フォーマット、キャラクターセットを取得する。
        '''

        try:
            body_part = msg.get_body()
            main_content = body_part.get_content()
            format_ = body_part.get_content_type()
            charset = body_part.get_content_charset()

        except Exception as error:
            print(error)
            main_content = '解析失敗'
            format_ = '不明'
            charset = '不明'
            # get_bodyでエラーになるのは文字コード設定がおかしいメールを受信した場合なので、
            # decodeせずにテキスト部分をそのまま返す。
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    format_ = part.get_content_type()
                    main_content = str(part.get_payload())
                    charset = part.get_content_charset()

        return main_content, format_, charset


    def get_attachments(self, msg:email.message.EmailMessage, b_num:bytes):
        '''
        添付ファイルが存在する場合はファイルに出力し、ファイルパスとファイル名を返す。
        ファイルはメール番号のディレクトリに格納する。
        '''

        files = []
        for part in msg.iter_attachments():
            try:
                filename = part.get_filename()
                if not filename:
                    continue
                # メール番号でディレクトリを作成
                new_dir = os.path.join('./tmp/{}/'.format(b_num.decode('utf-8')))
                os.makedirs(new_dir, exist_ok=True)
                # 添付ファイルを出力
                file_path = os.path.join(new_dir, filename)
                with open(file_path, 'wb') as fp:
                    fp.write(part.get_payload(decode=True))
                # ファイルパス（絶対パス）とファイル名を保存
                abs_path = os.path.abspath(file_path)
                files.append({'file_path':abs_path, 'file_name':filename})

            except Exception as error:
                print(error)

        return files


    def clean_tmp_dir(self):
        '''
        tmpディレクトリを空にする。
        '''

        shutil.rmtree('./tmp')
        os.mkdir('./tmp')


class FetchMail(Resource):
    '''
    メール受信用クラス。
    '''

    def get(self):
        '''
        メールを受信し、内容と添付ファイルの情報をJSON形式で返す。
        '''

        result = []

        # IMAP4の検索条件
        # 設定可能な内容は下記を参照
        # https://www.atmarkit.co.jp/fnetwork/rensai/netpro09/imap4-searchoption.html
        search_option = request.args.get('option')

        # 検索条件を指定しない場合は未読メールの検索とする
        if not search_option:
            search_option = 'UNSEEN'

        # メールサーバーに接続
        cli = imaplib.IMAP4_SSL(DOMAIN)

        try:
            # 認証
            cli.login(USER_ID, PASSWORD)

            # メールボックスを選択（標準はINBOX）
            cli.select()

            # 指定されたオプションを用いてメッセージを検索
            status, data = cli.search(None, search_option)

            # 受信エラーの場合はエラーを返して終了
            if status == 'NO':
                print('受信エラー')
                res = {
                    'status': 'ERROR'
                }
                return jsonify(res)

            # メールの解析
            for num in data[0].split():
                status, data = cli.fetch(num, '(RFC822)')
                msg = BytesParser(policy=policy.default).parsebytes(data[0][1])
                msg_id = msg.get('Message-Id', failobj='')
                from_ = msg.get('From', failobj='')
                to = msg.get('To', failobj='')
                cc = msg.get('Cc', failobj='')
                subject = msg.get('Subject', failobj='')
                date_str = msg.get('Date', failobj='')
                date_time = parsedate_to_datetime(date_str)
                if date_time:
                    # タイムゾーンを日本国内向けに上書き
                    date_time = date_time.astimezone(datetime.timezone(datetime.timedelta(hours=9)))
                date = date_time.strftime('%Y/%m/%d') if date_time else ''
                time = date_time.strftime('%H:%M:%S') if date_time else ''
                header_text = CommonUtil.get_header_text(self, msg)
                body, format_, charset = CommonUtil.get_main_content(self, msg)
                attachments = CommonUtil.get_attachments(self, msg, num)
                json_data = {}
                json_data['msg_id'] = msg_id
                json_data['header'] = header_text
                json_data['from'] = from_
                json_data['to'] = to
                json_data['cc'] = cc
                json_data['subject'] = subject
                json_data['date'] = date
                json_data['time'] = time
                json_data['format'] = format_
                json_data['charset'] = charset
                json_data['body'] = body
                json_data['attachments'] = attachments
                result.append(json_data)
            res = {
                'status': 'OK',
                'result': result
            }
            return jsonify(res)

        except Exception as error:
            print(error)
            res = {
                'status': 'ERROR'
            }
            return jsonify(res)

        finally:
            cli.close()
            cli.logout()


    def delete(self):
        '''
        メールを検索し、対象のメッセージをメールサーバーから削除する。
        '''

        # 日数の指定（指定された日数以前のメールが削除対象となる）
        data = request.json
        days = data.get('days')

        # 未指定時は90日を指定
        if not days:
            days = 90

        # 検索条件の生成
        target_date = datetime.datetime.now() - datetime.timedelta(days=days)
        search_option = target_date.strftime('BEFORE %d-%b-%Y')

        # メールサーバーに接続
        cli = imaplib.IMAP4_SSL(DOMAIN)

        try:
            # 認証
            cli.login(USER_ID, PASSWORD)

            # メールボックスを選択（標準はINBOX）
            cli.select()

            # 指定されたオプションを用いてメッセージを検索
            status, data = cli.search(None, search_option)

            # 受信エラーの場合はエラーを返して終了
            if status == 'NO':
                print('受信エラー')
                res = {
                    'status': 'ERROR'
                }
                return jsonify(res)

            # 対象メッセージの削除
            for num in data[0].split():
                cli.store(num, '+FLAGS', '\\Deleted')
            cli.expunge()

            res = {
                'status': 'OK',
            }
            return jsonify(res)

        except Exception as error:
            print(error)
            res = {
                'status': 'ERROR'
            }
            return jsonify(res)

        finally:
            cli.close()
            cli.logout()


class Clean(Resource):
    '''
    tmpディレクトリの掃除用クラス。
    '''

    def get(self):
        '''
        tmpディレクトリを空にする。
        '''

        CommonUtil.clean_tmp_dir(self)

        res = {
            'status': 'OK'
        }

        return jsonify(res)


API.add_resource(FetchMail, '/fetchmail')
API.add_resource(Clean, '/clean')


if __name__ == "__main__":
    APP.run(port=8080, debug=False)
