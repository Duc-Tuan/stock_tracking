from langchain.messages import HumanMessage
import os
import requests
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_classic.chains import RetrievalQA
from langchain_openai import ChatOpenAI

load_dotenv()

# -------------------------------
# 1️⃣ Cấu hình API
# -------------------------------
API_URLS = {
    "pnl": os.getenv("API_PNL_URL"),
    "acc": os.getenv("API_ACC_TRANSACTION_URL"),
}

LOGIN_URL = "http://127.0.0.1:8000/login"
USERNAME = "admin"
PASSWORD = "2Anhem34@123"

def get_new_token():
    """Gọi API /login để lấy access_token mới (chuẩn FastAPI OAuth2)."""
    try:
        response = requests.post(
            LOGIN_URL,
            data={  # ✅ phải là `data` chứ KHÔNG phải `json`
                "username": USERNAME,
                "password": PASSWORD
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        access_token = data.get("access_token") or data.get("token")
        if not access_token:
            raise ValueError(f"Không tìm thấy access_token trong phản hồi /login: {data}")

        # ✅ Cập nhật biến môi trường
        os.environ["API_TOKEN"] = access_token

        # ✅ Ghi đè vào .env để lưu token lâu dài
        try:
            with open(".env", "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            lines = []

        with open(".env", "w", encoding="utf-8") as f:
            token_updated = False
            for line in lines:
                if line.startswith("API_TOKEN="):
                    f.write(f"API_TOKEN={access_token}\n")
                    token_updated = True
                else:
                    f.write(line)
            if not token_updated:
                f.write(f"\nAPI_TOKEN={access_token}\n")

        print("🔑 Đã làm mới token thành công.")
        return access_token

    except requests.exceptions.RequestException as e:
        print(f"⚠️ Lỗi khi kết nối API /login: {e}")
    except Exception as e:
        print(f"⚠️ Lỗi khi làm mới token: {e}")
    return None

# -------------------------------
# ⚙️ Bổ sung ánh xạ tiếng Việt → param API
# -------------------------------
VN_PARAM_MAP = {
    "mã": "id_symbol",
    "thước": "id_symbol",
    "id": "id_symbol",
    "symbol": "id_symbol",
    "khung": "timeframe",
    "khung_thời_gian": "timeframe",
    "khung thời gian": "timeframe",
    "thời_gian": "timeframe",
    "thời gian": "timeframe",
    "tối_đa": "limit",
    "tối đa": "limit",
    "số_lượng": "limit",
    "số lượng": "limit",
    "giới_hạn": "limit",
    "giới hạn": "limit",
    "trang": "page",
}

def normalize_vietnamese_param(param):
    key = param.lower().strip().replace(" ", "_")
    return VN_PARAM_MAP.get(key, key)

def fetch_data_from_api(api_name, params=None):
    """Gọi API, tự động refresh token nếu Unauthorized."""
    if api_name not in API_URLS:
        raise ValueError(f"API '{api_name}' chưa được định nghĩa.")

    url = API_URLS[api_name]
    token = os.getenv("API_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            print("⚠️ Token hết hạn hoặc không hợp lệ. Đang làm mới token...")
            new_token = get_new_token()
            if not new_token:
                raise RuntimeError("Không thể làm mới token. Dừng tiến trình.")
            # Thử gọi lại API với token mới
            headers["Authorization"] = f"Bearer {new_token}"
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        else:
            raise  # Các lỗi khác giữ nguyên

# -------------------------------
# 2️⃣ Khởi tạo LLM
# -------------------------------
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

# -------------------------------
# 4️⃣ Trích xuất API và params từ câu tự nhiên
# -------------------------------
def interpret_user_query(query, llm):
    """Dùng GPT để hiểu câu tiếng Việt và trích API + params."""
    system_prompt = """
Bạn là một trợ lý giúp ánh xạ câu tiếng Việt của người dùng sang lệnh API JSON.
Hãy chỉ trả về JSON dạng:
{"api_name": "...", "params": {"id_symbol": "...", "timeframe": "...", "limit": "..."}}

Các API hợp lệ: pnl, acc.
Nếu không xác định được API nào, trả về {"api_name": null, "params": {}}.
"""
    full_prompt = f"{system_prompt}\nNgười dùng nói: {query}"
    response = llm.invoke([HumanMessage(content=full_prompt)])

    import json
    try:
        parsed = json.loads(response.content)
        return parsed.get("api_name"), parsed.get("params", {})
    except Exception:
        return None, {}
    
# -------------------------------
# 3️⃣ Chạy query dựa trên API (đã tích hợp interpret_user_query)
# -------------------------------
def run_api_query(user_query, llm):
    """
    Phân tích câu người dùng:
      - Nếu có chứa 'api:' → gọi API trực tiếp
      - Nếu là câu tự nhiên → interpret_user_query để tự hiểu API & params
    """
    # 1️⃣ Nếu user nhập dạng 'api:pnl ...' thì parse thủ công
    if user_query.lower().startswith("api:"):
        parts = user_query[len("api:"):].strip().split()
        api_name = parts[0]
        params = {}
        for p in parts[1:]:
            if "=" in p:
                k, v = p.split("=", 1)
                params[k] = v
    else:
        # 2️⃣ Nếu người dùng nói tự nhiên → dùng LLM để hiểu API + params
        api_name, params = interpret_user_query(user_query, llm)
        if not api_name:
            return "❌ Tôi không hiểu câu này thuộc API nào.", None, None

    # 3️⃣ Gọi API
    data = fetch_data_from_api(api_name, params)
    if not data:
        return f"❌ Không có dữ liệu trả về từ API '{api_name}'.", None, None

    # 4️⃣ Chuẩn bị prompt cho LLM để phân tích dữ liệu
    if isinstance(data, list):
        data_str = "\n".join([str(item) for item in data[:10]])
    else:
        data_str = str(data)

    prompt_text = (
        f"Dữ liệu từ API '{api_name}':\n{data_str}\n\n"
        f"Hãy trả lời câu hỏi dựa trên dữ liệu trên:\n{user_query}"
    )

    response = llm.invoke([HumanMessage(content=prompt_text)])
    answer = response.content if hasattr(response, "content") else str(response)

    return answer, api_name, data


# -------------------------------
# 4️⃣ Load Chatbot RetrievalQA
# -------------------------------
def load_chatbot():
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    db = FAISS.load_local("src/ai/vector_db", embeddings, allow_dangerous_deserialization=True)
    retriever = db.as_retriever(search_kwargs={"k": 3})
    llm_local = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
    qa = RetrievalQA.from_chain_type(llm=llm_local, retriever=retriever, chain_type="stuff")
    return qa


# -------------------------------
# 5️⃣ Main loop (có ghi nhớ API gần nhất)
# -------------------------------
if __name__ == "__main__":
    qa = load_chatbot()
    print("🤖 Chatbot đã sẵn sàng! Gõ 'exit' để thoát.\n")

    last_api_name = None
    last_api_data = None

    while True:
        q = input("🧠 Bạn: ").strip()
        if q.lower() in ["exit", "quit"]:
            break

        try:
            # Nếu là lệnh gọi API mới
            if q.lower().startswith("api:"):
                parts = q[len("api:"):].strip().split()
                api_name = parts[0]
                params = {}

                # 🔍 Tự động parse params từ câu lệnh
                # 🔍 Tự động parse params (hỗ trợ cả tiếng Việt)
                for p in parts[1:]:
                    if "=" in p:
                        k, v = p.split("=", 1)
                        k = normalize_vietnamese_param(k)
                        params[k] = v
                    else:
                        # Cho phép viết kiểu: khung thời_gian M1
                        idx = parts.index(p)
                        if idx + 1 < len(parts) and "=" not in parts[idx + 1]:
                            key = normalize_vietnamese_param(p)
                            params[key] = parts[idx + 1]
                # for p in parts[1:]:
                #     if "=" in p:
                #         k, v = p.split("=", 1)
                #         params[k] = v
                #     else:
                #         # Cho phép viết kiểu: page 1 limit 200
                #         idx = parts.index(p)
                #         if idx + 1 < len(parts) and "=" not in parts[idx + 1]:
                #             params[p] = parts[idx + 1]

                # Nếu người dùng không nhập page/limit -> mặc định
                params.setdefault("page", "1")
                params.setdefault("limit", "100")
                
                ans, last_api_name, last_api_data = run_api_query(q, llm)
                # ans, last_api_name, last_api_data = run_api_query(api_name, params, "Phân tích dữ liệu này giúp tôi", llm)
                print("🤖 Trả lời:", ans)
                continue

            # Nếu hỏi tiếp sau API trước đó
            elif last_api_data is not None:
                data_str = (
                    "\n".join([str(item) for item in last_api_data[:10]])
                    if isinstance(last_api_data, list)
                    else str(last_api_data)
                )
                prompt_text = (
                    f"Tiếp tục phân tích dựa trên dữ liệu gần nhất từ API '{last_api_name}':\n{data_str}\n\n"
                    f"Câu hỏi mới: {q}"
                )
                response = llm.invoke([HumanMessage(content=prompt_text)])
                ans = response.content if hasattr(response, "content") else str(response)
                print("🤖 Trả lời:", ans)
                continue

            # Nếu không có API trước đó → dùng RetrievalQA
            else:
                result = qa.invoke({"query": q})
                ans = result["result"]
                print("🤖 Trả lời:", ans)

        except Exception as e:
            print("⚠️ Lỗi:", e)

