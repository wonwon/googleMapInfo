import math
import os
import time

import googlemaps
import pandas as pd
from dotenv import load_dotenv

# 📌 .env ファイルを読み込み（APIキーを安全に管理）
load_dotenv()
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# 📌 Google Maps クライアントを作成
gmaps = googlemaps.Client(key=API_KEY)

# 📌 JR東加古川駅の緯度・経度
LOCATION = (34.7344, 134.8652)  # 東加古川駅の座標
RADIUS = 50000  # 半径50km
KEYWORD = "インドアゴルフ"  # 検索キーワード


def haversine(lat1, lon1, lat2, lon2):
    """2点間のハーサイン距離（km）を計算"""
    R = 6371.0  # 地球の半径（km）
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def get_places(query, location, radius):
    """Google Places APIを使って指定した地点の半径内で店舗を検索"""
    results = []
    next_page_token = None

    while True:
        try:
            response = gmaps.places(
                query=query,
                location=location,
                radius=radius,
                page_token=next_page_token,
            )

            if "results" in response:
                results.extend(response["results"])

            next_page_token = response.get("next_page_token")
            if not next_page_token:
                break

            time.sleep(2)

        except Exception as e:
            print(f"エラー発生: {e}")
            break

    return results


def get_place_details(place_id):
    """詳細情報（ウェブサイト・口コミ数）を取得"""
    try:
        details = gmaps.place(
            place_id=place_id, fields=["website", "user_ratings_total"]
        )
        return {
            "ウェブサイト": details.get("result", {}).get("website", "なし"),
            "口コミ数": details.get("result", {}).get("user_ratings_total", "N/A"),
        }
    except Exception as e:
        print(f"詳細情報取得エラー: {e}")
        return {"ウェブサイト": "エラー", "口コミ数": "エラー"}


def get_full_address(lat, lng):
    """緯度・経度から漢字の住所を取得"""
    try:
        reverse_geocode_result = gmaps.reverse_geocode((lat, lng), language="ja")
        if reverse_geocode_result:
            return reverse_geocode_result[0]["formatted_address"]
        else:
            return "住所不明"
    except Exception as e:
        print(f"住所取得エラー: {e}")
        return "住所不明"


# 📌 店舗情報を取得
places = get_places(KEYWORD, LOCATION, RADIUS)

# 📌 店舗情報を整理してデータリストに格納
data_list = []
for place in places:
    place_id = place["place_id"]
    details = get_place_details(place_id)
    address = get_full_address(
        place["geometry"]["location"]["lat"], place["geometry"]["location"]["lng"]
    )

    # 距離計算（東加古川駅からの距離）
    distance = haversine(
        LOCATION[0],
        LOCATION[1],
        place["geometry"]["location"]["lat"],
        place["geometry"]["location"]["lng"],
    )

    # Googleマップリンクを生成
    google_maps_link = f"https://www.google.com/maps/place/?q=place_id:{place_id}"

    data_list.append(
        {
            "店舗名": place["name"],
            "住所": address,
            "評価": place.get("rating", "N/A"),
            "口コミ数": details["口コミ数"],
            "ウェブサイト": details["ウェブサイト"],
            "距離（km）": round(distance, 2),
            "Googleマップリンク": google_maps_link,  # Googleマップのリンク
        }
    )

# 📌 距離順に並び替え
df = pd.DataFrame(data_list)
df_sorted = df.sort_values(by="距離（km）", ascending=True)

# 📌 検索結果をExcelに出力
output_file = "indoor_golf_sorted.xlsx"
df_sorted.to_excel(output_file, index=False, engine="openpyxl")

print(f"🎯 {len(places)} 件のインドアゴルフ店舗を取得し、距離順に並び替えました！")
print(f"📂 結果を {output_file} に保存しました！")
