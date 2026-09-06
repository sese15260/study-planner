# StudyMate

학습자 유형, 과목, 공부 분량, 기간을 입력하면 AI가 날짜별 Todo-list를 만들어주는 공부 계획 웹서비스입니다.

> 배포 URL: [https://studymate-navy.vercel.app/](https://studymate-navy.vercel.app/)

## 주요 기능

- 홈 / 이용 방법 / 공부 계획 / FAQ 섹션 이동
- 학습 정보 입력과 필수값·날짜·최대 60일 검증
- AI가 날짜별로 3개의 구체적인 Todo 생성
- `슬라이드 500장`처럼 숫자 분량을 입력하면 시작·끝 범위를 포함하도록 AI에 요청
- 로딩, API 오류, 네트워크 오류, 90초 시간 초과 안내
- Gemini의 일시 오류에는 한 번 자동 재시도하고, 계속 실패하면 숫자 분량을 날짜별 범위로 나눈 대체 계획 표시
- 모바일 반응형 화면

## 기술 스택과 폴더 역할

```
study-planner/
├── index.html          # 화면 구조와 입력 폼
├── css/style.css       # 디자인과 모바일 반응형
├── js/app.js           # 입력 검증, fetch 요청, 결과 화면 처리
├── api/recommend.py    # Vercel Python Serverless Function과 Gemini API 호출
├── requirements.txt    # Python 패키지 목록
├── SERVICE_PLAN.md     # 서비스 기획서
└── images/             # 제출용 스크린샷과 증빙 자료
```

HTML은 섹션·폼·결과 영역의 구조를, CSS는 색상·여백·반응형을, JavaScript는 사용자 입력과 화면 상태를 담당합니다. `api/recommend.py`는 브라우저에 API 키를 보내지 않고 서버에서만 Gemini API를 호출합니다.

## AI 요청 흐름

1. 사용자가 폼을 제출하면 `js/app.js`가 빈값과 날짜를 검증합니다.
2. 정상 값이면 로딩 화면을 보여주고 `fetch('/api/recommend')`로 JSON 데이터를 보냅니다.
3. `api/recommend.py`가 값을 다시 검증하고, 환경 변수의 `GEMINI_API_KEY`로 Gemini API를 호출합니다.
4. Python 함수는 날짜별 Todo가 담긴 JSON만 반환합니다. Gemini의 일시 오류에는 한 번 재시도하고, 계속 실패하면 숫자 분량을 나눈 대체 계획을 반환합니다.
5. JavaScript가 성공 결과를 Todo 카드로 표시하고, 설정 오류·입력 오류·지연은 안내 문구로 표시합니다.

배포 사이트에서는 `fetch('/api/recommend')`가 같은 Vercel 서버의 Python Function을 호출합니다. VS Code Live Server나 휴대폰 내부망 미리보기에서는 Python Function을 직접 실행할 수 없으므로, 배포된 StudyMate API를 호출하도록 분기했습니다. 이 경우에도 API 키는 브라우저에 전달되지 않고 Vercel 서버에만 있습니다.

## 환경 변수 설정

API 키는 절대로 `app.js`, `recommend.py`, README, GitHub 커밋에 작성하지 마세요.

1. [Google AI Studio](https://aistudio.google.com/app/apikey)에서 Gemini API 키를 만듭니다.
2. Vercel 프로젝트의 **Settings → Environment Variables**에서 아래 이름으로 값을 추가합니다.

   ```
   GEMINI_API_KEY
   ```

3. Production과 Preview 환경을 선택해 저장한 뒤 다시 배포합니다. Vercel CLI로 로컬 개발을 할 경우 Development 환경도 선택합니다.

Vercel 환경 변수는 코드 밖에서 관리되며, 값 변경은 새 배포에 적용됩니다. [Vercel 환경 변수 공식 문서](https://vercel.com/docs/environment-variables)를 참고하세요.

## 실행과 배포

### 화면만 로컬에서 확인

VS Code에서 `index.html`을 열고 Live Server의 **Go Live**를 사용합니다. 화면과 메뉴 이동을 확인할 수 있으며, 계획 생성 버튼은 배포된 API를 사용합니다. `file:///...`로 파일을 직접 열지 말고 `http://localhost:...` 또는 `http://127.0.0.1:...` 주소로 여세요.

### Vercel 배포

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
5. `GEMINI_API_KEY` 환경 변수를 추가한 뒤 Deploy합니다.
6. 발급된 `https://...vercel.app` 주소를 README의 배포 URL에 붙여 넣고 모바일 브라우저에서 **그 주소를 직접** 엽니다.

`api/recommend.py`는 Vercel에서 자동으로 `/api/recommend` 경로가 됩니다. Vercel은 `api/` 폴더의 Python 함수를 배포할 수 있습니다. [Vercel Python Functions 공식 문서](https://vercel.com/docs/functions/runtimes/python)

## 테스트 목록

| 상황 | 입력 또는 행동 | 기대 결과 |
|---|---|---|
| 정상 | 대학생 / 심리학 / 슬라이드 500장 / 2026-09-01~2026-09-03 | 날짜별 구체적인 슬라이드 범위 Todo 표시 |
| 빈 입력 | 아무 값 없이 버튼 클릭 | `필수 정보를 입력해주세요.` 표시 |
| 날짜 오류 | 목표일을 시작일보다 빠르게 선택 | 날짜 오류 안내 표시 |
| 기간 초과 | 61일 이상 선택 | 최대 60일 안내 표시 |
| API 일시 오류 | Gemini 서비스가 일시 실패 | 재시도 후 날짜별 대체 계획 표시 |
| API 설정 오류 | API 키 누락 또는 모델 설정 오류 | 결과 영역에 재시도 안내 표시 |
| 응답 지연 | 90초 이상 응답 없음 | 시간 초과 안내 표시 |

## 배포 후 문제 진단 순서

1. Vercel Deployments 화면에서 배포가 성공했는지 확인합니다.
2. Vercel Functions 로그에서 `/api/recommend` 오류 상태를 확인합니다.
3. 브라우저 개발자 도구의 Console과 Network에서 API 응답 상태를 확인합니다.
4. 원인을 수정하고 GitHub에 push한 뒤 새 Vercel 배포에서 다시 테스트합니다.

예를 들어 Live Server에서 `/api/recommend`가 404라면 Python 서버가 실행되지 않은 것이므로, 배포 URL에서 테스트하거나 현재 프로젝트의 배포 API를 호출하도록 확인합니다. Gemini 404라면 모델 이름을, 401/403이라면 Vercel 환경 변수 이름과 적용 환경을 확인합니다.

## 평가 기준 설명 메모

- **HTML/CSS/JS/API 구조**: HTML은 폼·결과의 구조, CSS는 반응형 디자인, JS는 `fetch`와 화면 상태, Python은 키 보호와 AI 호출을 담당합니다.
- **fetch 흐름**: JS가 JSON을 `POST /api/recommend`로 보내고, Python이 JSON 응답을 돌려주면 JS가 Todo 카드로 렌더링합니다.
- **로딩/성공/실패**: 요청 중 버튼을 비활성화하고 로딩 문구를 보여주며, 성공 시 결과 카드를 표시합니다. 입력 오류·설정 오류·시간 초과는 각각 안내합니다.
- **Serverless 검증과 응답 형식**: Python은 입력을 다시 검증하고, `dailyPlans → date, tasks[3개]` 형식만 응답으로 사용합니다.
- **환경 변수 보안**: 키를 프론트엔드에 넣으면 방문자가 볼 수 있으므로, Vercel 서버 환경 변수에서만 읽습니다.
- **AI 기능을 넣은 이유**: 전체 분량을 매일의 실행 단위로 나누는 작업을 자동화해 사용자가 바로 공부를 시작하게 돕습니다.
- **응답 지연 개선**: 현재는 90초 대기, 일시 오류 한 번 재시도, 대체 계획을 적용했습니다. 더 개선하려면 더 빠른 모델, 입력 길이 제한, 요청 횟수 제한을 고려합니다.
- **AI 기능 확장**: 두 번째 기능이 필요하면 `api/review.py`처럼 엔드포인트를 분리하고, 프론트에서도 별도 버튼과 결과 영역을 만듭니다.
- **프레임워크 허용 시**: React/Vue는 화면 상태와 컴포넌트 재사용에는 유리하지만 빌드 도구와 구조가 추가됩니다. 현재 서비스는 단일 페이지·작은 폼이므로 바닐라 JS가 더 단순합니다.

## 제출용 증빙 자료

`images/README.md`의 목록대로 데스크톱 화면, 모바일 화면, 실제 AI 계획 결과, Codex 대화 과정을 캡처해 `images/` 폴더에 저장하세요.

## 제출 전 체크리스트

- [ ] Vercel 배포 URL이 정상적으로 열린다.
- [ ] GitHub 저장소에 `index.html`, `css/`, `js/`, `api/`, `requirements.txt`가 있다.
- [ ] README에 서비스 소개, 기술 스택, 실행·배포 방법, 배포 URL, 환경 변수 설명이 있다.
- [ ] `SERVICE_PLAN.md`에 서비스 목적, 타겟, 섹션, AI 입력·출력·실패 처리가 있다.
- [ ] `images/`에 데스크톱, 모바일, AI 결과, Codex 사용 과정 스크린샷을 넣었다.
- [ ] 스크린샷과 GitHub 커밋에 API 키나 개인 정보가 보이지 않는다.
