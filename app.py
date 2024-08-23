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

        if user_id not in user_question_count:
            user_question_count[user_id] = 0

        if user_question_count[user_id] == 0:
            try:
                app.logger.info("LINEに待機メッセージを送信します")
                messaging_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="少々お待ちください…！")]
                    )
                )
                app.logger.info("待機メッセージ送信成功")
            except Exception as e:
                app.logger.error(f"LINE Messaging APIエラー: メッセージ送信中にエラーが発生しました: {e}, トレースバック: {traceback.format_exc()}")
                raise

            # 次に実際のプッシュメッセージを送信
            reply_message = get_openai_response(user_message)
            try:
                app.logger.info("LINEにプッシュメッセージを送信します")
                messaging_api.push_message(
                    user_id,
                    [TextMessage(text=reply_message)]
                )
                app.logger.info("プッシュメッセージ送信成功")
            except Exception as e:
                app.logger.error(f"LINE Messaging APIエラー: メッセージ送信中にエラーが発生しました: {e}, トレースバック: {traceback.format_exc()}")
                raise
        else:
            if user_question_count[user_id] <= 3:
                reply_message = get_openai_response(user_message)
                app.logger.info(f"OpenAIからの応答を取得しました: {reply_message}")
                user_question_count[user_id] += 1
                try:
                    app.logger.info("LINEにメッセージを送信します")
                    messaging_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[TextMessage(text=reply_message)]
                        )
                    )
                    app.logger.info("メッセージ送信成功")
                except Exception as e:
                    app.logger.error(f"LINE Messaging APIエラー: メッセージ送信中にエラーが発生しました: {e}, トレースバック: {traceback.format_exc()}")
                    raise
            else:
                reply_message = "貴重なお時間をいただき、誠にありがとうございました。回答は３問までです！お会いできる日を心待ちにしております！"
                try:
                    app.logger.info("3問目以降のメッセージを送信します")
                    messaging_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[TextMessage(text=reply_message)]
                        )
                    )
                    app.logger.info("メッセージ送信成功")
                except Exception as e:
                    app.logger.error(f"LINE Messaging APIエラー: メッセージ送信中にエラーが発生しました: {e}, トレースバック: {traceback.format_exc()}")
                    raise
    except Exception as e:
        app.logger.error(f"メッセージ処理中のエラー: {e}, トレースバック: {traceback.format_exc()}")

def get_openai_response(user_message):
    try:
        # OpenAI APIを呼び出して応答を取得
        response = openai.Completion.create(
            engine="text-davinci-003",  # 使用するモデル（例: text-davinci-003）
            prompt=user_message,        # ユーザーからのメッセージ
            max_tokens=150,             # 応答の最大トークン数
            n=1,                        # 応答の数
            stop=None,                  # 応答を停止するトークン
            temperature=0.7             # 応答の多様性
        )
        reply_message = response.choices[0].text.strip()
        return reply_message
    except Exception as e:
        app.logger.error(f"OpenAI APIエラー: {e}, トレースバック: {traceback.format_exc()}")
        return "申し訳ありませんが、処理中にエラーが発生しました。"

if __name__ == "__main__":
    # 開発サーバーを 0.0.0.0 で起動する
    app.run(host='0.0.0.0', port=5000)
