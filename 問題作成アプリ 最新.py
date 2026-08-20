from google import genai

# APIキーをダブルクォーテーション("")の中に貼り付けます
API_KEY = "AQ.Ab8RN6IU9uVbDSQXmZOjzHo9fFYHQOtgoZ-HQUc3fIONAPimBw"  # ←ここにAI Studioでコピーしたキーをそのまま貼り付け

client = genai.Client(api_key=API_KEY)

print("Geminiが問題を考えています...\n")

# gemini-2.5-flash または gemini-1.5-flash を指定
response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="「背骨を持つ動物のことを脊椎動物と呼ぶ。」という文章から、簡単な3択問題を1問作ってください。"
)

print(response.text)