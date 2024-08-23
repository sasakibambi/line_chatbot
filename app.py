from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest
from linebot.v3.webhooks import MessageEvent
from linebot.v3.messaging.models import TextMessage
import openai
import traceback

app = Flask(__name__)

# LINE Messaging APIの設定
configuration = Configuration(access_token='CHANNEL_ACCESS_TOKEN')
api_client = ApiClient(configuration)
messaging_api = MessagingApi(api_client)
handler = WebhookHandler('CHANNEL_SECRET')

# OpenAI APIキーの設定
openai.api_key = 'OPENAI_API_KEY'

# ユーザーの質問回数をカウントする辞書
user_question_count = {}

@app.route("/callback", methods=['POST'])
def callback():
    if 'x-line-signature' not in request.headers:
        app.logger.error("リクエストにx-line-signatureヘッダーが含まれていません。")
        abort(400)
    
    signature = request.headers['x-line-signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("無効な署名です。")
        abort(400)
    except Exception as e:
        app.logger.error(f"リクエスト処理中のエラー: {e}, トレースバック: {traceback.format_exc()}")
        abort(500)
    
    return 'OK'

@handler.add(MessageEvent)
def handle_message(event):
    try:
        user_id = event.source.user_id
        user_message = event.message.text

        app.logger.info(f"{user_id}からのメッセージを受信しました: {user_message}")

        # メッセージの長さを確認
        if len(user_message) > 250:
            reply_message = "ご質問は250文字以内でお願いします！"
            try:
                messaging_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=reply_message)]
                    )
                )
            except Exception as e:
                app.logger.error(f"LINE Messaging APIエラー: メッセージ送信中にエラーが発生しました: {e}, トレースバック: {traceback.format_exc()}")
            return

        # 質問回数を確認してから返信
        if user_id not in user_question_count:
            user_question_count[user_id] = 0

        if user_question_count[user_id] < 4:
            # まずはリプライトークンが有効なうちに「少々お待ちください」というメッセージを送信
            try:
                messaging_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="少々お待ちください...")]
                    )
                )
            except Exception as e:
                app.logger.error(f"LINE Messaging APIエラー: メッセージ送信中にエラーが発生しました: {e}, トレースバック: {traceback.format_exc()}")
                return
            
            # OpenAIからの応答を取得
            reply_message = get_openai_response(user_message)
            user_question_count[user_id] += 1

            # メッセージを再送信するためにプッシュメッセージを使用
            try:
                messaging_api.push_message(
                    user_id,
                    [TextMessage(text=reply_message)]
                )
            except Exception as e:
                app.logger.error(f"LINE Messaging APIエラー: メッセージ送信中にエラーが発生しました: {e}, トレースバック: {traceback.format_exc()}")
        else:
            reply_message = "貴重なお時間をいただき、誠にありがとうございました。回答は３問までです！お会いできる日を心待ちにしております！"
            try:
                messaging_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=reply_message)]
                    )
                )
            except Exception as e:
                app.logger.error(f"LINE Messaging APIエラー: メッセージ送信中にエラーが発生しました: {e}, トレースバック: {traceback.format_exc()}")
    except Exception as e:
        app.logger.error(f"メッセージ処理中のエラー: {e}, トレースバック: {traceback.format_exc()}")

def get_openai_response(user_message):
    try:
        # OpenAI APIを呼び出して応答を取得
        response = openai.Completion.create(
            engine="text-davinci-003",  # 使用するモデル（例: text-davinci-003）
            prompt=user_message,        # ユーザーからのメッセージ
            max_tokens=150              # 応答の最大トークン数
        )
        return response.choices[0].text.strip()
    except Exception as e:
        app.logger.error(f"OpenAI APIエラー: {e}, トレースバック: {traceback.format_exc()}")
        return "申し訳ありませんが、応答を取得できませんでした。"

if __name__ == "__main__":
    # 開発サーバーを 0.0.0.0 で起動する
    app.run(host='0.0.0.0', port=5000)
