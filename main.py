import os
import requests
from bs4 import BeautifulSoup
from PIL import Image
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import io
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from datetime import datetime

# 환경 변수에서 슬랙 토큰 가져오기
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
DRY_RUN = os.getenv('DRY_RUN', 'False').lower() == 'true'
if not DRY_RUN and not SLACK_BOT_TOKEN:
    raise ValueError("SLACK_BOT_TOKEN 환경 변수가 설정되지 않았습니다.")

# 블로그 카테고리 URL (최신 메뉴 게시글 찾기)
BLOG_CATEGORY_URL = "https://blog.naver.com/PostList.naver?blogId=yjm3038&categoryNo=13"

# 슬랙 채널 ID
CHANNEL_ID = os.getenv('CHANNEL_ID')
if not DRY_RUN and not CHANNEL_ID:
    raise ValueError("CHANNEL_ID 환경 변수가 설정되지 않았습니다.")

# 구글 채팅 웹훅 URL
GOOGLE_CHAT_WEBHOOK = os.getenv('GOOGLE_CHAT_WEBHOOK')

def is_holiday():
    """오늘 날짜가 한국 공휴일인지 확인합니다."""
    today = datetime.now().date()
    month = today.month
    day = today.day

    # 주요 고정 공휴일
    holidays = [
        (1, 1),   # 신정
        (3, 1),   # 삼일절
        (5, 5),   # 어린이날
        (6, 6),   # 현충일
        (8, 15),  # 광복절
        (10, 3),  # 개천절
        (10, 9),  # 한글날
        (12, 25), # 크리스마스
    ]

    if (month, day) in holidays:
        return True

    # 추가로 설날, 추석 등은 매년 다르니, 간단히 생략 또는 API 사용 (여기서는 생략)

    return False

def check_robots_txt(url):
    """robots.txt를 확인하여 크롤링 허용 여부를 체크합니다."""
    parsed_url = urlparse(url)
    robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
        user_agent = '*'  # 일반적인 사용자 에이전트
        if not rp.can_fetch(user_agent, url):
            print(f"robots.txt에서 크롤링이 허용되지 않음: {url}")
            return False
        else:
            print(f"robots.txt에서 크롤링 허용: {url}")
            return True
    except Exception as e:
        print(f"robots.txt 확인 실패: {e}")
        return True  # 확인 실패 시 허용으로 간주

