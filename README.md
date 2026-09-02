# StudyMate

학습자 유형, 과목, 공부 분량, 기간을 입력하면 AI가 날짜별 Todo-list를 만들어주는 공부 계획 웹서비스입니다.

> 배포 URL: Vercel 배포 후 이 문장을 실제 주소로 바꾸세요. 예: `https://study-planner.vercel.app`

## 주요 기능

- 홈 / 이용 방법 / 공부 계획 / FAQ 섹션 이동
- 학습 정보 입력과 필수값·날짜·최대 60일 검증
- AI가 날짜별로 3개의 구체적인 Todo 생성
- `슬라이드 500장`처럼 숫자 분량을 입력하면 시작·끝 범위를 포함하도록 AI에 요청
- 로딩, API 오류, 네트워크 오류, 20초 시간 초과 안내
- 모바일 반응형 화면

## 기술 스택과 폴더 역할

```
study-planner/
├── index.html          # 화면 구조와 입력 폼
├── css/style.css       # 디자인과 모바일 반응형
├── js/app.js           # 입력 검증, fetch 요청, 결과 화면 처리
├── api/recommend.py    # Vercel Python Serverless Function과 OpenAI API 호출
├── requirements.txt    # Python 패키지 목록
├── SERVICE_PLAN.md     # 서비스 기획서
└── images/             # 제출용 스크린샷과 증빙 자료
```

HTML은 섹션·폼·결과 영역의 구조를, CSS는 색상·여백·반응형을, JavaScript는 사용자 입력과 화면 상태를 담당합니다. `api/recommend.py`는 브라우저에 API 키를 보내지 않고 서버에서만 OpenAI API를 호출합니다.

## AI 요청 흐름

1. 사용자가 폼을 제출하면 `js/app.js`가 빈값과 날짜를 검증합니다.
2. 정상 값이면 로딩 화면을 보여주고 `fetch('/api/recommend')`로 JSON 데이터를 보냅니다.
3. `api/recommend.py`가 값을 다시 검증하고, 환경 변수의 `OPENAI_API_KEY`로 OpenAI Responses API를 호출합니다.
4. Python 함수는 날짜별 Todo가 담긴 JSON만 반환합니다.
5. JavaScript가 성공 결과를 Todo 카드로 표시하고, 오류·지연은 안내 문구로 표시합니다.

## 환경 변수 설정

API 키는 절대로 `app.js`, `recommend.py`, README, GitHub 커밋에 작성하지 마세요.

1. OpenAI Platform에서 API 키를 만듭니다.
2. Vercel 프로젝트의 **Settings → Environment Variables**에서 아래 이름으로 값을 추가합니다.

   ```
   OPENAI_API_KEY
   ```

3. Production과 Preview 환경을 선택해 저장한 뒤 다시 배포합니다.

Vercel 환경 변수는 코드 밖에서 관리되며, 값 변경은 새 배포에 적용됩니다. [Vercel 환경 변수 공식 문서](https://vercel.com/docs/environment-variables)를 참고하세요.

## 배포 방법

1. GitHub에서 빈 저장소를 만듭니다.
2. VS Code 터미널에서 아래 명령을 실행합니다. `<내 GitHub 저장소 주소>`만 본인 주소로 바꾸세요.

   ```bash
   git init
   git add .
   git commit -m "feat: add StudyMate AI study planner"
   git branch -M main
   git remote add origin <내 GitHub 저장소 주소>
   git push -u origin main
   ```

3. Vercel에서 **Add New → Project**를 누르고 GitHub 저장소를 Import합니다.
4. Framework Preset은 `Other`로 두고 Root Directory는 이 프로젝트 폴더로 설정합니다.
5. `OPENAI_API_KEY` 환경 변수를 추가한 뒤 Deploy합니다.
6. 발급된 `https://...vercel.app` 주소를 README의 배포 URL에 붙여 넣고 모바일 브라우저에서 **그 주소를 직접** 엽니다.

`api/recommend.py`는 Vercel에서 자동으로 `/api/recommend` 경로가 됩니다. Vercel은 `api/` 폴더의 Python 함수를 배포할 수 있습니다. [Vercel Python Functions 공식 문서](https://vercel.com/docs/functions/runtimes/python)

## 테스트 목록

| 상황 | 입력 또는 행동 | 기대 결과 |
|---|---|---|
| 정상 | 대학생 / 심리학 / 슬라이드 500장 / 2026-09-01~2026-09-03 | 날짜별 구체적인 슬라이드 범위 Todo 표시 |
| 빈 입력 | 아무 값 없이 버튼 클릭 | `필수 정보를 입력해주세요.` 표시 |
| 날짜 오류 | 목표일을 시작일보다 빠르게 선택 | 날짜 오류 안내 표시 |
| 기간 초과 | 61일 이상 선택 | 최대 60일 안내 표시 |
| API 오류 | API 키 누락 또는 서비스 오류 | 결과 영역에 재시도 안내 표시 |
| 응답 지연 | 20초 이상 응답 없음 | 시간 초과 안내 표시 |

## 배포 후 문제 진단 순서

1. Vercel Deployments 화면에서 배포가 성공했는지 확인합니다.
2. Vercel Functions 로그에서 `/api/recommend` 오류 상태를 확인합니다.
3. 브라우저 개발자 도구의 Console과 Network에서 API 응답 상태를 확인합니다.
4. 원인을 수정하고 GitHub에 push한 뒤 새 Vercel 배포에서 다시 테스트합니다.

## 제출용 증빙 자료

`images/README.md`의 목록대로 데스크톱 화면, 모바일 화면, 실제 AI 계획 결과, Codex 대화 과정을 캡처해 `images/` 폴더에 저장하세요.
