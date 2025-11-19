import streamlit as st
import duckdb
import pandas as pd
import datetime
import time

# ==========================================
# 1. 사용자 기본 정보 (본인 이름 필수 수정!)
# ==========================================
my_name = "신기호"  # <--- 여기를 본인 이름으로 바꾸세요!
my_address = "인천광역시 계양구 계산새로 109"
my_phone = "010-1234-5678"

# ==========================================
# 2. DuckDB 연결 및 데이터 자동 보정
# ==========================================
con = duckdb.connect(database='madang.db', read_only=False)

# 테이블 생성 (없을 경우)
con.execute("""
CREATE TABLE IF NOT EXISTS Book (bookid INTEGER, bookname VARCHAR, publisher VARCHAR, price INTEGER);
CREATE TABLE IF NOT EXISTS Customer (custid INTEGER, name VARCHAR, address VARCHAR, phone VARCHAR);
CREATE TABLE IF NOT EXISTS Orders (orderid INTEGER, custid INTEGER, bookid INTEGER, saleprice INTEGER, orderdate VARCHAR);
""")

# [핵심] 내 이름이 DB에 있는지 확인하고, 없으면 '자동으로' 넣어주는 로직
# 이렇게 하면 기존 DB가 있어도 내 정보가 안전하게 들어갑니다.
check_me = con.execute(f"SELECT count(*) FROM Customer WHERE name = '{my_name}'").fetchone()[0]

if check_me == 0:
    # 가장 큰 번호(custid) 찾아서 +1 (자동 번호 부여)
    max_id = con.execute("SELECT MAX(custid) FROM Customer").fetchone()[0]
    new_id = 1 if max_id is None else max_id + 1
    
    # 나를 고객으로 등록
    con.execute(f"INSERT INTO Customer VALUES ({new_id}, '{my_name}', '{my_address}', '{my_phone}')")
    
    # 내친김에 책 구매 내역도 하나 등록 (오늘 날짜)
    dt = datetime.date.today().strftime("%Y-%m-%d")
    
    # 주문번호 따기
    max_oid = con.execute("SELECT MAX(orderid) FROM Orders").fetchone()[0]
    new_oid = 1 if max_oid is None else max_oid + 1
    
    # 10번 책(Olympic Champions) 구매 등록
    con.execute(f"INSERT INTO Orders VALUES ({new_oid}, {new_id}, 10, 13000, '{dt}')")
    print(f"✅ {my_name}님 자동 등록 완료!")

# ==========================================
# 3. UI 구성 (신규 고객 등록 기능 추가)
# ==========================================
st.title(f"📱 마당 매니저 Pro")

# --- [사이드바] 신규 고객 직접 등록 기능 ---
with st.sidebar:
    st.header("➕ 신규 고객 등록")
    with st.form("new_user_form"):
        new_name = st.text_input("이름")
        new_addr = st.text_input("주소")
        new_ph = st.text_input("전화번호")
        
        submitted = st.form_submit_button("고객 추가하기")
        if submitted and new_name:
            # 중복 확인
            cnt = con.execute(f"SELECT count(*) FROM Customer WHERE name='{new_name}'").fetchone()[0]
            if cnt > 0:
                st.error("이미 등록된 이름입니다.")
            else:
                # ID 따기
                mx_id = con.execute("SELECT MAX(custid) FROM Customer").fetchone()[0]
                nxt_id = mx_id + 1 if mx_id else 1
                con.execute(f"INSERT INTO Customer VALUES ({nxt_id}, '{new_name}', '{new_addr}', '{new_ph}')")
                st.success(f"{new_name}님 등록 완료!")
                time.sleep(1)
                st.rerun() # 새로고침

# --- [메인 화면] ---
tab1, tab2 = st.tabs(["🔍 고객 조회", "💰 거래 입력"])

# 책 리스트 준비
books_df = con.execute("SELECT bookid, bookname, price FROM Book").df()
# 보기 좋게 'ID: 제목 (가격)' 형식으로 변환
book_options = [f"{row['bookid']}: {row['bookname']} ({row['price']}원)" for idx, row in books_df.iterrows()]

with tab1:
    st.subheader("고객 및 구매 내역 조회")
    # 기본값으로 내 이름을 넣어둡니다.
    search_input = st.text_input("고객명 검색", value=my_name)
    
    if search_input:
        # 고객 정보 확인
        cust_data = con.execute(f"SELECT * FROM Customer WHERE name = '{search_input}'").df()
        
        if not cust_data.empty:
            st.success(f"검색 결과: {search_input} (ID: {cust_data['custid'][0]})")
            st.table(cust_data) # 고객 정보 표로 보여주기
            
            st.write("📘 구매 기록")
            sql_log = f"""
            SELECT o.orderid, b.bookname, o.saleprice, o.orderdate 
            FROM Orders o 
            JOIN Book b ON o.bookid = b.bookid 
            JOIN Customer c ON o.custid = c.custid
            WHERE c.name = '{search_input}'
            ORDER BY o.orderdate DESC
            """
            log_df = con.execute(sql_log).df()
            if not log_df.empty:
                st.dataframe(log_df, use_container_width=True)
            else:
                st.info("구매 기록이 없습니다.")
        else:
            st.warning("등록되지 않은 고객입니다. 왼쪽 사이드바에서 등록해주세요!")

with tab2:
    st.subheader("새로운 책 판매 (주문 입력)")
    
    # 1. 고객 선택 (이름 입력하면 자동 확인)
    target_name = st.text_input("구매자 이름", value=my_name, key="order_name")
    
    target_custid = None
    if target_name:
        chk = con.execute(f"SELECT custid FROM Customer WHERE name='{target_name}'").fetchone()
        if chk:
            target_custid = chk[0]
            st.caption(f"✅ 고객 확인됨: ID {target_custid}")
        else:
            st.error("존재하지 않는 고객입니다. 먼저 등록해주세요.")
    
    # 2. 책 선택
    sel_book_str = st.selectbox("판매할 책 선택", book_options)
    
    # 3. 거래 버튼
    if st.button("판매 등록 (주문 완료)"):
        if target_custid and sel_book_str:
            # 책 ID와 가격 파싱
            bk_id = int(sel_book_str.split(":")[0])
            bk_price = int(sel_book_str.split("(")[1].replace("원)", ""))
            
            # 주문 번호 생성
            mx_oid = con.execute("SELECT MAX(orderid) FROM Orders").fetchone()[0]
            nw_oid = mx_oid + 1 if mx_oid else 1
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            
            # INSERT
            con.execute(f"INSERT INTO Orders VALUES ({nw_oid}, {target_custid}, {bk_id}, {bk_price}, '{today_str}')")
            st.success(f"주문이 완료되었습니다! (주문번호: {nw_oid})")
            time.sleep(1)
            st.rerun()