def get_latest_menu_image_url():
    """블로그에서 최신 메뉴 이미지 URL을 가져옵니다."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(BLOG_CATEGORY_URL, headers=headers)
    response.raise_for_status()
    html_content = response.text

    soup = BeautifulSoup(html_content, 'html.parser')

    # 메뉴 카테고리(13)의 최신 게시글 링크 찾기
    post_links = soup.find_all('a', href=lambda href: href and 'PostView.naver' in href and 'categoryNo=13' in href)
    if not post_links:
        print("메뉴 카테고리의 게시글 링크를 찾을 수 없습니다.")
        return None

    latest_post_url = post_links[0]['href']
    if not latest_post_url.startswith('http'):
        latest_post_url = 'https://blog.naver.com' + latest_post_url
    print(f"최신 메뉴 게시글 URL: {latest_post_url}")

    # 게시글 페이지 크롤링
    response = requests.get(latest_post_url, headers=headers)
    response.raise_for_status()
    post_html = response.text
    post_soup = BeautifulSoup(post_html, 'html.parser')

    # 게시글에서 메뉴 이미지 찾기 (postfiles.pstatic.net 도메인 사용)
    images = post_soup.find_all('img', src=lambda src: src and 'postfiles.pstatic.net' in src)
    print(f"게시글 이미지 개수: {len(images)}")
    for i, img in enumerate(images):
        src = img.get('src', '')
        data_src = img.get('data-src', '')
        data_lazy_src = img.get('data-lazy-src', '')
        print(f"이미지 {i}: src={src}, data-src={data_src}, data-lazy-src={data_lazy_src}")
        # 큰 버전 URL 찾기
        large_url = data_src or data_lazy_src or src
        if 'type=w773' in large_url or 'type=w80_blur' not in large_url:
            print(f"큰 이미지 후보: {large_url}")
    if images:
        # 큰 버전 우선 사용
        image_url = None
        for img in images:
            data_src = img.get('data-src', '')
            data_lazy_src = img.get('data-lazy-src', '')
            src = img.get('src', '')
            candidates = [data_src, data_lazy_src, src]
            for candidate in candidates:
                if candidate and ('type=w773' in candidate or '?' not in candidate):
                    image_url = candidate
                    break
            if image_url:
                break
        if not image_url:
            image_url = images[0]['src']
        # 쿼리 파라미터 처리: w80_blur -> w773, 또는 제거
        if 'type=w80_blur' in image_url:
            image_url = image_url.replace('type=w80_blur', 'type=w773')
        print(f"선택된 이미지 URL: {image_url}")
        return image_url
    return None

def download_image(image_url):
    """이미지를 다운로드하여 파일로 저장합니다."""
    response = requests.get(image_url)
    response.raise_for_status()
    image = Image.open(io.BytesIO(response.content))
    print(f"이미지 크기: {image.size}")  # (width, height)
    image_path = 'menu_image.png'
    image.save(image_path)
    return image_path

def send_slack_message(image_path):
    """슬랙 채널로 이미지를 전송합니다."""
    client = WebClient(token=SLACK_BOT_TOKEN)
    try:
        # 파일 업로드
        response = client.files_upload_v2(
            channel=CHANNEL_ID,
            file=image_path,
            title="오늘의 점심 메뉴",
            initial_comment="오늘의 점심 메뉴입니다."
        )
        print("슬랙 이미지 전송 성공")
    except SlackApiError as e:
        print(f"슬랙 이미지 전송 실패: {e.response['error']}")
        if 'error' in e.response:
            print(f"에러 상세: {e.response}")
        else:
            print(f"예외: {e}")

def send_google_chat_message(image_url):
    """구글 채팅으로 메시지를 전송합니다."""
    if not GOOGLE_CHAT_WEBHOOK:
        print("구글 채팅 웹훅이 설정되지 않아 생략")
        return
    message = {
        "text": f"오늘의 점심 메뉴입니다.\n{image_url}"
    }
    try:
        response = requests.post(GOOGLE_CHAT_WEBHOOK, json=message)
        response.raise_for_status()
        print("구글 채팅 메시지 전송 성공")
    except requests.RequestException as e:
        print(f"구글 채팅 메시지 전송 실패: {e}")

def main():
    dry_run = os.getenv('DRY_RUN', 'False').lower() == 'true'
    test_image_url = os.getenv('TEST_IMAGE_URL')
    print("점심 메뉴 조회 시작")

    # 공휴일 체크
    if is_holiday():
        print("오늘은 공휴일입니다. 메뉴 전송을 생략합니다.")
        return

    # robots.txt 확인 (경고만, 강제 중단하지 않음)
    check_robots_txt(BLOG_CATEGORY_URL)

    if test_image_url:
        image_url = test_image_url
        print(f"테스트 이미지 URL 사용: {image_url}")
    else:
        image_url = get_latest_menu_image_url()
        if not image_url:
            message = "오늘의 메뉴를 찾을 수 없습니다. 블로그를 확인해 주세요."
            print(message)
            if not dry_run:
                # 메시지만 전송 (이미지 없음)
                client = WebClient(token=SLACK_BOT_TOKEN)
                client.chat_postMessage(channel=CHANNEL_ID, text=message)
            return

    print(f"이미지 URL: {image_url}")
    image_path = download_image(image_url)
    print("이미지가 menu_image.png로 저장되었습니다.")

    if dry_run:
        print("테스트 모드: 메시지 전송 생략")
    else:
        send_slack_message(image_path)
        send_google_chat_message(image_url)
    print("완료")

if __name__ == "__main__":
    main()
