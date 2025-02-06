import os
import time
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup


def is_valid_url(url):
    """URLの形式が正しいかチェックする関数"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def crawl_website(root_url):
    """
    指定したルートURL以下の内部ページを再帰的にクロールし、
    各ページのURL、タイトル、及びInstagramリンクを取得する関数
    """
    visited = set()      # 訪問済みURLのセット
    pages = []           # 各ページの情報を格納するリスト
    to_visit = [root_url]  # クロール対象のURLリスト

    # ルートURLのドメイン情報を取得
    parsed_root = urlparse(root_url)
    base_netloc = parsed_root.netloc

    while to_visit:
        current_url = to_visit.pop(0)
        if current_url in visited:
            continue
        visited.add(current_url)
        print(f"Visiting: {current_url}")

        try:
            response = requests.get(current_url, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print(f"Error fetching {current_url}: {e}")
            continue

        soup = BeautifulSoup(response.text, 'html.parser')

        # ページタイトルの取得
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        # Instagramリンクを収集（重複除去のため set で管理）
        instagram_links = set()

        # ページ内のすべての<a>タグからリンクを抽出
        for a_tag in soup.find_all("a"):
            href = a_tag.get("href")
            if not href:
                continue

            # 相対パスの場合は絶対URLに変換
            absolute_href = urljoin(current_url, href)
            parsed_href = urlparse(absolute_href)
            # URLのパラメーターやフラグメントは除去
            clean_href = f"{parsed_href.scheme}://{parsed_href.netloc}{parsed_href.path}"

            # Instagramリンクの場合は専用に追加
            if "instagram.com" in parsed_href.netloc:
                instagram_links.add(clean_href)
            else:
                # 内部リンクの場合、ルートと同じドメインならクロール対象に追加
                if parsed_href.netloc == base_netloc:
                    if clean_href not in visited and clean_href not in to_visit:
                        to_visit.append(clean_href)
        # 現在のページ情報をリストに追加
        pages.append({
            "PageURL": current_url,
            "Title": title,
            "Instagram": ", ".join(instagram_links)
        })
        # サーバー負荷低減のため1秒待機
        time.sleep(1)
    return pages

def save_pages_to_excel(pages, filename):
    """ページ情報のリストをExcelファイルに出力する関数"""
    df = pd.DataFrame(pages)
    df.to_excel(filename, index=False)
    print(f"Saved {len(pages)} records to {filename}")

if __name__ == "__main__":
    # srcフォルダ内のスクリプトのディレクトリを取得
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 親ディレクトリ内の data フォルダ内の Excel ファイルのパスを構築
    input_file = os.path.join(script_dir, "..", "data", "indoor_golf_places_sorted.xlsx")
    
    try:
        stores_df = pd.read_excel(input_file)
        print(f"Excelファイルの読み込みに成功しました: {input_file}")
    except Exception as e:
        print(f"Excelファイルの読み込みエラー: {e}")
        exit(1)
    
    # Excelファイルが空でないか確認
    if stores_df.empty:
        print("Excelファイルに店舗データがありません。")
        exit(1)

    # 取得する店舗データの開始位置（1-indexed）と件数をユーザーに入力してもらう
    try:
        start_index = int(input("取得開始店舗番号（1からの番号、例：3）: "))
        count = int(input("取得する店舗件数（例：5）: "))
    except Exception as e:
        print(f"入力エラー: {e}")
        exit(1)

    # 1-indexed なので、Pythonの0-indexに変換
    start_idx = start_index - 1
    end_idx = start_idx + count

    # 指定された範囲の店舗データを取得（ilocは0-indexed）
    selected_stores_df = stores_df.iloc[start_idx:end_idx]
    print(f"店舗データ {start_index} 番目から {start_index + count - 1} 番目を処理します。")

    all_results = []
    # 各店舗の「ウェブサイト」URLに対してクローラーを実行
    for idx, row in selected_stores_df.iterrows():
        store_name = row.get("店舗名", "")
        website_url = row.get("ウェブサイト", "")
        # ウェブサイトURLが空、または「なし」や「エラー」ならスキップ
        if pd.isna(website_url) or website_url in ["なし", "エラー", ""]:
            print(f"店舗 '{store_name}' はウェブサイト情報が無いためスキップします。")
            continue
        if not is_valid_url(website_url):
            print(f"店舗 '{store_name}' のウェブサイトURLが無効です: {website_url}")
            continue

        print(f"Processing 店舗: {store_name} | URL: {website_url}")
        pages = crawl_website(website_url)
        # 各ページ情報に店舗情報を追加して結果リストにまとめる
        for page in pages:
            result = {
                "店舗名": store_name,
                "StoreURL": website_url,
                "PageURL": page.get("PageURL", ""),
                "Title": page.get("Title", ""),
                "Instagram": page.get("Instagram", "")
            }
            all_results.append(result)
    
    # 出力ファイルのパスを、親ディレクトリ内の data フォルダに設定
    output_file = os.path.join(script_dir, "..", "data", "crawled_indoor_golf_websites.xlsx")
    save_pages_to_excel(all_results, output_file)
