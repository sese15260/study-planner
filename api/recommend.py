"""StudyMate의 Vercel Serverless Function입니다.

POST /api/recommend 요청을 받아 Gemini API로 날짜별 공부 계획을 생성합니다.
API 키는 코드에 작성하지 않고 Vercel 환경 변수 GEMINI_API_KEY에서만 읽습니다.
"""

import json
import os
import re
import time
from datetime import date
from http.server import BaseHTTPRequestHandler
from ipaddress import ip_address
from urllib.parse import urlparse

from google import genai
from google.genai import errors, types


MAX_PLAN_DAYS = 60
MAX_BODY_BYTES = 10_000
LEARNER_TYPES = {"중학생", "고등학생", "대학생", "성인"}
STUDY_TIMES = {"1시간", "2시간", "3시간", "4시간", "5시간 이상"}
GEMINI_MODEL = "gemini-3.6-flash"
MAX_AI_ATTEMPTS = 2

STUDY_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "dailyPlans": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "tasks": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["date", "tasks"],
            },
        }
    },
    "required": ["dailyPlans"],
}


class ClientInputError(Exception):
    """사용자가 수정할 수 있는 입력 오류입니다."""


class PlanFormatError(Exception):
    """AI가 예상한 JSON 형식의 계획을 만들지 못했을 때 사용합니다."""


