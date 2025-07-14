import requests
from bs4 import BeautifulSoup
import pandas as pd

url = "https://finlife.fss.or.kr/finlife/jsp/irp/IRPSelectSearch.jsp"  # 실제 요청 URL은 다를 수 있음

# 대략적인 구조 (사이트가 동적 로딩이면 Selenium 필요할 수 있음)
def get_irp_table():
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    table = soup.find("table", {"class": "tbl_type1"})  # 클래스명은 확인 필요
    rows = table.find_all("tr")[1:]

    data = []
    for row in rows:
        cols = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cols) >= 6:  # 데이터 컬럼 수 확인
            data.append({
                "상품명": cols[0],
                "운용사": cols[1],
                "상품유형": cols[2],
                "1년 수익률": cols[3],
                "위험등급": cols[4],
                "수수료율": cols[5],
            })

    return pd.DataFrame(data)

df = get_irp_table()
print(df.head())
