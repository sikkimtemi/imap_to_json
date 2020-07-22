# imap_to_json

## 概要

IMAPでメールを受信し、主要項目をJSON形式に変換して返すAPIサーバーです。

添付ファイルは`tmp`ディレクトリの下にメール番号のディレクトリを作って出力し、ファイル名と絶対パスを返します。APIサーバーはローカルで動かす想定です。

## インストール

```bash
pip3 install -r requirements.txt
```

## 事前準備

`api_server.py`の`DOMAIN`、`USER_ID`、`PASSWORD`の値をを実際のIMAPサーバーのホスト名、ユーザーID、パスワードで書き換えます。

## 実行方法

```bash
python3 api_server.py
```

## 使い方

### メール受信

未読メッセージを受信したい場合。

```bash
curl http://127.0.0.1:8080/fetchmail
```

すべてのメッセージを受信したい場合。

```bash
curl http://127.0.0.1:8080/fetchmail?option=ALL
```

その他の利用可能なオプションについては下記を参照。

https://www.atmarkit.co.jp/fnetwork/rensai/netpro09/imap4-searchoption.html

### tmpディレクトリのクリーン

```bash
curl http://127.0.0.1:8080/clean
```

### メールサーバーからメールを削除

100日前までに届いたメールをすべて削除したい場合。

```bash
curl -X DELETE -H 'Content-Type: application/json' -d '{"days":100}' http://127.0.0.1:8080/fetchmail
```
