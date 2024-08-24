import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai

# Flaskアプリケーションのインスタンスを作成
app = Flask(__name__)

# LINE Messaging APIの設定
# 環境変数からアクセストークンとチャンネルシークレットを取得
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# ユーザーの質問回数をカウントする辞書を作成
# 各ユーザーごとに何回質問したかを記録する
user_question_count = {}

# OpenAI APIを使って応答を生成する関数
def get_openai_response(user_message):
    system_instruction = "あなたは聡明さと優しさを持ち合わせた女性です。以下の質問に対して、回答を日本語で250文字以内にまとめてください。"
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message}
            ]
        )
        reply_message = response['choices'][0]['message']['content'].strip()
        
# 返信メッセージの長さを制限
if len(reply_message) > 250:
    # 句点（。）で文章を分割
    sentences = reply_message.split('。')
    
    # 文章の途中で切れないようにする
    truncated_message = ''
    
    for sentence in sentences:
        # 次の文章を追加しても250文字以内なら追加
        if len(truncated_message) + len(sentence) + 1 <= 250:  # 1文字は句点のため
            truncated_message += sentence + '。'
        else:
            break
    
    # 最後に省略記号を追加
    reply_message = truncated_message.strip() + '...'
        # 返信メッセージの長さを制限
    #     if len(reply_message) > 250:
    #         reply_message = reply_message[:250].rsplit(' ', 1)[0] + '...'
        
    #     return reply_message
    # except Exception as e:
    #     app.logger.error(f"OpenAI APIのエラー: {e}")
    #     return "申し訳ありませんが、応答を生成できませんでした。もう一度お試しください。"

# ルートURLにアクセスされた場合の応答
@app.route("/", methods=['GET'])
def root():
    return 'Server is running', 200

# LINE Messaging APIからのWebHookを受け取るエンドポイント
@app.route("/callback", methods=['POST'])
def callback():
    # リクエストヘッダーにx-line-signatureが含まれているか確認
    if 'x-line-signature' not in request.headers:
        app.logger.error("リクエストにx-line-signatureヘッダーが含まれていません。")
        abort(400)

    # 署名とボディを取得
    signature = request.headers['x-line-signature']
    body = request.get_data(as_text=True)

    try:
        # WebhookHandlerでLINEのイベントを処理
        handler.handle(body, signature)
    except InvalidSignatureError:
        # 署名が無効な場合のエラーハンドリング
        app.logger.error("無効な署名です。")
        abort(400)
    except Exception as e:
        # その他のエラーが発生した場合
        app.logger.error(f"リクエスト処理中のエラー: {e}")
        abort(500)

    return 'OK'

# LINEでメッセージイベントが発生した場合の処理
@handler.add(MessageEvent)
def handle_message(event):
    try:
        # ユーザーIDとメッセージテキストを取得
        user_id = event.source.user_id
        user_message = event.message.text
        reply_token = event.reply_token  # reply_tokenを取得

        # ログにメッセージの受信を記録
        app.logger.info(f"{user_id}からのメッセージを受信しました: {user_message}")

        # ユーザーの質問回数を確認し、初めての質問の場合はカウントを初期化
        if user_id not in user_question_count:
            user_question_count[user_id] = 0

        # 質問回数が3回未満の場合、応答を送信
        if user_question_count[user_id] < 3:
            # ユーザーに「少々お待ちください」との応答をすぐに送信
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text="少々お待ちください...！")
            )

            # OpenAI APIからの応答を取得
            reply_message = get_openai_response(user_message)

            # 応答が空でないか確認
            if not reply_message:
                reply_message = "申し訳ありませんが、応答を生成できませんでした。"

            # プッシュメッセージで応答を送信
            try:
                line_bot_api.push_message(
                    user_id,
                    TextSendMessage(text=reply_message)
                )
            except LineBotApiError as e:
                # LINE Messaging APIのエラーをログに記録
                app.logger.error(f"LINE Messaging APIエラー: {e}")

            # 質問回数を増やす
            user_question_count[user_id] += 1

        else:
            # 質問回数が3回に達した場合、終了メッセージを送信
            reply_message = "貴重なお時間をいただき、誠にありがとうございました。回答は３問までです！"
            try:
                line_bot_api.reply_message(
                    reply_token,
                    TextSendMessage(text=reply_message)
                )
            except LineBotApiError as e:
                # LINE Messaging APIのエラーをログに記録
                app.logger.error(f"LINE Messaging APIエラー: {e}")

    except Exception as e:
        # メッセージ処理中のエラーをログに記録
        app.logger.error(f"メッセージ処理中のエラー: {e}")

# Flaskアプリケーションを実行
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
