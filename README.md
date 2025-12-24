# Lunch Menu Notifier

매일 아침 8시(KST)에 네이버 블로그에서 최신 점심 메뉴 이미지를 스크랩하여 슬랙 개인 메시지로 전송하는 자동화 시스템입니다.

## 기능
- 네이버 블로그에서 메뉴 이미지 자동 다운로드
- 슬랙 DM으로 메뉴 이미지 전송

## 설정
1. Slack API에서 앱 생성 (https://api.slack.com/apps) - "From an app manifest" 선택
2. 아래 JSON을 붙여넣기:
   ```json
   {
       "display_information": {
           "name": "Lunch Menu Notifier"
       },
       "settings": {
           "org_deploy_enabled": false,
           "socket_mode_enabled": false,
           "is_hosted": false,
           "token_rotation_enabled": false
       }
   }
   ```
3. OAuth & Permissions에서 Bot Token Scopes 추가: `chat:write`, `files:write`, `im:write`, `channels:join`
4. Install to Workspace: 앱을 워크스페이스에 설치 (워크스페이스 관리자 권한 필요, 설치 후 토큰 생성)
5. Bot User OAuth Token 복사 (Verification Token 아님, Client Secret 아님)
5. 채널 ID 확인 (메뉴를 전송할 채널): Slack 채널에서 채널 이름 클릭 > 채널 세부 정보 > 채널 ID 복사 (C로 시작)
6. Google Chat 웹훅 URL 확인 (선택사항): Google Chat 스페이스에서 웹훅 생성
7. GitHub 리포지토리에 코드를 푸시합니다.
8. GitHub 리포지토리 Settings > Secrets and variables > Actions에서 `SLACK_BOT_TOKEN`, `CHANNEL_ID`, `GOOGLE_CHAT_WEBHOOK`를 설정합니다.
9. 워크플로우가 자동으로 실행됩니다 (매일 8시 KST). 봇이 Slack 채널과 Google Chat에 메뉴 이미지를 전송합니다.

## 로컬 테스트
```bash
pip install -r requirements.txt

# 환경 변수 설정 (실제 토큰과 채널 ID 사용)
export SLACK_BOT_TOKEN="your_bot_token"
export CHANNEL_ID="C0A59M92L1K"
export GOOGLE_CHAT_WEBHOOK="your_webhook_url"

# 테스트 모드 (슬랙 전송 없이 콘솔 출력)
TEST_IMAGE_URL="https://example.com/menu.png" DRY_RUN=True python main.py

# 실제 실행 (이미지 스크랩 및 슬랙 전송)
python main.py
```

## 동작 과정
1. 공휴일 체크: 한국 공휴일(신정, 삼일절, 어린이날 등)에는 실행 생략
2. 블로그에서 이미지 URL 획득
3. PIL로 이미지 다운로드 및 저장 (`menu_image.jpg`)
4. 슬랙 채널로 메뉴 이미지 전송

## 주의사항
- 네이버 블로그 구조에 따라 이미지 파싱 로직을 조정해야 할 수 있습니다.
