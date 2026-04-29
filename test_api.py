import os
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()


def test_openai_api():
    print("\n[1] OpenAI API 테스트 시작")

    try:
        client = OpenAI()  # 환경변수 OPENAI_API_KEY 사용

        res = client.models.list()

        print("✅ OpenAI API 정상 동작")
        print(f"사용 가능한 모델 수: {len(res.data)}")

    except Exception as e:
        print("❌ OpenAI API 오류 발생")
        print(e)
if __name__ == "__main__":
    print("====== API 테스트 시작 ======")

    test_openai_api()

    print("\n====== 테스트 종료 ======")