class handler(BaseHTTPRequestHandler):
    """Vercel이 /api/recommend 경로에 연결하는 요청 처리 클래스입니다."""

    def do_POST(self):
        try:
            request_data = self.read_json_request()
            plan_input, expected_dates = validate_plan_input(request_data)
            try:
                study_plan = create_ai_plan(plan_input, expected_dates)
            except errors.APIError as error:
                status_code = getattr(error, "code", None)

                # API 키·모델 설정 오류가 아닐 때는 사용자가 바로 쓸 수 있는
                # 날짜별 분량 계획을 대신 만들어 결과 화면을 유지합니다.
                if status_code not in {401, 403, 404}:
                    print(f"Gemini API error: status={status_code}. Using fallback plan.")
                    study_plan = create_fallback_plan(plan_input, expected_dates)
                else:
                    raise
            self.send_json(200, study_plan)
        except ClientInputError as error:
            self.send_json(400, {"error": str(error)})
        except errors.APIError as error:
            status_code = getattr(error, "code", None)
            print(f"Gemini API error: status={status_code}")
            if status_code == 429:
                self.send_json(429, {"error": "요청이 많습니다. 잠시 후 다시 시도해주세요."})
            elif status_code in {401, 403}:
                self.send_json(502, {"error": "AI 기능 설정을 확인해주세요. 잠시 후 다시 시도해주세요."})
            elif status_code == 404:
                self.send_json(502, {"error": "AI 모델 설정을 확인하지 못했습니다. 잠시 후 다시 시도해주세요."})
            else:
                self.send_json(502, {"error": "AI 계획을 만드는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."})
        except (ConnectionError, TimeoutError):
            print("Could not connect to Gemini API or the request timed out.")
            self.send_json(504, {"error": "AI 응답이 오래 걸리고 있습니다. 잠시 후 다시 시도해주세요."})
        except PlanFormatError:
            print("Gemini returned an unexpected study-plan format.")
            self.send_json(502, {"error": "AI 계획 형식을 확인하지 못했습니다. 다시 시도해주세요."})
        except Exception as error:  # API 키 누락 등 예상하지 못한 서버 오류
            print(f"StudyMate server error: {type(error).__name__}")
            self.send_json(500, {"error": "AI 기능 설정에 문제가 있습니다. 잠시 후 다시 시도해주세요."})

    def do_GET(self):
        self.send_json(405, {"error": "POST 요청만 사용할 수 있습니다."})

    def do_OPTIONS(self):
        """VS Code Live Server의 CORS 사전 요청에 응답합니다."""
        self.send_response(204)
        self.send_cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def read_json_request(self):
        content_length = self.headers.get("Content-Length")

        if not content_length:
            raise ClientInputError("요청 내용을 찾을 수 없습니다.")

        try:
            body_size = int(content_length)
        except ValueError as error:
            raise ClientInputError("요청 형식이 올바르지 않습니다.") from error

        if body_size <= 0 or body_size > MAX_BODY_BYTES:
            raise ClientInputError("입력 내용이 너무 길거나 올바르지 않습니다.")

        try:
            return json.loads(self.rfile.read(body_size).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ClientInputError("JSON 요청 형식이 올바르지 않습니다.") from error

    def send_json(self, status_code, payload):
        response_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(response_body)

    def send_cors_headers(self):
        """Live Server와 같은 내 PC·내 네트워크 미리보기에서만 API 접근을 허용합니다."""
        origin = self.headers.get("Origin", "")

        if is_local_development_origin(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Vary", "Origin")


def is_local_development_origin(origin):
    """localhost 또는 192.168.x.x 같은 내부망 Live Server 주소인지 확인합니다."""
    try:
        parsed_origin = urlparse(origin)
        hostname = parsed_origin.hostname
    except ValueError:
        return False

    if parsed_origin.scheme != "http" or not hostname:
        return False

    if hostname == "localhost":
        return True

    try:
        return ip_address(hostname).is_private or ip_address(hostname).is_loopback
    except ValueError:
        return False


def validate_plan_input(data):
    """프론트에서 받은 값을 확인하고, 계획에 필요한 날짜 목록을 만듭니다."""
    if not isinstance(data, dict):
        raise ClientInputError("요청 형식이 올바르지 않습니다.")

    required_fields = ("learnerType", "subject", "amount", "startDate", "goalDate", "studyTime")
    values = {}

    for field in required_fields:
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ClientInputError("필수 정보를 입력해주세요.")
        values[field] = value.strip()

    if len(values["subject"]) > 100 or len(values["amount"]) > 150:
        raise ClientInputError("과목과 공부할 분량은 100자 이내로 입력해주세요.")

    if values["learnerType"] not in LEARNER_TYPES or values["studyTime"] not in STUDY_TIMES:
        raise ClientInputError("학습자 유형 또는 공부 가능 시간을 다시 선택해주세요.")

    try:
        start_date = date.fromisoformat(values["startDate"])
        goal_date = date.fromisoformat(values["goalDate"])
    except ValueError as error:
        raise ClientInputError("날짜 형식이 올바르지 않습니다.") from error

    if goal_date < start_date:
        raise ClientInputError("목표일은 시작일 이후로 선택해주세요.")

    plan_days = (goal_date - start_date).days + 1
    if plan_days > MAX_PLAN_DAYS:
        raise ClientInputError(f"계획 기간은 최대 {MAX_PLAN_DAYS}일까지 선택해주세요.")

    expected_dates = [date.fromordinal(start_date.toordinal() + day).isoformat() for day in range(plan_days)]
    return values, expected_dates


def create_ai_plan(plan_input, expected_dates):
    """Gemini API로 구조화된 날짜별 계획을 생성합니다."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    instructions = """
당신은 StudyMate의 학습 계획 코치입니다. 반드시 한국어로 답합니다.
사용자가 제공한 시작일부터 목표일까지의 모든 날짜를 빠짐없이 포함한 실천 가능한 공부 계획을 만드세요.
각 날짜에는 정확히 3개의 Todo를 작성하고, 각 Todo는 짧고 구체적인 행동 문장으로 작성하세요.
공부할 분량에 숫자와 단위 또는 범위가 있다면(예: 슬라이드 500장, 교재 1~8장, 문제 200개),
전체 분량을 날짜 수에 맞게 고르게 나누고 각 날짜 Todo에 '슬라이드 1~167장'처럼 시작과 끝 범위를 반드시 적으세요.
'오늘 분량 학습'처럼 범위가 없는 추상적인 문장을 쓰지 마세요.
숫자 분량이 없을 때에도 읽을 자료, 정리할 개념, 풀 문제처럼 구체적인 행동을 제시하세요.
JSON 스키마에 맞는 데이터만 반환하세요.
""".strip()

    user_input = {
        **plan_input,
        "requiredDates": expected_dates,
    }
    client = genai.Client(api_key=api_key)

    try:
        for attempt in range(MAX_AI_ATTEMPTS):
            try:
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=(
                        f"{instructions}\n\n"
                        "아래 학습 정보를 바탕으로 공부 계획을 만드세요.\n"
                        f"{json.dumps(user_input, ensure_ascii=False)}"
                    ),
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=STUDY_PLAN_SCHEMA,
                        temperature=0.4,
                        max_output_tokens=5000,
                    ),
                )
                break
            except errors.APIError as error:
                status_code = getattr(error, "code", None)
                is_temporary_error = status_code in {429, 500, 502, 503, 504}

                if is_temporary_error and attempt < MAX_AI_ATTEMPTS - 1:
                    print(f"Gemini temporary error: status={status_code}. Retrying once.")
                    time.sleep(1)
                    continue

                raise
    finally:
        client.close()

    try:
        study_plan = json.loads(response.text)
    except (AttributeError, TypeError, json.JSONDecodeError) as error:
        raise PlanFormatError from error

    validate_ai_plan(study_plan, expected_dates)
    return study_plan


def validate_ai_plan(study_plan, expected_dates):
    """AI 결과가 화면에 바로 표시해도 되는 구조인지 마지막으로 확인합니다."""
    daily_plans = study_plan.get("dailyPlans") if isinstance(study_plan, dict) else None
    if not isinstance(daily_plans, list) or len(daily_plans) != len(expected_dates):
        raise PlanFormatError

    received_dates = []
    for daily_plan in daily_plans:
        if not isinstance(daily_plan, dict):
            raise PlanFormatError
        tasks = daily_plan.get("tasks")
        plan_date = daily_plan.get("date")
        if not isinstance(plan_date, str) or not isinstance(tasks, list) or len(tasks) != 3:
            raise PlanFormatError
        if any(not isinstance(task, str) or not task.strip() for task in tasks):
            raise PlanFormatError
        received_dates.append(plan_date)

    if received_dates != expected_dates:
        raise PlanFormatError


def create_fallback_plan(plan_input, expected_dates):
    """Gemini가 일시적으로 응답하지 않을 때에도 사용할 수 있는 기본 계획입니다."""
    amount_range = parse_amount_range(plan_input["amount"])
    daily_plans = []

    for index, plan_date in enumerate(expected_dates):
        if amount_range:
            start, end, label, unit = split_amount_for_day(amount_range, index, len(expected_dates))
            range_text = f"{label} {start}~{end}{unit}".strip()
            tasks = [
                f"{range_text} 학습하기",
                f"{range_text} 핵심 개념 정리하기",
                f"{range_text} 학습 내용 복습하기",
            ]
        else:
            tasks = [
                f"{plan_input['subject']} {plan_input['amount']} 학습하기",
                f"{plan_input['subject']} 핵심 개념 3가지 정리하기",
                "전날 학습 내용 복습하기",
            ]

        daily_plans.append({"date": plan_date, "tasks": tasks})

    return {"dailyPlans": daily_plans}


def parse_amount_range(amount):
    """'슬라이드 500장', '교재 1~8장'에서 시작·끝 숫자와 단위를 찾습니다."""
    normalized_amount = amount.replace(",", "").strip()
    range_match = re.fullmatch(r"(.*?)(\d+)\s*[~\-–]\s*(\d+)\s*([^\d\s]*)", normalized_amount)

    if range_match:
        label, start, end, unit = range_match.groups()
        start_number, end_number = int(start), int(end)
        if end_number >= start_number:
            return start_number, end_number, label.strip() or "학습 분량", unit.strip()

    total_match = re.fullmatch(r"(.*?)(\d+)\s*([^\d\s]*)", normalized_amount)
    if total_match:
        label, total, unit = total_match.groups()
        total_number = int(total)
        if total_number > 0:
            return 1, total_number, label.strip() or "학습 분량", unit.strip()

    return None


def split_amount_for_day(amount_range, day_index, total_days):
    """전체 숫자 분량을 날짜 수만큼 최대한 고르게 나눕니다."""
    overall_start, overall_end, label, unit = amount_range
    total_amount = overall_end - overall_start + 1

    if total_amount < total_days:
        item = overall_start + min(day_index, total_amount - 1)
        return item, item, label, unit

    day_start = overall_start + (day_index * total_amount) // total_days
    day_end = overall_start + ((day_index + 1) * total_amount) // total_days - 1
    return day_start, day_end, label, unit
