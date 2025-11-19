import streamlit as st
import duckdb
import pandas as pd
import datetime
import time

# ==========================================
# 1. 사용자 기본 정보 (본인 이름 필수 수정!)
# ==========================================
my_name = "신기호"   # <--- 본인 이름으로 수정하세요!
my_address = "인천광역시 계양구 계산새로 109"
my_phone = "010-1234-5678"

# ==========================================
# 2. DuckDB 연결 및 "완전 초기화" (Reset)
# ==========================================
# 주의: 이 코드는 실행할 때마다 데이터를 초기화해서 꼬임을 방지합니다.
con = duckdb.connect(database='madang.db', read_only=False)

# 기존 테이블이 있다면 삭제 (박지성 복구를 위해 싹 지웁니다)
con.execute("DROP TABLE IF EXISTS Orders")
con.execute("DROP TABLE IF EXISTS Customer")
con.execute("DROP TABLE IF EXISTS Book")

# 테이블 새로 생성
con.execute("""
CREATE TABLE Book (bookid INTEGER, bookname VARCHAR, publisher VARCHAR, price INTEGER);
CREATE TABLE Customer (custid INTEGER, name VARCHAR, address VARCHAR, phone VARCHAR);
CREATE TABLE Orders (orderid INTEGER, custid INTEGER, bookid INTEGER, saleprice INTEGER, orderdate VARCHAR);
""")

# ==========================================
# 3. 데이터 입력 (박지성 + 나)
# ==========================================

# (1) 책 데이터 (기존 그대로)
books = [
    (1, '축구의 역사', '굿스포츠', 7000), (2, '축구아는 여자', '나무수', 13000),
    (3, '축구의 이해', '대한미디어', 22000), (4, '골프 바이블', '대한미디어', 35000),
    (5, '피겨 교본', '굿스포츠', 8000), (6, '역도 단계별기술', '굿스포츠', 6000),
    (7, '야구의 추억', '이상미디어', 20000), (8, '야구를 부탁해', '이상미디어', 13000),
    (9, '올림픽 이야기', '삼성당', 7500), (10, 'Olympic Champions', 'Pearson', 13000)
]
con.executemany("INSERT INTO Book VALUES (?, ?, ?, ?)", books)

# (2) 고객 데이터 (★ 박지성 살려내고, 나를 6번에 추가)
customers = [
    (1, '박지성', '영국 맨체스타', '000-5000-0001'),  # <--- 박지성 부활!
    (2, '김연아', '대한민국 서울', '000-6000-0001'),
    (3, '장미란', '대한민국 강원도', '000-7000-0001'),
    (4, '추신수', '미국 클리블랜드', '000-8000-0001'),
    (5, '박세리', '대한민국 대전', None),
    (6, my_name, my_address, my_phone)              # <--- 6번에 본인 추가
]
con.executemany("INSERT INTO Customer VALUES (?, ?, ?, ?)", customers)

# (3) 주문 데이터
orders = [
    (1, 1, 1, 6000, '2014-07-01'), (2, 1, 3, 21000, '2014-07-03'),
    (3, 2, 5, 8000, '2014-07-03'), (4, 3, 6, 6000, '2014-07-04'),
    (5, 4, 7, 20000, '2014-07-05'), (6, 1, 2, 12000, '2014-07-07'),
    (7, 4, 8, 13000, '2014-07-07'), (8, 3, 10, 12000, '2014-07-08'),
    (9, 2, 10, 7000, '2014-07-09'), (10, 3, 8, 13000, '2014-07-10')
]
con.executemany("INSERT INTO Orders VALUES (?, ?, ?, ?, ?)", orders)

# (4) 나의 구매 내역 추가 (6번 고객이 10번 책 구매)
dt = datetime.date.today().strftime("%Y-%m-%d")
con.execute(f"INSERT INTO Orders VALUES (11, 6, 10, 13000, '{dt}')")


# ==========================================
# 4. 화면 구성 (UI)
# ==========================================
st.title(f"📱 마당 서점 Pro ({my_name})")

# 사이드바 (신규 등록)
with st.sidebar:
    st.header("➕ 신규 고객 등록")
    with st.form("new_user"):
        nm = st.text_input("이름")
        ad = st.text_input("주소")
        ph = st.text_input("번호")
        if st.form_submit_button("등록"):
            mx = con.execute("SELECT MAX(custid) FROM Customer").fetchone()[0] + 1
            con.execute(f"INSERT INTO Customer VALUES ({mx}, '{nm}', '{ad}', '{ph}')")
            st.success(f"{nm}님 등록 완료!")
            time.sleep(1)
            st.rerun()

# 메인 탭
tab1, tab2 = st.tabs(["🔍 조회", "💰 주문"])

with tab1:
    st.subheader("고객 및 구매 내역")
    # 검색창 (기본값 비워둠)
    search = st.text_input("이름 검색 (예: 박지성)", value="")
    
    if search:
        cust = con.execute(f"SELECT * FROM Customer WHERE name='{search}'").df()
        if not cust.empty:
            st.success(f"ID: {cust['custid'][0]} / {cust['address'][0]}")
            
            # 구매 내역
            sql = f"""
            SELECT o.orderid, b.bookname, o.saleprice, o.orderdate 
            FROM Orders o, Book b, Customer c
            WHERE o.bookid=b.bookid AND o.custid=c.custid AND c.name='{search}'
            """
            st.dataframe(con.execute(sql).df())
        else:
            st.error("찾는 고객이 없습니다.")
    else:
        st.info("이름을 입력하면 구매 내역이 나옵니다.")
        # 전체 고객 명단 보여주기 (제대로 들어갔나 확인용)
        st.write("📋 **전체 고객 명단**")
        st.dataframe(con.execute("SELECT * FROM Customer").df())

with tab2:
    st.subheader("책 구매하기")
    # 고객 선택
    c_list = con.execute("SELECT name FROM Customer").df()['name'].tolist()
    who = st.selectbox("구매자", c_list, index=len(c_list)-1) # 기본값: 나(맨뒤)
    
    # 책 선택
    b_df = con.execute("SELECT bookid, bookname, price FROM Book").df()
    b_opts = [f"{r['bookid']}:{r['bookname']} ({r['price']}원)" for i,r in b_df.iterrows()]
    book_str = st.selectbox("책", b_opts)
    
    if st.button("주문 완료"):
        c_id = con.execute(f"SELECT custid FROM Customer WHERE name='{who}'").fetchone()[0]
        b_id = int(book_str.split(":")[0])
        prc = int(book_str.split("(")[1][:-2])
        o_id = con.execute("SELECT MAX(orderid) FROM Orders").fetchone()[0] + 1
        now = datetime.date.today().strftime("%Y-%m-%d")
        
        con.execute(f"INSERT INTO Orders VALUES ({o_id}, {c_id}, {b_id}, {prc}, '{now}')")
        st.success("주문 성공!")
        time.sleep(1)
        st.rerun()
