import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import query_documents

for q in ["ซาราเจโวเป็นเมืองหลวงของจังหวัดใด",
          "ผู้ลงมือลอบปลงพระชนม์เป็นสมาชิกขององค์กรลับใด",
          "ชาติใดที่แข่งขันกันสร้างกำลังทางเรือก่อนเกิดสงคราม"]:
    print("=" * 60)
    print(q)
    for i, c in enumerate(query_documents(q, n_results=10)):
        print(f"--- chunk {i} ---")
        print(c[:300])