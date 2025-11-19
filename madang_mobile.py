import streamlit as st
import duckdb
import pandas as pd
import datetime
import time

# ==========================================
# 1. 사용자 정보 설정 (수정 필수!)
# ==========================================
my_name = "본인_이름"  # <--- 여기에 본인 이름을 적으세요!
my_address = "인천광역시 계양구 계산새로 109"
my_phone = "010-1234-5678"

# ==========================================
# 2. DuckDB 연결 및 초기 세팅 (pymysql 대체)
# ==========================================
# 파일 기반 DB라서 클라우드에서도 작동합니다.
con = duckdb.connect(database='madang.db', read_only=False)

# 테이블이 없으면 생성 (초기화 로직)
con.execute("""
CREATE TABLE IF NOT EXISTS Book (bookid INTEGER, bookname VARCHAR, publisher VARCHAR, price INTEGER);
CREATE TABLE IF NOT EXISTS Customer (custid INTEGER, name VARCHAR, address VARCHAR, phone VARCHAR);
CREATE TABLE IF NOT EXISTS Orders (orderid INTEGER, custid INTEGER, bookid INTEGER, saleprice INTEGER, orderdate VARCHAR);
""")

# 데이터가 비어있으면 기초 데이터 + 내 정보 넣기
if con.execute("SELECT count(*) FROM Customer").fetchone()[0] == 0:
    # (1) 책 데이터
    books_data = [
        (1, '축구의 역사', '굿스포츠', 7000), (2, '축구아는 여자', '나무수', 13000),
        (3, '축구의 이해', '대한미디어', 22000), (4, '골프 바이블', '대한미디어', 35000),
        (5, '피겨 교본', '굿스포츠', 8000), (6, '역도 단계별기술', '굿스포츠', 6000),
        (7, '야구의 추억', '이상미디어', 20000), (8, '야구를 부탁해', '이상미디어', 13000),
        (9, '올림픽 이야기', '삼성당', 7500), (10, 'Olympic Champions', 'Pearson', 13000)
    ]
    con.executemany("INSERT INTO Book VALUES (?, ?, ?, ?)", books_data)

    # (2) 고객 데이터 (1번 박지성을 '나'로 변경하여 입력!)
    # 교수님 과제가 '박지성 말고 나를 등록'이므로 1번에 본인을 넣습니다.
    customers_data = [
        (1, my_name, my_address, my_phone), 
        (2, '김연아', '대한민국 서울', '000-6000-0001'), (3, '장미란', '대한민국 강원도', '000-7000-0001'),
        (4, '추신수', '미국 클리블랜드', '000-8000-0001'), (5, '박세리', '대한민국 대전', None)
    ]
    con.executemany("INSERT INTO Customer VALUES (?, ?, ?, ?)", customers_data)

    # (3) 주문 데이터 (기본 + 내 구매 내역)
    orders_data = [
        (1, 1, 1, 6000, '2014-07-01'), (2, 1, 3, 21000, '2014-07-03'),
        (3, 2, 5, 8000, '2014-07-03'), (4, 3, 6, 6000, '2014-07-04'),
        (5, 4, 7, 20000, '2014-07-05'), (6, 1, 2, 12000, '2014-07-07'),
        (7, 4, 8, 13000, '2014-07-07'), (8, 3, 10, 12000, '2014-07-08'),
        (9, 2, 10, 7000, '2014-07-09'), (10, 3, 8, 13000, '2014-07-10')
    ]
    con.executemany("INSERT INTO Orders VALUES (?, ?, ?, ?, ?)", orders_data)
    
    # [과제] 내가 책 하나 산 거 등록 (오늘 날짜)
    today = datetime.date.today().strftime("%Y-%m-%d")
    con.execute(f"INSERT INTO Orders VALUES (11, 1, 10, 13000, '{today}')")

# ==========================================
# 3. 마당 매니저 UI (교수님 코드 로직 반영)
# ==========================================
st.title("📱 모바일 마당 매니저")

# 책 리스트 가져오기 (Selectbox용)
books_df = con.execute("SELECT bookid, bookname FROM Book").df()
book_options = [f"{row['bookid']},{row['bookname']}" for idx, row in books_df.iterrows()]

tab1, tab2 = st.tabs(["고객 조회", "거래 입력"])

# --- [탭 1] 고객 조회 ---
with tab1:
    search_name = st.text_input("고객명 검색 (예: 본인이름)")
    if search_name:
        sql = f"""
            SELECT c.name, b.bookname, o.orderdate, o.saleprice 
            FROM Customer c, Book b, Orders o 
            WHERE c.custid = o.custid AND o.bookid = b.bookid AND c.name = '{search_name}'
        """
        result = con.execute(sql).df()
        
        if not result.empty:
            st.dataframe(result)
        else:
            st.warning("해당 고객의 구매 내역이 없습니다.")

# --- [탭 2] 거래 입력 ---
with tab2:
    st.subheader("새로운 거래 추가")
    
    # 1. 고객 정보 확인 (이름으로 검색해서 ID 찾기)
    input_name = st.text_input("구매 고객명", value=my_name) # 기본값 내 이름
    
    if input_name:
        cust_info = con.execute(f"SELECT custid FROM Customer WHERE name = '{input_name}'").fetchone()
        
        if cust_info:
            current_custid = cust_info[0]
            st.success(f"고객 확인됨: {input_name} (ID: {current_custid})")
            
            # 2. 책 선택
            select_book = st.selectbox("구매 서적:", book_options)
            
            if select_book:
                bookid = select_book.split(",")[0]
                
                # 가격 자동 입력 (책 테이블에서 가져오기)
                price_info = con.execute(f"SELECT price FROM Book WHERE bookid={bookid}").fetchone()
                default_price = price_info[0] if price_info else 0
                
                price = st.number_input("금액", value=default_price)
                
                if st.button('거래 입력'):
                    # 주문번호 자동 생성
                    max_order = con.execute("SELECT MAX(orderid) FROM Orders").fetchone()[0]
                    new_orderid = max_order + 1 if max_order else 1
                    
                    dt = datetime.date.today().strftime("%Y-%m-%d")
                    
                    insert_sql = f"""
                    INSERT INTO Orders (orderid, custid, bookid, saleprice, orderdate) 
                    VALUES ({new_orderid}, {current_custid}, {bookid}, {price}, '{dt}')
                    """
                    con.execute(insert_sql)
                    st.success('거래가 입력되었습니다.')
                    time.sleep(1)
                    st.rerun() # 화면 갱신
        else:
            st.error("등록되지 않은 고객입니다.")